/**
 * Device Management Page
 *
 * Top section: SSH connection form for Docker container management
 * Bottom section: Previously deployed apps (legacy device management)
 */

import { deviceManagementApi, dockerDevicesApi, restoreApi, devicesApi } from '../modules/api.js';
import { t, i18n } from '../modules/i18n.js';
import { router } from '../modules/router.js';
import { toast } from '../modules/toast.js';

let currentConnection = null;
let currentDeployments = [];
let passwordModalCallback = null;
let deviceMode = 'local'; // 'local' or 'remote'

// Restore state
let restoreDevices = [];
let restorePorts = [];
let selectedRestoreDevice = null;
let restoreOperation = null;
let restorePollingInterval = null;

export async function renderDevicesPage() {
  const container = document.getElementById('content-area');

  const subtitle = deviceMode === 'embedded' ? t('devices.restore.subtitle') : t('devices.subtitle');

  container.innerHTML = `
    <div class="page-header">
      <h1 class="page-title" data-i18n="devices.title">${t('devices.title')}</h1>
      <p class="page-subtitle text-text-secondary">${subtitle}</p>
    </div>

    <!-- Device Mode Toggle -->
    <div class="device-mode-toggle mb-6">
      <button class="device-mode-btn ${deviceMode === 'local' ? 'active' : ''}" data-mode="local">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="2" y="3" width="20" height="14" rx="2"/>
          <path d="M8 21h8M12 17v4"/>
        </svg>
        ${t('devices.mode.local')}
      </button>
      <button class="device-mode-btn ${deviceMode === 'remote' ? 'active' : ''}" data-mode="remote">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="2" y="2" width="20" height="8" rx="2"/>
          <rect x="2" y="14" width="20" height="8" rx="2"/>
          <circle cx="6" cy="6" r="1"/><circle cx="6" cy="18" r="1"/>
        </svg>
        ${t('devices.mode.remote')}
      </button>
      <button class="device-mode-btn ${deviceMode === 'embedded' ? 'active' : ''}" data-mode="embedded">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="4" y="4" width="16" height="16" rx="2"/>
          <rect x="9" y="9" width="6" height="6"/>
          <line x1="9" y1="2" x2="9" y2="4"/><line x1="15" y1="2" x2="15" y2="4"/>
          <line x1="9" y1="20" x2="9" y2="22"/><line x1="15" y1="20" x2="15" y2="22"/>
          <line x1="2" y1="9" x2="4" y2="9"/><line x1="2" y1="15" x2="4" y2="15"/>
          <line x1="20" y1="9" x2="22" y2="9"/><line x1="20" y1="15" x2="22" y2="15"/>
        </svg>
        ${t('devices.mode.embedded')}
      </button>
    </div>

    <!-- Local Docker Status (shown in local mode) -->
    <div id="local-docker-section" class="docker-connect-section mb-6" style="display: ${deviceMode === 'local' ? 'block' : 'none'};">
      <div class="docker-connect-card">
        <div class="docker-connect-header">
          <h3 class="docker-connect-title">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="2" y="3" width="20" height="14" rx="2"/>
              <path d="M8 21h8M12 17v4"/>
            </svg>
            ${t('devices.docker.localTitle')}
          </h3>
          <div id="local-docker-status"></div>
        </div>
      </div>
    </div>

    <!-- Remote Docker Connection (shown in remote mode) -->
    <div id="remote-docker-section" class="docker-connect-section mb-6" style="display: ${deviceMode === 'remote' ? 'block' : 'none'};">
      <div class="docker-connect-card">
        <div class="docker-connect-header">
          <h3 class="docker-connect-title">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="2" y="2" width="20" height="8" rx="2"/>
              <rect x="2" y="14" width="20" height="8" rx="2"/>
              <circle cx="6" cy="6" r="1"/><circle cx="6" cy="18" r="1"/>
            </svg>
            ${t('devices.docker.remoteTitle')}
          </h3>
          <div id="docker-connection-status"></div>
        </div>
        <form id="docker-connect-form" class="docker-connect-form">
          <div class="docker-connect-fields">
            <div class="form-group mb-0">
              <label>${t('deploy.connection.host')}</label>
              <div class="input-with-scan">
                <input type="text" id="docker-host" class="input" placeholder="192.168.x.x" required>
                <button type="button" class="btn btn-secondary btn-scan" id="scan-mdns-btn" title="${t('deploy.connection.scanHint')}">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="3"/>
                    <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z"/>
                  </svg>
                  ${t('deploy.connection.scan')}
                </button>
              </div>
              <div class="mdns-devices-dropdown" id="mdns-dropdown-devices" style="display: none;"></div>
            </div>
            <div class="form-group mb-0">
              <label>${t('deploy.connection.username')}</label>
              <input type="text" id="docker-username" class="input" value="recomputer" required>
            </div>
            <div class="form-group mb-0">
              <label>${t('deploy.connection.password')}</label>
              <input type="password" id="docker-password" class="input" required>
            </div>
            <div class="form-group mb-0 flex items-end">
              <button type="submit" class="btn btn-primary w-full" id="docker-connect-btn">
                ${t('deploy.connection.connect')}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>

    <!-- Deployed Applications (hidden in embedded mode) -->
    <div id="deployed-apps-section" style="display: ${deviceMode === 'embedded' ? 'none' : 'block'};">
      <div class="containers-header mb-4">
        <h3 class="text-base font-semibold text-text-primary">${t('devices.deployedApps')}</h3>
        <div class="flex gap-2">
          <button class="btn btn-sm btn-secondary" id="prune-images-btn" title="${t('devices.actions.pruneImagesHint')}">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
            </svg>
            ${t('devices.actions.pruneImages')}
          </button>
          <button class="btn btn-sm btn-secondary" id="refresh-apps-btn">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M1 4v6h6M23 20v-6h-6"/>
              <path d="M20.49 9A9 9 0 005.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 013.51 15"/>
            </svg>
            ${t('devices.actions.refresh')}
          </button>
        </div>
      </div>
      <div id="devices-list">
        <div class="flex items-center justify-center py-4">
          <div class="spinner spinner-lg"></div>
        </div>
      </div>
    </div>

    <!-- Device Restore Section (only shown in embedded mode) -->
    <div id="restore-section" class="restore-section-standalone" style="display: ${deviceMode === 'embedded' ? 'block' : 'none'}">
      <div class="restore-card">
        <div class="restore-device-selector mb-4">
          <label class="block mb-2 text-sm font-medium text-text-secondary">${t('devices.restore.selectDevice')}</label>
          <div id="restore-device-options" class="restore-device-options">
            <!-- Device options will be populated -->
          </div>
        </div>

        <!-- Watcher USB Config -->
        <div id="restore-watcher-config" class="restore-config" style="display: none;">
          <p class="text-sm text-text-secondary mb-3">${t('devices.restore.watcherHint')}</p>
          <div class="flex gap-3 items-end">
            <div class="form-group mb-0 flex-1">
              <label>${t('devices.restore.selectPort')}</label>
              <select id="restore-port-select" class="input">
                <option value="">-- ${t('devices.restore.selectPort')} --</option>
              </select>
            </div>
            <button type="button" class="btn btn-secondary" id="restore-refresh-ports">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M1 4v6h6M23 20v-6h-6"/>
                <path d="M20.49 9A9 9 0 005.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 013.51 15"/>
              </svg>
              ${t('devices.restore.refreshPorts')}
            </button>
          </div>
        </div>

        <!-- reCamera SSH Config -->
        <div id="restore-recamera-config" class="restore-config" style="display: none;">
          <p class="text-sm text-text-secondary mb-3">${t('devices.restore.recameraHint')}</p>
          <div class="grid gap-3" style="grid-template-columns: 1fr 1fr 1fr;">
            <div class="form-group mb-0">
              <label>${t('devices.restore.host')}</label>
              <input type="text" id="restore-host" class="input" placeholder="192.168.x.x">
            </div>
            <div class="form-group mb-0">
              <label>${t('devices.restore.username')}</label>
              <input type="text" id="restore-username" class="input" value="recamera">
            </div>
            <div class="form-group mb-0">
              <label>${t('devices.restore.password')}</label>
              <input type="password" id="restore-password" class="input">
            </div>
          </div>
        </div>

        <!-- Restore Button -->
        <div class="restore-action mt-4">
          <button type="button" class="btn btn-primary" id="restore-start-btn" disabled>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
              <path d="M3 3v5h5"/>
            </svg>
            ${t('devices.restore.startRestore')}
          </button>
        </div>

        <!-- Progress -->
        <div id="restore-progress" class="restore-progress mt-4" style="display: none;">
          <div class="flex items-center justify-between mb-2">
            <span class="text-sm font-medium text-text-primary" id="restore-progress-message"></span>
            <span class="text-sm text-text-secondary" id="restore-progress-percent">0%</span>
          </div>
          <div class="progress-bar">
            <div class="progress-bar-fill" id="restore-progress-bar" style="width: 0%;"></div>
          </div>
        </div>

        <!-- Logs -->
        <div id="restore-logs-section" class="restore-logs mt-4" style="display: none;">
          <div class="deploy-logs-toggle" id="restore-logs-toggle">
            <span class="deploy-logs-label">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
                <line x1="16" y1="13" x2="8" y2="13"/>
                <line x1="16" y1="17" x2="8" y2="17"/>
              </svg>
              ${t('devices.restore.logs')}
              <span class="deploy-logs-count" id="restore-logs-count">0</span>
            </span>
            <svg class="deploy-section-chevron" id="restore-logs-chevron" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="6 9 12 15 18 9"/>
            </svg>
          </div>
          <div class="deploy-logs-panel" id="restore-logs-panel">
            <div class="deploy-logs-viewer dark-scrollbar" id="restore-logs-viewer"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Password Modal -->
    <div id="password-modal" class="modal-overlay" style="display: none;">
      <div class="modal-content" style="max-width: 400px;">
        <h3 class="modal-title">${t('devices.password.title')}</h3>
        <p class="text-text-secondary mb-4">${t('devices.password.description')}</p>
        <form id="password-form">
          <input type="password" id="ssh-password" class="input mb-4" placeholder="SSH Password" required>
          <div class="flex gap-3 justify-end">
            <button type="button" class="btn btn-secondary" id="password-cancel">${t('common.cancel')}</button>
            <button type="submit" class="btn btn-primary">${t('devices.password.submit')}</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Remove App Confirmation Modal -->
    <div id="remove-app-modal" class="modal-overlay" style="display: none;">
      <div class="modal-content" style="max-width: 450px;">
        <h3 class="modal-title">${t('devices.actions.confirmRemove')}</h3>
        <p class="text-text-secondary mb-4">${t('devices.actions.confirmRemoveMessage')}</p>
        <p class="text-sm text-text-muted mb-2" id="remove-app-name"></p>
        <label class="flex items-center gap-2 mb-2 cursor-pointer">
          <input type="checkbox" id="remove-images-checkbox" class="checkbox">
          <span class="text-sm">${t('devices.actions.removeWithImages')}</span>
        </label>
        <p class="text-xs text-text-muted mb-3">${t('devices.actions.removeWithImagesHint')}</p>
        <label class="flex items-center gap-2 mb-2 cursor-pointer">
          <input type="checkbox" id="remove-volumes-checkbox" class="checkbox">
          <span class="text-sm">${t('devices.actions.removeWithVolumes')}</span>
        </label>
        <p class="text-xs text-text-muted mb-4">${t('devices.actions.removeWithVolumesHint')}</p>
        <div class="flex gap-3 justify-end">
          <button type="button" class="btn btn-secondary" id="remove-app-cancel">${t('common.cancel')}</button>
          <button type="button" class="btn btn-danger" id="remove-app-confirm">${t('devices.actions.remove')}</button>
        </div>
      </div>
    </div>

    <!-- Prune Images Confirmation Modal -->
    <div id="prune-images-modal" class="modal-overlay" style="display: none;">
      <div class="modal-content" style="max-width: 450px;">
        <h3 class="modal-title">${t('devices.actions.confirmPrune')}</h3>
        <p class="text-text-secondary mb-4">${t('devices.actions.confirmPruneMessage')}</p>
        <div class="flex gap-3 justify-end">
          <button type="button" class="btn btn-secondary" id="prune-images-cancel">${t('common.cancel')}</button>
          <button type="button" class="btn btn-danger" id="prune-images-confirm">${t('devices.actions.pruneImages')}</button>
        </div>
      </div>
    </div>

    <!-- Configure App Modal -->
    <div id="configure-app-modal" class="modal-overlay" style="display: none;">
      <div class="modal-content" style="max-width: 480px;">
        <div class="flex items-center justify-between mb-4">
          <h3 id="configure-app-title" class="text-lg font-semibold"></h3>
          <button id="configure-close" class="btn-icon" style="background:none;border:none;cursor:pointer;padding:4px;">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M18 6L6 18M6 6l12 12"/>
            </svg>
          </button>
        </div>
        <p class="text-text-secondary text-sm mb-4">${t('devices.configure.desc')}</p>
        <div id="configure-form-fields"></div>
        <div id="configure-error" class="text-red-500 text-sm mb-3" style="display:none"></div>
        <div class="flex gap-3 justify-end mt-4">
          <button id="configure-cancel" class="btn btn-secondary">${t('common.cancel')}</button>
          <button id="configure-save" class="btn btn-primary">${t('common.save')}</button>
        </div>
      </div>
    </div>
  `;

  // Setup handlers
  setupDeviceModeToggle();
  setupDockerConnectForm();
  setupPasswordModal();
  setupRestoreSection();

  // Load content based on current mode
  if (deviceMode === 'local') {
    await checkLocalDocker();
  } else if (deviceMode === 'embedded') {
    await loadRestoreDevices();
  }
}

// ============================================
// Device Mode Toggle
// ============================================

function setupDeviceModeToggle() {
  document.querySelectorAll('.device-mode-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const newMode = btn.dataset.mode;
      if (newMode === deviceMode) return;

      deviceMode = newMode;

      // Update toggle buttons
      document.querySelectorAll('.device-mode-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.mode === deviceMode);
      });

      // Show/hide sections based on mode
      const localSection = document.getElementById('local-docker-section');
      const remoteSection = document.getElementById('remote-docker-section');
      const deployedAppsSection = document.getElementById('deployed-apps-section');
      const restoreSection = document.getElementById('restore-section');

      if (deviceMode === 'local') {
        localSection.style.display = 'block';
        remoteSection.style.display = 'none';
        deployedAppsSection.style.display = 'block';
        restoreSection.style.display = 'none';
        currentConnection = null;
        await checkLocalDocker();
      } else if (deviceMode === 'remote') {
        localSection.style.display = 'none';
        remoteSection.style.display = 'block';
        deployedAppsSection.style.display = 'block';
        restoreSection.style.display = 'none';
        // Show connect prompt for deployed apps
        loadDeployedApps();
      } else if (deviceMode === 'embedded') {
        localSection.style.display = 'none';
        remoteSection.style.display = 'none';
        deployedAppsSection.style.display = 'none';
        restoreSection.style.display = 'block';
        // Load restore devices
        await loadRestoreDevices();
      }
    });
  });
}

async function checkLocalDocker() {
  const statusEl = document.getElementById('local-docker-status');
  statusEl.innerHTML = `<span class="spinner spinner-sm"></span>`;

  try {
    const result = await dockerDevicesApi.checkLocal();

    if (result.success) {
      // Mark as connected (local mode uses null connection to indicate local)
      currentConnection = { _local: true };

      statusEl.innerHTML = `
        <span class="status-badge ready">
          <span class="status-dot"></span>
          ${result.device.hostname} (Docker ${result.device.docker_version})
        </span>
      `;

      // Load managed apps
      await loadDeployedApps();
    }
  } catch (error) {
    currentConnection = null;
    statusEl.innerHTML = `
      <span class="status-badge failed">
        ${t('devices.docker.notAvailable')}
      </span>
    `;
    // Show empty state
    const listEl = document.getElementById('devices-list');
    listEl.innerHTML = `
      <div class="empty-state">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="text-text-muted mb-4">
          <rect x="2" y="3" width="20" height="14" rx="2"/>
          <path d="M8 21h8M12 17v4"/>
        </svg>
        <p class="text-text-secondary">${t('devices.docker.notAvailable')}</p>
        <p class="text-sm text-text-muted">${t('devices.docker.installDocker')}</p>
      </div>
    `;
  }
}

// ============================================
// Docker Connection & Container Management
// ============================================

function setupDockerConnectForm() {
  const form = document.getElementById('docker-connect-form');
  if (form) {
    form.addEventListener('submit', handleDockerConnect);
  }

  const refreshBtn = document.getElementById('refresh-apps-btn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => loadDeployedApps());
  }

  // mDNS scan button
  const scanBtn = document.getElementById('scan-mdns-btn');
  if (scanBtn) {
    scanBtn.addEventListener('click', () => scanMdnsForDevices());
  }

  // Prune images button
  const pruneBtn = document.getElementById('prune-images-btn');
  if (pruneBtn) {
    pruneBtn.addEventListener('click', () => {
      if (!currentConnection) {
        toast.error(t('devices.connectFirst'));
        return;
      }
      const modal = document.getElementById('prune-images-modal');
      if (modal) modal.style.display = 'flex';
    });
  }

  // Setup modals
  setupRemoveAppModal();
  setupPruneImagesModal();
  setupConfigureModal();

  // Restore last connection from sessionStorage
  const saved = sessionStorage.getItem('docker_connection');
  if (saved) {
    try {
      const conn = JSON.parse(saved);
      const hostInput = document.getElementById('docker-host');
      const userInput = document.getElementById('docker-username');
      if (hostInput) hostInput.value = conn.host || '';
      if (userInput) userInput.value = conn.username || 'recomputer';
    } catch (_e) { /* ignore stored connection parse errors */ }
  }
}

async function handleDockerConnect(e) {
  e.preventDefault();
  const btn = document.getElementById('docker-connect-btn');
  const originalText = btn.innerHTML;

  const connection = {
    host: document.getElementById('docker-host').value.trim(),
    username: document.getElementById('docker-username').value.trim(),
    password: document.getElementById('docker-password').value,
    port: 22,
  };

  try {
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner spinner-sm"></span>`;

    const result = await dockerDevicesApi.connect(connection);

    if (result.success) {
      currentConnection = connection;
      // Save (without password) to sessionStorage
      sessionStorage.setItem('docker_connection', JSON.stringify({
        host: connection.host,
        username: connection.username,
      }));

      // Show connection status
      const statusEl = document.getElementById('docker-connection-status');
      statusEl.innerHTML = `
        <span class="status-badge ready">
          <span class="status-dot"></span>
          ${result.device.hostname} (${result.device.docker_version})
        </span>
      `;

      toast.success(t('devices.docker.connected'));
      await loadDeployedApps();
    }
  } catch (error) {
    toast.error(error.message);
    const statusEl = document.getElementById('docker-connection-status');
    statusEl.innerHTML = `<span class="status-badge failed">${t('devices.docker.connectionFailed')}</span>`;
  } finally {
    btn.disabled = false;
    btn.innerHTML = originalText;
  }
}

// ============================================
// mDNS Device Discovery
// ============================================

async function scanMdnsForDevices() {
  const btn = document.getElementById('scan-mdns-btn');
  const dropdown = document.getElementById('mdns-dropdown-devices');
  const hostInput = document.getElementById('docker-host');

  if (!btn || !dropdown) return;

  const originalContent = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = `<span class="spinner spinner-sm"></span> ${t('deploy.connection.scanning')}`;

  try {
    const result = await devicesApi.scanMdns({ timeout: 3, filterKnown: true });
    const devices = result.devices || [];

    if (devices.length === 0) {
      dropdown.innerHTML = `
        <div class="mdns-empty">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          <span>${t('deploy.connection.noDevicesFound')}</span>
        </div>
      `;
      dropdown.style.display = 'block';

      // Auto-hide after 3 seconds
      setTimeout(() => {
        dropdown.style.display = 'none';
      }, 3000);
    } else {
      dropdown.innerHTML = `
        <div class="mdns-header">${t('deploy.connection.discoveredDevices')}</div>
        ${devices.map(device => `
          <div class="mdns-device" data-ip="${device.ip}" data-hostname="${device.hostname}">
            <span class="mdns-device-icon">${getMdnsDeviceIcon(device.device_type)}</span>
            <span class="mdns-device-name">${device.hostname}</span>
            <span class="mdns-device-ip">${device.ip}</span>
          </div>
        `).join('')}
      `;
      dropdown.style.display = 'block';

      // Setup click handlers for device selection
      dropdown.querySelectorAll('.mdns-device').forEach(el => {
        el.addEventListener('click', () => {
          const ip = el.dataset.ip;
          if (hostInput) {
            hostInput.value = ip;
            hostInput.dispatchEvent(new Event('input', { bubbles: true }));
          }
          dropdown.style.display = 'none';
        });
      });

      // Close dropdown when clicking outside
      const closeDropdown = (e) => {
        if (!dropdown.contains(e.target) && e.target !== btn && !btn.contains(e.target)) {
          dropdown.style.display = 'none';
          document.removeEventListener('click', closeDropdown);
        }
      };
      setTimeout(() => document.addEventListener('click', closeDropdown), 100);
    }
  } catch (error) {
    console.error('mDNS scan failed:', error);
    toast.error(error.message || t('common.error'));
  } finally {
    btn.disabled = false;
    btn.innerHTML = originalContent;
  }
}

function getMdnsDeviceIcon(deviceType) {
  switch (deviceType) {
    case 'raspberry':
      return '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="4" width="16" height="16" rx="2"/><circle cx="9" cy="9" r="1"/><circle cx="15" cy="9" r="1"/><circle cx="9" cy="15" r="1"/><circle cx="15" cy="15" r="1"/></svg>';
    case 'jetson':
      return '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><path d="M15 2v2M15 20v2M9 2v2M9 20v2M2 15h2M20 15h2M2 9h2M20 9h2"/></svg>';
    case 'recomputer':
    case 'recamera':
      return '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/></svg>';
    default:
      return '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="2" width="20" height="8" rx="2"/><rect x="2" y="14" width="20" height="8" rx="2"/><circle cx="6" cy="6" r="1"/><circle cx="6" cy="18" r="1"/></svg>';
  }
}

// ============================================
// Deployed Applications (Detected from Device)
// ============================================

async function loadDeployedApps() {
  const listContainer = document.getElementById('devices-list');

  // If not connected (and not local mode with Docker available)
  if (!currentConnection) {
    listContainer.innerHTML = `
      <div class="empty-state">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="text-text-muted mb-4">
          <rect x="2" y="2" width="20" height="8" rx="2"/>
          <rect x="2" y="14" width="20" height="8" rx="2"/>
          <circle cx="6" cy="6" r="1"/><circle cx="6" cy="18" r="1"/>
        </svg>
        <p class="text-text-secondary">${t('devices.connectFirst')}</p>
        <p class="text-sm text-text-muted">${t('devices.connectFirstDesc')}</p>
      </div>
    `;
    return;
  }

  listContainer.innerHTML = `<div class="flex items-center justify-center py-4"><div class="spinner spinner-lg"></div></div>`;

  try {
    let result;
    if (currentConnection._local) {
      result = await dockerDevicesApi.listLocalManagedApps();
    } else {
      result = await dockerDevicesApi.listManagedApps(currentConnection);
    }
    const apps = result.apps || [];
    currentDeployments = apps;
    renderManagedAppsList(apps);
  } catch (error) {
    console.error('Failed to load managed apps:', error);
    listContainer.innerHTML = `
      <div class="text-center text-text-secondary py-4">
        ${t('common.error')}: ${error.message}
      </div>
    `;
  }
}

function renderManagedAppsList(apps) {
  const listContainer = document.getElementById('devices-list');

  if (!apps || apps.length === 0) {
    listContainer.innerHTML = `
      <div class="empty-state">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="text-text-muted mb-4">
          <path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"/>
          <polyline points="7.5 4.21 12 6.81 16.5 4.21"/>
          <polyline points="7.5 19.79 7.5 14.6 3 12"/>
          <polyline points="21 12 16.5 14.6 16.5 19.79"/>
          <polyline points="3.27 6.96 12 12.01 20.73 6.96"/>
          <line x1="12" y1="22.08" x2="12" y2="12"/>
        </svg>
        <p class="text-text-secondary">${t('devices.noManagedApps')}</p>
        <p class="text-sm text-text-muted">${t('devices.noManagedAppsDesc')}</p>
      </div>
    `;
    return;
  }

  listContainer.innerHTML = `
    <div class="device-grid">
      ${apps.map(renderManagedAppCard).join('')}
    </div>
  `;

  setupManagedAppHandlers();
}

function renderManagedAppCard(app) {
  const statusClass = app.status === 'running' ? 'ready' :
                      app.status === 'exited' ? 'failed' : 'pending';
  const statusText = t(`devices.docker.containerStatus.${app.status}`) || app.status;

  const deployedDate = app.deployed_at ? new Date(app.deployed_at).toLocaleDateString() : '-';

  // Build ports display - show first 2, hover for more
  let portsDisplay = '-';
  if (app.ports && app.ports.length > 0) {
    const visiblePorts = app.ports.slice(0, 2);
    const hasMore = app.ports.length > 2;
    const allPortsTooltip = app.ports.join('\n');
    portsDisplay = `
      <div class="ports-container" ${hasMore ? `title="${allPortsTooltip}"` : ''}>
        ${visiblePorts.map(p => `<div class="port-item">${p}</div>`).join('')}
        ${hasMore ? `<div class="port-item port-more">+${app.ports.length - 2} more</div>` : ''}
      </div>`;
  }

  // Container count info
  const containerCount = app.containers ? app.containers.length : 1;
  const containerNames = app.containers ? app.containers.map(c => c.container_name).join(',') : '';

  return `
    <div class="device-management-card" data-solution-id="${app.solution_id}" data-containers="${containerNames}">
      <div class="device-card-header">
        <div>
          <div class="device-card-title">${app.solution_name || app.solution_id}</div>
          <div class="device-card-subtitle text-text-secondary">
            ${app.device_id || ''} ${deployedDate !== '-' ? `• ${deployedDate}` : ''}
            ${containerCount > 1 ? `• ${containerCount} ${t('devices.containers')}` : ''}
          </div>
        </div>
        <span class="status-badge ${statusClass}">
          <span class="status-dot"></span>
          ${statusText}
        </span>
      </div>

      <div class="device-card-body">
        <div class="device-info-row">
          <span class="device-info-label">${t('devices.docker.ports')}:</span>
          <span class="device-info-value">${portsDisplay}</span>
        </div>
      </div>

      <div class="device-card-actions">
        ${app.status === 'running' ? `
          <button class="btn btn-sm btn-secondary managed-app-action"
                  data-solution-id="${app.solution_id}" data-containers="${containerNames}" data-action="restart">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M1 4v6h6M23 20v-6h-6"/>
              <path d="M20.49 9A9 9 0 005.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 013.51 15"/>
            </svg>
            ${t('devices.actions.restart')}
          </button>
          <button class="btn btn-sm btn-secondary managed-app-action"
                  data-solution-id="${app.solution_id}" data-containers="${containerNames}" data-action="stop">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="6" y="6" width="12" height="12"/>
            </svg>
            ${t('devices.actions.stop')}
          </button>
        ` : `
          <button class="btn btn-sm btn-primary managed-app-action"
                  data-solution-id="${app.solution_id}" data-containers="${containerNames}" data-action="start">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="5 3 19 12 5 21 5 3"/>
            </svg>
            ${t('devices.actions.start')}
          </button>
        `}
        ${app.config_fields && app.config_fields.length > 0 ? `
          <button class="btn btn-sm btn-secondary managed-app-configure"
                  data-solution-id="${app.solution_id}"
                  data-solution-name="${app.solution_name || app.solution_id}">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="3"/>
              <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z"/>
            </svg>
            ${t('devices.actions.configure')}
          </button>
        ` : ''}
        <button class="btn btn-sm btn-danger managed-app-remove"
                data-solution-id="${app.solution_id}" data-containers="${containerNames}" data-solution-name="${app.solution_name || app.solution_id}">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
          </svg>
          ${t('devices.actions.remove')}
        </button>
      </div>
    </div>
  `;
}

function setupManagedAppHandlers() {
  // Start/stop/restart action handlers
  document.querySelectorAll('.managed-app-action').forEach(btn => {
    btn.addEventListener('click', async () => {
      const containersStr = btn.dataset.containers;
      const solutionId = btn.dataset.solutionId;
      const action = btn.dataset.action;

      // Get all container names for this app
      const containerNames = containersStr ? containersStr.split(',').filter(Boolean) : [];

      if (containerNames.length === 0) {
        toast.error(t('common.error'));
        return;
      }

      const originalHTML = btn.innerHTML;
      btn.disabled = true;
      btn.innerHTML = `<span class="spinner spinner-sm"></span>`;

      try {
        // Perform action on all containers in the app
        for (const containerName of containerNames) {
          if (currentConnection._local) {
            await dockerDevicesApi.localContainerAction(containerName, action);
          } else {
            await dockerDevicesApi.containerAction(currentConnection, containerName, action);
          }
        }
        toast.success(`${solutionId} ${action}ed`);
        await loadDeployedApps();
      } catch (error) {
        toast.error(error.message);
        btn.innerHTML = originalHTML;
        btn.disabled = false;
      }
    });
  });

  // Configure app button handlers
  document.querySelectorAll('.managed-app-configure').forEach(btn => {
    btn.addEventListener('click', () => {
      const solutionId = btn.dataset.solutionId;
      const solutionName = btn.dataset.solutionName;
      showConfigureModal(solutionId, solutionName);
    });
  });

  // Remove app button handlers
  document.querySelectorAll('.managed-app-remove').forEach(btn => {
    btn.addEventListener('click', () => {
      const solutionId = btn.dataset.solutionId;
      const containersStr = btn.dataset.containers;
      const solutionName = btn.dataset.solutionName;
      showRemoveAppModal(solutionId, containersStr, solutionName);
    });
  });
}

// Store pending operations
let pendingRemoveApp = null;
let pendingConfigSolutionId = null;

function showRemoveAppModal(solutionId, containerNames, solutionName) {
  const modal = document.getElementById('remove-app-modal');
  const appNameEl = document.getElementById('remove-app-name');
  const imagesCheckbox = document.getElementById('remove-images-checkbox');
  const volumesCheckbox = document.getElementById('remove-volumes-checkbox');

  pendingRemoveApp = { solutionId, containerNames };
  appNameEl.textContent = solutionName;
  imagesCheckbox.checked = false;
  volumesCheckbox.checked = false;
  modal.style.display = 'flex';
}

function setupRemoveAppModal() {
  const modal = document.getElementById('remove-app-modal');
  const cancelBtn = document.getElementById('remove-app-cancel');
  const confirmBtn = document.getElementById('remove-app-confirm');

  cancelBtn?.addEventListener('click', () => {
    modal.style.display = 'none';
    pendingRemoveApp = null;
  });

  confirmBtn?.addEventListener('click', async () => {
    if (!pendingRemoveApp) return;

    const { solutionId, containerNames } = pendingRemoveApp;
    const removeImages = document.getElementById('remove-images-checkbox').checked;
    const removeVolumes = document.getElementById('remove-volumes-checkbox').checked;
    const originalText = confirmBtn.innerHTML;

    confirmBtn.disabled = true;
    confirmBtn.innerHTML = `<span class="spinner spinner-sm"></span> ${t('devices.actions.removing')}`;

    try {
      let result;
      if (currentConnection._local) {
        result = await dockerDevicesApi.localRemoveApp(solutionId, containerNames, removeImages, removeVolumes);
      } else {
        result = await dockerDevicesApi.removeApp(currentConnection, solutionId, containerNames, removeImages, removeVolumes);
      }

      if (result.success) {
        toast.success(t('devices.actions.removed'));
      } else {
        // Partial success - show warning
        const failedContainers = result.containers?.filter(c => !c.success) || [];
        if (failedContainers.length > 0) {
          toast.warning(`${t('devices.actions.removed')} (${failedContainers.length} errors)`);
        } else {
          toast.success(t('devices.actions.removed'));
        }
      }

      modal.style.display = 'none';
      pendingRemoveApp = null;
      await loadDeployedApps();
    } catch (error) {
      toast.error(error.message);
    } finally {
      confirmBtn.disabled = false;
      confirmBtn.innerHTML = originalText;
    }
  });

  modal?.addEventListener('click', (e) => {
    if (e.target === modal) {
      modal.style.display = 'none';
      pendingRemoveApp = null;
    }
  });
}

function setupPruneImagesModal() {
  const modal = document.getElementById('prune-images-modal');
  const cancelBtn = document.getElementById('prune-images-cancel');
  const confirmBtn = document.getElementById('prune-images-confirm');

  cancelBtn?.addEventListener('click', () => {
    modal.style.display = 'none';
  });

  confirmBtn?.addEventListener('click', async () => {
    const originalText = confirmBtn.innerHTML;
    confirmBtn.disabled = true;
    confirmBtn.innerHTML = `<span class="spinner spinner-sm"></span> ${t('devices.actions.pruning')}`;

    try {
      let result;
      if (currentConnection._local) {
        result = await dockerDevicesApi.localPruneImages();
      } else {
        result = await dockerDevicesApi.pruneImages(currentConnection);
      }

      toast.success(`${t('devices.actions.pruned')}: ${result.space_reclaimed || ''}`);
      modal.style.display = 'none';
    } catch (error) {
      toast.error(error.message);
    } finally {
      confirmBtn.disabled = false;
      confirmBtn.innerHTML = originalText;
    }
  });

  modal?.addEventListener('click', (e) => {
    if (e.target === modal) {
      modal.style.display = 'none';
    }
  });
}

// ============================================
// Configure App Modal
// ============================================

async function showConfigureModal(solutionId, solutionName) {
  const modal = document.getElementById('configure-app-modal');
  const titleEl = document.getElementById('configure-app-title');
  const fieldsEl = document.getElementById('configure-form-fields');
  const errorEl = document.getElementById('configure-error');

  // Reset state
  pendingConfigSolutionId = solutionId;
  errorEl.style.display = 'none';
  fieldsEl.innerHTML = `<div class="flex items-center justify-center py-4"><div class="spinner spinner-sm"></div></div>`;
  titleEl.textContent = solutionName;
  modal.style.display = 'flex';

  try {
    const data = currentConnection?._local
      ? await dockerDevicesApi.getLocalConfig(solutionId)
      : await dockerDevicesApi.getRemoteConfig(solutionId);

    if (!data?.config?.fields?.length) {
      toast.warning(t('devices.configure.noFields'));
      modal.style.display = 'none';
      pendingConfigSolutionId = null;
      return;
    }

    const lang = i18n.locale;
    fieldsEl.innerHTML = data.config.fields.map(field => `
      <div class="mb-3">
        <label class="block text-sm font-medium mb-1">
          ${lang === 'zh' && field.name_zh ? field.name_zh : field.name}
          ${field.required ? '<span class="text-red-500">*</span>' : ''}
        </label>
        <input type="${field.type || 'text'}"
               class="input w-full"
               data-field-id="${field.id}"
               value="${field.current_value || ''}"
               placeholder="${field.placeholder || ''}" />
        ${field.description ? `<p class="text-xs text-text-secondary mt-1">${lang === 'zh' && field.description_zh ? field.description_zh : field.description}</p>` : ''}
      </div>
    `).join('');
  } catch (error) {
    fieldsEl.innerHTML = `<p class="text-text-secondary text-sm">${t('devices.configure.error')}: ${error.message}</p>`;
  }
}

function setupConfigureModal() {
  const modal = document.getElementById('configure-app-modal');
  const closeBtn = document.getElementById('configure-close');
  const cancelBtn = document.getElementById('configure-cancel');
  const saveBtn = document.getElementById('configure-save');

  const hideModal = () => {
    modal.style.display = 'none';
    pendingConfigSolutionId = null;
  };

  closeBtn?.addEventListener('click', hideModal);
  cancelBtn?.addEventListener('click', hideModal);

  modal?.addEventListener('click', (e) => {
    if (e.target === modal) hideModal();
  });

  saveBtn?.addEventListener('click', async () => {
    if (!pendingConfigSolutionId) return;

    const errorEl = document.getElementById('configure-error');
    errorEl.style.display = 'none';

    // Collect field values
    const fields = document.querySelectorAll('#configure-form-fields input');
    const values = {};
    let hasEmpty = false;
    fields.forEach(f => {
      values[f.dataset.fieldId] = f.value;
      if (f.closest('.mb-3')?.querySelector('.text-red-500') && !f.value.trim()) {
        hasEmpty = true;
      }
    });

    if (hasEmpty) {
      errorEl.textContent = t('deploy.validation.required');
      errorEl.style.display = 'block';
      return;
    }

    // Show loading state
    const originalText = saveBtn.textContent;
    saveBtn.disabled = true;
    saveBtn.textContent = t('devices.configure.saving');

    try {
      const result = currentConnection?._local
        ? await dockerDevicesApi.updateLocalConfig(pendingConfigSolutionId, values)
        : await dockerDevicesApi.updateRemoteConfig(pendingConfigSolutionId, values, currentConnection);

      if (result.success) {
        toast.success(t('devices.configure.saved'));
        hideModal();
        await loadDeployedApps();
      } else {
        errorEl.textContent = result.error || t('devices.configure.error');
        errorEl.style.display = 'block';
      }
    } catch (error) {
      errorEl.textContent = error.message || t('devices.configure.error');
      errorEl.style.display = 'block';
    } finally {
      saveBtn.disabled = false;
      saveBtn.textContent = originalText;
    }
  });
}

function renderDeploymentsList(deployments) {
  const listContainer = document.getElementById('devices-list');

  if (!deployments || deployments.length === 0) {
    listContainer.innerHTML = renderEmptyState();
    return;
  }

  listContainer.innerHTML = `
    <div class="device-grid">
      ${deployments.map(renderDeploymentCard).join('')}
    </div>
  `;

  setupEventHandlers();
}

function renderDeploymentCard(deployment) {
  const statusClass = deployment.status === 'running' ? 'ready' :
                      deployment.status === 'stopped' ? 'failed' : 'pending';

  const statusText = t(`devices.status.${deployment.status}`) || deployment.status;
  const name = i18n.locale === 'zh' && deployment.solution_name_zh
    ? deployment.solution_name_zh
    : deployment.solution_name;

  const deployedDate = new Date(deployment.deployed_at).toLocaleDateString();

  return `
    <div class="device-management-card" data-deployment-id="${deployment.deployment_id}">
      <button class="device-card-delete" data-deployment-id="${deployment.deployment_id}" title="${t('devices.actions.delete')}">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M18 6L6 18M6 6l12 12"/>
        </svg>
      </button>
      <div class="device-card-header">
        <div>
          <div class="device-card-title">${name}</div>
          <div class="device-card-subtitle text-text-secondary">
            ${deployment.device_id} - ${deployedDate}
          </div>
        </div>
        <span class="status-badge ${statusClass}">
          <span class="status-dot"></span>
          ${statusText}
        </span>
      </div>

      <div class="device-card-body">
        <div class="device-info-row">
          <span class="device-info-label">URL:</span>
          <a href="${deployment.app_url}" target="_blank" class="device-info-value link">
            ${deployment.app_url}
            <i class="ri-external-link-line ml-1"></i>
          </a>
        </div>

        ${deployment.host ? `
          <div class="device-info-row">
            <span class="device-info-label">Host:</span>
            <span class="device-info-value">${deployment.host}</span>
          </div>
        ` : ''}
      </div>

      <div class="device-card-actions">
        <button class="btn btn-sm btn-secondary action-btn"
                data-action="update"
                data-deployment-id="${deployment.deployment_id}">
          <i class="ri-refresh-line"></i>
          ${t('devices.actions.update')}
        </button>

        ${deployment.status === 'running' ? `
          <button class="btn btn-sm btn-secondary action-btn"
                  data-action="restart"
                  data-deployment-id="${deployment.deployment_id}">
            <i class="ri-restart-line"></i>
            ${t('devices.actions.restart')}
          </button>
        ` : `
          <button class="btn btn-sm btn-primary action-btn"
                  data-action="start"
                  data-deployment-id="${deployment.deployment_id}">
            <i class="ri-play-line"></i>
            ${t('devices.actions.start')}
          </button>
        `}

        <a href="${deployment.app_url}" target="_blank" class="btn btn-sm btn-primary">
          <i class="ri-external-link-line"></i>
          ${t('devices.openApp')}
        </a>
      </div>
    </div>
  `;
}

function renderEmptyState() {
  return `
    <div class="empty-state">
      <svg class="empty-state-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <rect x="4" y="4" width="16" height="16" rx="2"/>
        <path d="M9 9h6M9 13h6M9 17h4"/>
      </svg>
      <h3 class="empty-state-title">${t('devices.empty')}</h3>
      <p class="empty-state-description">${t('devices.emptyDescription')}</p>
    </div>
  `;
}

function setupEventHandlers() {
  document.querySelectorAll('.device-card-delete').forEach(btn => {
    btn.addEventListener('click', handleDeleteClick);
  });

  document.querySelectorAll('.action-btn').forEach(btn => {
    btn.addEventListener('click', handleActionClick);
  });
}

async function handleDeleteClick(event) {
  const btn = event.currentTarget;
  const deploymentId = btn.dataset.deploymentId;
  if (!confirm(t('devices.actions.confirmDelete'))) return;

  try {
    await deviceManagementApi.deleteDeployment(deploymentId);
    const card = btn.closest('.device-management-card');
    if (card) card.remove();
    toast.success(t('devices.actions.deleted'));
  } catch (error) {
    toast.error(t('common.error') + ': ' + error.message);
  }
}

async function handleActionClick(event) {
  const btn = event.currentTarget;
  const action = btn.dataset.action;
  const deploymentId = btn.dataset.deploymentId;

  const deployment = currentDeployments.find(d => d.deployment_id === deploymentId);
  if (!deployment) return;

  const needsPassword = deployment.device_type === 'docker_remote' &&
                        !deployment.connection_info?.password;

  if (needsPassword) {
    const password = await showPasswordModal();
    if (!password) return;
    await performAction(deploymentId, action, password, btn);
  } else {
    await performAction(deploymentId, action, null, btn);
  }
}

async function performAction(deploymentId, action, password, btn) {
  const originalText = btn.innerHTML;

  try {
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner spinner-sm"></span>`;

    const result = await deviceManagementApi.performAction(deploymentId, action, password);

    if (result.success) {
      toast.success(result.message);
      const deployments = await deviceManagementApi.listActive();
      currentDeployments = deployments;
      renderDeploymentsList(deployments);
    } else {
      toast.error(result.message);
      btn.innerHTML = originalText;
      btn.disabled = false;
    }
  } catch (error) {
    toast.error(error.message);
    btn.innerHTML = originalText;
    btn.disabled = false;
  }
}

// ============================================
// Password Modal
// ============================================

function setupPasswordModal() {
  const modal = document.getElementById('password-modal');
  const form = document.getElementById('password-form');
  const cancelBtn = document.getElementById('password-cancel');
  const passwordInput = document.getElementById('ssh-password');

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const password = passwordInput.value;
    passwordInput.value = '';
    modal.style.display = 'none';

    if (passwordModalCallback) {
      passwordModalCallback(password);
      passwordModalCallback = null;
    }
  });

  cancelBtn.addEventListener('click', () => {
    passwordInput.value = '';
    modal.style.display = 'none';

    if (passwordModalCallback) {
      passwordModalCallback(null);
      passwordModalCallback = null;
    }
  });

  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      passwordInput.value = '';
      modal.style.display = 'none';

      if (passwordModalCallback) {
        passwordModalCallback(null);
        passwordModalCallback = null;
      }
    }
  });
}

function showPasswordModal() {
  return new Promise((resolve) => {
    const modal = document.getElementById('password-modal');
    const passwordInput = document.getElementById('ssh-password');

    passwordModalCallback = resolve;
    passwordInput.value = '';
    modal.style.display = 'flex';
    passwordInput.focus();
  });
}

// ============================================
// Device Restore Section
// ============================================

async function setupRestoreSection() {
  // Load supported devices
  await loadRestoreDevices();

  // Setup event handlers
  document.getElementById('restore-refresh-ports')?.addEventListener('click', loadRestorePorts);
  document.getElementById('restore-start-btn')?.addEventListener('click', startRestore);
  document.getElementById('restore-logs-toggle')?.addEventListener('click', toggleRestoreLogs);

  // Monitor form inputs for button state
  document.getElementById('restore-port-select')?.addEventListener('change', updateRestoreButtonState);
  document.getElementById('restore-host')?.addEventListener('input', updateRestoreButtonState);
  document.getElementById('restore-password')?.addEventListener('input', updateRestoreButtonState);
}

async function loadRestoreDevices() {
  try {
    const devices = await restoreApi.getDevices(i18n.locale);
    restoreDevices = devices;
    renderRestoreDeviceOptions();
  } catch (error) {
    console.error('Failed to load restore devices:', error);
  }
}

function renderRestoreDeviceOptions() {
  const container = document.getElementById('restore-device-options');
  if (!container) return;

  container.innerHTML = restoreDevices.map(device => `
    <label class="restore-device-option ${selectedRestoreDevice === device.id ? 'selected' : ''}" data-device-id="${device.id}">
      <input type="radio" name="restore-device" value="${device.id}" ${selectedRestoreDevice === device.id ? 'checked' : ''}>
      <div class="restore-device-radio"></div>
      <div class="restore-device-info">
        <div class="restore-device-name">${device.name}</div>
        <div class="restore-device-desc">${device.description}</div>
      </div>
    </label>
  `).join('');

  // Setup click handlers
  container.querySelectorAll('.restore-device-option').forEach(option => {
    option.addEventListener('click', () => {
      const deviceId = option.dataset.deviceId;
      selectRestoreDevice(deviceId);
    });
  });
}

function selectRestoreDevice(deviceId) {
  selectedRestoreDevice = deviceId;

  // Update UI
  document.querySelectorAll('.restore-device-option').forEach(opt => {
    opt.classList.toggle('selected', opt.dataset.deviceId === deviceId);
  });

  // Show/hide config sections
  const watcherConfig = document.getElementById('restore-watcher-config');
  const recameraConfig = document.getElementById('restore-recamera-config');

  if (deviceId === 'sensecap_watcher') {
    watcherConfig.style.display = 'block';
    recameraConfig.style.display = 'none';
    loadRestorePorts();
  } else if (deviceId === 'recamera') {
    watcherConfig.style.display = 'none';
    recameraConfig.style.display = 'block';
  } else {
    watcherConfig.style.display = 'none';
    recameraConfig.style.display = 'none';
  }

  updateRestoreButtonState();
}

async function loadRestorePorts() {
  const select = document.getElementById('restore-port-select');
  if (!select) return;

  select.innerHTML = `<option value="">-- ${t('common.loading')} --</option>`;

  try {
    const ports = await restoreApi.getPorts();
    restorePorts = ports;

    if (ports.length === 0) {
      select.innerHTML = `<option value="">-- ${t('devices.restore.noPortsFound')} --</option>`;
    } else {
      select.innerHTML = `<option value="">-- ${t('devices.restore.selectPort')} --</option>` +
        ports.map(p => `
          <option value="${p.device}" ${p.is_himax ? 'selected' : ''}>
            ${p.device} ${p.is_himax ? '(Himax WE2)' : ''} - ${p.description}
          </option>
        `).join('');

      // Auto-select Himax port if found
      const himaxPort = ports.find(p => p.is_himax);
      if (himaxPort) {
        select.value = himaxPort.device;
      }
    }

    updateRestoreButtonState();
  } catch (error) {
    console.error('Failed to load ports:', error);
    select.innerHTML = `<option value="">-- ${t('common.error')} --</option>`;
  }
}

function updateRestoreButtonState() {
  const btn = document.getElementById('restore-start-btn');
  if (!btn) return;

  let enabled = false;

  if (selectedRestoreDevice === 'sensecap_watcher') {
    const port = document.getElementById('restore-port-select')?.value;
    enabled = !!port;
  } else if (selectedRestoreDevice === 'recamera') {
    const host = document.getElementById('restore-host')?.value?.trim();
    const password = document.getElementById('restore-password')?.value;
    enabled = !!host && !!password;
  }

  btn.disabled = !enabled || (restoreOperation && restoreOperation.status === 'running');
}

async function startRestore() {
  const btn = document.getElementById('restore-start-btn');
  if (!btn || btn.disabled) return;

  let connection = {};

  if (selectedRestoreDevice === 'sensecap_watcher') {
    connection.port = document.getElementById('restore-port-select').value;
  } else if (selectedRestoreDevice === 'recamera') {
    connection.host = document.getElementById('restore-host').value.trim();
    connection.username = document.getElementById('restore-username').value.trim() || 'root';
    connection.password = document.getElementById('restore-password').value;
  }

  // Update UI
  const originalText = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = `<span class="spinner spinner-sm"></span> ${t('devices.restore.restoring')}`;

  // Show progress
  document.getElementById('restore-progress').style.display = 'block';
  document.getElementById('restore-logs-section').style.display = 'block';
  document.getElementById('restore-logs-viewer').innerHTML = '';
  document.getElementById('restore-logs-count').textContent = '0';

  try {
    const result = await restoreApi.start(selectedRestoreDevice, connection);

    if (result.success) {
      restoreOperation = { id: result.operation_id, status: 'running' };
      startRestorePolling(result.operation_id);
    }
  } catch (error) {
    toast.error(error.message || t('devices.restore.failed'));
    btn.disabled = false;
    btn.innerHTML = originalText;
    restoreOperation = null;
  }
}

function startRestorePolling(operationId) {
  // Clear any existing polling
  if (restorePollingInterval) {
    clearInterval(restorePollingInterval);
  }

  // Poll every 1 second
  restorePollingInterval = setInterval(async () => {
    try {
      const status = await restoreApi.getStatus(operationId);
      updateRestoreProgress(status);

      if (status.status === 'completed' || status.status === 'failed') {
        clearInterval(restorePollingInterval);
        restorePollingInterval = null;
        restoreOperation = status;

        // Reset button
        const btn = document.getElementById('restore-start-btn');
        if (btn) {
          btn.disabled = false;
          btn.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>
              <path d="M3 3v5h5"/>
            </svg>
            ${t('devices.restore.startRestore')}
          `;
        }

        if (status.status === 'completed') {
          toast.success(t('devices.restore.success'));
        } else {
          toast.error(status.error || t('devices.restore.failed'));
        }
      }
    } catch (error) {
      console.error('Failed to get restore status:', error);
    }
  }, 1000);
}

function updateRestoreProgress(status) {
  // Update progress bar
  const progressBar = document.getElementById('restore-progress-bar');
  const progressPercent = document.getElementById('restore-progress-percent');
  const progressMessage = document.getElementById('restore-progress-message');

  if (progressBar) progressBar.style.width = `${status.progress}%`;
  if (progressPercent) progressPercent.textContent = `${status.progress}%`;
  if (progressMessage) progressMessage.textContent = status.message || status.current_step || '';

  // Update logs
  const logsViewer = document.getElementById('restore-logs-viewer');
  const logsCount = document.getElementById('restore-logs-count');

  if (logsViewer && status.logs) {
    logsViewer.innerHTML = status.logs.map(log => `
      <div class="deploy-log-entry ${log.level}">
        <span class="time">${new Date(log.timestamp).toLocaleTimeString()}</span>
        <span class="msg">${log.message}</span>
      </div>
    `).join('');
    logsViewer.scrollTop = logsViewer.scrollHeight;

    if (logsCount) logsCount.textContent = status.logs.length;
  }
}

function toggleRestoreLogs() {
  const panel = document.getElementById('restore-logs-panel');
  const chevron = document.getElementById('restore-logs-chevron');

  if (panel) {
    panel.classList.toggle('expanded');
  }
  if (chevron) {
    chevron.classList.toggle('expanded');
  }
}

// Re-render when language changes
i18n.onLocaleChange(() => {
  if (router.currentRoute === 'devices') {
    renderDevicesPage();
  }
});
