import { defineConfig } from 'vite'

export default defineConfig({
  server: {
    port: 5173,
    proxy: {
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
  },
})
