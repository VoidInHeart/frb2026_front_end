<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import MarkdownArticle from "../components/MarkdownArticle.vue";
import ReviewStageTracker from "../components/ReviewStageTracker.vue";
import StageFindingsPanel from "../components/StageFindingsPanel.vue";
import {
  buildReviewDigest,
  countAnchorsByType,
  getAnchorCount,
  getPageCount,
  getPaperMeta,
  runFormatReview,
  runInnovationReview,
  runLogicReview,
  submitPaperMeta
} from "../services/api";
import {
  clearSession,
  reviewSession,
  setCurrentStage,
  setShowImages,
  setStageReview,
  setTransmissionStatus,
  setWorkflowSummary
} from "../stores/reviewSession";

const router = useRouter();

const loadingStage = ref("");
const transmissionLoading = ref(false);
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

const transmissionReady = computed(() => Boolean(reviewSession.transmissionStatus?.success));

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

const stageActionLabel = computed(() => {
  if (visibleStage.value === "innovation" || activeStageResult.value?.severe) {
    return "进入汇总页面";
  }

  return "进入下一阶段";
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

async function loadStage(stageKey) {
  if (!submission.value) {
    return null;
  }

  errorMessage.value = "";
  loadingStage.value = stageKey;

  try {
    let result = null;
    const payload = {
      paperMarkdown: submission.value.paperMarkdown,
      paperMeta: paperMeta.value
    };

    if (stageKey === "format") {
      result = await runFormatReview(payload);
    }

    if (stageKey === "logic") {
      result = await runLogicReview(payload);
    }

    if (stageKey === "innovation") {
      result = await runInnovationReview(payload);
    }

    if (!result) {
      return null;
    }

    setStageReview(stageKey, result);
    refreshSummarySnapshot();

    pageMessage.value = result.severe
      ? `${result.stageLabel}发现严重问题，后续未执行阶段会在进度条中保持灰色。`
      : `${result.stageLabel}已完成。`;

    return result;
  } catch (error) {
    errorMessage.value =
      error instanceof Error ? error.message : "阶段结果加载失败";
    return null;
  } finally {
    loadingStage.value = "";
  }
}

async function ensureStageReady(stageKey) {
  if (stageReviews.value[stageKey]) {
    return stageReviews.value[stageKey];
  }

  return loadStage(stageKey);
}

async function goNext() {
  const stageKey = visibleStage.value;
  const result = activeStageResult.value ?? (await ensureStageReady(stageKey));

  if (!result) {
    return;
  }

  if (stageKey === "innovation" || result.severe) {
    setCurrentStage("summary");
    refreshSummarySnapshot();
    router.push({ name: "summary" });
    return;
  }

  const nextStage = stageKey === "format" ? "logic" : "innovation";

  setCurrentStage(nextStage);
  await ensureStageReady(nextStage);
}

function restartReview() {
  clearSession();
  router.push({ name: "upload" });
}

onMounted(async () => {
  if (!submission.value) {
    router.replace({ name: "upload" });
    return;
  }

  await ensureTransmissionReady();
  await ensureStageReady(visibleStage.value);
});
</script>

<template>
  <section v-if="submission" class="workspace-layout">
    <header class="workspace-hero glass-card">
      <div class="hero-top">
        <div class="hero-copy">
          <p class="summary-kicker">分阶段审查工作区</p>
          <h1 class="section-title">上传后的审查流程已经重构为三阶段主线</h1>
          <p class="section-subtitle hero-subtitle">
            左侧始终展示解析后的论文正文；右侧展示当前阶段的问题结果，并在需要时进入独立汇总页面。
          </p>
        </div>

        <div class="hero-actions">
          <span
            class="pill"
            :class="transmissionReady ? 'pill-success' : 'pill-neutral'"
          >
            {{ transmissionReady ? "解析结果已同步" : "等待同步解析结果" }}
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
      :active-stage="visibleStage"
      :reviews="stageReviews"
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
        :action-label="stageActionLabel"
        :action-disabled="loadingStage === visibleStage || transmissionLoading"
        @next="goNext"
      />
    </section>
  </section>
</template>

<style scoped>
.workspace-layout {
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
  min-height: calc(100vh - 320px);
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
  max-height: calc(100vh - 420px);
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
