<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import MarkdownArticle from "../components/MarkdownArticle.vue";
import RecommendationList from "../components/RecommendationList.vue";
import ReviewSummaryPanel from "../components/ReviewSummaryPanel.vue";
import {
  countAnchorsByType,
  fetchSystemRuleLibrary,
  fetchRecommendations,
  getAnchorCount,
  getPageCount,
  getPaperMeta,
  generateReviewComment,
  submitPaperMeta
} from "../services/api";
import {
  clearSession,
  reviewSession,
  setCustomRulesText,
  setRuleLibraryCatalog,
  setRecommendations,
  setReviewSummary,
  setShowImages,
  setTransmissionStatus
} from "../stores/reviewSession";

const route = useRoute();
const router = useRouter();
const reviewLoading = ref(false);
const recommendationLoading = ref(false);
const transmissionLoading = ref(false);
const errorMessage = ref("");
const pageMessage = ref("");
const activeFlow = ref("global-analysis");
const activeRuleTab = ref("system");

const flowItems = [
  {
    id: "global-analysis",
    label: "全局性问题分析",
    kicker: "Flow 01"
  },
  {
    id: "rule-analysis",
    label: "基于规则的问题分析",
    kicker: "Flow 02"
  },
  {
    id: "repair",
    label: "修复",
    kicker: "Flow 03"
  }
];

const validFlowIds = new Set(flowItems.map((item) => item.id));

function resolveFlow(flowId) {
  return validFlowIds.has(flowId) ? flowId : "global-analysis";
}

const submission = computed(() => reviewSession.currentSubmission);
const paperMeta = computed(() => getPaperMeta(submission.value));
const reviewSummary = computed(() => reviewSession.reviewSummary);
const recommendations = computed(() => reviewSession.recommendations);
const showImages = computed({
  get: () => reviewSession.preferences.showImages,
  set: (value) => setShowImages(value)
});

const pageCount = computed(() => getPageCount(paperMeta.value));
const anchorCount = computed(() => getAnchorCount(paperMeta.value));
const figureCount = computed(() => countAnchorsByType(paperMeta.value, "figure"));
const tableCount = computed(() => countAnchorsByType(paperMeta.value, "table"));

const systemRules = computed(() => reviewSession.ruleLibrary.systemRules ?? []);
const selectedSystemRuleIds = computed(
  () => reviewSession.ruleLibrary.selectedSystemRuleIds ?? []
);
const selectedSystemRules = computed(() =>
  systemRules.value.filter((item) => selectedSystemRuleIds.value.includes(item.id))
);
const customRuleItems = computed(() => parseRuleLines(reviewSession.ruleLibrary.customRulesText));

const globalAnalysisComments = computed(() => buildGlobalAnalysisComments());
const ruleAnalysisTabs = computed(() => buildRuleAnalysisTabs());

function parseRuleLines(text) {
  return (text ?? "")
    .split(/\r?\n/)
    .map((line) => line.replace(/^\d+[.)、]\s*/, "").trim())
    .filter(Boolean);
}

function formatAnchorLabel(anchor) {
  if (!anchor) {
    return "未定位锚点";
  }

  return `${anchor.anchor_id} · P${anchor.page_no}`;
}

function buildGlobalAnalysisComments() {
  const anchors = paperMeta.value?.anchors ?? [];
  const paragraphAnchor = anchors.find((item) => item.type === "paragraph");
  const figureAnchor = anchors.find((item) => item.type === "figure");
  const tableAnchor = anchors.find((item) => item.type === "table");
  const summary = reviewSummary.value;

  return [
    {
      id: "global-structure",
      title: "结构节奏仍然偏松",
      anchor: formatAnchorLabel(paragraphAnchor),
      severity: "高优先级",
      description:
        summary?.summary ??
        "当前论文整体逻辑可以读通，但摘要到方法之间的过渡还不够紧，关键信息分散，读者需要反复回看才能建立主线。",
      suggestion:
        "建议先在摘要末尾补一句研究主张，再在引言结尾明确贡献列表，让后文每个章节都能对齐到这条主线。"
    },
    {
      id: "global-evidence",
      title: "证据呈现还不够聚焦",
      anchor: formatAnchorLabel(figureAnchor),
      severity: "中优先级",
      description:
        "图表与文字的互相解释还不够紧密，部分结论没有快速指向图表证据，评审阅读时需要自己做额外映射。",
      suggestion:
        "建议在图表首次出现的段落里补上结论性句子，并明确指出对应的观察点，减少读者自己推断的成本。"
    },
    {
      id: "global-experiment",
      title: "实验结论和分析层次可以再拉开",
      anchor: formatAnchorLabel(tableAnchor),
      severity: "中优先级",
      description:
        "实验章节现在更像结果罗列，缺少按“主结果、失败案例、局限性”层层展开的阅读节奏。",
      suggestion:
        "建议把实验结果拆成主结论和补充观察两层，并在表格后追加针对异常样本或边界场景的解释。"
    }
  ];
}

function buildRuleAnalysisTabs() {
  const systemComments = selectedSystemRules.value.map((rule, index) => ({
    id: `system-${rule.id}`,
    title: `${rule.title}：需要补充可执行说明`,
    anchor: `系统规则 ${index + 1}`,
    sourceLabel: rule.category,
    description:
      `基于“${rule.title}”这条标准规则，当前稿件已经覆盖了主要内容，但仍有部分段落缺少显式说明，导致规则命中后反馈不够稳定。`,
    suggestion:
      "建议在相关章节补上更明确的结论句或结构提示，让规则反馈可以直接落到具体位置。"
  }));

  const customComments = customRuleItems.value.map((rule, index) => ({
    id: `custom-${index}`,
    title: `自建规则 ${index + 1}`,
    anchor: `自建库 · ${index + 1}`,
    sourceLabel: "用户自建",
    description: `按照“${rule}”这条自建规则看，论文目前有一定覆盖，但还缺少更直接的支撑内容。`,
    suggestion:
      "建议把这条规则对应的检查点前置到正文里，让后续自动分析结果更稳定。"
  }));

  const llmComments = [
    {
      id: "llm-1",
      title: "建议新增“问题定义是否前置”的规则",
      anchor: "大模型推荐 01",
      sourceLabel: "结构建议",
      description:
        "从整篇论文的阅读路径来看，问题定义与任务边界出现得偏后，容易影响评审对后续方法设计的理解。",
      suggestion:
        "可以新增规则：在摘要或引言第一页必须明确说明研究问题、任务边界和评价目标。",
      recommendedRule:
        "在摘要或引言第一页明确说明研究问题、任务边界和评价目标。"
    },
    {
      id: "llm-2",
      title: "建议新增“图表必须配解释句”的规则",
      anchor: "大模型推荐 02",
      sourceLabel: "图表解释",
      description:
        "图表虽然已经存在，但文字部分没有做到首尾呼应，评审很难迅速判断图表想证明什么。",
      suggestion:
        "可以新增规则：每个核心图表首次出现时，正文必须配一条结论性解释句。",
      recommendedRule:
        "每个核心图表首次出现时，正文必须配一条结论性解释句。"
    },
    {
      id: "llm-3",
      title: "建议新增“异常案例分析”的规则",
      anchor: "大模型推荐 03",
      sourceLabel: "实验分析",
      description:
        "当前实验结果展示了总体表现，但缺少异常样本、误判样本或边界场景的补充分析。",
      suggestion:
        "可以新增规则：实验部分至少补充一段异常案例、误判分析或边界场景讨论。",
      recommendedRule:
        "实验部分至少补充一段异常案例、误判分析或边界场景讨论。"
    }
  ];

  return [
    {
      id: "system",
      label: "标准规则库",
      comments: systemComments
    },
    {
      id: "custom",
      label: "自建规则库",
      comments: customComments
    },
    {
      id: "llm",
      label: "大模型推荐",
      comments: llmComments
    }
  ];
}

const activeRuleTabData = computed(
  () => ruleAnalysisTabs.value.find((item) => item.id === activeRuleTab.value) ?? ruleAnalysisTabs.value[0]
);

function appendRuleToCustomLibrary(ruleText) {
  const currentItems = parseRuleLines(reviewSession.ruleLibrary.customRulesText);

  if (currentItems.includes(ruleText)) {
    pageMessage.value = "这条规则已经在用户自建库里了。";
    return;
  }

  const nextItems = [...currentItems, ruleText];
  const serialized = nextItems.map((item, index) => `${index + 1}. ${item}`).join("\n");
  setCustomRulesText(serialized);
  pageMessage.value = "已添加到用户自建规则库。";
}

async function resendDocumentIr() {
  if (!submission.value) {
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
      paperMeta: paperMeta.value
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

function openRecommendation(paper) {
  router.push({
    name: "recommendation-detail",
    params: { paperId: paper.id },
    query: {
      fromFlow: activeFlow.value
    }
  });
}

function restartFlow() {
  clearSession();
  router.push({ name: "upload" });
}

watch(
  () => route.query.flow,
  (flow) => {
    const nextFlow = resolveFlow(String(flow ?? ""));

    if (nextFlow !== activeFlow.value) {
      activeFlow.value = nextFlow;
    }
  },
  { immediate: true }
);

watch(activeFlow, (flow) => {
  if (route.query.flow === flow) {
    return;
  }

  router.replace({
    name: "workspace",
    query: {
      ...route.query,
      flow
    }
  });
});

onMounted(async () => {
  if (!submission.value) {
    router.replace({ name: "upload" });
    return;
  }

  if (!reviewSession.ruleLibrary.systemRules.length) {
    try {
      const rules = await fetchSystemRuleLibrary();
      setRuleLibraryCatalog(rules);
    } catch (error) {
      errorMessage.value =
        error instanceof Error ? error.message : "规则库加载失败";
    }
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
          <h1 class="section-title">论文分析</h1>
          <p class="section-subtitle">
            这一页现在拆成三个连续流程：先看全局性问题，再切到基于规则的问题分析，最后进入修复与推荐阶段。
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

      <section class="workflow-card glass-card">
        <div class="workflow-header">
          <div>
            <p class="summary-kicker">流式工作流程</p>
            <h2 class="section-title">点击不同流程，切换不同分析界面</h2>
          </div>
        </div>

        <div class="workflow-line" role="tablist" aria-label="论文分析流程">
          <template v-for="(item, index) in flowItems" :key="item.id">
            <button
              class="workflow-step"
              :class="{ active: activeFlow === item.id }"
              type="button"
              role="tab"
              :aria-selected="activeFlow === item.id"
              @click="activeFlow = item.id"
            >
              <span class="workflow-dot"></span>
              <span class="workflow-text">
                <small>{{ item.kicker }}</small>
                <strong>{{ item.label }}</strong>
              </span>
            </button>
            <div
              v-if="index < flowItems.length - 1"
              class="workflow-connector"
              :class="{
                active:
                  flowItems.findIndex((entry) => entry.id === activeFlow) > index
              }"
            ></div>
          </template>
        </div>
      </section>

      <div v-if="pageMessage" class="success-banner">
        {{ pageMessage }}
      </div>

      <div v-if="errorMessage" class="error-banner">
        {{ errorMessage }}
      </div>

      <section v-if="activeFlow === 'global-analysis'" class="flow-panel two-column-flow">
        <section class="paper-panel glass-card">
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
              doc_id: {{ paperMeta?.doc_id || "unknown" }}
            </span>
            <span class="pill pill-neutral">
              source: {{ submission.sourceMode }}
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

        <section class="commentary-panel glass-card">
          <div class="column-head">
            <div>
              <p class="summary-kicker">全局性问题分析</p>
              <h2 class="section-title">问题叙述与修改建议</h2>
            </div>
            <span class="pill pill-accent">{{ globalAnalysisComments.length }} 条</span>
          </div>

          <div class="panel-scroll comment-scroll">
            <article
              v-for="comment in globalAnalysisComments"
              :key="comment.id"
              class="analysis-card"
            >
              <div class="analysis-card-head">
                <div>
                  <h3>{{ comment.title }}</h3>
                  <span class="muted-text">{{ comment.anchor }}</span>
                </div>
                <span class="pill pill-neutral">{{ comment.severity }}</span>
              </div>
              <section class="analysis-block">
                <h4>问题叙述</h4>
                <p>{{ comment.description }}</p>
              </section>
              <section class="analysis-block">
                <h4>修改建议</h4>
                <p>{{ comment.suggestion }}</p>
              </section>
            </article>
          </div>
        </section>
      </section>

      <section v-else-if="activeFlow === 'rule-analysis'" class="flow-panel two-column-flow">
        <section class="paper-panel glass-card">
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
              已选标准规则 {{ selectedSystemRules.length }}
            </span>
            <span class="pill pill-neutral">
              自建规则 {{ customRuleItems.length }}
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

        <section class="commentary-panel glass-card">
          <div class="column-head">
            <div>
              <p class="summary-kicker">基于规则的问题分析</p>
              <h2 class="section-title">按规则来源查看问题反馈</h2>
            </div>
          </div>

          <div class="rule-tabs" role="tablist" aria-label="规则分析标签页">
            <button
              v-for="tab in ruleAnalysisTabs"
              :key="tab.id"
              class="rule-tab"
              :class="{ active: activeRuleTab === tab.id }"
              type="button"
              @click="activeRuleTab = tab.id"
            >
              {{ tab.label }}
            </button>
          </div>

          <div class="panel-scroll comment-scroll">
            <div v-if="!activeRuleTabData?.comments.length" class="empty-state">
              当前标签还没有可展示的评论。
            </div>

            <article
              v-for="comment in activeRuleTabData?.comments ?? []"
              :key="comment.id"
              class="analysis-card"
            >
              <div class="analysis-card-head">
                <div>
                  <h3>{{ comment.title }}</h3>
                  <span class="muted-text">{{ comment.anchor }}</span>
                </div>
                <span class="pill pill-neutral">{{ comment.sourceLabel }}</span>
              </div>
              <section class="analysis-block">
                <h4>问题叙述</h4>
                <p>{{ comment.description }}</p>
              </section>
              <section class="analysis-block">
                <h4>修改建议</h4>
                <p>{{ comment.suggestion }}</p>
              </section>
              <div
                v-if="activeRuleTab === 'llm' && comment.recommendedRule"
                class="analysis-actions"
              >
                <button
                  class="secondary-button"
                  type="button"
                  @click="appendRuleToCustomLibrary(comment.recommendedRule)"
                >
                  添加到用户自建库
                </button>
              </div>
            </article>
          </div>
        </section>
      </section>

      <section v-else class="flow-panel repair-flow">
        <section class="repair-left-column">
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

          <div class="scroll-shell">
            <ReviewSummaryPanel
              :review-summary="reviewSummary"
              :transmission-status="reviewSession.transmissionStatus"
              :review-loading="reviewLoading"
            />
          </div>
        </section>

        <div class="scroll-shell">
          <RecommendationList
            :recommendations="recommendations"
            :loading="recommendationLoading"
            @select="openRecommendation"
          />
        </div>
      </section>
    </section>
  </section>
</template>

<style scoped>
.workspace-layout,
.workspace-main {
  display: grid;
  gap: 18px;
}

.workspace-hero,
.workflow-card,
.paper-panel,
.commentary-panel,
.action-bar {
  padding: 24px;
}

.workspace-hero {
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
  justify-content: center;
  gap: 10px;
}

.meta-row {
  justify-content: flex-start;
}

.meta-row .pill {
  min-width: 220px;
  padding: 6px 16px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 700;
  text-align: center;
}

.workflow-card,
.flow-panel {
  display: grid;
  gap: 18px;
}

.workflow-line {
  display: grid;
  grid-template-columns: repeat(5, auto);
  align-items: center;
  gap: 0;
  justify-content: center;
}

.workflow-step {
  display: inline-flex;
  align-items: center;
  gap: 14px;
  padding: 14px 18px;
  border: none;
  background: transparent;
  color: var(--muted);
}

.workflow-step.active {
  color: var(--primary);
}

.workflow-dot {
  width: 18px;
  height: 18px;
  border-radius: 999px;
  border: 3px solid rgba(19, 63, 103, 0.24);
  background: rgba(255, 255, 255, 0.92);
  transition: transform 0.2s ease, border-color 0.2s ease, background 0.2s ease;
}

.workflow-step.active .workflow-dot {
  transform: scale(1.12);
  border-color: var(--primary);
  background: var(--accent);
}

.workflow-text {
  display: grid;
  gap: 2px;
  text-align: left;
}

.workflow-text small {
  color: var(--muted);
}

.workflow-text strong {
  font-size: 15px;
}

.workflow-connector {
  width: 92px;
  height: 2px;
  background: rgba(19, 63, 103, 0.16);
}

.workflow-connector.active {
  background: linear-gradient(90deg, var(--accent), var(--primary));
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

.two-column-flow {
  grid-template-columns: minmax(0, 1.06fr) minmax(360px, 0.94fr);
  align-items: stretch;
}

.paper-panel,
.commentary-panel {
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr);
  gap: 18px;
  min-height: calc(100vh - 290px);
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

.comment-scroll {
  display: grid;
  gap: 14px;
  align-content: start;
  max-height: calc(100vh - 420px);
}

.analysis-card {
  padding: 18px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(19, 63, 103, 0.12);
  display: grid;
  gap: 16px;
}

.analysis-card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.analysis-card-head h3,
.analysis-block h4,
.analysis-block p {
  margin: 0;
}

.analysis-block {
  display: grid;
  gap: 8px;
}

.analysis-block h4 {
  font-size: 14px;
  color: var(--primary);
}

.analysis-block p {
  line-height: 1.75;
}

.analysis-actions {
  display: flex;
  justify-content: flex-end;
}

.rule-tabs {
  display: flex;
  gap: 6px;
  padding: 6px;
  border-radius: 999px;
  background: rgba(19, 63, 103, 0.08);
  width: fit-content;
}

.rule-tab {
  min-height: 40px;
  padding: 0 16px;
  border-radius: 999px;
  border: none;
  background: transparent;
  color: var(--muted);
  font-weight: 600;
}

.rule-tab.active {
  background: rgba(255, 255, 255, 0.92);
  color: var(--primary);
  box-shadow: 0 8px 18px rgba(19, 63, 103, 0.12);
}

.repair-flow {
  grid-template-columns: minmax(360px, 0.94fr) minmax(360px, 1.06fr);
  align-items: stretch;
}

.repair-left-column {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 18px;
}

.action-bar {
  display: grid;
  gap: 16px;
}

.scroll-shell {
  min-height: calc(100vh - 320px);
  max-height: calc(100vh - 320px);
  overflow-y: auto;
  overflow-x: hidden;
  border-radius: 28px;
}

@media (max-width: 1240px) {
  .two-column-flow,
  .repair-flow {
    grid-template-columns: 1fr;
  }

  .paper-panel,
  .commentary-panel,
  .scroll-shell {
    min-height: auto;
    max-height: none;
  }

  .article-scroll,
  .comment-scroll {
    max-height: 65vh;
  }
}

@media (max-width: 900px) {
  .workflow-line {
    grid-template-columns: 1fr;
    gap: 8px;
    justify-items: stretch;
  }

  .workflow-connector {
    display: none;
  }

  .workflow-step {
    justify-content: flex-start;
    padding: 14px 0;
  }
}

@media (max-width: 720px) {
  .column-head,
  .analysis-card-head {
    align-items: flex-start;
    flex-direction: column;
  }

  .rule-tabs {
    width: 100%;
    flex-wrap: wrap;
  }
}
</style>
