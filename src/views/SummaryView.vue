<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import RecommendationList from "../components/RecommendationList.vue";
import ReviewStageTracker from "../components/ReviewStageTracker.vue";
import SummaryIssueBoard from "../components/SummaryIssueBoard.vue";
import SummarySuggestionPanel from "../components/SummarySuggestionPanel.vue";
import {
  buildReviewDigest,
  countAnchorsByType,
  fetchRecommendations,
  getAnchorCount,
  getPageCount,
  getPaperMeta,
  submitPaperMeta
} from "../services/api";
import {
  reviewSession,
  setCurrentStage,
  setRecommendations,
  setTransmissionStatus,
  setWorkflowSummary
} from "../stores/reviewSession";

const router = useRouter();

const recommendationLoading = ref(false);
const transmissionLoading = ref(false);
const errorMessage = ref("");

const submission = computed(() => reviewSession.currentSubmission);
const paperMeta = computed(() => getPaperMeta(submission.value));
const stageReviews = computed(() => reviewSession.workflow.reviews);
const summary = computed(() => reviewSession.workflow.summary);
const recommendations = computed(() => reviewSession.recommendations);
const transmissionReady = computed(() => Boolean(reviewSession.transmissionStatus?.success));

const pageCount = computed(() => getPageCount(paperMeta.value));
const anchorCount = computed(() => getAnchorCount(paperMeta.value));
const figureCount = computed(() => countAnchorsByType(paperMeta.value, "figure"));
const tableCount = computed(() => countAnchorsByType(paperMeta.value, "table"));

function refreshSummarySnapshot() {
  setWorkflowSummary(
    buildReviewDigest({
      formatReview: stageReviews.value.format,
      logicReview: stageReviews.value.logic,
      innovationReview: stageReviews.value.innovation
    })
  );
}

async function ensureTransmissionReady() {
  if (!submission.value || transmissionReady.value) {
    return;
  }

  errorMessage.value = "";
  transmissionLoading.value = true;

  try {
    const transmission = await submitPaperMeta({
      submissionId: submission.value.submissionId,
      paperMeta: paperMeta.value
    });

    setTransmissionStatus(transmission);
  } catch (error) {
    errorMessage.value =
      error instanceof Error ? error.message : "解析结果同步失败";
  } finally {
    transmissionLoading.value = false;
  }
}

async function loadRecommendationsIfNeeded() {
  if (!submission.value || recommendations.value.length) {
    return;
  }

  errorMessage.value = "";
  recommendationLoading.value = true;

  try {
    const items = await fetchRecommendations({
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
  if (!submission.value) {
    router.replace({ name: "upload" });
    return;
  }

  setCurrentStage("summary");
  refreshSummarySnapshot();
  await ensureTransmissionReady();
  await loadRecommendationsIfNeeded();
});
</script>

<template>
  <section v-if="submission" class="summary-page-layout">
    <header class="summary-hero glass-card">
      <div class="hero-copy">
        <button class="ghost-button hero-button" type="button" @click="backToWorkspace">
          返回审查工作区
        </button>
        <p class="summary-kicker">汇总页面</p>
        <h1 class="section-title">汇总结果与推荐论文</h1>
        <p class="section-subtitle hero-subtitle">
          左侧汇总各阶段问题与证据链，右侧展示修改建议和推荐论文列表。
        </p>
      </div>

      <div class="hero-pills">
        <span class="pill pill-primary">{{ submission.paperName }}</span>
        <span class="pill pill-neutral">页数 {{ pageCount }}</span>
        <span class="pill pill-neutral">锚点 {{ anchorCount }}</span>
        <span class="pill pill-neutral">图 {{ figureCount }}</span>
        <span class="pill pill-neutral">表 {{ tableCount }}</span>
      </div>
    </header>

    <ReviewStageTracker
      active-stage="summary"
      :reviews="stageReviews"
    />

    <div v-if="errorMessage" class="error-banner">{{ errorMessage }}</div>

    <section class="summary-layout">
      <SummaryIssueBoard :summary="summary" />

      <div class="summary-sidebar">
        <SummarySuggestionPanel
          :summary="summary"
          :transmission-status="reviewSession.transmissionStatus"
          :loading="transmissionLoading"
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

.hero-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
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
