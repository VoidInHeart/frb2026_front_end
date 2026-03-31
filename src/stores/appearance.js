import { reactive } from "vue";

const STORAGE_KEY = "app-appearance-theme";
const DEFAULT_THEME = "day";

export const appearanceThemes = [
  { id: "day", label: "白昼" },
  { id: "dark", label: "暗黑" },
  { id: "sci-fi", label: "科幻" },
  { id: "vivid", label: "炫彩" }
];

export const appearanceState = reactive({
  theme: DEFAULT_THEME
});

function isValidTheme(theme) {
  return appearanceThemes.some((item) => item.id === theme);
}

function applyTheme(theme) {
  if (typeof document !== "undefined") {
    document.documentElement.setAttribute("data-theme", theme);
  }
}

export function setAppearanceTheme(theme) {
  if (!isValidTheme(theme)) {
    return;
  }

  appearanceState.theme = theme;
  applyTheme(theme);

  if (typeof localStorage !== "undefined") {
    localStorage.setItem(STORAGE_KEY, theme);
  }
}

export function initializeAppearanceTheme() {
  let initialTheme = DEFAULT_THEME;

  if (typeof localStorage !== "undefined") {
    const storedTheme = localStorage.getItem(STORAGE_KEY);
    if (storedTheme && isValidTheme(storedTheme)) {
      initialTheme = storedTheme;
    }
  }

  setAppearanceTheme(initialTheme);
}
