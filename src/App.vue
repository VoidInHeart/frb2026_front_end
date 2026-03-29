<script setup>
import { RouterView } from "vue-router";
import TopBar from "./components/TopBar.vue";
</script>

<template>
  <div class="app-shell">
    <div class="ambient ambient-left"></div>
    <div class="ambient ambient-right"></div>
    <TopBar />
    <main class="page-shell">
      <RouterView />
    </main>
  </div>
</template>
