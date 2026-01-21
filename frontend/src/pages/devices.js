/**
 * Device Management Page
 *
 * Displays deployed applications with controls for:
 * - Application status monitoring
 * - Update/restart actions
 * - Kiosk mode configuration
 */

import { deviceManagementApi } from '../modules/api.js';
import { t, i18n, getLocalizedField } from '../modules/i18n.js';
import { router } from '../modules/router.js';
import { toast } from '../modules/toast.js';

let currentDeployments = [];
let passwordModalCallback = null;

export async function renderDevicesPage() {
  const container = document.getElementById('content-area');

  container.innerHTML = `
    <div class="page-header">
      <h1 class="page-title" data-i18n="devices.title">${t('devices.title')}</h1>
      <p class="page-subtitle text-text-secondary" data-i18n="devices.subtitle">${t('devices.subtitle')}</p>
    </div>

    <div id="devices-list">
      <div class="flex items-center justify-center py-8">
        <div class="spinner spinner-lg"></div>
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

  // Setup password modal handlers
  setupPasswordModal();

  try {
    const deployments = await deviceManagementApi.listActive();
    currentDeployments = deployments;
    renderDeploymentsList(deployments);
  } catch (error) {
    console.error('Failed to load devices:', error);
    toast.error(t('common.error') + ': ' + error.message);
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

  // Setup event handlers
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
        <!-- URL -->
        <div class="device-info-row">
          <span class="device-info-label">URL:</span>
          <a href="${deployment.app_url}" target="_blank" class="device-info-value link">
            ${deployment.app_url}
            <i class="ri-external-link-line ml-1"></i>
          </a>
        </div>

        <!-- Host (for remote) -->
        ${deployment.host ? `
          <div class="device-info-row">
            <span class="device-info-label">Host:</span>
            <span class="device-info-value">${deployment.host}</span>
          </div>
        ` : ''}

        <!-- Kiosk Status -->
        <div class="device-info-row kiosk-row">
          <span class="device-info-label">${t('devices.kiosk.title')}:</span>
          <div class="kiosk-controls">
            <label class="toggle-switch">
              <input type="checkbox"
                     class="kiosk-toggle"
                     data-deployment-id="${deployment.deployment_id}"
                     ${deployment.kiosk_enabled ? 'checked' : ''}>
              <span class="toggle-slider"></span>
            </label>
            ${deployment.kiosk_enabled ?
              `<span class="kiosk-user text-sm text-text-secondary ml-2">(${deployment.kiosk_user})</span>` : ''}
          </div>
        </div>
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
      <h3 class="empty-state-title" data-i18n="devices.empty">${t('devices.empty')}</h3>
      <p class="empty-state-description" data-i18n="devices.emptyDescription">${t('devices.emptyDescription')}</p>
    </div>
  `;
}

function setupEventHandlers() {
  // Action buttons
  document.querySelectorAll('.action-btn').forEach(btn => {
    btn.addEventListener('click', handleActionClick);
  });

  // Kiosk toggles
  document.querySelectorAll('.kiosk-toggle').forEach(toggle => {
    toggle.addEventListener('change', handleKioskToggle);
  });
}

async function handleActionClick(event) {
  const btn = event.currentTarget;
  const action = btn.dataset.action;
  const deploymentId = btn.dataset.deploymentId;

  const deployment = currentDeployments.find(d => d.deployment_id === deploymentId);
  if (!deployment) return;

  // Check if remote and might need password
  const needsPassword = deployment.device_type === 'docker_remote' &&
                        !deployment.connection_info?.password;

  if (needsPassword) {
    // Show password modal
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
      // Refresh the list
      const deployments = await deviceManagementApi.listActive();
      currentDeployments = deployments;
      renderDeploymentsList(deployments);
    } else {
      toast.error(result.message);
      btn.innerHTML = originalText;
      btn.disabled = false;
    }
  } catch (error) {
    console.error('Action failed:', error);
    toast.error(error.message);
    btn.innerHTML = originalText;
    btn.disabled = false;
  }
}

async function handleKioskToggle(event) {
  const toggle = event.currentTarget;
  const deploymentId = toggle.dataset.deploymentId;
  const enabled = toggle.checked;

  const deployment = currentDeployments.find(d => d.deployment_id === deploymentId);
  if (!deployment) return;

  // If enabling, we need user input
  if (enabled) {
    const kioskUser = prompt(t('devices.kiosk.user') + ':', 'user');
    if (!kioskUser) {
      toggle.checked = false;
      return;
    }

    // Check if needs password for remote
    const needsPassword = deployment.device_type === 'docker_remote' &&
                          !deployment.connection_info?.password;

    let password = null;
    if (needsPassword) {
      password = await showPasswordModal();
      if (!password) {
        toggle.checked = false;
        return;
      }
    }

    await configureKiosk(deploymentId, enabled, kioskUser, password, toggle);
  } else {
    // Disabling - need user that was configured
    const kioskUser = deployment.kiosk_user || 'user';

    const needsPassword = deployment.device_type === 'docker_remote' &&
                          !deployment.connection_info?.password;

    let password = null;
    if (needsPassword) {
      password = await showPasswordModal();
      if (!password) {
        toggle.checked = true;
        return;
      }
    }

    await configureKiosk(deploymentId, enabled, kioskUser, password, toggle);
  }
}

async function configureKiosk(deploymentId, enabled, kioskUser, password, toggle) {
  const kioskRow = toggle.closest('.kiosk-row');
  const controlsDiv = kioskRow.querySelector('.kiosk-controls');
  const originalHTML = controlsDiv.innerHTML;

  try {
    controlsDiv.innerHTML = `<span class="spinner spinner-sm"></span> <span class="ml-2">${t('devices.kiosk.configuring')}</span>`;

    const result = await deviceManagementApi.configureKiosk(deploymentId, {
      enabled,
      kiosk_user: kioskUser,
      password,
    });

    if (result.success) {
      toast.success(result.message);
      // Refresh the list
      const deployments = await deviceManagementApi.listActive();
      currentDeployments = deployments;
      renderDeploymentsList(deployments);
    } else {
      toast.error(result.message);
      controlsDiv.innerHTML = originalHTML;
      toggle.checked = !enabled;
    }
  } catch (error) {
    console.error('Kiosk config failed:', error);
    toast.error(error.message);
    controlsDiv.innerHTML = originalHTML;
    toggle.checked = !enabled;
  }
}

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

  // Close on backdrop click
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
