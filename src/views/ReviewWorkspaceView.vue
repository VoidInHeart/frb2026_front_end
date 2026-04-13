<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import MarkdownArticle from "../components/MarkdownArticle.vue";
import ReviewStageTracker from "../components/ReviewStageTracker.vue";
import StageFindingsPanel from "../components/StageFindingsPanel.vue";
import {
  buildReviewDigest,
  countAnchorsByType,
  fetchRunState,
  fetchStageSnapshot,
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

const loadingStage = ref("");
const actionInFlight = ref("");
const errorMessage = ref("");
const pageMessage = ref("");

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
  reviewSession.workflow.currentStage === "summary"
    ? lastCompletedStage.value
    : reviewSession.workflow.currentStage
);

const activeStageMeta = computed(
  () => stageMetaMap[visibleStage.value] ?? stageMetaMap.format
);

const activeStageResult = computed(
  () => stageReviews.value[visibleStage.value] ?? null
);

const visibleStageStatus = computed(
  () =>
    runState.value?.stageRuns?.find((item) => item.stageName === visibleStage.value)
      ?.status ?? ""
);

const statusText = computed(() => {
  if (!runState.value) {
    return "";
  }

  if (runState.value.status === "waiting") {
    return `waiting · ${runState.value.nextStage}`;
  }

  return visibleStageStatus.value || runState.value.status;
});

const controlActions = computed(() => {
  if (loadingStage.value || actionInFlight.value || activeStageResult.value) {
    return [];
  }

  if (!runState.value || runState.value.nextStage !== visibleStage.value) {
    return [];
  }

  const allowedActions = runState.value.allowedActions?.length
    ? runState.value.allowedActions
    : ["continue"];

  return allowedActions.map((action) => ({
    key: action,
    label:
      action === "continue"
        ? "开始本阶段"
        : action === "skip"
          ? "跳过阶段"
          : "终止 run",
    variant:
      action === "continue"
        ? "primary"
        : action === "skip"
          ? "secondary"
          : "ghost",
    disabled: false
  }));
});

const footerAction = computed(() => {
  if (!activeStageResult.value) {
    return null;
  }

  if (["failed", "aborted"].includes(runState.value?.status ?? "")) {
    return null;
  }

  const nextStage = runState.value?.nextStage;
  const shouldGoSummary =
    nextStage === "summary" ||
    visibleStage.value === "innovation" ||
    activeStageResult.value.severe;

  return {
    label: shouldGoSummary ? "进入汇总页面" : "进入下一阶段",
    disabled: Boolean(loadingStage.value || actionInFlight.value)
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

function wait(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

async function syncRunState() {
  if (!runRecord.value?.runId) {
    return null;
  }

  const nextState = await fetchRunState(runRecord.value.runId);
  setRunState(nextState);
  return nextState;
}

async function loadStageSnapshot(stageKey) {
  if (!runRecord.value?.runId) {
    return null;
  }

  const result = await fetchStageSnapshot({
    runId: runRecord.value.runId,
    stageName: stageKey
  });

  if (stageKey in stageReviews.value) {
    setStageReview(stageKey, result);
    refreshSummarySnapshot();
  }

  return result;
}

async function pollStageUntilSettled(stageKey) {
  for (let attempt = 0; attempt < 20; attempt += 1) {
    await wait(900);
    const latestState = await syncRunState();
    const stageStatus =
      latestState?.stageRuns?.find((item) => item.stageName === stageKey)?.status ?? "";

    if (["completed", "skipped"].includes(stageStatus)) {
      return loadStageSnapshot(stageKey);
    }

    if (
      ["failed", "aborted"].includes(stageStatus) ||
      ["failed", "aborted"].includes(latestState?.status ?? "")
    ) {
      return null;
    }
  }

  return null;
}

async function ensureStageReady(stageKey) {
  if (stageReviews.value[stageKey]) {
    return stageReviews.value[stageKey];
  }

  const latestState = await syncRunState();
  const stageStatus =
    latestState?.stageRuns?.find((item) => item.stageName === stageKey)?.status ?? "";

  if (["completed", "skipped"].includes(stageStatus)) {
    return loadStageSnapshot(stageKey);
  }

  if (stageStatus === "running") {
    return pollStageUntilSettled(stageKey);
  }

  if (
    latestState?.nextStage === stageKey &&
    !["waiting", "failed", "aborted", "completed"].includes(latestState.status)
  ) {
    return handleStageAction("continue", stageKey);
  }

  return null;
}

async function handleStageAction(action, stageKey = visibleStage.value) {
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

    if (action === "abort") {
      pageMessage.value = "当前 run 已终止。";
      return null;
    }

    let result = immediateResult;
    const stageStatus =
      latestState?.stageRuns?.find((item) => item.stageName === stageKey)?.status ?? "";

    if (!result && ["completed", "skipped"].includes(stageStatus)) {
      result = await loadStageSnapshot(stageKey);
    }

    if (!result && stageStatus === "running") {
      result = await pollStageUntilSettled(stageKey);
    }

    if (result) {
      setStageReview(stageKey, result);
      refreshSummarySnapshot();
      pageMessage.value =
        result.stageStatus === "skipped"
          ? `${result.stageLabel}已跳过。`
          : `${result.stageLabel}已完成。`;
    }

    return result;
  } catch (error) {
    if (error?.code === "STAGE_NOT_READY") {
      await syncRunState();
      pageMessage.value = "当前阶段尚未就绪，已同步最新 run state。";
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

async function handleFooterAction() {
  const result = activeStageResult.value ?? (await ensureStageReady(visibleStage.value));

  if (!result) {
    return;
  }

  const nextStage = runState.value?.nextStage;
  const shouldGoSummary =
    nextStage === "summary" ||
    visibleStage.value === "innovation" ||
    result.severe;

  if (shouldGoSummary) {
    setCurrentStage("summary");
    refreshSummarySnapshot();
    router.push({ name: "summary" });
    return;
  }

  const targetStage = nextStage === "logic" || nextStage === "innovation"
    ? nextStage
    : visibleStage.value === "format"
      ? "logic"
      : "innovation";

  setCurrentStage(targetStage);
  await ensureStageReady(targetStage);
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
  const nextStage = latestState?.nextStage ?? reviewSession.workflow.currentStage ?? "format";

  if (reviewSession.workflow.currentStage !== "summary") {
    setCurrentStage(nextStage);
  }

  await ensureStageReady(visibleStage.value);
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
            左侧保持论文正文，右侧跟随后端 run state 展示当前允许阶段的结果或操作。
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
      :active-stage="reviewSession.workflow.currentStage"
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
            当前查看：{{ activeStageMeta.title }}
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
        :loading="loadingStage === visibleStage"
        :actions="controlActions"
        :footer-action="footerAction"
        :status-text="statusText"
        @action="handleStageAction"
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
