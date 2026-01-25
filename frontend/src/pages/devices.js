/**
 * Device Management Page
 *
 * Top section: SSH connection form for Docker container management
 * Bottom section: Previously deployed apps (legacy device management)
 */

import { deviceManagementApi, dockerDevicesApi } from '../modules/api.js';
import { t, i18n } from '../modules/i18n.js';
import { router } from '../modules/router.js';
import { toast } from '../modules/toast.js';

let currentConnection = null;
let currentContainers = [];
let currentDeployments = [];
let passwordModalCallback = null;

export async function renderDevicesPage() {
  const container = document.getElementById('content-area');

  container.innerHTML = `
    <div class="page-header">
      <h1 class="page-title" data-i18n="devices.title">${t('devices.title')}</h1>
      <p class="page-subtitle text-text-secondary" data-i18n="devices.subtitle">${t('devices.subtitle')}</p>
    </div>

    <!-- Docker Device Connection -->
    <div class="docker-connect-section mb-6">
      <div class="docker-connect-card">
        <div class="docker-connect-header">
          <h3 class="docker-connect-title">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="2" y="2" width="20" height="8" rx="2"/>
              <rect x="2" y="14" width="20" height="8" rx="2"/>
              <circle cx="6" cy="6" r="1"/><circle cx="6" cy="18" r="1"/>
            </svg>
            ${t('devices.docker.title')}
          </h3>
          <div id="docker-connection-status"></div>
        </div>
        <form id="docker-connect-form" class="docker-connect-form">
          <div class="docker-connect-fields">
            <div class="form-group mb-0">
              <label>${t('deploy.connection.host')}</label>
              <input type="text" id="docker-host" class="input" placeholder="192.168.x.x" required>
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

    <!-- Container List (shown after connection) -->
    <div id="containers-section" style="display: none;">
      <div class="containers-header mb-4">
        <h3 class="text-base font-semibold text-text-primary">${t('devices.docker.containers')}</h3>
        <button class="btn btn-sm btn-secondary" id="refresh-containers-btn">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M1 4v6h6M23 20v-6h-6"/>
            <path d="M20.49 9A9 9 0 005.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 013.51 15"/>
          </svg>
          ${t('devices.actions.refresh')}
        </button>
      </div>
      <div id="containers-list">
        <div class="flex items-center justify-center py-4">
          <div class="spinner spinner-lg"></div>
        </div>
      </div>
    </div>

    <!-- Deployed Applications (legacy) -->
    <div class="mt-8" id="deployed-apps-section">
      <h3 class="text-base font-semibold text-text-primary mb-4">${t('devices.deployedApps')}</h3>
      <div id="devices-list">
        <div class="flex items-center justify-center py-4">
          <div class="spinner spinner-lg"></div>
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
  `;

  // Setup handlers
  setupDockerConnectForm();
  setupPasswordModal();

  // Load deployed apps (legacy)
  loadDeployedApps();
}

// ============================================
// Docker Connection & Container Management
// ============================================

function setupDockerConnectForm() {
  const form = document.getElementById('docker-connect-form');
  form.addEventListener('submit', handleDockerConnect);

  const refreshBtn = document.getElementById('refresh-containers-btn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', refreshContainers);
  }

  // Restore last connection from sessionStorage
  const saved = sessionStorage.getItem('docker_connection');
  if (saved) {
    try {
      const conn = JSON.parse(saved);
      document.getElementById('docker-host').value = conn.host || '';
      document.getElementById('docker-username').value = conn.username || 'recomputer';
    } catch (e) {}
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
      await loadContainers();
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

async function loadContainers() {
  if (!currentConnection) return;

  const section = document.getElementById('containers-section');
  section.style.display = 'block';

  const listEl = document.getElementById('containers-list');
  listEl.innerHTML = `<div class="flex items-center justify-center py-4"><div class="spinner spinner-lg"></div></div>`;

  try {
    const result = await dockerDevicesApi.listContainers(currentConnection);
    currentContainers = result.containers || [];
    renderContainersList();
  } catch (error) {
    listEl.innerHTML = `<div class="text-center text-text-secondary py-4">${t('common.error')}: ${error.message}</div>`;
  }
}

async function refreshContainers() {
  await loadContainers();
}

function renderContainersList() {
  const listEl = document.getElementById('containers-list');

  if (!currentContainers || currentContainers.length === 0) {
    listEl.innerHTML = `
      <div class="text-center text-text-secondary py-4">
        ${t('devices.docker.noContainers')}
      </div>
    `;
    return;
  }

  listEl.innerHTML = `
    <div class="container-table">
      <div class="container-table-header">
        <div class="container-col-name">${t('devices.docker.containerName')}</div>
        <div class="container-col-image">${t('devices.docker.image')}</div>
        <div class="container-col-version">${t('devices.docker.version')}</div>
        <div class="container-col-status">${t('devices.docker.status')}</div>
        <div class="container-col-actions">${t('devices.docker.actions')}</div>
      </div>
      ${currentContainers.map(renderContainerRow).join('')}
    </div>
  `;

  setupContainerHandlers();
}

function renderContainerRow(container) {
  const statusClass = container.status === 'running' ? 'ready' :
                      container.status === 'exited' ? 'failed' : 'pending';

  const statusText = t(`devices.docker.containerStatus.${container.status}`) || container.status;

  return `
    <div class="container-table-row" data-container="${container.name}">
      <div class="container-col-name">
        <span class="container-name-text">${container.name}</span>
      </div>
      <div class="container-col-image">${container.image}</div>
      <div class="container-col-version">
        <span class="container-version-tag">${container.current_tag}</span>
        ${container.update_available ? `<span class="container-update-badge">!</span>` : ''}
      </div>
      <div class="container-col-status">
        <span class="status-badge ${statusClass}">${statusText}</span>
      </div>
      <div class="container-col-actions">
        ${container.status === 'running' ? `
          <button class="btn btn-sm btn-secondary container-action-btn" data-container="${container.name}" data-action="restart" title="Restart">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M1 4v6h6M23 20v-6h-6"/>
              <path d="M20.49 9A9 9 0 005.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 013.51 15"/>
            </svg>
          </button>
          <button class="btn btn-sm btn-secondary container-action-btn" data-container="${container.name}" data-action="stop" title="Stop">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="6" y="6" width="12" height="12"/>
            </svg>
          </button>
        ` : `
          <button class="btn btn-sm btn-primary container-action-btn" data-container="${container.name}" data-action="start" title="Start">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="5 3 19 12 5 21 5 3"/>
            </svg>
          </button>
        `}
      </div>
    </div>
  `;
}

function setupContainerHandlers() {
  document.querySelectorAll('.container-action-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const containerName = btn.dataset.container;
      const action = btn.dataset.action;

      const originalHTML = btn.innerHTML;
      btn.disabled = true;
      btn.innerHTML = `<span class="spinner spinner-sm"></span>`;

      try {
        await dockerDevicesApi.containerAction(currentConnection, containerName, action);
        toast.success(`${containerName} ${action}ed`);
        await loadContainers();
      } catch (error) {
        toast.error(error.message);
        btn.innerHTML = originalHTML;
        btn.disabled = false;
      }
    });
  });
}

// ============================================
// Deployed Applications (Legacy)
// ============================================

async function loadDeployedApps() {
  try {
    const deployments = await deviceManagementApi.listActive();
    currentDeployments = deployments;
    renderDeploymentsList(deployments);
  } catch (error) {
    console.error('Failed to load devices:', error);
    document.getElementById('devices-list').innerHTML = renderEmptyState();
  }
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

// Re-render when language changes
i18n.onLocaleChange(() => {
  if (router.currentRoute === 'devices') {
    renderDevicesPage();
  }
});
