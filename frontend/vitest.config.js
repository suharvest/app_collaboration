import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/modules/__tests__/setup.js'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      include: ['src/modules/**/*.js'],
      exclude: ['src/modules/__tests__/**']
    },
    include: ['src/**/__tests__/**/*.test.js']
  }
})
