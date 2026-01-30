/**
 * i18n Module Tests
 *
 * Tests for internationalization functionality.
 * Ensures language switching, translation lookup, and fallback work correctly.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

describe('i18n Module', () => {
  beforeEach(() => {
    vi.resetModules()
    localStorage.getItem.mockReset()
    localStorage.setItem.mockReset()

    // Mock navigator.language
    Object.defineProperty(navigator, 'language', {
      value: 'en-US',
      configurable: true,
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Locale Detection', () => {
    it('should detect English from browser language', async () => {
      Object.defineProperty(navigator, 'language', { value: 'en-US', configurable: true })
      localStorage.getItem.mockReturnValue(null)

      const { i18n } = await import('../i18n.js')
      expect(i18n.locale).toBe('en')
    })

    it('should detect Chinese from browser language', async () => {
      Object.defineProperty(navigator, 'language', { value: 'zh-CN', configurable: true })
      localStorage.getItem.mockReturnValue(null)

      const { i18n } = await import('../i18n.js')
      expect(i18n.locale).toBe('zh')
    })

    it('should use saved locale from localStorage', async () => {
      localStorage.getItem.mockReturnValue('zh')

      const { i18n } = await import('../i18n.js')
      expect(i18n.locale).toBe('zh')
    })

    it('should prioritize saved locale over browser language', async () => {
      Object.defineProperty(navigator, 'language', { value: 'en-US', configurable: true })
      localStorage.getItem.mockReturnValue('zh')

      const { i18n } = await import('../i18n.js')
      expect(i18n.locale).toBe('zh')
    })
  })

  describe('Language Switching', () => {
    it('should switch locale and save to localStorage', async () => {
      localStorage.getItem.mockReturnValue('en')

      const { i18n } = await import('../i18n.js')
      i18n.locale = 'zh'

      expect(i18n.locale).toBe('zh')
      expect(localStorage.setItem).toHaveBeenCalledWith('locale', 'zh')
    })

    it('should toggle between en and zh', async () => {
      localStorage.getItem.mockReturnValue('en')

      const { i18n } = await import('../i18n.js')
      expect(i18n.locale).toBe('en')

      i18n.toggle()
      expect(i18n.locale).toBe('zh')

      i18n.toggle()
      expect(i18n.locale).toBe('en')
    })

    it('should not change locale if same value', async () => {
      localStorage.getItem.mockReturnValue('en')

      const { i18n } = await import('../i18n.js')
      i18n.locale = 'en'

      expect(localStorage.setItem).not.toHaveBeenCalled()
    })

    it('should not accept invalid locale', async () => {
      localStorage.getItem.mockReturnValue('en')

      const { i18n } = await import('../i18n.js')
      i18n.locale = 'fr' // Invalid locale

      expect(i18n.locale).toBe('en') // Should remain unchanged
    })
  })

  describe('Translation Lookup', () => {
    it('should return English translations', async () => {
      localStorage.getItem.mockReturnValue('en')

      const { t } = await import('../i18n.js')

      expect(t('app.title')).toBe('SenseCraft Solution')
      expect(t('nav.solutions')).toBe('Solutions')
      expect(t('nav.devices')).toBe('Devices')
    })

    it('should return Chinese translations', async () => {
      localStorage.getItem.mockReturnValue('zh')

      const { t } = await import('../i18n.js')

      expect(t('app.title')).toBe('SenseCraft 解决方案')
      expect(t('nav.solutions')).toBe('解决方案')
      expect(t('nav.devices')).toBe('设备管理')
    })

    it('should return key if translation not found', async () => {
      localStorage.getItem.mockReturnValue('en')

      const { t } = await import('../i18n.js')

      expect(t('nonexistent.key')).toBe('nonexistent.key')
    })

    it('should handle nested keys', async () => {
      localStorage.getItem.mockReturnValue('en')

      const { t } = await import('../i18n.js')

      expect(t('solutions.difficulty.beginner')).toBe('Beginner')
      expect(t('deploy.status.running')).toBe('Deploying...')
    })

    it('should replace template parameters', async () => {
      localStorage.getItem.mockReturnValue('en')

      const { t } = await import('../i18n.js')

      // Using a key that has {count} placeholder
      expect(t('management.contentFiles.presetsFound', { count: 3 })).toBe('3 presets found')
    })
  })

  describe('Localized Field Helper', () => {
    it('should get localized field based on current locale', async () => {
      localStorage.getItem.mockReturnValue('zh')

      const { getLocalizedField } = await import('../i18n.js')

      const obj = {
        name: 'English Name',
        name_zh: '中文名称',
      }

      expect(getLocalizedField(obj, 'name')).toBe('中文名称')
    })

    it('should fallback to English field if Chinese not available', async () => {
      localStorage.getItem.mockReturnValue('zh')

      const { getLocalizedField } = await import('../i18n.js')

      const obj = {
        name: 'English Only',
      }

      expect(getLocalizedField(obj, 'name')).toBe('English Only')
    })

    it('should return English field when locale is en', async () => {
      localStorage.getItem.mockReturnValue('en')

      const { getLocalizedField } = await import('../i18n.js')

      const obj = {
        name: 'English Name',
        name_zh: '中文名称',
      }

      expect(getLocalizedField(obj, 'name')).toBe('English Name')
    })

    it('should return empty string for null/undefined object', async () => {
      localStorage.getItem.mockReturnValue('en')

      const { getLocalizedField } = await import('../i18n.js')

      expect(getLocalizedField(null, 'name')).toBe('')
      expect(getLocalizedField(undefined, 'name')).toBe('')
    })
  })

  describe('Locale Change Listeners', () => {
    it('should notify listeners on locale change', async () => {
      localStorage.getItem.mockReturnValue('en')

      const { i18n } = await import('../i18n.js')
      const callback = vi.fn()

      i18n.onLocaleChange(callback)
      i18n.locale = 'zh'

      expect(callback).toHaveBeenCalledWith('zh')
    })

    it('should allow unsubscribing from locale changes', async () => {
      localStorage.getItem.mockReturnValue('en')

      const { i18n } = await import('../i18n.js')
      const callback = vi.fn()

      const unsubscribe = i18n.onLocaleChange(callback)
      unsubscribe()
      i18n.locale = 'zh'

      expect(callback).not.toHaveBeenCalled()
    })

    it('should not notify if locale unchanged', async () => {
      localStorage.getItem.mockReturnValue('en')

      const { i18n } = await import('../i18n.js')
      const callback = vi.fn()

      i18n.onLocaleChange(callback)
      i18n.locale = 'en' // Same locale

      expect(callback).not.toHaveBeenCalled()
    })
  })

  describe('Supported Locales', () => {
    it('should only support en and zh locales', async () => {
      localStorage.getItem.mockReturnValue('en')

      const { i18n } = await import('../i18n.js')

      // Valid locales should work
      i18n.locale = 'zh'
      expect(i18n.locale).toBe('zh')

      i18n.locale = 'en'
      expect(i18n.locale).toBe('en')

      // Invalid locales should be ignored
      i18n.locale = 'de'
      expect(i18n.locale).toBe('en')

      i18n.locale = 'ja'
      expect(i18n.locale).toBe('en')
    })
  })

  describe('Translation Completeness', () => {
    it('should have all nav translations in both languages', async () => {
      localStorage.getItem.mockReturnValue('en')
      const { t: tEn } = await import('../i18n.js')

      vi.resetModules()
      localStorage.getItem.mockReturnValue('zh')
      const { t: tZh } = await import('../i18n.js')

      const navKeys = ['solutions', 'devices', 'deployments', 'management', 'settings']

      for (const key of navKeys) {
        const enValue = tEn(`nav.${key}`)
        const zhValue = tZh(`nav.${key}`)

        expect(enValue).not.toBe(`nav.${key}`) // Should not return key
        expect(zhValue).not.toBe(`nav.${key}`) // Should not return key
      }
    })

    it('should have all difficulty levels in both languages', async () => {
      localStorage.getItem.mockReturnValue('en')
      const { t: tEn } = await import('../i18n.js')

      vi.resetModules()
      localStorage.getItem.mockReturnValue('zh')
      const { t: tZh } = await import('../i18n.js')

      const levels = ['beginner', 'intermediate', 'advanced']

      for (const level of levels) {
        const enValue = tEn(`solutions.difficulty.${level}`)
        const zhValue = tZh(`solutions.difficulty.${level}`)

        expect(enValue).not.toBe(`solutions.difficulty.${level}`)
        expect(zhValue).not.toBe(`solutions.difficulty.${level}`)
      }
    })
  })
})
