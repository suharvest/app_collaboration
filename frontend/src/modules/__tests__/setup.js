/**
 * Vitest Setup File
 * Configures the test environment before each test run
 */

import { vi } from 'vitest'

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
}
global.localStorage = localStorageMock

// Mock window.location
Object.defineProperty(window, 'location', {
  value: {
    protocol: 'http:',
    host: 'localhost:5173',
    hostname: 'localhost',
    port: '5173',
    pathname: '/',
    search: '',
    hash: '',
    href: 'http://localhost:5173/',
  },
  writable: true,
})

// Reset mocks before each test
beforeEach(() => {
  vi.clearAllMocks()
  localStorageMock.getItem.mockReset()
  localStorageMock.setItem.mockReset()

  // Reset window.__TAURI__ and __BACKEND_PORT__
  delete window.__TAURI__
  delete window.__BACKEND_PORT__
})
