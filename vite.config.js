import { defineConfig, loadEnv } from "vite";
import vue from "@vitejs/plugin-vue";

function getApiProxy(baseUrl) {
  if (!baseUrl) {
    return undefined;
  }

  try {
    const parsedUrl = new URL(baseUrl);
    const prefix = parsedUrl.pathname.replace(/\/$/, "") || "/api";

    return {
      [prefix]: {
        target: parsedUrl.origin,
        changeOrigin: true,
        secure: false
      }
    };
  } catch {
    return undefined;
  }
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");

  return {
    plugins: [vue()],
    server: {
      host: "0.0.0.0",
      port: 5173,
      proxy: getApiProxy(env.VITE_API_BASE_URL)
    }
  };
});
