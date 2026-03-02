/**
 * Settings Page
 */

import { getApiBase } from '../modules/api.js';
import { t, i18n } from '../modules/i18n.js';
import { router } from '../modules/router.js';
import { toast } from '../modules/toast.js';

const isTauri = window.__TAURI__ !== undefined;

export function renderSettingsPage() {
  const container = document.getElementById('content-area');

  container.innerHTML = `
    <div class="page-header">
      <h1 class="page-title" data-i18n="settings.title">${t('settings.title')}</h1>
    </div>

    <div>
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

      <!-- API Access -->
      <div class="device-card mb-4">
        <div class="device-card-header">
          <div class="device-card-title">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
              <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
            </svg>
            ${t('settings.apiAccess.title')}
          </div>
        </div>
        <div id="api-access-section">
          <p class="text-sm text-text-muted mb-3">${t('settings.apiAccess.enableDesc')}</p>
          <div id="api-status-area" class="text-sm text-text-secondary">
            <span class="text-text-muted">${t('common.loading')}</span>
          </div>
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
  loadApiStatus();
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

// ── API Access Section ──────────────────────────────────────────────

async function loadApiStatus() {
  const area = document.getElementById('api-status-area');
  if (!area) return;

  try {
    const res = await fetch(`${getApiBase()}/keys/status`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    renderApiSection(area, data);
  } catch {
    area.innerHTML = `<p class="text-text-muted">${t('settings.apiAccess.webModeHint')}</p>`;
  }
}

function renderApiSection(area, statusData) {
  const { api_enabled } = statusData;

  let html = '';

  // Toggle
  html += `
    <div class="flex items-center gap-3 mb-4">
      <label class="flex items-center gap-2 cursor-pointer">
        <input type="checkbox" id="api-toggle" ${api_enabled ? 'checked' : ''}
          class="w-4 h-4 rounded">
        <span class="text-sm font-medium">${t('settings.apiAccess.enable')}</span>
      </label>
      <span class="text-xs px-2 py-0.5 rounded ${api_enabled ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}">
        ${api_enabled ? t('settings.apiAccess.enabled') : t('settings.apiAccess.disabled')}
      </span>
    </div>
  `;

  // New key display (outside api-keys-section so loadApiKeys() doesn't destroy it)
  html += `<div id="new-key-display" class="hidden mb-3 mt-4"></div>`;

  // Key management section
  html += `<div id="api-keys-section" class="mt-4"></div>`;

  area.innerHTML = html;

  // Attach toggle handler
  area.querySelector('#api-toggle')?.addEventListener('change', handleApiToggle);

  // Load keys
  loadApiKeys();
}

async function handleApiToggle(e) {
  const enabled = e.target.checked;
  try {
    if (isTauri) {
      const invoke = window.__TAURI__?.core?.invoke;
      if (!invoke) return;
      await invoke('enable_api', { enabled });
      toast.show(t('settings.apiAccess.restarting'), 'info');
      await invoke('restart_sidecar');
      setTimeout(() => loadApiStatus(), 2000);
    } else {
      const res = await fetch(`${getApiBase()}/keys/toggle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      loadApiStatus();
    }
  } catch (err) {
    toast.show(`Error: ${err}`, 'error');
    e.target.checked = !enabled; // revert
  }
}

async function loadApiKeys() {
  const section = document.getElementById('api-keys-section');
  if (!section) return;

  try {
    const res = await fetch(`${getApiBase()}/keys`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    renderApiKeys(section, data.keys || []);
  } catch {
    section.innerHTML = '';
  }
}

function renderApiKeys(section, keys) {
  let html = `
    <div class="flex items-center justify-between mb-3">
      <h4 class="text-sm font-medium">${t('settings.apiAccess.keys.title')}</h4>
    </div>
  `;

  // Create key form
  html += `
    <div class="flex gap-2 mb-3">
      <input type="text" id="new-key-name" placeholder="${t('settings.apiAccess.keys.namePlaceholder')}"
        class="input-field flex-1 text-sm" style="max-width: 240px;">
      <button id="create-key-btn" class="btn btn-secondary text-sm">
        ${t('settings.apiAccess.keys.create')}
      </button>
    </div>
  `;

  if (keys.length === 0) {
    html += `<p class="text-sm text-text-muted">${t('settings.apiAccess.keys.emptyDesc')}</p>`;
  } else {
    html += `<div class="space-y-2">`;
    for (const key of keys) {
      const lastUsed = key.last_used_at
        ? new Date(key.last_used_at).toLocaleString()
        : t('settings.apiAccess.keys.never');
      const created = new Date(key.created_at).toLocaleDateString();

      html += `
        <div class="flex items-center justify-between p-2 rounded bg-bg-secondary text-sm">
          <div>
            <span class="font-medium">${escapeHtml(key.name)}</span>
            <span class="text-text-muted ml-3">${t('settings.apiAccess.keys.createdAt')}: ${created}</span>
            <span class="text-text-muted ml-3">${t('settings.apiAccess.keys.lastUsed')}: ${lastUsed}</span>
          </div>
          <button class="btn-icon text-red-500 delete-key-btn" data-id="${key.id}" data-name="${escapeHtml(key.name)}" title="${t('settings.apiAccess.keys.delete')}">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6"/>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
            </svg>
          </button>
        </div>
      `;
    }
    html += `</div>`;
  }

  section.innerHTML = html;

  // Attach handlers
  section.querySelector('#create-key-btn')?.addEventListener('click', handleCreateKey);
  section.querySelectorAll('.delete-key-btn').forEach(btn => {
    btn.addEventListener('click', () => handleDeleteKey(btn.dataset.id, btn.dataset.name));
  });
}

async function handleCreateKey() {
  const input = document.getElementById('new-key-name');
  const name = input?.value?.trim();
  if (!name) {
    input?.focus();
    return;
  }

  const btn = document.getElementById('create-key-btn');
  btn.disabled = true;
  btn.textContent = t('settings.apiAccess.keys.creating');

  try {
    const res = await fetch(`${getApiBase()}/keys`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => null);
      throw new Error(err?.detail || `HTTP ${res.status}`);
    }
    const data = await res.json();

    // Show the key (only shown once)
    const display = document.getElementById('new-key-display');
    if (display) {
      display.className = 'mb-3 p-3 rounded bg-green-50 border border-green-200';
      display.innerHTML = `
        <p class="text-sm text-green-700 mb-2">${t('settings.apiAccess.keys.created')}</p>
        <div class="flex items-center gap-2">
          <code class="text-sm bg-white px-2 py-1 rounded border flex-1 break-all">${escapeHtml(data.api_key)}</code>
          <button id="copy-key-btn" class="btn btn-secondary text-sm">${t('settings.apiAccess.keys.copy')}</button>
        </div>
      `;
      display.querySelector('#copy-key-btn')?.addEventListener('click', () => {
        navigator.clipboard.writeText(data.api_key);
        toast.show(t('settings.apiAccess.keys.copied'), 'success');
      });
    }

    input.value = '';
    loadApiKeys();
  } catch (err) {
    toast.show(`Error: ${err.message}`, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = t('settings.apiAccess.keys.create');
  }
}

async function handleDeleteKey(id, name) {
  if (!confirm(t('settings.apiAccess.keys.confirmDelete', { name }))) return;

  try {
    // Prefer ID-based delete; fall back to name-based
    const url = id
      ? `${getApiBase()}/keys/id/${encodeURIComponent(id)}`
      : `${getApiBase()}/keys/${encodeURIComponent(name)}`;
    const res = await fetch(url, { method: 'DELETE' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    loadApiKeys();
  } catch (err) {
    toast.show(`Error: ${err.message}`, 'error');
  }
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

// Re-render when language changes
i18n.onLocaleChange(() => {
  if (router.currentRoute === 'settings') {
    renderSettingsPage();
  }
});
