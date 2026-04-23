<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { RouterLink, useRoute } from "vue-router";
import { reviewSession } from "../stores/reviewSession";
import {
  appearanceState,
  appearanceThemes,
  setAppearanceTheme
} from "../stores/appearance";

const route = useRoute();
const appearanceMenuOpen = ref(false);
const appearanceMenuRef = ref(null);

const workspaceReady = computed(() => Boolean(reviewSession.currentSubmission));
const summaryReady = computed(
  () =>
    Boolean(reviewSession.currentSubmission) &&
    (Boolean(reviewSession.workflow.summary) ||
      Object.values(reviewSession.workflow.reviews).some(Boolean))
);

const stageLabelMap = {
  format: "格式审查",
  logic: "逻辑审查",
  innovation: "方法与创新点",
  summary: "汇总"
};

const currentStageLabel = computed(() => {
  if (route.name === "home") {
    return "主页";
  }

  if (route.name === "about") {
    return "关于我们";
  }

  if (route.name === "loading") {
    return "正在解析";
  }

  if (!workspaceReady.value) {
    return "等待上传";
  }

  return stageLabelMap[reviewSession.workflow.currentStage] ?? "等待开始";
});

function toggleAppearanceMenu() {
  appearanceMenuOpen.value = !appearanceMenuOpen.value;
}

function selectAppearanceTheme(theme) {
  setAppearanceTheme(theme);
  appearanceMenuOpen.value = false;
}

function handleClickOutside(event) {
  if (
    appearanceMenuRef.value &&
    !appearanceMenuRef.value.contains(event.target)
  ) {
    appearanceMenuOpen.value = false;
  }
}

onMounted(() => {
  document.addEventListener("pointerdown", handleClickOutside);
});

onBeforeUnmount(() => {
  document.removeEventListener("pointerdown", handleClickOutside);
});
</script>

<template>
  <header class="topbar">
    <div class="topbar-brand">
      <div class="topbar-kicker">Rule-Driven Expert Review</div>
      <RouterLink class="topbar-title" to="/">研航智审</RouterLink>
    </div>

    <nav class="topbar-nav">
      <RouterLink class="nav-link" :class="{ active: route.name === 'home' }" to="/">
        主页
      </RouterLink>

      <RouterLink
        class="nav-link"
        :class="{ active: route.name === 'upload' || route.name === 'loading' }"
        to="/upload"
      >
        开启评审
      </RouterLink>

      <RouterLink
        class="nav-link"
        :class="{ active: route.name === 'workspace', disabled: !workspaceReady }"
        :to="workspaceReady ? '/workspace' : '/upload'"
      >
        审查工作区
      </RouterLink>

      <RouterLink
        class="nav-link"
        :class="{
          active: route.name === 'summary',
          'summary-active': route.name === 'summary',
          disabled: !summaryReady
        }"
        :to="summaryReady ? '/summary' : '/upload'"
      >
        汇总页面
      </RouterLink>

      <RouterLink class="nav-link" :class="{ active: route.name === 'about' }" to="/about">
        About Us
      </RouterLink>

      <span class="pill pill-primary">{{ currentStageLabel }}</span>

      <div ref="appearanceMenuRef" class="appearance-menu">
        <button
          class="ghost-button appearance-trigger"
          type="button"
          @click="toggleAppearanceMenu"
        >
          外观
        </button>
        <div v-if="appearanceMenuOpen" class="appearance-panel glass-card">
          <button
            v-for="item in appearanceThemes"
            :key="item.id"
            class="appearance-option"
            :class="{ active: appearanceState.theme === item.id }"
            type="button"
            @click="selectAppearanceTheme(item.id)"
          >
            {{ item.label }}
          </button>
        </div>
      </div>
    </nav>
  </header>
</template>

<style scoped>
.topbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 20;
  width: 100%;
  margin: 0;
  padding: 14px clamp(14px, 2.2vw, 32px);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  border-bottom: 1px solid var(--border);
  background: var(--panel);
  backdrop-filter: blur(18px);
  box-shadow: 0 8px 24px rgba(19, 42, 76, 0.08);
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
  background: var(--primary-soft);
  color: var(--primary);
  font-weight: 700;
}

.nav-link.summary-active {
  background: rgba(47, 133, 90, 0.12);
  color: var(--success);
}

.nav-link.disabled {
  opacity: 0.55;
}

.appearance-menu {
  position: relative;
}

.appearance-trigger {
  min-height: 40px;
  padding: 0 14px;
  border-radius: 12px;
}

.appearance-panel {
  position: absolute;
  right: 0;
  top: calc(100% + 8px);
  min-width: 140px;
  padding: 10px;
  border-radius: 14px;
  display: grid;
  gap: 8px;
  z-index: 12;
}

.appearance-option {
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--surface-muted);
  color: var(--text);
  padding: 8px 10px;
  text-align: left;
}

.appearance-option.active {
  background: var(--primary-soft);
  border-color: var(--primary);
  color: var(--primary);
  font-weight: 700;
}

@media (max-width: 720px) {
  .topbar {
    padding: 12px 14px;
    align-items: flex-start;
    flex-direction: column;
  }

  .appearance-panel {
    right: auto;
    left: 0;
  }
}
</style>
