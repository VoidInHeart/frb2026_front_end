<script setup>
defineProps({
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
  actionLabel: {
    type: String,
    default: "进入下一阶段"
  },
  actionDisabled: {
    type: Boolean,
    default: false
  }
});

defineEmits(["next"]);

function getSeverityClass(severity) {
  if (severity === "严重") {
    return "severity-critical";
  }

  if (severity === "一般") {
    return "severity-major";
  }

  return "severity-minor";
}
</script>

<template>
  <section class="findings-panel glass-card">
    <div class="panel-head">
      <div>
        <p class="summary-kicker">{{ kicker }}</p>
        <h2 class="section-title">{{ title }}</h2>
      </div>
      <span
        v-if="result"
        class="pill"
        :class="result.severe ? 'pill-accent' : 'pill-success'"
      >
        {{ result.severe ? "存在严重问题" : "可继续推进" }}
      </span>
    </div>

    <div v-if="loading" class="empty-state panel-empty">
      正在载入当前阶段的审查结果...
    </div>

    <template v-else-if="result">
      <div class="result-banner" :class="{ 'result-banner-critical': result.severe }">
        <strong>{{ result.headline }}</strong>
        <p>{{ result.overview }}</p>
      </div>

      <div v-if="result.issues.length" class="finding-list">
        <article v-for="issue in result.issues" :key="issue.id" class="finding-card">
          <div class="finding-head">
            <div>
              <div class="finding-title-row">
                <h3>{{ issue.title }}</h3>
                <span class="finding-location">{{ issue.location }}</span>
              </div>
            </div>
            <span class="severity-badge" :class="getSeverityClass(issue.severity)">
              {{ issue.severity }}
            </span>
          </div>
          <p class="finding-description">{{ issue.description }}</p>
        </article>
      </div>

      <div v-else class="empty-state panel-empty">
        当前阶段未发现需要阻断流程的问题，可以继续进入下一阶段。
      </div>
    </template>

    <div v-else class="empty-state panel-empty">
      当前阶段还没有结果。
    </div>

    <div class="panel-footer">
      <button
        class="primary-button footer-button"
        type="button"
        :disabled="actionDisabled || loading || !result"
        @click="$emit('next')"
      >
        {{ actionLabel }}
      </button>
    </div>
  </section>
</template>

<style scoped>
.findings-panel {
  padding: 24px;
  display: grid;
  grid-template-rows: auto minmax(0, auto) minmax(0, 1fr) auto;
  gap: 18px;
  min-height: calc(100vh - 320px);
}

.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.summary-kicker {
  margin: 0 0 6px;
  font-size: 12px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--muted);
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
}

.panel-footer {
  display: flex;
  justify-content: flex-end;
}

.footer-button {
  min-width: 220px;
}

@media (max-width: 720px) {
  .panel-head,
  .finding-head {
    flex-direction: column;
  }

  .panel-footer {
    justify-content: stretch;
  }

  .footer-button {
    width: 100%;
  }
}
</style>
