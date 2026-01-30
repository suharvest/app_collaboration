/**
 * API Module Tests
 *
 * Tests for frontend API communication layer.
 * Ensures port configuration, request building, and error handling work correctly.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

// We need to re-import the module fresh for each test to reset module state
// Use dynamic imports and vi.resetModules()

describe('API Module', () => {
  beforeEach(() => {
    vi.resetModules()
    global.fetch = vi.fn()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('getBackendPort', () => {
    it('should return default port 3260 in web mode', async () => {
      // Ensure not in Tauri mode
      delete window.__TAURI__
      delete window.__BACKEND_PORT__

      const { default: api } = await import('../api.js')
      // Access internal function through export
      const { getApiBase } = await import('../api.js')
      const base = getApiBase()

      // In web mode, should return relative path
      expect(base).toBe('/api')
    })

    it('should use injected port in Tauri mode', async () => {
      window.__TAURI__ = { core: { invoke: vi.fn() } }
      window.__BACKEND_PORT__ = 4567

      const { getApiBase } = await import('../api.js')
      const base = getApiBase()

      expect(base).toBe('http://127.0.0.1:4567/api')
    })

    it('should fallback to 3260 if BACKEND_PORT not set in Tauri', async () => {
      window.__TAURI__ = { core: { invoke: vi.fn() } }
      delete window.__BACKEND_PORT__

      const { getApiBase } = await import('../api.js')
      const base = getApiBase()

      expect(base).toBe('http://127.0.0.1:3260/api')
    })
  })

  describe('getWsBase', () => {
    it('should return ws:// URL in web mode with http', async () => {
      delete window.__TAURI__
      window.location.protocol = 'http:'
      window.location.host = 'localhost:5173'

      const { getWsBase } = await import('../api.js')
      const wsBase = getWsBase()

      expect(wsBase).toBe('ws://localhost:5173')
    })

    it('should return wss:// URL in web mode with https', async () => {
      delete window.__TAURI__
      window.location.protocol = 'https:'
      window.location.host = 'example.com'

      const { getWsBase } = await import('../api.js')
      const wsBase = getWsBase()

      expect(wsBase).toBe('wss://example.com')
    })

    it('should return ws://127.0.0.1:PORT in Tauri mode', async () => {
      window.__TAURI__ = { core: { invoke: vi.fn() } }
      window.__BACKEND_PORT__ = 4567

      const { getWsBase } = await import('../api.js')
      const wsBase = getWsBase()

      expect(wsBase).toBe('ws://127.0.0.1:4567')
    })
  })

  describe('getAssetUrl', () => {
    it('should build correct asset URL in web mode', async () => {
      delete window.__TAURI__

      const { getAssetUrl } = await import('../api.js')
      const url = getAssetUrl('my_solution', 'gallery/cover.png')

      expect(url).toBe('/api/solutions/my_solution/assets/gallery/cover.png')
    })

    it('should build full URL in Tauri mode', async () => {
      window.__TAURI__ = { core: { invoke: vi.fn() } }
      window.__BACKEND_PORT__ = 3260

      const { getAssetUrl } = await import('../api.js')
      const url = getAssetUrl('my_solution', 'gallery/cover.png')

      expect(url).toBe('http://127.0.0.1:3260/api/solutions/my_solution/assets/gallery/cover.png')
    })

    it('should return absolute URLs unchanged', async () => {
      const { getAssetUrl } = await import('../api.js')

      expect(getAssetUrl('s', 'https://example.com/img.png')).toBe('https://example.com/img.png')
      expect(getAssetUrl('s', 'http://example.com/img.png')).toBe('http://example.com/img.png')
    })

    it('should return empty string for empty path', async () => {
      const { getAssetUrl } = await import('../api.js')

      expect(getAssetUrl('my_solution', '')).toBe('')
      expect(getAssetUrl('my_solution', null)).toBe('')
    })
  })

  describe('buildQueryString', () => {
    it('should build query string from object', async () => {
      const { buildQueryString } = await import('../api.js')

      const result = buildQueryString({ lang: 'zh', page: 1 })
      expect(result).toBe('?lang=zh&page=1')
    })

    it('should skip null and undefined values', async () => {
      const { buildQueryString } = await import('../api.js')

      const result = buildQueryString({ lang: 'en', page: null, size: undefined })
      expect(result).toBe('?lang=en')
    })

    it('should return empty string for empty object', async () => {
      const { buildQueryString } = await import('../api.js')

      expect(buildQueryString({})).toBe('')
    })
  })

  describe('solutionsApi', () => {
    it('should call list endpoint with lang parameter', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        headers: new Map([['content-type', 'application/json']]),
        json: () => Promise.resolve([{ id: 'test' }])
      })

      const { solutionsApi } = await import('../api.js')
      await solutionsApi.list('zh')

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/solutions?lang=zh'),
        expect.any(Object)
      )
    })

    it('should call get endpoint with solution ID and lang', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        headers: new Map([['content-type', 'application/json']]),
        json: () => Promise.resolve({ id: 'test' })
      })

      const { solutionsApi } = await import('../api.js')
      await solutionsApi.get('my_solution', 'en')

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/solutions/my_solution?lang=en'),
        expect.any(Object)
      )
    })

    it('should call getDeployment with correct parameters', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        headers: new Map([['content-type', 'application/json']]),
        json: () => Promise.resolve({ devices: [], presets: [] })
      })

      const { solutionsApi } = await import('../api.js')
      await solutionsApi.getDeployment('smart_warehouse', 'zh')

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/solutions/smart_warehouse/deployment?lang=zh'),
        expect.any(Object)
      )
    })
  })

  describe('devicesApi', () => {
    it('should call detect with solution ID', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        headers: new Map([['content-type', 'application/json']]),
        json: () => Promise.resolve({ devices: [] })
      })

      const { devicesApi } = await import('../api.js')
      await devicesApi.detect('my_solution')

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/devices/detect/my_solution'),
        expect.any(Object)
      )
    })

    it('should call detect with preset parameter', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        headers: new Map([['content-type', 'application/json']]),
        json: () => Promise.resolve({ devices: [] })
      })

      const { devicesApi } = await import('../api.js')
      await devicesApi.detect('my_solution', 'cloud_preset')

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/devices/detect/my_solution?preset=cloud_preset'),
        expect.any(Object)
      )
    })
  })

  describe('Error Handling', () => {
    it('should throw ApiError on non-200 response', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: () => Promise.resolve({ detail: 'Solution not found' })
      })

      const { solutionsApi, ApiError } = await import('../api.js')

      await expect(solutionsApi.get('nonexistent')).rejects.toThrow('Solution not found')
    })

    it('should throw ApiError with status code', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: () => Promise.resolve({ detail: 'Server error' })
      })

      const { solutionsApi, ApiError } = await import('../api.js')

      try {
        await solutionsApi.list()
      } catch (error) {
        expect(error.status).toBe(500)
        expect(error.message).toBe('Server error')
      }
    })

    it('should handle timeout errors', async () => {
      global.fetch = vi.fn().mockImplementation(() => {
        return new Promise((_, reject) => {
          const error = new Error('Aborted')
          error.name = 'AbortError'
          reject(error)
        })
      })

      const { solutionsApi } = await import('../api.js')

      await expect(solutionsApi.list()).rejects.toThrow('Request timeout')
    })

    it('should handle network errors', async () => {
      global.fetch = vi.fn().mockRejectedValue(new Error('Network error'))

      const { solutionsApi } = await import('../api.js')

      await expect(solutionsApi.list()).rejects.toThrow('Network error')
    })
  })

  describe('LogsWebSocket', () => {
    it('should construct with deployment ID', async () => {
      const { LogsWebSocket } = await import('../api.js')

      const ws = new LogsWebSocket('deploy-123')
      expect(ws.deploymentId).toBe('deploy-123')
      // isConnected returns false when ws is null (not connected)
      expect(ws.isConnected).toBeFalsy()
    })

    it('should register and emit events', async () => {
      const { LogsWebSocket } = await import('../api.js')

      const ws = new LogsWebSocket('deploy-123')
      const callback = vi.fn()

      ws.on('log', callback)
      ws.emit('log', { type: 'log', message: 'test' })

      expect(callback).toHaveBeenCalledWith({ type: 'log', message: 'test' })
    })

    it('should unregister events with off()', async () => {
      const { LogsWebSocket } = await import('../api.js')

      const ws = new LogsWebSocket('deploy-123')
      const callback = vi.fn()

      ws.on('log', callback)
      ws.off('log', callback)
      ws.emit('log', { type: 'log', message: 'test' })

      expect(callback).not.toHaveBeenCalled()
    })

    it('should return unsubscribe function from on()', async () => {
      const { LogsWebSocket } = await import('../api.js')

      const ws = new LogsWebSocket('deploy-123')
      const callback = vi.fn()

      const unsubscribe = ws.on('log', callback)
      unsubscribe()
      ws.emit('log', { type: 'log', message: 'test' })

      expect(callback).not.toHaveBeenCalled()
    })
  })
})

describe('Port Configuration Constants', () => {
  it('should use consistent default port 3260', async () => {
    // This test ensures the frontend default matches the backend default
    // If this test fails, check provisioning_station/config.py:68
    const EXPECTED_DEFAULT_PORT = 3260

    // Reset module state
    vi.resetModules()

    // Set up Tauri mode before importing module
    window.__TAURI__ = { core: { invoke: vi.fn() } }
    delete window.__BACKEND_PORT__ // No port set, should fallback

    const { getApiBase } = await import('../api.js')
    const base = getApiBase()

    // In Tauri mode without BACKEND_PORT, should fallback to 3260
    expect(base).toContain(`:${EXPECTED_DEFAULT_PORT}/api`)
  })
})
