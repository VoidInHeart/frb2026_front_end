<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import RecommendationList from "../components/RecommendationList.vue";
import ReviewStageTracker from "../components/ReviewStageTracker.vue";
import SummaryIssueBoard from "../components/SummaryIssueBoard.vue";
import SummarySuggestionPanel from "../components/SummarySuggestionPanel.vue";
import {
  countAnchorsByType,
  fetchRecommendations,
  fetchRunState,
  fetchRunSummary,
  fetchStageRecord,
  getAnchorCount,
  getPageCount,
  getPaperMeta,
  triggerStageExecution
} from "../services/api";
import {
  reviewSession,
  setCurrentStage,
  setRecommendations,
  setRunState,
  setWorkflowSummary
} from "../stores/reviewSession";

const router = useRouter();
const POLL_INTERVAL_MS = 15000;
const FINAL_STAGE_STATUSES = new Set(["completed", "skipped", "failed", "aborted"]);

const recommendationLoading = ref(false);
const summaryLoading = ref(false);
const actionLoading = ref("");
const errorMessage = ref("");
const summaryPending = ref(false);
const summaryPollInFlight = ref(false);
const summaryStageStatus = ref("");

let summaryPollTimer = 0;

const submission = computed(() => reviewSession.currentSubmission);
const runRecord = computed(() => reviewSession.runRecord);
const runState = computed(() => reviewSession.runState);
const paperMeta = computed(() => getPaperMeta(submission.value));
const stageReviews = computed(() => reviewSession.workflow.reviews);
const summary = computed(() => reviewSession.workflow.summary);
const recommendations = computed(() => reviewSession.recommendations);

const pageCount = computed(() => getPageCount(paperMeta.value));
const anchorCount = computed(() => getAnchorCount(paperMeta.value));
const figureCount = computed(() => countAnchorsByType(paperMeta.value, "figure"));
const tableCount = computed(() => countAnchorsByType(paperMeta.value, "table"));

const summaryActions = computed(() => {
  if (
    !runState.value ||
    runState.value.nextStage !== "summary" ||
    summary.value ||
    summaryPending.value ||
    ["failed", "aborted"].includes(runState.value.status)
  ) {
    return [];
  }

  const allowedActions = runState.value.allowedActions?.length
    ? runState.value.allowedActions
    : ["continue"];

  return allowedActions.map((action) => ({
    key: action,
    label:
      action === "continue"
        ? "生成汇总"
        : action === "skip"
          ? "跳过汇总阶段"
          : "终止 run",
    variant:
      action === "continue"
        ? "primary"
        : action === "skip"
          ? "secondary"
          : "ghost",
    disabled: Boolean(actionLoading.value)
  }));
});

async function syncRunState() {
  if (!runRecord.value?.runId) {
    return null;
  }

  const nextState = await fetchRunState(runRecord.value.runId);
  setRunState(nextState);
  return nextState;
}

function stopSummaryPolling() {
  if (summaryPollTimer) {
    window.clearInterval(summaryPollTimer);
    summaryPollTimer = 0;
  }
}

function startSummaryPolling() {
  stopSummaryPolling();
  summaryPollTimer = window.setInterval(() => {
    void tickSummaryPolling();
  }, POLL_INTERVAL_MS);
}

async function loadSummary() {
  if (!runRecord.value?.runId) {
    return;
  }

  errorMessage.value = "";
  summaryLoading.value = true;

  try {
    const digest = await fetchRunSummary({
      runId: runRecord.value.runId,
      formatReview: stageReviews.value.format,
      logicReview: stageReviews.value.logic,
      innovationReview: stageReviews.value.innovation
    });

    setWorkflowSummary(digest);
  } catch (error) {
    errorMessage.value =
      error instanceof Error ? error.message : "汇总结果加载失败";
  } finally {
    summaryLoading.value = false;
  }
}

async function loadSummaryStageRecord() {
  if (!runRecord.value?.runId) {
    return null;
  }

  const snapshot = await fetchStageRecord({
    runId: runRecord.value.runId,
    stageName: "summary"
  });

  summaryStageStatus.value = snapshot.stageStatus;
  return snapshot;
}

async function tickSummaryPolling() {
  if (!summaryPending.value || !runRecord.value?.runId || summaryPollInFlight.value) {
    return;
  }

  summaryPollInFlight.value = true;

  try {
    const snapshot = await loadSummaryStageRecord();

    if (!snapshot || !FINAL_STAGE_STATUSES.has(snapshot.stageStatus)) {
      return;
    }

    summaryPending.value = false;
    const latestState = await syncRunState();

    if (snapshot.stageStatus === "completed") {
      await loadSummary();
    }

    if (latestState?.status === "completed") {
      await loadRecommendationsIfNeeded();
    }
  } catch (error) {
    errorMessage.value =
      error instanceof Error ? error.message : "summary 阶段轮询失败";
  } finally {
    summaryPollInFlight.value = false;
  }
}

async function handleSummaryAction(action) {
  if (!runRecord.value?.runId) {
    return;
  }

  errorMessage.value = "";
  actionLoading.value = action;

  try {
    await triggerStageExecution({
      runId: runRecord.value.runId,
      stageName: "summary",
      action
    });

    const snapshot = await loadSummaryStageRecord();
    const latestState = await syncRunState();

    if (snapshot && FINAL_STAGE_STATUSES.has(snapshot.stageStatus)) {
      summaryPending.value = false;

      if (snapshot.stageStatus === "completed") {
        await loadSummary();
      }

      if (latestState?.status === "completed") {
        await loadRecommendationsIfNeeded();
      }
      return;
    }

    summaryPending.value = true;
  } catch (error) {
    summaryPending.value = false;
    errorMessage.value =
      error instanceof Error ? error.message : "汇总阶段执行失败";
  } finally {
    actionLoading.value = "";
  }
}

async function loadRecommendationsIfNeeded() {
  if (!submission.value || !runRecord.value?.runId || recommendations.value.length) {
    return;
  }

  errorMessage.value = "";
  recommendationLoading.value = true;

  try {
    const items = await fetchRecommendations({
      runId: runRecord.value.runId,
      submissionId: submission.value.submissionId,
      paperMeta: paperMeta.value
    });

    setRecommendations(items);
  } catch (error) {
    errorMessage.value =
      error instanceof Error ? error.message : "推荐论文获取失败";
  } finally {
    recommendationLoading.value = false;
  }
}

function backToWorkspace() {
  router.push({ name: "workspace" });
}

function openRecommendation(paper) {
  router.push({
    name: "recommendation-detail",
    params: {
      paperId: paper.id
    },
    query: {
      fromPage: "summary"
    }
  });
}

onMounted(async () => {
  if (!submission.value || !runRecord.value?.runId) {
    router.replace({ name: "upload" });
    return;
  }

  setCurrentStage("summary");
  startSummaryPolling();

  const latestState = await syncRunState();
  const snapshot = await loadSummaryStageRecord();

  if (snapshot?.stageStatus === "completed") {
    await loadSummary();

    if (latestState?.status === "completed") {
      await loadRecommendationsIfNeeded();
    }
    return;
  }

  if (
    latestState?.nextStage === "summary" &&
    !summary.value &&
    !["waiting", "failed", "aborted"].includes(latestState.status) &&
    !FINAL_STAGE_STATUSES.has(snapshot?.stageStatus ?? "")
  ) {
    await handleSummaryAction("continue");

    if (summaryPending.value) {
      void tickSummaryPolling();
    }
    return;
  }

  if (
    latestState?.nextStage === "summary" &&
    ["pending", "running", "in_progress", "waiting"].includes(snapshot?.stageStatus ?? "")
  ) {
    summaryPending.value = true;
    void tickSummaryPolling();
    return;
  }

  if (latestState?.status === "completed") {
    await loadRecommendationsIfNeeded();
  }
});

onBeforeUnmount(() => {
  stopSummaryPolling();
});
</script>

<template>
  <section v-if="submission" class="summary-page-layout">
    <header class="summary-hero glass-card">
      <div class="hero-copy">
        <button class="ghost-button hero-button" type="button" @click="backToWorkspace">
          返回审查工作区
        </button>
        <p class="summary-kicker">汇总页</p>
        <h1 class="section-title">汇总结果与推荐论文</h1>
        <p class="section-subtitle hero-subtitle">
          页面先轮询 `GET /runs/:runId/stages/summary`，确认 summary 阶段完成后，再读取 `/summary` 和 `/recommendations`。
        </p>
      </div>

      <div class="hero-pills">
        <span class="pill pill-primary">{{ submission.paperName }}</span>
        <span class="pill pill-neutral">页数 {{ pageCount }}</span>
        <span class="pill pill-neutral">锚点 {{ anchorCount }}</span>
        <span class="pill pill-neutral">图 {{ figureCount }}</span>
        <span class="pill pill-neutral">表 {{ tableCount }}</span>
        <span v-if="runState" class="pill pill-neutral">run: {{ runState.status }}</span>
        <span v-if="summaryStageStatus" class="pill pill-neutral">
          summary_stage: {{ summaryStageStatus }}
        </span>
      </div>
    </header>

    <ReviewStageTracker
      active-stage="summary"
      :reviews="stageReviews"
      :run-state="runState"
      :summary-ready="Boolean(summary)"
    />

    <div v-if="summaryActions.length" class="action-banner glass-card">
      <strong>summary 阶段尚未执行完成</strong>
      <div class="action-row">
        <button
          v-for="action in summaryActions"
          :key="action.key"
          :class="
            action.variant === 'ghost'
              ? 'ghost-button'
              : action.variant === 'secondary'
                ? 'secondary-button'
                : 'primary-button'
          "
          type="button"
          :disabled="action.disabled"
          @click="handleSummaryAction(action.key)"
        >
          {{ action.label }}
        </button>
      </div>
    </div>

    <div v-if="errorMessage" class="error-banner">{{ errorMessage }}</div>

    <section class="summary-layout">
      <SummaryIssueBoard :summary="summary" />

      <div class="summary-sidebar">
        <SummarySuggestionPanel
          :summary="summary"
          :run-record="runRecord"
          :run-state="runState"
          :loading="summaryLoading || actionLoading !== '' || summaryPending"
        />

        <RecommendationList
          :recommendations="recommendations"
          :loading="recommendationLoading"
          collapsible
          :default-expanded="false"
          @select="openRecommendation"
        />
      </div>
    </section>
  </section>
</template>

<style scoped>
.summary-page-layout {
  display: grid;
  gap: 18px;
}

.summary-hero {
  padding: 24px;
  display: grid;
  gap: 18px;
}

.hero-copy {
  display: grid;
  gap: 8px;
}

.hero-button {
  width: fit-content;
}

.summary-kicker {
  margin: 0 0 6px;
  font-size: 12px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--muted);
}

.hero-subtitle {
  max-width: 760px;
}

.hero-pills,
.action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.action-banner {
  padding: 18px 20px;
  display: grid;
  gap: 14px;
}

.summary-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.08fr) minmax(360px, 0.92fr);
  gap: 18px;
  align-items: start;
}

.summary-sidebar {
  display: grid;
  gap: 18px;
  align-content: start;
}

.error-banner {
  padding: 13px 14px;
  border-radius: 14px;
  background: rgba(192, 86, 33, 0.12);
  border: 1px solid rgba(192, 86, 33, 0.18);
  color: var(--danger);
}

@media (max-width: 1240px) {
  .summary-layout {
    grid-template-columns: 1fr;
  }
}
</style>
