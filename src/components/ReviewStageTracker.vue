<script setup>
import { computed } from "vue";

const props = defineProps({
  activeStage: {
    type: String,
    default: "format"
  },
  reviews: {
    type: Object,
    default: () => ({})
  }
});

const stageItems = [
  {
    id: "format",
    label: "格式审查",
    kicker: "Stage 01"
  },
  {
    id: "logic",
    label: "逻辑审查",
    kicker: "Stage 02"
  },
  {
    id: "innovation",
    label: "方法与创新点审查",
    kicker: "Stage 03"
  }
];

const activeIndex = computed(() => {
  if (props.activeStage === "summary") {
    return stageItems.length - 1;
  }

  const index = stageItems.findIndex((item) => item.id === props.activeStage);
  return index === -1 ? 0 : index;
});

const completedCount = computed(
  () => stageItems.filter((item) => Boolean(props.reviews?.[item.id])).length
);

const severeStageLabel = computed(
  () => stageItems.find((item) => props.reviews?.[item.id]?.severe)?.label ?? ""
);

const trackerCopy = computed(() =>
  severeStageLabel.value
    ? `${severeStageLabel.value}发现严重问题，后续阶段将被跳过。`
    : "已执行或正在执行的阶段以绿色显示，未执行阶段保持灰色，严重问题会直接提前进入汇总环节。"
);

function isReached(itemId, index) {
  if (props.activeStage === "summary") {
    return Boolean(props.reviews?.[itemId]);
  }

  return index < activeIndex.value || props.activeStage === itemId;
}
</script>

<template>
  <section class="tracker-card glass-card">
    <div class="tracker-head">
      <div>
        <p class="summary-kicker">审查主线</p>
        <h2 class="section-title">三阶段审查进度</h2>
        <p class="tracker-copy">
          {{ trackerCopy }}
        </p>
      </div>
      <div class="tracker-summary">
        <span class="pill pill-neutral">已完成 {{ completedCount }}/3</span>
        <span
          class="summary-chip"
          :class="{ active: activeStage === 'summary' }"
        >
          汇总
        </span>
      </div>
    </div>

    <div class="tracker-line" aria-label="三阶段审查进度">
      <template v-for="(item, index) in stageItems" :key="item.id">
        <div class="tracker-node" :class="{ reached: isReached(item.id, index) }">
          <span class="tracker-dot"></span>
          <div class="tracker-text">
            <small>{{ item.kicker }}</small>
            <strong>{{ item.label }}</strong>
          </div>
        </div>
        <div
          v-if="index < stageItems.length - 1"
          class="tracker-connector"
          :class="{ reached: index < activeIndex }"
        ></div>
      </template>
    </div>
  </section>
</template>

<style scoped>
.tracker-card {
  padding: 22px 24px;
  display: grid;
  gap: 18px;
}

.tracker-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
}

.summary-kicker {
  margin: 0 0 6px;
  font-size: 12px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--muted);
}

.tracker-copy {
  margin: 10px 0 0;
  color: var(--muted);
  line-height: 1.7;
  max-width: 720px;
}

.tracker-summary {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.summary-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 38px;
  padding: 0 14px;
  border-radius: 999px;
  border: 1px solid rgba(95, 108, 123, 0.18);
  background: rgba(95, 108, 123, 0.08);
  color: var(--muted);
  font-weight: 700;
}

.summary-chip.active {
  border-color: rgba(47, 133, 90, 0.28);
  background: rgba(47, 133, 90, 0.12);
  color: var(--success);
}

.tracker-line {
  display: grid;
  grid-template-columns: auto minmax(56px, 1fr) auto minmax(56px, 1fr) auto;
  align-items: center;
}

.tracker-node {
  display: inline-flex;
  align-items: center;
  gap: 14px;
  color: var(--muted);
}

.tracker-node.reached {
  color: var(--success);
}

.tracker-dot {
  width: 18px;
  height: 18px;
  border-radius: 999px;
  border: 3px solid rgba(95, 108, 123, 0.28);
  background: rgba(255, 255, 255, 0.92);
}

.tracker-node.reached .tracker-dot {
  border-color: rgba(47, 133, 90, 0.6);
  background: rgba(47, 133, 90, 0.18);
}

.tracker-text {
  display: grid;
  gap: 2px;
}

.tracker-text small {
  font-size: 12px;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.tracker-text strong {
  font-size: 15px;
}

.tracker-connector {
  height: 2px;
  background: rgba(95, 108, 123, 0.18);
}

.tracker-connector.reached {
  background: linear-gradient(90deg, rgba(47, 133, 90, 0.35), rgba(47, 133, 90, 0.8));
}

@media (max-width: 900px) {
  .tracker-head {
    flex-direction: column;
  }

  .tracker-summary {
    justify-content: flex-start;
  }

  .tracker-line {
    grid-template-columns: 1fr;
    gap: 10px;
  }

  .tracker-connector {
    display: none;
  }
}
</style>
