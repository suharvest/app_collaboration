/**
 * Deploy Page - Docker Installation Dialog
 * Handles Docker not installed scenarios and auto-installation
 */

import { t } from '../../modules/i18n.js';
import { deploymentsApi } from '../../modules/api.js';
import { escapeHtml } from '../../modules/utils.js';
import { toast } from '../../modules/toast.js';
import {
  getCurrentSolution,
  getDeviceState,
  getSelectedPresetId,
} from './state.js';
import { getDeviceById, getSelectedTarget } from './utils.js';
import { updateSectionUI, updateChoiceOptionUI } from './ui-updates.js';
import { addLogToDevice, connectLogsWebSocket } from './websocket.js';

// ============================================
// Docker Not Installed Handler
// ============================================

/**
 * Handle Docker not installed event from WebSocket
 */
export function handleDockerNotInstalled(deviceId, data) {
  const state = getDeviceState(deviceId);
  if (!state) return;

  // Flag to suppress the generic failure toast — the dialog (or specific error) is enough
  state.dockerInstallPending = true;

  // Update status to failed (deployment stopped)
  state.deploymentStatus = 'failed';
  updateSectionUI(deviceId);
  updateChoiceOptionUI(deviceId);

  if (data.can_auto_fix) {
    // Show confirmation dialog
    showDockerInstallDialog(deviceId, data.message, data.fix_action);
  } else {
    addLogToDevice(deviceId, 'error', data.message);
    toast.error(data.message);
  }
}

// ============================================
// Docker Installation Dialog
// ============================================

/**
 * Show dialog asking user to confirm Docker installation
 */
export function showDockerInstallDialog(deviceId, message, fixAction) {
  // Create dialog overlay
  const overlay = document.createElement('div');
  overlay.className = 'dialog-overlay';
  overlay.id = 'docker-install-dialog';

  const actionText = fixAction === 'install_docker' ? t('deploy.docker.installAction') :
                     fixAction === 'fix_docker_permission' ? t('deploy.docker.fixPermissionAction') :
                     fixAction === 'start_docker' ? t('deploy.docker.startAction') :
                     fixAction === 'replace_containers' ? t('deploy.docker.replaceAction') :
                     t('deploy.docker.fixAction');

  const dialogTitle = fixAction === 'replace_containers'
    ? t('deploy.docker.existingContainers')
    : t('deploy.docker.notInstalled');
  const dialogHint = fixAction === 'replace_containers'
    ? t('deploy.docker.replaceHint')
    : t('deploy.docker.installHint');

  overlay.innerHTML = `
    <div class="dialog">
      <div class="dialog-header">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
          <line x1="12" y1="9" x2="12" y2="13"/>
          <line x1="12" y1="17" x2="12.01" y2="17"/>
        </svg>
        <h3>${dialogTitle}</h3>
      </div>
      <div class="dialog-body">
        <p>${escapeHtml(message)}</p>
        <p class="dialog-hint">${dialogHint}</p>
      </div>
      <div class="dialog-actions">
        <button class="btn btn-secondary" id="dialog-cancel">${t('common.cancel')}</button>
        <button class="btn btn-primary" id="dialog-confirm">${actionText}</button>
      </div>
    </div>
  `;

  document.body.appendChild(overlay);

  // Handle cancel
  overlay.querySelector('#dialog-cancel').addEventListener('click', () => {
    overlay.remove();
    addLogToDevice(deviceId, 'warning', t('deploy.docker.installCancelled'));
  });

  // Handle confirm - restart deployment with appropriate auto-fix flag
  overlay.querySelector('#dialog-confirm').addEventListener('click', () => {
    overlay.remove();
    const logMsg = fixAction === 'replace_containers'
      ? t('deploy.docker.replacing')
      : t('deploy.docker.installing');
    addLogToDevice(deviceId, 'info', logMsg);
    startDeploymentWithDockerInstall(deviceId, fixAction);
  });

  // Click outside to close
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) {
      overlay.remove();
      addLogToDevice(deviceId, 'warning', t('deploy.docker.installCancelled'));
    }
  });
}

// ============================================
// Deployment with Docker Installation
// ============================================

/**
 * Start deployment with auto-fix flag (Docker install or container replacement)
 */
export async function startDeploymentWithDockerInstall(deviceId, fixAction = 'install_docker') {
  const device = getDeviceById(deviceId);
  if (!device) return;

  const currentSolution = getCurrentSolution();
  const state = getDeviceState(deviceId);
  state.dockerInstallPending = false;
  state.deploymentStatus = 'running';
  updateSectionUI(deviceId);
  updateChoiceOptionUI(deviceId);

  // Build params with auto_install_docker flag
  const params = {
    solution_id: currentSolution.id,
    preset_id: getSelectedPresetId(),  // Include preset ID for preset-based solutions
    selected_devices: [deviceId],
    device_connections: {},
    options: {},
  };

  // Get selected target for docker_deploy with targets
  let selectedTarget = null;
  if (device.targets) {
    selectedTarget = getSelectedTarget(device);
  }
  if (selectedTarget) {
    params.options.deploy_target = selectedTarget.id;
    params.options.config_file = selectedTarget.config_file;
  }

  // Build auto-fix flags based on fixAction
  const autoFixFlags = fixAction === 'replace_containers'
    ? { auto_replace_containers: true }
    : { auto_install_docker: true };

  // Add connection info with appropriate auto-fix flag
  const traits = device.ui_traits || {};
  const isRemote = selectedTarget?.id === 'remote' ||
                   selectedTarget?.id?.endsWith('_remote') ||
                   selectedTarget?.id?.includes('remote');

  if (traits.connection === 'ssh' || (traits.has_targets && selectedTarget && isRemote)) {
    params.device_connections[deviceId] = {
      host: document.getElementById(`ssh-host-${deviceId}`)?.value,
      port: parseInt(document.getElementById(`ssh-port-${deviceId}`)?.value || '22'),
      username: document.getElementById(`ssh-user-${deviceId}`)?.value,
      password: document.getElementById(`ssh-pass-${deviceId}`)?.value,
      ...autoFixFlags,
    };
    if (selectedTarget) {
      params.device_connections[deviceId].target = selectedTarget.id;
      params.device_connections[deviceId].target_type = selectedTarget.target_type || (isRemote ? 'remote' : 'local');
    }
  } else if (device.type === 'docker_remote') {
    // Legacy: direct docker_remote type
    params.device_connections[deviceId] = {
      host: document.getElementById(`ssh-host-${deviceId}`)?.value,
      port: parseInt(document.getElementById(`ssh-port-${deviceId}`)?.value || '22'),
      username: document.getElementById(`ssh-user-${deviceId}`)?.value,
      password: document.getElementById(`ssh-pass-${deviceId}`)?.value,
      ...autoFixFlags,
    };
  } else {
    // Local deployment (docker_local) - no SSH needed, just pass the flag
    params.device_connections[deviceId] = {
      ...autoFixFlags,
    };
    if (selectedTarget) {
      params.device_connections[deviceId].target = selectedTarget.id;
      params.device_connections[deviceId].target_type = 'local';
    }
  }

  try {
    const result = await deploymentsApi.start(params);
    connectLogsWebSocket(result.deployment_id, deviceId);
    addLogToDevice(deviceId, 'info', `Deployment ID: ${result.deployment_id}`);
  } catch (error) {
    console.error('Deployment failed:', error);
    state.deploymentStatus = 'failed';
    updateSectionUI(deviceId);
    updateChoiceOptionUI(deviceId);
    addLogToDevice(deviceId, 'error', error.message);
    toast.error(t('common.error') + ': ' + error.message);
  }
}
