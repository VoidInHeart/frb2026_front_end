<script setup>
import { ref, watch } from "vue";

const props = defineProps({
  recommendations: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  },
  collapsible: {
    type: Boolean,
    default: false
  },
  defaultExpanded: {
    type: Boolean,
    default: true
  }
});

const emit = defineEmits(["select"]);

const expanded = ref(props.collapsible ? props.defaultExpanded : true);

watch(
  () => props.collapsible,
  (value) => {
    expanded.value = value ? props.defaultExpanded : true;
  },
  { immediate: true }
);

watch(
  () => props.defaultExpanded,
  (value) => {
    if (props.collapsible) {
      expanded.value = value;
    }
  }
);

function toggleExpanded() {
  if (!props.collapsible) {
    return;
  }

  expanded.value = !expanded.value;
}

function openRecommendation(paper) {
  emit("select", paper);
}
</script>

<template>
  <section class="recommendation-panel glass-card">
    <div class="recommendation-header">
      <div>
        <p class="summary-kicker">推荐论文</p>
        <h2 class="section-title">相关论文列表</h2>
        <p v-if="collapsible && !expanded" class="collapsed-copy">
          推荐模块默认折叠，按需展开后再进入详情页。
        </p>
      </div>

      <div class="recommendation-header-actions">
        <span class="pill pill-accent">{{ recommendations.length }} 篇</span>
        <button
          v-if="collapsible"
          class="ghost-button compact-toggle"
          type="button"
          @click="toggleExpanded"
        >
          {{ expanded ? "收起" : "展开" }}
        </button>
      </div>
    </div>

    <div v-if="collapsible && !expanded" class="empty-state">
      推荐论文已折叠。展开后可查看推荐理由并跳转到论文详情。
    </div>

    <div v-else-if="loading" class="empty-state">正在获取推荐论文...</div>

    <div v-else-if="recommendations.length" class="recommendation-list">
      <article
        v-for="paper in recommendations"
        :key="paper.id"
        class="recommendation-card"
      >
        <div class="recommendation-rank">
          {{ String(paper.rank ?? 0).padStart(2, "0") }}
        </div>

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

          <div class="recommendation-actions">
            <button
              class="secondary-button"
              type="button"
              @click="openRecommendation(paper)"
            >
              查看详情
            </button>
          </div>
        </div>
      </article>
    </div>

    <div v-else class="empty-state">
      当前还没有推荐论文结果。
    </div>
  </section>
</template>

<style scoped>
.recommendation-panel {
  padding: 24px;
  display: grid;
  gap: 18px;
}

.recommendation-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.recommendation-header-actions {
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

.collapsed-copy {
  margin: 10px 0 0;
  color: var(--muted);
  line-height: 1.7;
}

.compact-toggle {
  min-height: 38px;
  border-radius: 12px;
}

.recommendation-list {
  display: grid;
  gap: 14px;
}

.recommendation-card {
  padding: 18px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(19, 63, 103, 0.12);
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 16px;
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
  line-height: 1.75;
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

.recommendation-actions {
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 640px) {
  .recommendation-header,
  .recommendation-card {
    grid-template-columns: 1fr;
  }

  .recommendation-header {
    flex-direction: column;
  }

  .recommendation-header-actions,
  .recommendation-actions {
    justify-content: flex-start;
  }
}
</style>
