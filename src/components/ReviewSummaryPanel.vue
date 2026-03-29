<script setup>
defineProps({
  reviewSummary: {
    type: Object,
    default: null
  },
  transmissionStatus: {
    type: Object,
    default: null
  },
  reviewLoading: {
    type: Boolean,
    default: false
  }
});
</script>

<template>
  <section class="summary-panel glass-card">
    <div class="summary-header">
      <div>
        <p class="summary-kicker">评审概览</p>
        <h2 class="section-title">评语与维度评分</h2>
      </div>
      <span
        class="pill"
        :class="transmissionStatus?.success ? 'pill-success' : 'pill-neutral'"
      >
        {{
          transmissionStatus?.success
            ? "document_ir.json 已发送"
            : "等待传输 document_ir.json"
        }}
      </span>
    </div>

    <div v-if="reviewLoading" class="empty-state">正在生成评语与分维度评分...</div>

    <template v-else-if="reviewSummary">
      <div class="summary-topline">
        <div class="score-chip">
          <span>综合评分</span>
          <strong>{{ reviewSummary.overallScore }}</strong>
        </div>
        <div class="verdict-block">
          <span class="muted-text">建议结论</span>
          <strong>{{ reviewSummary.verdict }}</strong>
        </div>
      </div>

      <p class="summary-text">{{ reviewSummary.summary }}</p>

      <div class="score-grid">
        <article
          v-for="item in reviewSummary.dimensionScores"
          :key="item.label"
          class="score-card"
        >
          <div class="score-card-head">
            <span>{{ item.label }}</span>
            <strong>{{ item.score }}</strong>
          </div>
          <div class="score-track">
            <div
              class="score-track-fill"
              :style="{ width: `${item.score}%` }"
            ></div>
          </div>
        </article>
      </div>

      <div class="insight-grid">
        <section class="insight-card">
          <h3>亮点</h3>
          <ul>
            <li v-for="item in reviewSummary.strengths" :key="item">{{ item }}</li>
          </ul>
        </section>
        <section class="insight-card">
          <h3>待完善点</h3>
          <ul>
            <li v-for="item in reviewSummary.weaknesses" :key="item">{{ item }}</li>
          </ul>
        </section>
      </div>

      <section class="insight-card">
        <h3>建议动作</h3>
        <ul>
          <li v-for="item in reviewSummary.nextActions" :key="item">{{ item }}</li>
        </ul>
      </section>
    </template>

    <div v-else class="empty-state">
      还没有评语结果，可以点击上方按钮调用生成评语接口。
    </div>
  </section>
</template>

<style scoped>
.summary-panel {
  padding: 24px;
  display: grid;
  gap: 20px;
}

.summary-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.summary-kicker {
  margin: 0 0 6px;
  font-size: 12px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--muted);
}

.summary-topline {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.score-chip,
.verdict-block {
  min-width: 180px;
  padding: 18px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(19, 63, 103, 0.12);
  display: grid;
  gap: 8px;
}

.score-chip strong {
  font-size: 34px;
  color: var(--primary);
  line-height: 1;
}

.verdict-block strong {
  font-size: 18px;
}

.summary-text {
  margin: 0;
  line-height: 1.8;
}

.score-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.score-card {
  padding: 14px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(19, 63, 103, 0.12);
  display: grid;
  gap: 10px;
}

.score-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  font-weight: 700;
}

.score-track {
  width: 100%;
  height: 10px;
  border-radius: 999px;
  background: rgba(19, 63, 103, 0.08);
  overflow: hidden;
}

.score-track-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #d07a35, #133f67);
}

.insight-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.insight-card {
  padding: 18px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(19, 63, 103, 0.12);
}

.insight-card h3 {
  margin: 0 0 12px;
  font-size: 17px;
}

.insight-card ul {
  margin: 0;
  padding-left: 18px;
  display: grid;
  gap: 10px;
}

@media (max-width: 720px) {
  .score-grid,
  .insight-grid {
    grid-template-columns: 1fr;
  }
}
</style>
