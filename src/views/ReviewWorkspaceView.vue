<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import MarkdownArticle from "../components/MarkdownArticle.vue";
import ReviewStageTracker from "../components/ReviewStageTracker.vue";
import StageFindingsPanel from "../components/StageFindingsPanel.vue";
import {
  buildReviewDigest,
  countAnchorsByType,
  fetchRunState,
  fetchStageRecord,
  getAnchorCount,
  getPageCount,
  getPaperMeta,
  triggerStageExecution
} from "../services/api";
import {
  clearSession,
  reviewSession,
  setCurrentStage,
  setRunState,
  setShowImages,
  setStageReview,
  setWorkflowSummary
} from "../stores/reviewSession";

const router = useRouter();

const POLL_INTERVAL_MS = 15000;
const REVIEW_STAGE_ORDER = ["format", "logic", "innovation"];
const FINAL_STAGE_STATUSES = new Set([
  "complete",
  "completed",
  "skipped",
  "failed",
  "aborted"
]);

const loadingStage = ref("");
const actionInFlight = ref("");
const decisionInFlight = ref("");
const errorMessage = ref("");
const pageMessage = ref("");
const pollingStage = ref("");
const stagePollInFlight = ref(false);
const displayedStageStatuses = ref({
  format: "",
  logic: "",
  innovation: "",
  summary: ""
});

let stagePollTimer = 0;

const stageMetaMap = {
  format: {
    kicker: "阶段一",
    title: "格式审查"
  },
  logic: {
    kicker: "阶段二",
    title: "逻辑审查"
  },
  innovation: {
    kicker: "阶段三",
    title: "创新性审查"
  }
};

const submission = computed(() => reviewSession.currentSubmission);
const runRecord = computed(() => reviewSession.runRecord);
const runState = computed(() => reviewSession.runState);
const paperMeta = computed(() => getPaperMeta(submission.value));
const stageReviews = computed(() => reviewSession.workflow.reviews);
const currentStageDisplayed = computed(
  () => reviewSession.workflow.currentStageDisplayed ?? reviewSession.workflow.currentStage
);

const showImages = computed({
  get: () => reviewSession.preferences.showImages,
  set: (value) => setShowImages(value)
});

const pageCount = computed(() => getPageCount(paperMeta.value));
const anchorCount = computed(() => getAnchorCount(paperMeta.value));
const figureCount = computed(() => countAnchorsByType(paperMeta.value, "figure"));
const tableCount = computed(() => countAnchorsByType(paperMeta.value, "table"));
const runReady = computed(() => Boolean(runRecord.value?.runId));

const lastCompletedStage = computed(() => {
  if (stageReviews.value.innovation) {
    return "innovation";
  }

  if (stageReviews.value.logic) {
    return "logic";
  }

  return "format";
});

const visibleStage = computed(() =>
  currentStageDisplayed.value === "summary"
    ? lastCompletedStage.value
    : currentStageDisplayed.value
);

const activeStageMeta = computed(
  () => stageMetaMap[visibleStage.value] ?? stageMetaMap.format
);

const activeStageResult = computed(
  () => stageReviews.value[visibleStage.value] ?? null
);

const visibleStageStatus = computed(
  () =>
    displayedStageStatuses.value[visibleStage.value] ||
    runState.value?.stageRuns?.find((item) => item.stageName === visibleStage.value)
      ?.status ||
    ""
);

const stagePanelLoading = computed(
  () =>
    loadingStage.value === visibleStage.value || pollingStage.value === visibleStage.value
);

const stateCompleted = computed(() =>
  ["complete", "completed"].includes(runState.value?.status ?? "")
);

const statusText = computed(() => {
  if (visibleStageStatus.value) {
    return visibleStageStatus.value;
  }

  if (!runState.value) {
    return "";
  }

  return runState.value.status;
});

const decisionActions = computed(() => {
  if (
    !activeStageResult.value ||
    stagePanelLoading.value ||
    actionInFlight.value ||
    decisionInFlight.value ||
    ["failed", "aborted"].includes(runState.value?.status ?? "") ||
    visibleStage.value === "summary"
  ) {
    return [];
  }

  return [
    {
      key: "jump_summary",
      label: "跳过后续审查阶段",
      variant: "ghost",
      disabled: false
    },
    {
      key: "skip",
      label: "跳过下一阶段审查",
      variant: "secondary",
      disabled: stateCompleted.value
    },
    {
      key: "continue",
      label: "继续下一阶段审查",
      variant: "primary",
      disabled: stateCompleted.value
    }
  ];
});

const footerAction = computed(() => {
  if (
    !runReady.value ||
    visibleStage.value === "summary" ||
    activeStageResult.value ||
    stagePanelLoading.value ||
    actionInFlight.value ||
    decisionInFlight.value ||
    ["failed", "aborted"].includes(runState.value?.status ?? "")
  ) {
    return null;
  }

  const visibleStatus = visibleStageStatus.value || "";
  const nextStage = runState.value?.nextStage ?? "";
  const allowedActions = Array.isArray(runState.value?.allowedActions)
    ? runState.value.allowedActions
    : [];
  const allowedStatuses = ["", "pending", "created"];
  const canContinue = allowedActions.length === 0 || allowedActions.includes("continue");

  if (!canContinue || !allowedStatuses.includes(visibleStatus)) {
    return null;
  }

  if (nextStage && nextStage !== visibleStage.value) {
    return null;
  }

  return {
    label:
      visibleStage.value === "format"
        ? "开始第一阶段审查"
        : `开始${activeStageMeta.value.title}`,
    disabled: false
  };
});

function refreshSummarySnapshot() {
  setWorkflowSummary(
    buildReviewDigest({
      formatReview: stageReviews.value.format,
      logicReview: stageReviews.value.logic,
      innovationReview: stageReviews.value.innovation
    })
  );
}

function isFinalStageStatus(status) {
  return FINAL_STAGE_STATUSES.has(status ?? "");
}

function hasObjectContent(value) {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value)
    ? Object.keys(value).length > 0
    : false;
}

function hasDisplayableStageSnapshot(snapshot) {
  if (!snapshot) {
    return false;
  }

  if (snapshot.review) {
    return true;
  }

  if (snapshot.stageStatus === "skipped") {
    return true;
  }

  return hasObjectContent(snapshot.stageOutput);
}

function hasFinalizedStageSnapshot(snapshot) {
  if (!snapshot) {
    return false;
  }

  if (snapshot.stageStatus === "skipped") {
    return true;
  }

  if (snapshot.review) {
    return isFinalStageStatus(snapshot.stageStatus || "completed");
  }

  return isFinalStageStatus(snapshot.stageStatus);
}

function getStateStageStatus(state, stageKey) {
  return (
    state?.stageRuns?.find((item) => item.stageName === stageKey)?.status ?? ""
  );
}

function getNextReviewStage(stageKey) {
  const index = REVIEW_STAGE_ORDER.indexOf(stageKey);

  if (index === -1 || index === REVIEW_STAGE_ORDER.length - 1) {
    return "summary";
  }

  return REVIEW_STAGE_ORDER[index + 1];
}

function setDisplayedStageStatus(stageKey, status = "") {
  if (!stageKey) {
    return;
  }

  displayedStageStatuses.value = {
    ...displayedStageStatuses.value,
    [stageKey]: status
  };
}

async function syncRunState() {
  if (!runRecord.value?.runId) {
    return null;
  }

  const nextState = await fetchRunState(runRecord.value.runId);
  setRunState(nextState);
  return nextState;
}

function stopStagePolling() {
  if (stagePollTimer) {
    window.clearInterval(stagePollTimer);
    stagePollTimer = 0;
  }
}

function startStagePolling() {
  stopStagePolling();
  stagePollTimer = window.setInterval(() => {
    void tickStagePolling();
  }, POLL_INTERVAL_MS);
}

function applyStageSnapshot(stageKey, snapshot) {
  setDisplayedStageStatus(stageKey, snapshot.stageStatus);

  if (snapshot.review && stageKey in stageReviews.value) {
    setStageReview(stageKey, snapshot.review);
    refreshSummarySnapshot();
  }
}

async function tryFetchStageSnapshot(stageKey) {
  try {
    const snapshot = await fetchStageRecord({
      runId: runRecord.value.runId,
      stageName: stageKey
    });

    applyStageSnapshot(stageKey, snapshot);

    return {
      snapshot,
      stageNotReady: false,
      displayable: hasDisplayableStageSnapshot(snapshot),
      finalized: hasFinalizedStageSnapshot(snapshot)
    };
  } catch (error) {
    if (error?.code === "STAGE_NOT_READY") {
      return {
        snapshot: null,
        stageNotReady: true,
        displayable: false,
        finalized: false
      };
    }

    throw error;
  }
}

async function tickStagePolling() {
  const stageKey = pollingStage.value;

  if (!stageKey || !runRecord.value?.runId || stagePollInFlight.value) {
    return;
  }

  stagePollInFlight.value = true;

  try {
    const result = await tryFetchStageSnapshot(stageKey);

    if (result.stageNotReady) {
      return;
    }

    if (result.finalized) {
      pollingStage.value = "";
      await syncRunState();
      return;
    }

    if (result.displayable) {
      return;
    }

    if (result.snapshot && isFinalStageStatus(result.snapshot.stageStatus)) {
      pollingStage.value = "";
      await syncRunState();
    }
  } catch (error) {
    errorMessage.value =
      error instanceof Error ? error.message : "阶段结果轮询失败";
  } finally {
    stagePollInFlight.value = false;
  }
}

async function triggerStage(stageKey, action = "continue") {
  if (!runRecord.value?.runId) {
    return;
  }

  errorMessage.value = "";
  pageMessage.value = "";
  actionInFlight.value = action;
  loadingStage.value = stageKey;

  try {
    await triggerStageExecution({
      runId: runRecord.value.runId,
      stageName: stageKey,
      action
    });

    setDisplayedStageStatus(stageKey, "running");
    pollingStage.value = stageKey;
    void tickStagePolling();
  } catch (error) {
    if (error?.code === "STAGE_NOT_READY") {
      const latestState = await syncRunState();
      const stageStatus = getStateStageStatus(latestState, stageKey);

      setDisplayedStageStatus(stageKey, stageStatus);
      pollingStage.value = stageKey;
      pageMessage.value = "当前阶段尚未就绪，继续等待阶段快照。";
      void tickStagePolling();
      return;
    }

    errorMessage.value =
      error instanceof Error ? error.message : "阶段触发失败";
  } finally {
    loadingStage.value = "";
    actionInFlight.value = "";
  }
}

async function ensureDisplayedStage(stageKey, { autoStart = false, action = "continue" } = {}) {
  if (!runRecord.value?.runId || !stageKey || stageKey === "summary") {
    return;
  }

  if (stageReviews.value[stageKey]) {
    setDisplayedStageStatus(
      stageKey,
      stageReviews.value[stageKey]?.stageStatus ?? "completed"
    );
    await syncRunState();
    return;
  }

  const latestState = await syncRunState();
  const stateStageStatus = getStateStageStatus(latestState, stageKey);

  if (stateStageStatus) {
    setDisplayedStageStatus(stageKey, stateStageStatus);
  }

  const snapshotResult = await tryFetchStageSnapshot(stageKey);

  if (snapshotResult.finalized) {
    await syncRunState();
    return;
  }

  if (
    snapshotResult.stageNotReady ||
    snapshotResult.displayable ||
    ["running", "in_progress", "waiting"].includes(stateStageStatus)
  ) {
    pollingStage.value = stageKey;
    void tickStagePolling();
    return;
  }

  if (
    autoStart &&
    (latestState?.nextStage === stageKey ||
      ["pending", "created", ""].includes(stateStageStatus))
  ) {
    await triggerStage(stageKey, action);
  }
}

async function openStage(stageKey, action = "continue") {
  if (!stageKey || stageKey === "summary") {
    setCurrentStage("summary");
    await router.push({ name: "summary" });
    return;
  }

  setCurrentStage(stageKey);
  await ensureDisplayedStage(stageKey, {
    autoStart: true,
    action
  });
}

async function handleDecisionAction(action) {
  if (!activeStageResult.value || !runRecord.value?.runId) {
    return;
  }

  errorMessage.value = "";
  pageMessage.value = "";
  decisionInFlight.value = action;

  try {
    if (action === "jump_summary") {
      pageMessage.value = "正在进入汇总阶段。";
      await openStage("summary");
      return;
    }

    const nextStage = getNextReviewStage(currentStageDisplayed.value);

    if (!nextStage || nextStage === "summary") {
      pageMessage.value = "正在进入汇总阶段。";
      await openStage("summary");
      return;
    }

    if (action === "skip") {
      pageMessage.value = `正在跳过${stageMetaMap[nextStage]?.title ?? nextStage}。`;
      await openStage(nextStage, "skip");
      return;
    }

    pageMessage.value = `正在进入${stageMetaMap[nextStage]?.title ?? nextStage}。`;
    await openStage(nextStage, "continue");
  } catch (error) {
    errorMessage.value =
      error instanceof Error ? error.message : "阶段切换失败";
  } finally {
    decisionInFlight.value = "";
  }
}

async function handleFooterAction() {
  if (!visibleStage.value || visibleStage.value === "summary") {
    return;
  }

  errorMessage.value = "";
  pageMessage.value = `正在启动${activeStageMeta.value.title}。`;
  await triggerStage(visibleStage.value, "continue");
}

function restartReview() {
  clearSession();
  router.push({ name: "upload" });
}

onMounted(async () => {
  if (!submission.value || !runRecord.value?.runId) {
    router.replace({ name: "upload" });
    return;
  }

  const initialStage =
    currentStageDisplayed.value && currentStageDisplayed.value !== "summary"
      ? currentStageDisplayed.value
      : "format";

  setCurrentStage(initialStage);
  startStagePolling();
  await ensureDisplayedStage(initialStage, {
    autoStart: false,
    action: "continue"
  });
});

onBeforeUnmount(() => {
  stopStagePolling();
});
</script>

<template>
  <section v-if="submission" class="workspace-layout">
    <header class="workspace-hero glass-card">
      <div class="hero-top">
        <div class="hero-copy">
          <p class="summary-kicker">分阶段审查工作区</p>
          <h1 class="section-title">按阶段快照驱动的审查流程</h1>
          <p class="section-subtitle hero-subtitle">
            当前页面展示哪个阶段，就只请求哪个 `GET /runs/{run_id}/stages/{stage_name}`。
            `GET /state` 只在拿到阶段结果后用来更新整体 workflow 状态和按钮可用性。
          </p>
        </div>

        <div class="hero-actions">
          <span class="pill" :class="runReady ? 'pill-success' : 'pill-neutral'">
            {{ runReady ? `run_id: ${runRecord.runId}` : "run 未就绪" }}
          </span>
          <button class="ghost-button" type="button" @click="restartReview">
            重新上传论文
          </button>
        </div>
      </div>

      <div class="hero-pills">
        <span class="pill pill-primary">{{ submission.paperName }}</span>
        <span class="pill pill-neutral">页数 {{ pageCount }}</span>
        <span class="pill pill-neutral">锚点 {{ anchorCount }}</span>
        <span class="pill pill-neutral">图 {{ figureCount }}</span>
        <span class="pill pill-neutral">表 {{ tableCount }}</span>
        <span class="pill pill-neutral">来源 {{ submission.sourceMode }}</span>
      </div>
    </header>

    <ReviewStageTracker
      :active-stage="currentStageDisplayed"
      :reviews="stageReviews"
      :run-state="runState"
      :summary-ready="Boolean(reviewSession.workflow.summary)"
    />

    <div v-if="pageMessage" class="success-banner">{{ pageMessage }}</div>
    <div v-if="errorMessage" class="error-banner">{{ errorMessage }}</div>

    <section class="stage-layout">
      <section class="paper-panel glass-card">
        <div class="column-head">
          <div>
            <p class="summary-kicker">论文正文</p>
            <h2 class="section-title">解析后的 Markdown 论文</h2>
          </div>

          <label class="toggle-field">
            <input v-model="showImages" type="checkbox" />
            <span>显示图像</span>
          </label>
        </div>

        <div class="meta-row">
          <span class="pill pill-primary">
            doc_id: {{ paperMeta?.doc_id || "unknown" }}
          </span>
          <span class="pill pill-neutral">
            当前查看: {{ activeStageMeta.title }}
          </span>
          <span v-if="runState" class="pill pill-neutral">
            next_stage: {{ runState.nextStage }}
          </span>
        </div>

        <div class="panel-scroll article-scroll">
          <MarkdownArticle
            :markdown="submission.paperMarkdown"
            :show-images="showImages"
            :asset-base="submission.paperAssetBase"
          />
        </div>
      </section>

      <StageFindingsPanel
        :kicker="activeStageMeta.kicker"
        :title="activeStageMeta.title"
        :result="activeStageResult"
        :loading="stagePanelLoading"
        :actions="decisionActions"
        :footer-action="footerAction"
        :status-text="statusText"
        @action="handleDecisionAction"
        @footer="handleFooterAction"
      />
    </section>
  </section>
</template>

<style scoped>
.workspace-layout {
  --workspace-panel-height: clamp(750px, calc((100vh - 380px) * 1.5), 1050px);
  display: grid;
  gap: 18px;
}

.workspace-hero,
.paper-panel {
  padding: 24px;
}

.workspace-hero {
  display: grid;
  gap: 18px;
}

.hero-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
}

.hero-copy {
  display: grid;
  gap: 8px;
}

.hero-subtitle {
  max-width: 760px;
}

.hero-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.summary-kicker {
  margin: 0 0 6px;
  font-size: 12px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--muted);
}

.hero-pills,
.meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.success-banner,
.error-banner {
  padding: 13px 14px;
  border-radius: 14px;
}

.success-banner {
  background: rgba(46, 125, 92, 0.12);
  border: 1px solid rgba(46, 125, 92, 0.18);
  color: var(--success);
}

.error-banner {
  background: rgba(192, 86, 33, 0.12);
  border: 1px solid rgba(192, 86, 33, 0.18);
  color: var(--danger);
}

.stage-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.12fr) minmax(360px, 0.88fr);
  gap: 18px;
  align-items: stretch;
}

.paper-panel {
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr);
  gap: 18px;
  min-height: var(--workspace-panel-height);
  max-height: var(--workspace-panel-height);
}

.column-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.toggle-field {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 999px;
  background: rgba(19, 63, 103, 0.08);
  color: var(--primary);
  font-weight: 700;
}

.panel-scroll {
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 6px;
}

.article-scroll {
  height: 100%;
  max-height: none;
}

@media (max-width: 1240px) {
  .stage-layout {
    grid-template-columns: 1fr;
  }

  .paper-panel,
  .article-scroll {
    min-height: auto;
    max-height: none;
  }
}

@media (max-width: 720px) {
  .hero-top,
  .column-head {
    flex-direction: column;
  }

  .hero-actions {
    justify-content: flex-start;
  }
}
</style>
