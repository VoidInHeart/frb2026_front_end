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
  },
  runState: {
    type: Object,
    default: null
  },
  summaryReady: {
    type: Boolean,
    default: false
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
    label: "方法与创新点",
    kicker: "Stage 03"
  },
  {
    id: "summary",
    label: "汇总",
    kicker: "Stage 04"
  }
];

function getRunStageStatus(stageId) {
  return (
    props.runState?.stageRuns?.find((item) => item.stageName === stageId)?.status ?? ""
  );
}

function getStageStatus(stageId) {
  const runStageStatus = getRunStageStatus(stageId);

  if (runStageStatus) {
    return runStageStatus;
  }

  if (stageId === "summary") {
    if (props.summaryReady) {
      return "completed";
    }

    return props.activeStage === "summary" ? "running" : "pending";
  }

  if (props.reviews?.[stageId]?.stageStatus) {
    return props.reviews[stageId].stageStatus;
  }

  if (props.reviews?.[stageId]) {
    return "completed";
  }

  if (props.activeStage === stageId) {
    return "running";
  }

  return "pending";
}

function isReached(status) {
  return ["completed", "skipped", "running", "waiting"].includes(status);
}

const completedCount = computed(
  () =>
    stageItems.filter((item) =>
      ["completed", "skipped"].includes(getStageStatus(item.id))
    ).length
);

const trackerCopy = computed(() => {
  if (props.runState?.status === "aborted") {
    return "当前 run 已终止，后续阶段不会继续触发。";
  }

  if (props.runState?.status === "failed") {
    return "当前 run 执行失败，请先处理错误后再重试。";
  }

  const severeStage = stageItems.find((item) => props.reviews?.[item.id]?.severe);

  if (severeStage) {
    return `${severeStage.label}发现高优先级问题，流程可能提前进入汇总。`;
  }

  if (props.runState?.status === "waiting") {
    return "当前 run 处于等待决策状态，请先执行继续、跳过或终止。";
  }

  return "阶段顺序由后端 run state 控制，前端只在当前允许阶段触发执行。";
});
</script>

<template>
  <section class="tracker-card glass-card">
    <div class="tracker-head">
      <div>
        <p class="summary-kicker">运行主线</p>
        <h2 class="section-title">四阶段进度</h2>
        <p class="tracker-copy">{{ trackerCopy }}</p>
      </div>

      <div class="tracker-summary">
        <span class="pill pill-neutral">已完成 {{ completedCount }}/4</span>
        <span class="pill pill-primary">{{ props.runState?.status || "idle" }}</span>
      </div>
    </div>

    <div class="tracker-line" aria-label="四阶段进度">
      <template v-for="(item, index) in stageItems" :key="item.id">
        <div
          class="tracker-node"
          :class="{
            reached: isReached(getStageStatus(item.id)),
            active: activeStage === item.id
          }"
        >
          <span class="tracker-dot"></span>
          <div class="tracker-text">
            <small>{{ item.kicker }}</small>
            <strong>{{ item.label }}</strong>
            <span class="tracker-status">{{ getStageStatus(item.id) }}</span>
          </div>
        </div>

        <div
          v-if="index < stageItems.length - 1"
          class="tracker-connector"
          :class="{ reached: isReached(getStageStatus(item.id)) }"
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

.tracker-line {
  display: grid;
  grid-template-columns: auto minmax(36px, 1fr) auto minmax(36px, 1fr) auto minmax(36px, 1fr) auto;
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

.tracker-node.active {
  color: var(--primary);
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

.tracker-node.active .tracker-dot {
  border-color: rgba(19, 63, 103, 0.55);
  background: rgba(19, 63, 103, 0.14);
}

.tracker-text {
  display: grid;
  gap: 2px;
}

.tracker-text small,
.tracker-status {
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.tracker-status {
  color: var(--muted);
}

.tracker-connector {
  height: 2px;
  background: rgba(95, 108, 123, 0.18);
}

.tracker-connector.reached {
  background: linear-gradient(90deg, rgba(47, 133, 90, 0.35), rgba(47, 133, 90, 0.8));
}

@media (max-width: 960px) {
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
