/**
 * Settings Page
 */

import { t, i18n } from '../modules/i18n.js';
import { router } from '../modules/router.js';

export function renderSettingsPage() {
  const container = document.getElementById('content-area');

  container.innerHTML = `
    <div class="page-header">
      <h1 class="page-title" data-i18n="settings.title">${t('settings.title')}</h1>
    </div>

    <div class="max-w-2xl">
      <!-- Language Setting -->
      <div class="device-card mb-4">
        <div class="device-card-header">
          <div class="device-card-title">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="2" y1="12" x2="22" y2="12"/>
              <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
            </svg>
            ${t('settings.language')}
          </div>
        </div>
        <div class="flex gap-2">
          <button
            class="btn ${i18n.locale === 'en' ? 'btn-primary' : 'btn-secondary'}"
            id="lang-en"
          >
            English
          </button>
          <button
            class="btn ${i18n.locale === 'zh' ? 'btn-primary' : 'btn-secondary'}"
            id="lang-zh"
          >
            中文
          </button>
        </div>
      </div>

      <!-- About -->
      <div class="device-card">
        <div class="device-card-header">
          <div class="device-card-title">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="16" x2="12" y2="12"/>
              <line x1="12" y1="8" x2="12.01" y2="8"/>
            </svg>
            ${t('settings.about')}
          </div>
        </div>
        <div class="text-sm text-text-secondary">
          <p class="mb-2"><strong>SenseCraft Solution</strong></p>
          <p class="mb-2">${t('settings.version')}: 1.0.0</p>
          <p class="text-text-muted">
            IoT solution deployment platform for Seeed Studio products.
          </p>
        </div>
      </div>
    </div>
  `;

  setupEventHandlers(container);
}

function setupEventHandlers(container) {
  container.querySelector('#lang-en')?.addEventListener('click', () => {
    i18n.locale = 'en';
    renderSettingsPage();
  });

  container.querySelector('#lang-zh')?.addEventListener('click', () => {
    i18n.locale = 'zh';
    renderSettingsPage();
  });
}

// Re-render when language changes
i18n.onLocaleChange(() => {
  if (router.currentRoute === 'settings') {
    renderSettingsPage();
  }
});
