import { defineConfig } from "vitest/config";
import vue from "@vitejs/plugin-vue";

const apiProxy = {
  "/api": {
    target: "http://127.0.0.1:8001",
    changeOrigin: true,
  },
};

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: apiProxy,
  },
  preview: {
    host: true,
    proxy: apiProxy,
  },
  test: {
    environment: "jsdom",
  },
});
