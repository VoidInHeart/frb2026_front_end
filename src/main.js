import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";
import "./styles.css";
import { initializeAppearanceTheme } from "./stores/appearance";

initializeAppearanceTheme();

createApp(App).use(router).mount("#app");
