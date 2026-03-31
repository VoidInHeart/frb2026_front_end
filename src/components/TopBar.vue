<script setup>
import { computed } from "vue";
import { RouterLink, useRoute } from "vue-router";
import { reviewSession } from "../stores/reviewSession";

const route = useRoute();
const workspaceReady = computed(() => Boolean(reviewSession.currentSubmission));
const ruleSelectionCount = computed(
  () => reviewSession.ruleLibrary.selectedSystemRuleIds.length
);
</script>

<template>
  <header class="topbar glass-card">
    <div class="topbar-brand">
      <div class="topbar-kicker">Paper Review Frontend</div>
      <RouterLink class="topbar-title" to="/">论文评分系统</RouterLink>
    </div>
    <nav class="topbar-nav">
      <RouterLink
        class="nav-link"
        :class="{ active: route.name === 'upload' }"
        to="/"
      >
        上传
      </RouterLink>
      <RouterLink
        class="nav-link"
        :class="{ active: route.name === 'rule-library-management' }"
        to="/rule-library"
      >
        规则库管理
      </RouterLink>
      <RouterLink
        class="nav-link"
        :class="{
          active: route.name === 'workspace',
          disabled: !workspaceReady
        }"
        :to="workspaceReady ? '/workspace' : '/'"
      >
        工作台
      </RouterLink>
      <span class="pill pill-primary">
        {{ workspaceReady ? "已加载论文" : "等待上传" }}
      </span>
      <span class="pill pill-neutral">
        {{ `已选规则 ${ruleSelectionCount}` }}
      </span>
    </nav>
  </header>
</template>

<style scoped>
.topbar {
  position: sticky;
  top: 14px;
  z-index: 8;
  width: min(calc(100% - 32px), var(--content-width));
  margin: 18px auto 0;
  padding: 16px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.topbar-brand {
  display: grid;
  gap: 4px;
}

.topbar-kicker {
  font-size: 12px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--muted);
}

.topbar-title {
  font-family: Georgia, "Times New Roman", serif;
  font-size: 24px;
  font-weight: 700;
  color: var(--primary);
}

.topbar-nav {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.nav-link {
  padding: 10px 14px;
  border-radius: 12px;
  color: var(--muted);
}

.nav-link.active {
  background: rgba(19, 63, 103, 0.1);
  color: var(--primary);
  font-weight: 700;
}

.nav-link.disabled {
  opacity: 0.55;
}

@media (max-width: 720px) {
  .topbar {
    width: min(calc(100% - 20px), var(--content-width));
    padding: 14px;
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
