<script setup>
import { appearanceState } from "../stores/appearance";

defineProps({
  recommendations: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  }
});

defineEmits(["select"]);
</script>

<template>
  <section
    :class="[
      'recommendation-panel',
      'glass-card',
      { 'recommendation-panel-dark': ['dark', 'sci-fi'].includes(appearanceState.theme) }
    ]"
  >
    <div class="recommendation-header">
      <div>
        <p class="summary-kicker">推荐论文</p>
        <h2 class="section-title">相关论文列表</h2>
      </div>
      <span class="pill pill-accent">{{ recommendations.length }} 篇</span>
    </div>

    <div v-if="loading" class="empty-state">正在获取推荐论文...</div>

    <div v-else-if="recommendations.length" class="recommendation-list">
      <article
        v-for="paper in recommendations"
        :key="paper.id"
        class="recommendation-card"
        @click="$emit('select', paper)"
      >
        <div class="recommendation-rank">0{{ paper.rank }}</div>
        <div class="recommendation-body">
          <div class="recommendation-meta">
            <span class="pill pill-primary">{{ paper.venue }} {{ paper.year }}</span>
            <span class="pill pill-neutral">相关度 {{ paper.relevanceScore }}</span>
          </div>
          <h3>{{ paper.title }}</h3>
          <p class="recommendation-authors">{{ paper.authors }}</p>
          <p class="recommendation-reason">{{ paper.reason }}</p>
          <div class="recommendation-tags">
            <span v-for="keyword in paper.keywords" :key="keyword" class="tag">
              {{ keyword }}
            </span>
          </div>
        </div>
      </article>
    </div>

    <div v-else class="empty-state">
      还没有推荐论文结果，可以点击上方按钮调用推荐接口。
    </div>
  </section>
</template>

<style scoped>
.recommendation-panel {
  padding: 24px;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 18px;
  height: 100%;
  min-height: 100%;
}

.recommendation-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.summary-kicker {
  margin: 0 0 6px;
  font-size: 12px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--muted);
}

.recommendation-list {
  display: grid;
  gap: 14px;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  align-content: start;
}

.recommendation-card {
  padding: 18px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(19, 63, 103, 0.12);
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 16px;
  transition:
    transform 0.2s ease,
    box-shadow 0.2s ease,
    border-color 0.2s ease;
}

.recommendation-card:hover {
  transform: translateY(-2px);
  border-color: rgba(19, 63, 103, 0.22);
  box-shadow: 0 18px 40px rgba(19, 63, 103, 0.1);
}

.recommendation-rank {
  min-width: 48px;
  height: 48px;
  border-radius: 16px;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, rgba(208, 122, 53, 0.18), rgba(19, 63, 103, 0.12));
  color: var(--primary);
  font-weight: 800;
}

.recommendation-body {
  display: grid;
  gap: 10px;
}

.recommendation-meta,
.recommendation-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.recommendation-body h3 {
  margin: 0;
  font-size: 19px;
}

.recommendation-authors,
.recommendation-reason {
  margin: 0;
  color: var(--muted);
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

.recommendation-panel-dark .recommendation-card {
  background: rgba(255, 255, 255, 0.12);
}

.recommendation-panel-dark .recommendation-rank {
  background: linear-gradient(
    135deg,
    rgba(208, 122, 53, 0.1),
    rgba(19, 63, 103, 0.08)
  );
}

.recommendation-panel-dark .tag {
  background: rgba(255, 255, 255, 0.12);
}

@media (max-width: 640px) {
  .recommendation-card {
    grid-template-columns: 1fr;
  }
}
</style>
