<script setup>
import { computed } from "vue";
import { RouterView, useRoute } from "vue-router";
import TopBar from "./components/TopBar.vue";

const route = useRoute();
const isHomeRoute = computed(() => route.name === "home");
</script>

<template>
  <div class="app-shell">
    <div class="ambient ambient-left"></div>
    <div class="ambient ambient-right"></div>
    <TopBar />
    <main class="page-shell" :class="{ 'page-shell-home': isHomeRoute }">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.page-shell-home {
  padding-top: calc(var(--topbar-offset) - 45px);
  padding-bottom: 0;
}

@media (max-width: 720px) {
  .page-shell-home {
    padding-top: calc(var(--topbar-offset) - 38px);
    padding-bottom: 0;
  }
}
</style>
