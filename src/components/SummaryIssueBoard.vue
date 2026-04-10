<script setup>
import { computed } from "vue";

const props = defineProps({
  summary: {
    type: Object,
    default: null
  }
});

const issues = computed(() => props.summary?.issues ?? []);

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
  <section class="summary-issue-board glass-card">
    <div class="board-head">
      <div>
        <p class="summary-kicker">汇总左栏</p>
        <h2 class="section-title">问题与证据链</h2>
      </div>
      <span class="pill pill-primary">{{ issues.length }} 个问题</span>
    </div>

    <div v-if="issues.length" class="issue-list">
      <details
        v-for="issue in issues"
        :key="issue.id"
        class="issue-card"
        open
      >
        <summary class="issue-summary">
          <div class="issue-summary-main">
            <div class="issue-tag-row">
              <span class="issue-stage-tag">{{ issue.stageLabel }}</span>
              <span class="issue-location">{{ issue.location }}</span>
            </div>
            <h3>{{ issue.title }}</h3>
          </div>
          <span class="severity-badge" :class="getSeverityClass(issue.severity)">
            {{ issue.severity }}
          </span>
        </summary>

        <div class="issue-body">
          <p class="issue-description">{{ issue.description }}</p>

          <details class="evidence-box">
            <summary>证据链</summary>
            <ul>
              <li v-for="item in issue.evidence" :key="item">{{ item }}</li>
            </ul>
          </details>
        </div>
      </details>
    </div>

    <div v-else class="empty-state">
      当前还没有可汇总的问题。
    </div>
  </section>
</template>

<style scoped>
.summary-issue-board {
  padding: 24px;
  display: grid;
  gap: 18px;
}

.board-head {
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

.issue-list {
  display: grid;
  gap: 14px;
}

.issue-card,
.evidence-box {
  border: 1px solid rgba(19, 63, 103, 0.12);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.68);
}

.issue-summary,
.evidence-box > summary {
  list-style: none;
  cursor: pointer;
}

.issue-summary::-webkit-details-marker,
.evidence-box > summary::-webkit-details-marker {
  display: none;
}

.issue-summary {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 20px;
}

.issue-summary-main {
  display: grid;
  gap: 10px;
  min-width: 0;
}

.issue-tag-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.issue-stage-tag,
.issue-location {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.issue-stage-tag {
  background: rgba(19, 63, 103, 0.08);
  color: var(--primary);
}

.issue-location {
  background: rgba(95, 108, 123, 0.08);
  color: var(--muted);
}

.issue-summary h3 {
  margin: 0;
  font-size: 18px;
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

.issue-body {
  padding: 0 20px 20px;
  display: grid;
  gap: 14px;
}

.issue-description {
  margin: 0;
  line-height: 1.75;
}

.evidence-box {
  overflow: hidden;
}

.evidence-box > summary {
  padding: 14px 16px;
  font-weight: 700;
  color: var(--primary);
  border-bottom: 1px solid transparent;
}

.evidence-box[open] > summary {
  border-bottom-color: rgba(19, 63, 103, 0.1);
}

.evidence-box ul {
  margin: 0;
  padding: 0 18px 18px 34px;
  display: grid;
  gap: 10px;
  color: var(--muted);
}

@media (max-width: 720px) {
  .board-head,
  .issue-summary {
    flex-direction: column;
  }
}
</style>
