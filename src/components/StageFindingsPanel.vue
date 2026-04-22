<script setup>
import { computed } from "vue";

const props = defineProps({
  kicker: {
    type: String,
    default: ""
  },
  title: {
    type: String,
    default: ""
  },
  result: {
    type: Object,
    default: null
  },
  loading: {
    type: Boolean,
    default: false
  },
  actions: {
    type: Array,
    default: () => []
  },
  footerAction: {
    type: Object,
    default: null
  },
  startAction: {
    type: Object,
    default: null
  },
  statusText: {
    type: String,
    default: ""
  }
});

const emit = defineEmits(["action", "footer", "start"]);

function normalizeStatusLabel(value) {
  return String(value ?? "").trim().toLowerCase();
}

function getSeverityClass(severity) {
  if (severity === "严重" || severity === "critical" || severity === "major") {
    return "severity-critical";
  }

  if (severity === "一般" || severity === "medium" || severity === "warning") {
    return "severity-major";
  }

  return "severity-minor";
}

function getActionClass(variant) {
  if (variant === "ghost") {
    return "ghost-button";
  }

  if (variant === "secondary") {
    return "secondary-button";
  }

  return "primary-button";
}

const visibleActions = computed(() => props.actions.filter(Boolean));
const resultStatusText = computed(
  () => props.result?.stageStatus || (props.result?.severe ? "critical" : "completed")
);
const shouldShowStatusText = computed(() => {
  if (!props.statusText) {
    return false;
  }

  if (!props.result) {
    return true;
  }

  return normalizeStatusLabel(props.statusText) !== normalizeStatusLabel(resultStatusText.value);
});
const hasFooterAction = computed(() => Boolean(props.footerAction));
const hasStartAction = computed(() => Boolean(props.startAction));
</script>

<template>
  <section class="findings-panel glass-card">
    <div class="panel-head">
      <div>
        <p class="summary-kicker">{{ props.kicker }}</p>
        <h2 class="section-title">{{ props.title }}</h2>
      </div>

      <div class="panel-badges">
        <span v-if="shouldShowStatusText" class="pill pill-neutral">{{ props.statusText }}</span>
        <span
          v-if="props.result"
          class="pill"
          :class="props.result.severe ? 'pill-accent' : 'pill-success'"
        >
          {{ resultStatusText }}
        </span>
      </div>
    </div>

    <div v-if="props.loading && !props.result" class="panel-body panel-body-empty">
      <div class="empty-state panel-empty">正在读取当前阶段结果...</div>
    </div>

    <div v-else-if="props.result" class="panel-body">
      <div class="banner-stack">
        <div v-if="props.loading" class="result-banner result-banner-progress">
          <strong>当前结果持续更新中</strong>
          <p>后端已经返回本阶段的累计结果，页面会继续轮询并逐步刷新。</p>
        </div>

        <div class="result-banner" :class="{ 'result-banner-critical': props.result.severe }">
          <strong>{{ props.result.headline }}</strong>
          <p>{{ props.result.overview }}</p>
        </div>
      </div>

      <div v-if="props.result.issues?.length" class="finding-list">
        <article v-for="issue in props.result.issues" :key="issue.id" class="finding-card">
          <div class="finding-head">
            <div>
              <div class="finding-title-row">
                <h3>{{ issue.title }}</h3>
                <span class="finding-location">{{ issue.location }}</span>
              </div>
              <div v-if="issue.ruleLabel || issue.ruleId" class="finding-meta-row">
                <span class="finding-rule-tag">
                  {{ issue.ruleLabel || issue.ruleId }}
                </span>
                <span v-if="issue.ruleLabel && issue.ruleId" class="finding-rule-id">
                  {{ issue.ruleId }}
                </span>
              </div>
            </div>
            <span class="severity-badge" :class="getSeverityClass(issue.severity)">
              {{ issue.severity }}
            </span>
          </div>

          <p class="finding-description">{{ issue.description }}</p>
        </article>
      </div>

      <div v-else class="empty-state panel-empty panel-empty-compact">
        当前阶段没有可展示的问题结果。
      </div>
    </div>

    <div v-else class="panel-body panel-body-empty">
      <div class="empty-state panel-empty">
        当前阶段还没有结果，可以按当前 run state 触发执行或决策。
      </div>
    </div>

    <div v-if="hasStartAction" class="standalone-action-row">
      <button
        class="primary-button standalone-action-button"
        type="button"
        :disabled="props.startAction.disabled"
        @click="emit('start')"
      >
        {{ props.startAction.label }}
      </button>
      <p v-if="props.startAction.hint" class="standalone-action-hint">
        {{ props.startAction.hint }}
      </p>
    </div>

    <div v-if="visibleActions.length || hasFooterAction" class="panel-footer">
      <div v-if="visibleActions.length" class="action-row">
        <span
          v-for="action in visibleActions"
          :key="action.key"
          class="action-button-wrap"
          :class="{ 'action-button-wrap-tooltip': action.disabled && action.disabledReason }"
          :title="action.disabled && action.disabledReason ? action.disabledReason : null"
          :data-tooltip="action.disabled && action.disabledReason ? action.disabledReason : null"
        >
          <button
            :class="getActionClass(action.variant)"
            type="button"
            :disabled="action.disabled"
            @click="emit('action', action.key)"
          >
            {{ action.label }}
          </button>
        </span>
      </div>

      <button
        v-else-if="hasFooterAction"
        class="primary-button footer-button"
        type="button"
        :disabled="props.footerAction.disabled"
        @click="emit('footer')"
      >
        {{ props.footerAction.label }}
      </button>
    </div>
  </section>
</template>

<style scoped>
.findings-panel {
  padding: 24px;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 18px;
  min-height: var(--workspace-panel-height, 750px);
  max-height: var(--workspace-panel-height, 1050px);
}

.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.panel-badges {
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

.panel-body {
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 16px;
}

.panel-body-empty {
  grid-template-rows: minmax(0, 1fr);
}

.banner-stack {
  display: grid;
  gap: 12px;
}

.result-banner {
  padding: 18px;
  border-radius: 20px;
  background: rgba(47, 133, 90, 0.08);
  border: 1px solid rgba(47, 133, 90, 0.16);
}

.result-banner-critical {
  background: rgba(208, 122, 53, 0.1);
  border-color: rgba(208, 122, 53, 0.18);
}

.result-banner-progress {
  background: rgba(19, 63, 103, 0.08);
  border-color: rgba(19, 63, 103, 0.16);
}

.result-banner strong,
.result-banner p {
  margin: 0;
}

.result-banner p {
  margin-top: 10px;
  color: var(--muted);
  line-height: 1.7;
}

.finding-list {
  display: grid;
  gap: 14px;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  align-content: start;
  padding-right: 4px;
}

.finding-card {
  padding: 18px;
  border-radius: 20px;
  border: 1px solid rgba(19, 63, 103, 0.12);
  background: rgba(255, 255, 255, 0.68);
  display: grid;
  gap: 12px;
}

.finding-meta-row {
  margin-top: 10px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.finding-rule-tag,
.finding-rule-id {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.finding-rule-tag {
  background: rgba(19, 63, 103, 0.08);
  color: var(--primary);
}

.finding-rule-id {
  background: rgba(95, 108, 123, 0.08);
  color: var(--muted);
}

.finding-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.finding-title-row {
  display: grid;
  gap: 8px;
}

.finding-title-row h3 {
  margin: 0;
  font-size: 18px;
}

.finding-location {
  color: var(--muted);
  font-size: 13px;
}

.finding-description {
  margin: 0;
  color: var(--text);
  line-height: 1.75;
}

.severity-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 64px;
  padding: 7px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.severity-critical {
  background: rgba(217, 72, 72, 0.12);
  color: #c53030;
}

.severity-major {
  background: rgba(208, 122, 53, 0.12);
  color: var(--accent);
}

.severity-minor {
  background: rgba(19, 63, 103, 0.08);
  color: var(--primary);
}

.panel-empty {
  min-height: 160px;
  display: grid;
  place-items: center;
  text-align: center;
}

.panel-empty-compact {
  min-height: 0;
  align-content: start;
}

.standalone-action-row {
  display: grid;
  gap: 10px;
  justify-items: start;
}

.standalone-action-button {
  min-width: 220px;
}

.standalone-action-hint {
  margin: 0;
  color: var(--muted);
  line-height: 1.7;
}

.panel-footer {
  display: flex;
  justify-content: flex-end;
}

.action-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.action-button-wrap {
  position: relative;
  display: inline-flex;
}

.action-button-wrap-tooltip {
  cursor: not-allowed;
}

.action-button-wrap-tooltip > button {
  pointer-events: none;
}

.action-button-wrap-tooltip::after {
  content: attr(data-tooltip);
  position: absolute;
  right: 0;
  bottom: calc(100% + 10px);
  min-width: 220px;
  max-width: 260px;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(15, 23, 42, 0.94);
  color: #fff;
  font-size: 12px;
  line-height: 1.5;
  box-shadow: 0 18px 36px rgba(15, 23, 42, 0.18);
  opacity: 0;
  transform: translateY(4px);
  pointer-events: none;
  transition: opacity 0.16s ease, transform 0.16s ease;
  z-index: 2;
}

.action-button-wrap-tooltip:hover::after {
  opacity: 1;
  transform: translateY(0);
}

.footer-button {
  min-width: 220px;
}

@media (max-width: 1240px) {
  .findings-panel {
    min-height: auto;
    max-height: none;
  }
}

@media (max-width: 720px) {
  .panel-head,
  .finding-head {
    flex-direction: column;
  }

  .panel-footer,
  .action-row,
  .standalone-action-row {
    justify-content: stretch;
  }

  .action-row > .action-button-wrap,
  .footer-button,
  .standalone-action-button,
  .action-row > .action-button-wrap > button {
    width: 100%;
  }
}
</style>
