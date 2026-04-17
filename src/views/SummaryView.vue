<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import RecommendationList from "../components/RecommendationList.vue";
import ReviewStageTracker from "../components/ReviewStageTracker.vue";
import SummaryIssueBoard from "../components/SummaryIssueBoard.vue";
import SummarySuggestionPanel from "../components/SummarySuggestionPanel.vue";
import {
  countAnchorsByType,
  fetchRecommendationsRecord,
  fetchRunState,
  fetchRunSummaryRecord,
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

const recommendationLoading = ref(false);
const summaryLoading = ref(false);
const summaryPending = ref(false);
const summaryTriggering = ref(false);
const pollInFlight = ref(false);
const errorMessage = ref("");

let pollTimer = 0;

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

async function syncRunState() {
  if (!runRecord.value?.runId) {
    return null;
  }

  const nextState = await fetchRunState(runRecord.value.runId);
  setRunState(nextState);
  return nextState;
}

function stopPolling() {
  if (pollTimer) {
    window.clearInterval(pollTimer);
    pollTimer = 0;
  }
}

function startPolling() {
  stopPolling();
  pollTimer = window.setInterval(() => {
    void tickPolling();
  }, POLL_INTERVAL_MS);
}

async function tryLoadSummary() {
  if (!runRecord.value?.runId) {
    return false;
  }

  summaryLoading.value = true;

  try {
    const record = await fetchRunSummaryRecord({
      runId: runRecord.value.runId,
      formatReview: stageReviews.value.format,
      logicReview: stageReviews.value.logic,
      innovationReview: stageReviews.value.innovation
    });

    if (!record.isReady || !record.digest) {
      return false;
    }

    setWorkflowSummary(record.digest);
    return true;
  } finally {
    summaryLoading.value = false;
  }
}

async function tryLoadRecommendations() {
  if (!runRecord.value?.runId) {
    return false;
  }

  recommendationLoading.value = true;

  try {
    const record = await fetchRecommendationsRecord({
      runId: runRecord.value.runId,
      submissionId: submission.value?.submissionId,
      paperMeta: paperMeta.value
    });

    if (!record.isReady) {
      return false;
    }

    setRecommendations(record.items);
    return true;
  } finally {
    recommendationLoading.value = false;
  }
}

async function tickPolling() {
  if (!runRecord.value?.runId || pollInFlight.value) {
    return;
  }

  pollInFlight.value = true;

  try {
    const summaryReady = await tryLoadSummary();

    if (!summaryReady) {
      return;
    }

    await tryLoadRecommendations();
    await syncRunState();
    summaryPending.value = false;
    stopPolling();
  } catch (error) {
    errorMessage.value =
      error instanceof Error ? error.message : "汇总结果轮询失败";
  } finally {
    pollInFlight.value = false;
  }
}

async function triggerSummaryStage() {
  if (!runRecord.value?.runId) {
    return;
  }

  summaryTriggering.value = true;

  try {
    await triggerStageExecution({
      runId: runRecord.value.runId,
      stageName: "summary",
      action: "continue"
    });
  } catch (error) {
    if (!["RUN_STATE_CONFLICT", "STAGE_NOT_READY"].includes(error?.code ?? "")) {
      throw error;
    }
  } finally {
    summaryTriggering.value = false;
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
  startPolling();

  try {
    await syncRunState();

    const summaryReady = await tryLoadSummary();

    if (summaryReady) {
      await tryLoadRecommendations();
      stopPolling();
      return;
    }

    summaryPending.value = true;
    await triggerSummaryStage();
    void tickPolling();
  } catch (error) {
    errorMessage.value =
      error instanceof Error ? error.message : "汇总阶段启动失败";
  }
});

onBeforeUnmount(() => {
  stopPolling();
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
          进入页面后会自动触发 `POST /runs/{run_id}/stages/summary`，随后轮询
          `GET /summary` 和 `GET /recommendations`。
        </p>
      </div>

      <div class="hero-pills">
        <span class="pill pill-primary">{{ submission.paperName }}</span>
        <span class="pill pill-neutral">页数 {{ pageCount }}</span>
        <span class="pill pill-neutral">锚点 {{ anchorCount }}</span>
        <span class="pill pill-neutral">图 {{ figureCount }}</span>
        <span class="pill pill-neutral">表 {{ tableCount }}</span>
        <span v-if="runState" class="pill pill-neutral">run: {{ runState.status }}</span>
      </div>
    </header>

    <ReviewStageTracker
      active-stage="summary"
      :reviews="stageReviews"
      :run-state="runState"
      :summary-ready="Boolean(summary)"
    />

    <div
      v-if="summaryPending || summaryTriggering"
      class="action-banner glass-card"
    >
      <strong>正在生成汇总与推荐结果</strong>
      <span class="summary-note">
        后端较慢时会持续轮询，直到 `/summary` 返回非空结果为止。
      </span>
    </div>

    <div v-if="errorMessage" class="error-banner">{{ errorMessage }}</div>

    <section class="summary-layout">
      <SummaryIssueBoard :summary="summary" />

      <div class="summary-sidebar">
        <SummarySuggestionPanel
          :summary="summary"
          :run-record="runRecord"
          :run-state="runState"
          :loading="summaryLoading || summaryPending || summaryTriggering"
        />

        <RecommendationList
          :recommendations="recommendations"
          :loading="recommendationLoading || summaryPending || summaryTriggering"
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

.hero-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.action-banner {
  padding: 18px 20px;
  display: grid;
  gap: 10px;
}

.summary-note {
  color: var(--muted);
  line-height: 1.7;
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
