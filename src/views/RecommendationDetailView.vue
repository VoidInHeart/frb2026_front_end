<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { fetchRecommendationDetail } from "../services/api";
import { reviewSession, setRecommendationDetail } from "../stores/reviewSession";

const route = useRoute();
const router = useRouter();
const loading = ref(false);
const errorMessage = ref("");

const paperId = computed(() => String(route.params.paperId ?? ""));
const returnFlow = computed(() => String(route.query.fromFlow ?? "repair"));
const detail = computed(
  () => reviewSession.recommendationDetails[paperId.value] ?? null
);
const summaryItem = computed(() =>
  reviewSession.recommendations.find((item) => item.id === paperId.value)
);

async function loadDetail() {
  errorMessage.value = "";
  loading.value = true;

  try {
    const response = await fetchRecommendationDetail(paperId.value);

    if (!response) {
      throw new Error("没有找到该推荐论文详情");
    }

    setRecommendationDetail(paperId.value, response);
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : "详情加载失败";
  } finally {
    loading.value = false;
  }
}

function backToWorkspace() {
  router.push({
    name: "workspace",
    query: {
      flow: returnFlow.value
    }
  });
}

onMounted(async () => {
  if (!detail.value) {
    await loadDetail();
  }
});
</script>

<template>
  <section class="detail-layout">
    <header class="detail-hero glass-card">
      <div class="hero-left">
        <button class="ghost-button back-button" type="button" @click="backToWorkspace()">
          返回上一页
        </button>
        <p class="summary-kicker">第三界面</p>
        <h1 class="section-title detail-title">
          {{ detail?.title || summaryItem?.title || "推荐论文详情" }}
        </h1>
        <p class="section-subtitle">
          展示推荐论文的摘要、相关性分析与可借鉴点，便于从工作台跳转后继续深入查看。
        </p>
      </div>
      <div class="hero-right">
        <span class="pill pill-primary">
          相关度 {{ detail?.relevanceScore || summaryItem?.relevanceScore || "--" }}
        </span>
        <span class="pill pill-neutral">
          {{ detail?.venue || summaryItem?.venue || "Unknown Venue" }}
          {{ detail?.year || summaryItem?.year || "" }}
        </span>
      </div>
    </header>

    <div v-if="errorMessage" class="error-banner">
      {{ errorMessage }}
    </div>

    <div v-if="loading" class="glass-card loading-card">正在加载推荐论文详情...</div>

    <template v-else-if="detail || summaryItem">
      <section class="grid-two">
        <article class="glass-card info-card">
          <p class="info-label">作者</p>
          <strong>{{ detail?.authors || summaryItem?.authors || "暂无作者信息" }}</strong>
        </article>
        <article class="glass-card info-card">
          <p class="info-label">关键词</p>
          <div class="tag-row">
            <span
              v-for="keyword in detail?.keywords || summaryItem?.keywords || []"
              :key="keyword"
              class="tag"
            >
              {{ keyword }}
            </span>
          </div>
        </article>
      </section>

      <section class="grid-two">
        <article class="glass-card content-card">
          <p class="summary-kicker">摘要</p>
          <h2 class="section-title">Abstract</h2>
          <p class="content-text">
            {{ detail?.abstract || "当前接口暂未返回摘要内容。" }}
          </p>
        </article>
        <article class="glass-card content-card">
          <p class="summary-kicker">相关性分析</p>
          <h2 class="section-title">Why It Matters</h2>
          <p class="content-text">
            {{
              detail?.relevanceAnalysis ||
              summaryItem?.reason ||
              "当前接口暂未返回相关性说明。"
            }}
          </p>
        </article>
      </section>

      <section class="glass-card content-card">
        <p class="summary-kicker">借鉴点</p>
        <h2 class="section-title">Key Takeaways</h2>
        <ul class="takeaway-list">
          <li v-for="item in detail?.keyTakeaways || []" :key="item">{{ item }}</li>
        </ul>
      </section>
    </template>
  </section>
</template>

<style scoped>
.detail-layout {
  display: grid;
  gap: 18px;
}

.detail-hero {
  padding: 28px;
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: flex-start;
}

.hero-left {
  display: grid;
  gap: 10px;
}

.summary-kicker {
  margin: 0;
  font-size: 12px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--muted);
}

.detail-title {
  font-size: clamp(28px, 4vw, 44px);
}

.hero-right,
.tag-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.back-button {
  width: fit-content;
}

.error-banner,
.loading-card,
.info-card,
.content-card {
  padding: 22px;
}

.error-banner {
  border-radius: 14px;
  background: rgba(192, 86, 33, 0.12);
  border: 1px solid rgba(192, 86, 33, 0.18);
  color: var(--danger);
}

.loading-card {
  text-align: center;
}

.info-card {
  display: grid;
  gap: 12px;
}

.info-label {
  margin: 0;
  color: var(--muted);
  font-size: 13px;
}

.tag {
  display: inline-flex;
  align-items: center;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(19, 63, 103, 0.08);
  color: var(--primary);
  font-size: 12px;
  font-weight: 700;
}

.content-card {
  display: grid;
  gap: 14px;
}

.content-text {
  margin: 0;
  line-height: 1.8;
}

.takeaway-list {
  margin: 0;
  padding-left: 18px;
  display: grid;
  gap: 10px;
}

@media (max-width: 840px) {
  .detail-hero {
    flex-direction: column;
  }
}
</style>
