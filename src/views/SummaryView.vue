<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import RecommendationList from "../components/RecommendationList.vue";
import ReviewStageTracker from "../components/ReviewStageTracker.vue";
import SummaryIssueBoard from "../components/SummaryIssueBoard.vue";
import SummarySuggestionPanel from "../components/SummarySuggestionPanel.vue";
import {
  fetchRecommendationsRecord,
  fetchRunState,
  fetchRunSummaryRecord,
  getChunkCount,
  getImageCount,
  getPageCount,
  getPaperMeta
} from "../services/api";
import {
  reviewSession,
  setCurrentStage,
  setDisplayedStage,
  setRecommendations,
  setRunState,
  setWorkflowSummary
} from "../stores/reviewSession";

const router = useRouter();

const POLL_INTERVAL_MS = 15000;
const REVIEW_STAGE_ORDER = ["format", "logic", "innovation"];

const recommendationLoading = ref(false);
const summaryLoading = ref(false);
const summaryPending = ref(false);
const recommendationPending = ref(false);
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
const chunkCount = computed(() => getChunkCount(submission.value));
const imageCount = computed(() => getImageCount(submission.value));
const revisitableStageIds = computed(() =>
  REVIEW_STAGE_ORDER.filter((stageKey) => {
    const reviewStatus = stageReviews.value[stageKey]?.stageStatus ?? "";
    const stateStatus =
      runState.value?.stageRuns?.find((item) => item.stageName === stageKey)?.status ??
      reviewStatus;

    return ["complete", "completed"].includes(String(stateStatus));
  })
);

const bannerTitle = computed(() =>
  summaryPending.value ? "正在生成汇总结果" : "正在生成推荐论文"
);

const bannerNote = computed(() =>
  summaryPending.value
    ? "主任务尚未产出最终汇总，页面会持续轮询 /summary。"
    : "主任务已经完成，推荐论文正在后台异步生成，页面会持续轮询 /recommendations。"
);

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
    await syncRunState();

    if (!summaryReady) {
      summaryPending.value = true;
      recommendationPending.value = false;
      return;
    }

    summaryPending.value = false;
    const recommendationsReady = await tryLoadRecommendations();
    recommendationPending.value = !recommendationsReady;

    if (recommendationsReady) {
      stopPolling();
    }
  } catch (error) {
    errorMessage.value =
      error instanceof Error ? error.message : "汇总结果轮询失败";
  } finally {
    pollInFlight.value = false;
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

function openStageSnapshot(stageKey) {
  if (!stageKey || stageKey === "summary") {
    return;
  }

  setDisplayedStage(stageKey);
  router.push({ name: "workspace" });
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
      summaryPending.value = false;
      const recommendationsReady = await tryLoadRecommendations();
      recommendationPending.value = !recommendationsReady;
      if (recommendationsReady) {
        stopPolling();
      }
      return;
    }

    summaryPending.value = true;
    recommendationPending.value = false;
    void tickPolling();
  } catch (error) {
    errorMessage.value =
      error instanceof Error ? error.message : "汇总阶段初始化失败";
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
        <h1 class="section-title">汇总结论与推荐论文</h1>
        <p class="section-subtitle hero-subtitle">
          页面会自动轮询 `GET /summary` 和 `GET /recommendations`。
          当前后端会先完成主任务，再在后台异步生成推荐论文。
        </p>
      </div>

      <div class="hero-pills">
        <span class="pill pill-primary">{{ submission.paperName }}</span>
        <span class="pill pill-neutral">页数 {{ pageCount }}</span>
        <span class="pill pill-neutral">分块 {{ chunkCount }}</span>
        <span class="pill pill-neutral">图片 {{ imageCount }}</span>
        <span v-if="runState" class="pill pill-neutral">run: {{ runState.status }}</span>
      </div>
    </header>

    <ReviewStageTracker
      active-stage="summary"
      :reviews="stageReviews"
      :run-state="runState"
      :summary-ready="Boolean(summary)"
      :clickable-stage-ids="revisitableStageIds"
      @select-stage="openStageSnapshot"
    />

    <div
      v-if="summaryPending || recommendationPending"
      class="action-banner glass-card"
    >
      <strong>{{ bannerTitle }}</strong>
      <span class="summary-note">{{ bannerNote }}</span>
    </div>

    <div v-if="errorMessage" class="error-banner">{{ errorMessage }}</div>

    <section class="summary-layout">
      <SummaryIssueBoard :summary="summary" />

      <div class="summary-sidebar">
        <SummarySuggestionPanel
          :summary="summary"
          :run-record="runRecord"
          :run-state="runState"
          :loading="summaryLoading || summaryPending"
        />

        <RecommendationList
          :recommendations="recommendations"
          :loading="recommendationLoading || summaryPending || recommendationPending"
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
