<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import MarkdownArticle from "../components/MarkdownArticle.vue";
import RecommendationList from "../components/RecommendationList.vue";
import ReviewSummaryPanel from "../components/ReviewSummaryPanel.vue";
import {
  fetchRecommendations,
  generateReviewComment,
  submitDocumentIr
} from "../services/api";
import {
  clearSession,
  reviewSession,
  setRecommendations,
  setReviewSummary,
  setShowImages,
  setTransmissionStatus
} from "../stores/reviewSession";

const router = useRouter();
const reviewLoading = ref(false);
const recommendationLoading = ref(false);
const transmissionLoading = ref(false);
const errorMessage = ref("");

const submission = computed(() => reviewSession.currentSubmission);
const documentIr = computed(() => submission.value?.documentIr ?? null);
const reviewSummary = computed(() => reviewSession.reviewSummary);
const recommendations = computed(() => reviewSession.recommendations);
const showImages = computed({
  get: () => reviewSession.preferences.showImages,
  set: (value) => setShowImages(value)
});

const pageCount = computed(() => documentIr.value?.pages?.length ?? 0);
const blockCount = computed(() => documentIr.value?.blocks?.length ?? 0);
const headingCount = computed(
  () =>
    (documentIr.value?.blocks ?? []).filter((block) => block.type === "heading")
      .length
);

async function resendDocumentIr() {
  if (!submission.value) {
    return;
  }

  errorMessage.value = "";
  transmissionLoading.value = true;

  try {
    const transmission = await submitDocumentIr({
      submissionId: submission.value.submissionId,
      documentIr: submission.value.documentIr
    });

    setTransmissionStatus(transmission);
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "JSON 发送失败";
  } finally {
    transmissionLoading.value = false;
  }
}

async function loadReviewSummary() {
  if (!submission.value) {
    return;
  }

  errorMessage.value = "";
  reviewLoading.value = true;

  try {
    const summary = await generateReviewComment({
      submissionId: submission.value.submissionId,
      documentIr: submission.value.documentIr
    });

    setReviewSummary(summary);
  } catch (error) {
    errorMessage.value =
      error instanceof Error ? error.message : "评语生成失败";
  } finally {
    reviewLoading.value = false;
  }
}

async function loadRecommendations() {
  if (!submission.value) {
    return;
  }

  errorMessage.value = "";
  recommendationLoading.value = true;

  try {
    const items = await fetchRecommendations({
      submissionId: submission.value.submissionId,
      documentIr: submission.value.documentIr
    });

    setRecommendations(items);
  } catch (error) {
    errorMessage.value =
      error instanceof Error ? error.message : "推荐论文获取失败";
  } finally {
    recommendationLoading.value = false;
  }
}

function openRecommendation(paper) {
  router.push({
    name: "recommendation-detail",
    params: { paperId: paper.id }
  });
}

function restartFlow() {
  clearSession();
  router.push({ name: "upload" });
}

onMounted(async () => {
  if (!submission.value) {
    router.replace({ name: "upload" });
    return;
  }

  if (!reviewSession.transmissionStatus?.success) {
    await resendDocumentIr();
  }

  if (!reviewSummary.value) {
    await loadReviewSummary();
  }

  if (!recommendations.value.length) {
    await loadRecommendations();
  }
});
</script>

<template>
  <section v-if="submission" class="workspace-layout">
    <section class="workspace-main">
      <header class="workspace-hero glass-card">
        <div>
          <p class="summary-kicker">第二界面</p>
          <h1 class="section-title">论文解析结果与评审建议</h1>
          <p class="section-subtitle">
            左侧展示 `paper.md` 解析内容，右侧展示评语和推荐论文；`document_ir.json`
            的传输状态也会在右侧同步显示。
          </p>
        </div>

        <div class="hero-pills">
          <span class="pill pill-primary">{{ submission.paperName }}</span>
          <span class="pill pill-neutral">页数 {{ pageCount }}</span>
          <span class="pill pill-neutral">块数 {{ blockCount }}</span>
          <span class="pill pill-neutral">标题块 {{ headingCount }}</span>
        </div>
      </header>

      <div v-if="errorMessage" class="error-banner">
        {{ errorMessage }}
      </div>

      <div class="workspace-columns">
        <section class="left-column glass-card">
          <div class="column-head">
            <div>
              <p class="summary-kicker">论文展示</p>
              <h2 class="section-title">解析后的 Markdown</h2>
            </div>
            <label class="toggle-field">
              <input v-model="showImages" type="checkbox" />
              <span>显示图片</span>
            </label>
          </div>

          <div class="meta-row">
            <span class="pill pill-primary">
              doc_id: {{ documentIr?.doc_id || "unknown" }}
            </span>
            <span class="pill pill-neutral">
              source: {{ submission.sourceMode }}
            </span>
          </div>

          <div class="article-scroll">
            <MarkdownArticle
              :markdown="submission.paperMarkdown"
              :show-images="showImages"
              :asset-base="submission.paperAssetBase"
            />
          </div>
        </section>

        <section class="right-column">
          <section class="action-bar glass-card">
            <div>
              <p class="summary-kicker">接口操作</p>
              <h2 class="section-title">评语与推荐调用</h2>
            </div>

            <div class="button-row">
              <button
                class="primary-button"
                type="button"
                :disabled="reviewLoading"
                @click="loadReviewSummary"
              >
                {{ reviewLoading ? "生成中..." : "生成评语" }}
              </button>
              <button
                class="secondary-button"
                type="button"
                :disabled="recommendationLoading"
                @click="loadRecommendations"
              >
                {{ recommendationLoading ? "获取中..." : "刷新推荐论文" }}
              </button>
              <button
                class="ghost-button"
                type="button"
                :disabled="transmissionLoading"
                @click="resendDocumentIr"
              >
                {{ transmissionLoading ? "发送中..." : "重新发送 JSON" }}
              </button>
              <button class="ghost-button" type="button" @click="restartFlow">
                返回上传页
              </button>
            </div>
          </section>

          <ReviewSummaryPanel
            :review-summary="reviewSummary"
            :transmission-status="reviewSession.transmissionStatus"
            :review-loading="reviewLoading"
          />

          <RecommendationList
            :recommendations="recommendations"
            :loading="recommendationLoading"
            @select="openRecommendation"
          />
        </section>
      </div>
    </section>
  </section>
</template>

<style scoped>
.workspace-layout,
.workspace-main {
  display: grid;
  gap: 18px;
}

.workspace-hero {
  padding: 24px;
  display: grid;
  gap: 16px;
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

.error-banner {
  padding: 13px 14px;
  border-radius: 14px;
  background: rgba(192, 86, 33, 0.12);
  border: 1px solid rgba(192, 86, 33, 0.18);
  color: var(--danger);
}

.workspace-columns {
  display: grid;
  grid-template-columns: minmax(0, 1.08fr) minmax(360px, 0.92fr);
  gap: 18px;
  align-items: start;
}

.left-column,
.action-bar {
  padding: 22px;
}

.left-column {
  display: grid;
  gap: 18px;
  min-height: calc(100vh - 190px);
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

.article-scroll {
  max-height: calc(100vh - 340px);
  overflow: auto;
  padding-right: 6px;
}

.right-column {
  display: grid;
  gap: 18px;
}

.action-bar {
  display: grid;
  gap: 16px;
}

@media (max-width: 1180px) {
  .workspace-columns {
    grid-template-columns: 1fr;
  }

  .left-column {
    min-height: auto;
  }

  .article-scroll {
    max-height: none;
  }
}

@media (max-width: 720px) {
  .column-head {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
