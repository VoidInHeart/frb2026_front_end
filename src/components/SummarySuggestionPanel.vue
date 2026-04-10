<script setup>
import { computed } from "vue";

const props = defineProps({
  summary: {
    type: Object,
    default: null
  },
  transmissionStatus: {
    type: Object,
    default: null
  },
  loading: {
    type: Boolean,
    default: false
  }
});

const suggestions = computed(() => props.summary?.modificationSuggestions ?? []);
</script>

<template>
  <section class="summary-panel glass-card">
    <div class="summary-head">
      <div>
        <p class="summary-kicker">汇总右栏</p>
        <h2 class="section-title">修改建议</h2>
      </div>
      <span
        class="pill"
        :class="transmissionStatus?.success ? 'pill-success' : 'pill-neutral'"
      >
        {{ transmissionStatus?.success ? "解析结果已同步" : "等待同步解析结果" }}
      </span>
    </div>

    <div v-if="loading" class="empty-state">
      正在整理汇总结果...
    </div>

    <template v-else-if="summary">
      <div class="summary-banner">
        <strong>{{ summary.verdict }}</strong>
        <p>{{ summary.overview }}</p>
      </div>

      <div v-if="summary.skippedAfterStageLabel" class="summary-note">
        后续流程已在“{{ summary.skippedAfterStageLabel }}”后提前收束，请优先处理该阶段的严重问题。
      </div>

      <div v-if="suggestions.length" class="suggestion-list">
        <article
          v-for="item in suggestions"
          :key="item.id"
          class="suggestion-card"
        >
          <div class="suggestion-head">
            <h3>{{ item.title }}</h3>
            <span class="pill pill-neutral">{{ item.stageLabel }}</span>
          </div>
          <p>{{ item.content }}</p>
        </article>
      </div>

      <div v-else class="empty-state">
        当前还没有可展示的修改建议。
      </div>
    </template>

    <div v-else class="empty-state">
      进入汇总后会在这里展示修改建议。
    </div>
  </section>
</template>

<style scoped>
.summary-panel {
  padding: 24px;
  display: grid;
  gap: 18px;
}

.summary-head {
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

.summary-banner {
  padding: 18px;
  border-radius: 20px;
  background: rgba(19, 63, 103, 0.08);
  border: 1px solid rgba(19, 63, 103, 0.14);
}

.summary-banner strong,
.summary-banner p {
  margin: 0;
}

.summary-banner p {
  margin-top: 10px;
  line-height: 1.75;
  color: var(--muted);
}

.summary-note {
  padding: 14px 16px;
  border-radius: 18px;
  background: rgba(208, 122, 53, 0.1);
  border: 1px solid rgba(208, 122, 53, 0.18);
  color: var(--accent);
  line-height: 1.7;
}

.suggestion-list {
  display: grid;
  gap: 14px;
}

.suggestion-card {
  padding: 18px;
  border-radius: 20px;
  border: 1px solid rgba(19, 63, 103, 0.12);
  background: rgba(255, 255, 255, 0.68);
  display: grid;
  gap: 10px;
}

.suggestion-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.suggestion-head h3,
.suggestion-card p {
  margin: 0;
}

.suggestion-card p {
  line-height: 1.75;
}

@media (max-width: 720px) {
  .summary-head,
  .suggestion-head {
    flex-direction: column;
  }
}
</style>
