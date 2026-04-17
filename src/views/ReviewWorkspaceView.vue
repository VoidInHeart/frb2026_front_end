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
const FINAL_STAGE_STATUSES = new Set(["completed", "skipped", "failed", "aborted"]);

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
    title: "方法与创新点审查"
  }
};

const submission = computed(() => reviewSession.currentSubmission);
const runRecord = computed(() => reviewSession.runRecord);
const runState = computed(() => reviewSession.runState);
const paperMeta = computed(() => getPaperMeta(submission.value));
const stageReviews = computed(() => reviewSession.workflow.reviews);
const currentStageDisplayed = computed(
  () =>
    reviewSession.workflow.currentStageDisplayed ?? reviewSession.workflow.currentStage
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

const statusText = computed(() => {
  if (visibleStageStatus.value) {
    return visibleStageStatus.value;
  }

  if (!runState.value) {
    return "";
  }

  if (runState.value.status === "waiting") {
    return `waiting -> ${runState.value.nextStage}`;
  }

  return runState.value.status;
});

const decisionActions = computed(() => {
  if (
    !activeStageResult.value ||
    loadingStage.value ||
    actionInFlight.value ||
    decisionInFlight.value ||
    ["failed", "aborted"].includes(runState.value?.status ?? "") ||
    currentStageDisplayed.value === "summary"
  ) {
    return [];
  }

  return [
    {
      key: "abort",
      label: "跳过后续阶段审查",
      variant: "ghost",
      disabled: false
    },
    {
      key: "skip",
      label: "跳过下一阶段审查",
      variant: "secondary",
      disabled: false
    },
    {
      key: "continue",
      label: "继续下一阶段审查",
      variant: "primary",
      disabled: false
    }
  ];
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

function setDisplayedStageStatus(stageKey, status = "") {
  if (!stageKey) {
    return;
  }

  displayedStageStatuses.value = {
    ...displayedStageStatuses.value,
    [stageKey]: status
  };
}

function getSequentialNextStage(stageKey) {
  if (stageKey === "format") {
    return "logic";
  }

  if (stageKey === "logic") {
    return "innovation";
  }

  return "summary";
}

function resolveUpcomingStage(state = runState.value, fallbackStage = visibleStage.value) {
  const nextStage = state?.nextStage;

  if (nextStage && nextStage !== fallbackStage) {
    return nextStage;
  }

  return getSequentialNextStage(fallbackStage);
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

async function loadStageSnapshot(stageKey) {
  if (!runRecord.value?.runId) {
    return null;
  }

  const snapshot = await fetchStageRecord({
    runId: runRecord.value.runId,
    stageName: stageKey
  });

  setDisplayedStageStatus(stageKey, snapshot.stageStatus);

  if (snapshot.review && stageKey in stageReviews.value) {
    setStageReview(stageKey, snapshot.review);
    refreshSummarySnapshot();
  }

  return snapshot;
}

async function tickStagePolling() {
  const stageKey = pollingStage.value;

  if (!stageKey || !runRecord.value?.runId || stagePollInFlight.value) {
    return;
  }

  stagePollInFlight.value = true;

  try {
    const snapshot = await loadStageSnapshot(stageKey);

    if (!snapshot) {
      return;
    }

    if (FINAL_STAGE_STATUSES.has(snapshot.stageStatus)) {
      if (pollingStage.value === stageKey) {
        pollingStage.value = "";
      }

      if (["failed", "aborted"].includes(snapshot.stageStatus)) {
        await syncRunState();
      }
    }
  } catch (error) {
    errorMessage.value =
      error instanceof Error ? error.message : "阶段结果轮询失败";
  } finally {
    stagePollInFlight.value = false;
  }
}

async function ensureStageReady(stageKey) {
  if (stageReviews.value[stageKey]) {
    setDisplayedStageStatus(
      stageKey,
      stageReviews.value[stageKey]?.stageStatus ?? "completed"
    );
    return stageReviews.value[stageKey];
  }

  const latestState = await syncRunState();
  const stageStatus =
    latestState?.stageRuns?.find((item) => item.stageName === stageKey)?.status ?? "";

  setDisplayedStageStatus(stageKey, stageStatus);

  if (["completed", "skipped"].includes(stageStatus)) {
    const snapshot = await loadStageSnapshot(stageKey);
    return snapshot?.review ?? null;
  }

  if (["running", "in_progress", "waiting"].includes(stageStatus)) {
    pollingStage.value = stageKey;
    return null;
  }

  if (
    latestState?.nextStage === stageKey &&
    !["failed", "aborted", "completed"].includes(latestState.status)
  ) {
    return performStageAction("continue", stageKey);
  }

  return null;
}

async function performStageAction(action, stageKey = visibleStage.value) {
  if (!runRecord.value?.runId) {
    return null;
  }

  errorMessage.value = "";
  pageMessage.value = "";
  actionInFlight.value = action;
  loadingStage.value = stageKey;

  try {
    const immediateResult = await triggerStageExecution({
      runId: runRecord.value.runId,
      stageName: stageKey,
      action
    });
    const latestState = await syncRunState();
    const stageStatus =
      latestState?.stageRuns?.find((item) => item.stageName === stageKey)?.status ?? "";

    setDisplayedStageStatus(
      stageKey,
      immediateResult?.stageStatus ?? stageStatus
    );

    if (action === "abort") {
      if (pollingStage.value === stageKey) {
        pollingStage.value = "";
      }
      pageMessage.value = "当前 run 已终止。";
      return null;
    }

    let result = immediateResult;

    if (!result && FINAL_STAGE_STATUSES.has(stageStatus)) {
      const snapshot = await loadStageSnapshot(stageKey);
      result = snapshot?.review ?? null;
    }

    if (result) {
      if (pollingStage.value === stageKey) {
        pollingStage.value = "";
      }
      setStageReview(stageKey, result);
      refreshSummarySnapshot();
      pageMessage.value =
        result.stageStatus === "skipped"
          ? `${result.stageLabel}已跳过。`
          : `${result.stageLabel}已完成。`;
    } else if (["pending", "running", "in_progress", "waiting"].includes(stageStatus)) {
      pollingStage.value = stageKey;
    } else if (pollingStage.value === stageKey) {
      pollingStage.value = "";
    }

    return result;
  } catch (error) {
    if (error?.code === "STAGE_NOT_READY") {
      const latestState = await syncRunState();
      const stageStatus =
        latestState?.stageRuns?.find((item) => item.stageName === stageKey)?.status ?? "";

      setDisplayedStageStatus(stageKey, stageStatus);
      if (["running", "in_progress", "waiting"].includes(stageStatus)) {
        pollingStage.value = stageKey;
      }
      pageMessage.value = "当前阶段尚未就绪，已同步最新 workflow state。";
      return null;
    }

    errorMessage.value =
      error instanceof Error ? error.message : "阶段结果加载失败";
    return null;
  } finally {
    loadingStage.value = "";
    actionInFlight.value = "";
  }
}

async function openStage(stageKey) {
  if (!stageKey || stageKey === "summary") {
    setCurrentStage("summary");
    refreshSummarySnapshot();
    await router.push({ name: "summary" });
    return;
  }

  setCurrentStage(stageKey);
  await ensureStageReady(stageKey);
}

async function handleDecisionAction(action) {
  if (!activeStageResult.value || !runRecord.value?.runId) {
    return;
  }

  errorMessage.value = "";
  pageMessage.value = "";
  decisionInFlight.value = action;

  try {
    let latestState = await syncRunState();
    const upcomingStage = resolveUpcomingStage(latestState);

    if (action === "abort") {
      if (upcomingStage && upcomingStage !== "summary") {
        await triggerStageExecution({
          runId: runRecord.value.runId,
          stageName: upcomingStage,
          action: "abort"
        });
        latestState = await syncRunState();
      }

      pageMessage.value = "已跳过后续阶段审查，正在进入汇总。";
      await openStage("summary");
      return;
    }

    if (action === "skip") {
      if (!upcomingStage || upcomingStage === "summary") {
        pageMessage.value = "下一步已收束到汇总。";
        await openStage("summary");
        return;
      }

      await performStageAction("skip", upcomingStage);
      latestState = await syncRunState();

      const targetStage = resolveUpcomingStage(latestState, upcomingStage);

      if (!targetStage || targetStage === "summary") {
        pageMessage.value = "已跳过下一阶段审查，正在进入汇总。";
        await openStage("summary");
        return;
      }

      pageMessage.value = `已跳过${stageMetaMap[upcomingStage]?.title ?? upcomingStage}，正在进入下一阶段。`;
      await openStage(targetStage);
      return;
    }

    if (!upcomingStage || upcomingStage === "summary") {
      pageMessage.value = "正在进入汇总。";
      await openStage("summary");
      return;
    }

    pageMessage.value = `正在进入${stageMetaMap[upcomingStage]?.title ?? upcomingStage}。`;
    await openStage(upcomingStage);
  } catch (error) {
    errorMessage.value =
      error instanceof Error ? error.message : "阶段决策执行失败";
  } finally {
    decisionInFlight.value = "";
  }
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

  const latestState = await syncRunState();
  const nextStage =
    latestState?.nextStage ?? currentStageDisplayed.value ?? reviewSession.workflow.currentStage ?? "format";

  if (currentStageDisplayed.value !== "summary") {
    setCurrentStage(nextStage);
  }

  startStagePolling();
  await ensureStageReady(visibleStage.value);

  if (pollingStage.value) {
    void tickStagePolling();
  }
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
          <h1 class="section-title">统一 run/state/stage 协议工作流</h1>
          <p class="section-subtitle hero-subtitle">
            `state` 只负责描述 workflow 指针和允许动作；当前页面真正展示的阶段结果，统一从阶段快照接口读取。
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
        :status-text="statusText"
        @action="handleDecisionAction"
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
