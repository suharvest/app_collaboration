/**
 * Deploy Page - UI Update Functions
 * Shared UI update functions used by multiple modules
 * This file should not import from websocket.js or handlers.js to avoid circular dependencies
 */

import { t } from '../../modules/i18n.js';
import {
  getCurrentSolution,
  getDeviceStates,
  getDeviceState,
  getSelectedDevice,
} from './state.js';
import {
  getDeviceById,
  getStatusClass,
  getStatusIcon,
  getStatusText,
  getButtonClass,
  getDeployButtonContent,
  areAllRequiredDevicesCompleted,
} from './utils.js';
import {
  renderSelectedDeviceContent,
  renderDockerTargetContent,
  renderRecameraCppTargetContent,
  renderPostDeploymentSection,
} from './renderers.js';

// ============================================
// Section UI Updates
// ============================================

/**
 * Update section UI for a device
 */
export function updateSectionUI(deviceId) {
  const state = getDeviceState(deviceId);
  if (!state) return;

  // Update status badge
  const statusEl = document.getElementById(`status-${deviceId}`);
  if (statusEl) {
    statusEl.className = `deploy-section-status ${getStatusClass(state)}`;
    statusEl.innerHTML = `${getStatusIcon(state)}<span>${getStatusText(state)}</span>`;
  }

  // Update step number
  const stepEl = document.getElementById(`step-${deviceId}`);
  if (stepEl && state.deploymentStatus === 'completed') {
    stepEl.classList.add('completed');
    stepEl.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>`;
  }

  // Update button
  const btn = document.getElementById(`deploy-btn-${deviceId}`);
  if (btn) {
    const device = getDeviceById(deviceId);
    btn.innerHTML = getDeployButtonContent(state, device?.type === 'manual');
    btn.disabled = state.deploymentStatus === 'running';
    btn.className = `deploy-action-btn ${getButtonClass(state)}`;
  }

  // Update logs count
  const logsCount = document.getElementById(`logs-count-${deviceId}`);
  if (logsCount) {
    logsCount.textContent = state.logs.length;
  }

  // Update post-deployment section if all required devices are now complete
  updatePostDeploymentUI();
}

/**
 * Update the post-deployment success section
 * Called when any device status changes to check if all required devices are complete
 */
export function updatePostDeploymentUI() {
  const currentSolution = getCurrentSolution();
  const deployment = currentSolution?.deployment;
  if (!deployment) return;

  const container = document.getElementById('post-deployment-container');
  if (!container) return;

  // Re-render the post-deployment section
  container.innerHTML = renderPostDeploymentSection(deployment);
}

/**
 * Toggle section expand/collapse
 */
export function toggleSection(deviceId) {
  const state = getDeviceState(deviceId);
  if (!state) return;

  state.sectionExpanded = !state.sectionExpanded;

  const content = document.getElementById(`content-${deviceId}`);
  const chevron = document.getElementById(`chevron-${deviceId}`);

  if (content) content.classList.toggle('expanded', state.sectionExpanded);
  if (chevron) chevron.classList.toggle('expanded', state.sectionExpanded);
}

/**
 * Expand the next section after completing current one
 */
export function expandNextSection(currentDeviceId) {
  const currentSolution = getCurrentSolution();
  const deviceStates = getDeviceStates();
  const deployment = currentSolution?.deployment || {};

  // Only expand next for sequential mode
  if (deployment.selection_mode === 'single_choice') return;

  const devices = deployment.devices || [];
  const currentIndex = devices.findIndex(d => d.id === currentDeviceId);

  if (currentIndex >= 0 && currentIndex < devices.length - 1) {
    const nextDevice = devices[currentIndex + 1];
    const nextState = deviceStates[nextDevice.id];
    if (nextState && !nextState.sectionExpanded) {
      toggleSection(nextDevice.id);
    }
  }
}

// ============================================
// Choice Option UI (Single Choice Mode)
// ============================================

/**
 * Update choice option UI for single_choice mode
 * @param {string} deviceId
 * @param {Function} setupHandlers - Optional handler setup function to avoid circular dependency
 */
export function updateChoiceOptionUI(deviceId, setupHandlers = null) {
  const state = getDeviceState(deviceId);
  if (!state) return;

  const option = document.querySelector(`.deploy-choice-option[data-device-id="${deviceId}"]`);
  if (!option) return;

  const isCompleted = state.deploymentStatus === 'completed';

  // Update option classes
  option.classList.toggle('completed', isCompleted);

  // Update radio visual
  const radioDiv = option.querySelector('.deploy-choice-radio');
  if (radioDiv && isCompleted) {
    radioDiv.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>`;
  }

  // Update or add status badge
  let statusBadge = option.querySelector('.deploy-choice-status');
  if (isCompleted) {
    if (!statusBadge) {
      statusBadge = document.createElement('div');
      statusBadge.className = 'deploy-choice-status completed';
      option.appendChild(statusBadge);
    }
    statusBadge.innerHTML = `
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <polyline points="20 6 9 17 4 12"/>
      </svg>
      <span>${t('deploy.status.completed')}</span>
    `;
  }

  // Also update the selected section content
  const selectedDevice = getSelectedDevice();
  const container = document.getElementById('content-area');
  if (container && selectedDevice === deviceId) {
    const selectedSection = container.querySelector('#selected-device-section');
    if (selectedSection) {
      const device = getDeviceById(deviceId);
      selectedSection.innerHTML = device ? renderSelectedDeviceContent(device) : '';
      // Call setupHandlers if provided
      if (setupHandlers) {
        setupHandlers(container);
      }
    }
  }
}

// ============================================
// Docker Target UI
// ============================================

/**
 * Update docker target UI when user switches between local/remote
 * @param {string} deviceId
 * @param {HTMLElement} container
 * @param {Function} testSSHHandler - Optional SSH test handler to avoid circular dependency
 * @param {Function} scanMdnsHandler - Optional mDNS scan handler to avoid circular dependency
 */
export function updateDockerTargetUI(deviceId, container, testSSHHandler = null, scanMdnsHandler = null) {
  const device = getDeviceById(deviceId);
  if (!device || !device.targets) return;

  const state = getDeviceState(deviceId);

  // Update target selector options (selected state)
  container.querySelectorAll(`.deploy-mode-option[data-device-id="${deviceId}"]`).forEach(el => {
    const targetId = el.dataset.targetId;
    const isSelected = targetId === state.selectedTarget;
    el.classList.toggle('selected', isSelected);
    const radio = el.querySelector('input[type="radio"]');
    if (radio) radio.checked = isSelected;
  });

  // Re-render target content based on device type
  const contentEl = document.getElementById(`target-content-${deviceId}`);
  if (contentEl) {
    if (device.type === 'recamera_cpp') {
      contentEl.innerHTML = renderRecameraCppTargetContent(device);
    } else {
      contentEl.innerHTML = renderDockerTargetContent(device);
    }

    // Re-attach SSH test button handler if provided
    if (testSSHHandler) {
      const testBtn = contentEl.querySelector(`#test-ssh-${deviceId}`);
      if (testBtn) {
        testBtn.addEventListener('click', async (e) => {
          e.stopPropagation();
          await testSSHHandler(deviceId, testBtn);
        });
      }
    }

    // Re-attach mDNS scan button handler if provided
    if (scanMdnsHandler) {
      const scanBtn = contentEl.querySelector(`#scan-mdns-${deviceId}`);
      if (scanBtn) {
        scanBtn.addEventListener('click', async (e) => {
          e.stopPropagation();
          await scanMdnsHandler(deviceId, scanBtn);
        });
      }
    }
  }
}
