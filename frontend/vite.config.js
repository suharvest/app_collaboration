import { defineConfig } from 'vite'

// Check if running in Tauri development mode
const isTauriDev = process.env.TAURI_ENV_DEBUG !== undefined;

export default defineConfig({
  // Prevent Vite from obscuring Rust errors
  clearScreen: false,
  server: {
    port: 5173,
    // Tauri expects a fixed port, fail if that port is not available
    strictPort: true,
    // Enable CORS for Tauri webview
    cors: true,
    proxy: isTauriDev ? {} : {
      // Only use proxy in non-Tauri mode (regular web development)
      '/api/preview/ws': {
        target: 'http://localhost:3260',
        changeOrigin: true,
        ws: true,
      },
      '/api': {
        target: 'http://localhost:3260',
        changeOrigin: true,
        ws: true,
      },
      '/ws': {
        target: 'http://localhost:3260',
        changeOrigin: true,
        ws: true,
      },
      '/solutions': {
        target: 'http://localhost:3260',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    // Tauri uses Chromium on Windows and WebKit on macOS/Linux
    target: ['es2021', 'chrome100', 'safari14'],
    // Don't minify for debug builds
    minify: !process.env.TAURI_ENV_DEBUG ? 'esbuild' : false,
    // Produce sourcemaps for debug builds
    sourcemap: !!process.env.TAURI_ENV_DEBUG,
  },
  // Env variables for Tauri
  envPrefix: ['VITE_', 'TAURI_ENV_'],
})
