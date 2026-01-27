/**
 * Deploy Page - Event Handlers
 * All event handling and UI update functions
 */

import { t, getLocalizedField, i18n } from '../../modules/i18n.js';
import { solutionsApi } from '../../modules/api.js';
import { escapeHtml } from '../../modules/utils.js';
import { toast } from '../../modules/toast.js';
import { router } from '../../modules/router.js';
import {
  getCurrentSolution,
  getDeviceStates,
  getDeviceState,
  getSelectedDevice,
  getSelectedPresetId,
  setSelectedDevice,
  setSelectedPresetId,
  setShowDetailedLogs,
  setDeviceGroupSelection,
  createInitialDeviceState,
  cleanupState,
} from './state.js';
import {
  getFilteredDeviceGroups,
  getFilteredDevices,
  getDeviceById,
} from './utils.js';
import {
  renderDeploySection,
  renderDeviceGroupSections,
  renderSelectedDeviceContent,
} from './renderers.js';
import { toggleLogs, refreshAllLogViewers } from './websocket.js';
import { initPreviewWindow, handlePreviewButtonClick } from './preview.js';
import { startDeployment, testSSHConnection, refreshSerialPorts, markDeviceComplete } from './devices.js';
import {
  updateSectionUI,
  toggleSection,
  expandNextSection,
  updateChoiceOptionUI,
  updateDockerTargetUI as baseUpdateDockerTargetUI,
} from './ui-updates.js';

// Re-export UI update functions so other modules can import from handlers.js
export { updateSectionUI, toggleSection, expandNextSection, updateChoiceOptionUI };

// ============================================
// Main Event Setup
// ============================================

/**
 * Setup all event handlers for the deploy page
 */
export function setupEventHandlers(container) {
  const currentSolution = getCurrentSolution();

  // Back button
  container.querySelector('#back-btn')?.addEventListener('click', () => {
    cleanupState();
    router.navigate('solution', { id: currentSolution.id });
  });

  // Radio options for single_choice mode
  container.querySelectorAll('.deploy-choice-option').forEach(el => {
    el.addEventListener('click', () => {
      const deviceId = el.dataset.deviceId;
      if (getSelectedDevice() !== deviceId) {
        setSelectedDevice(deviceId);
        // Re-render the options and selected section
        updateSelectedDevice(container);
      }
    });
  });

  // Docker deploy target options (local/remote)
  container.querySelectorAll('.deploy-mode-option[data-target-id]').forEach(el => {
    el.addEventListener('click', () => {
      const deviceId = el.dataset.deviceId;
      const targetId = el.dataset.targetId;
      const state = getDeviceState(deviceId);

      if (state && state.selectedTarget !== targetId) {
        state.selectedTarget = targetId;
        // Update UI: re-render target selector and content
        updateDockerTargetUI(deviceId, container);
      }
    });
  });

  // Preset selector buttons (Level 1)
  container.querySelectorAll('.deploy-preset-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const presetId = btn.dataset.presetId;
      handlePresetChange(presetId);
    });
  });

  // Device group selectors (template variable replacement)
  container.querySelectorAll('.device-group-selector').forEach(select => {
    select.addEventListener('change', async (e) => {
      const groupId = select.dataset.groupId;
      const selectedDevice = e.target.value;
      await handleDeviceGroupSelectorChange(groupId, selectedDevice);
    });
  });

  // Section headers (expand/collapse)
  container.querySelectorAll('[id^="section-header-"]').forEach(el => {
    el.addEventListener('click', () => {
      const deviceId = el.dataset.deviceId;
      toggleSection(deviceId);
    });
  });

  // Deploy buttons
  container.querySelectorAll('[id^="deploy-btn-"]').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const deviceId = btn.dataset.deviceId;
      const device = getDeviceById(deviceId);

      if (device?.type === 'manual') {
        markDeviceComplete(deviceId, expandNextSection);
      } else if (device?.type === 'preview') {
        handlePreviewButtonClick(deviceId);
      } else {
        startDeployment(deviceId);
      }
    });
  });

  // Initialize preview windows
  const deployment = currentSolution.deployment || {};
  const devices = deployment.devices || [];
  devices.forEach(device => {
    if (device.type === 'preview') {
      initPreviewWindow(device.id);
    }
  });

  // Logs toggle
  container.querySelectorAll('[id^="logs-toggle-"]').forEach(el => {
    el.addEventListener('click', (e) => {
      e.stopPropagation();
      const deviceId = el.dataset.deviceId;
      toggleLogs(deviceId);
    });
  });

  // Refresh ports
  container.querySelectorAll('[id^="refresh-ports-"]').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      await refreshSerialPorts(btn);
    });
  });

  // Test SSH connection
  container.querySelectorAll('[id^="test-ssh-"]').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const deviceId = btn.dataset.deviceId;
      await testSSHConnection(deviceId, btn);
    });
  });

  // Setup handlers for selected device section (single_choice mode)
  setupSelectedDeviceHandlers(container);

  // Serial port selection
  container.querySelectorAll('[id^="serial-port-"]').forEach(select => {
    select.addEventListener('change', () => {
      const deviceId = select.id.replace('serial-port-', '');
      const deviceStates = getDeviceStates();
      if (select.value) {
        deviceStates[deviceId].detected = true;
        deviceStates[deviceId].port = select.value;
        updateSectionUI(deviceId);
      }
    });
  });

  // Detailed logs toggle
  container.querySelectorAll('[id^="detailed-logs-"]').forEach(checkbox => {
    checkbox.addEventListener('change', (e) => {
      e.stopPropagation();
      setShowDetailedLogs(checkbox.checked);
      // Re-render all log viewers to apply filter
      refreshAllLogViewers();
    });
  });
}

/**
 * Setup handlers for selected device section (single_choice mode)
 */
export function setupSelectedDeviceHandlers(container) {
  const deviceStates = getDeviceStates();

  // Deploy buttons in selected section
  container.querySelectorAll('.deploy-selected-card [id^="deploy-btn-"]').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const deviceId = btn.dataset.deviceId;
      startDeployment(deviceId);
    });
  });

  // Logs toggle in selected section
  container.querySelectorAll('.deploy-selected-card [id^="logs-toggle-"]').forEach(el => {
    el.addEventListener('click', (e) => {
      e.stopPropagation();
      const deviceId = el.dataset.deviceId;
      toggleLogs(deviceId);
    });
  });

  // Test SSH connection in selected section
  container.querySelectorAll('.deploy-selected-card [id^="test-ssh-"]').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const deviceId = btn.dataset.deviceId;
      await testSSHConnection(deviceId, btn);
    });
  });

  // Refresh ports in selected section
  container.querySelectorAll('.deploy-selected-card [id^="refresh-ports-"]').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      await refreshSerialPorts(btn);
    });
  });

  // Serial port selection in selected section
  container.querySelectorAll('.deploy-selected-card [id^="serial-port-"]').forEach(select => {
    select.addEventListener('change', () => {
      const deviceId = select.id.replace('serial-port-', '');
      if (select.value) {
        deviceStates[deviceId].detected = true;
        deviceStates[deviceId].port = select.value;
        updateSectionUI(deviceId);
      }
    });
  });

  // Detailed logs toggle in selected section
  container.querySelectorAll('.deploy-selected-card [id^="detailed-logs-"]').forEach(checkbox => {
    checkbox.addEventListener('change', (e) => {
      e.stopPropagation();
      setShowDetailedLogs(checkbox.checked);
      refreshAllLogViewers();
    });
  });
}

/**
 * Attach event handlers for deployment section elements
 */
export function attachSectionEventHandlers(container) {
  const currentSolution = getCurrentSolution();
  const deviceStates = getDeviceStates();

  // Section headers (expand/collapse)
  container.querySelectorAll('[id^="section-header-"]').forEach(el => {
    el.addEventListener('click', () => {
      const deviceId = el.dataset.deviceId;
      toggleSection(deviceId);
    });
  });

  // Deploy buttons
  container.querySelectorAll('[id^="deploy-btn-"]').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const deviceId = btn.dataset.deviceId;
      const device = getDeviceById(deviceId);

      if (device?.type === 'manual') {
        markDeviceComplete(deviceId, expandNextSection);
      } else if (device?.type === 'preview') {
        handlePreviewButtonClick(deviceId);
      } else {
        startDeployment(deviceId);
      }
    });
  });

  // Logs toggle
  container.querySelectorAll('[id^="logs-toggle-"]').forEach(el => {
    el.addEventListener('click', (e) => {
      e.stopPropagation();
      const deviceId = el.dataset.deviceId;
      toggleLogs(deviceId);
    });
  });

  // Refresh ports
  container.querySelectorAll('[id^="refresh-ports-"]').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      await refreshSerialPorts(btn);
    });
  });

  // Test SSH connection
  container.querySelectorAll('[id^="test-ssh-"]').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const deviceId = btn.dataset.deviceId;
      await testSSHConnection(deviceId, btn);
    });
  });

  // Serial port selection
  container.querySelectorAll('[id^="serial-port-"]').forEach(select => {
    select.addEventListener('change', () => {
      const deviceId = select.id.replace('serial-port-', '');
      if (select.value) {
        deviceStates[deviceId].detected = true;
        deviceStates[deviceId].port = select.value;
        updateSectionUI(deviceId);
      }
    });
  });

  // Detailed logs toggle
  container.querySelectorAll('[id^="detailed-logs-"]').forEach(checkbox => {
    checkbox.addEventListener('change', (e) => {
      e.stopPropagation();
      setShowDetailedLogs(checkbox.checked);
      refreshAllLogViewers();
    });
  });

  // Initialize device states for filtered devices
  const deployment = currentSolution.deployment || {};
  const devices = deployment.devices || [];
  const filteredDevices = getFilteredDevices(devices);
  filteredDevices.forEach((device, index) => {
    if (!deviceStates[device.id]) {
      deviceStates[device.id] = createInitialDeviceState(device, index);
    }
  });
}

// ============================================
// Preset Change Handler
// ============================================

/**
 * Handle preset selector change
 */
export async function handlePresetChange(presetId) {
  const currentSolution = getCurrentSolution();

  if (presetId === getSelectedPresetId()) return;
  setSelectedPresetId(presetId);

  // Update button states
  document.querySelectorAll('.deploy-preset-btn').forEach(btn => {
    btn.classList.toggle('selected', btn.dataset.presetId === presetId);
  });

  // Show loading state on section content
  const contentEl = document.getElementById('deploy-preset-section-content');
  if (contentEl) {
    contentEl.classList.add('loading');
  }

  // Re-render device group sections filtered by new preset
  const deployment = currentSolution.deployment || {};
  const presets = deployment.presets || [];
  const devices = deployment.devices || [];
  const filteredDeviceGroups = getFilteredDeviceGroups(presets);
  const deviceGroupContainer = document.getElementById('deploy-device-groups-container');
  if (deviceGroupContainer) {
    deviceGroupContainer.innerHTML = renderDeviceGroupSections(filteredDeviceGroups);
    // Re-attach event handlers for new device group selectors
    deviceGroupContainer.querySelectorAll('.device-group-selector').forEach(select => {
      select.addEventListener('change', async (e) => {
        const groupId = select.dataset.groupId;
        const selectedDevice = e.target.value;
        await handleDeviceGroupSelectorChange(groupId, selectedDevice);
      });
    });
  }

  // Re-render deployment steps filtered by new preset
  const sectionsContainer = document.getElementById('deploy-sections-container');
  if (sectionsContainer) {
    const filteredDevices = getFilteredDevices(devices);
    sectionsContainer.innerHTML = filteredDevices.map((device, index) => renderDeploySection(device, index + 1)).join('');
    // Re-attach event handlers for the new sections
    attachSectionEventHandlers(sectionsContainer);
  }

  try {
    // Fetch new section content
    const result = await solutionsApi.getPresetSection(
      currentSolution.id,
      presetId,
      i18n.locale
    );

    if (result.section) {
      const sectionEl = document.getElementById('deploy-preset-section');
      if (sectionEl) {
        const title = result.section.title || '';
        const description = result.section.description || '';
        sectionEl.innerHTML = `
          ${title ? `<h3 class="deploy-preset-section-title">${escapeHtml(title)}</h3>` : ''}
          <div class="deploy-preset-section-content markdown-content" id="deploy-preset-section-content">
            ${description}
          </div>
        `;
      }
    }
  } catch (error) {
    console.error('Failed to load preset section:', error);
    toast.error(t('common.error') + ': ' + error.message);
  } finally {
    const el = document.getElementById('deploy-preset-section-content');
    if (el) {
      el.classList.remove('loading');
    }
  }
}

// ============================================
// Device Group Selector Handler
// ============================================

/**
 * Handle device group selector change
 */
export async function handleDeviceGroupSelectorChange(groupId, selectedDevice) {
  const currentSolution = getCurrentSolution();
  const selectedPresetId = getSelectedPresetId();

  setDeviceGroupSelection(groupId, selectedDevice);

  // Show loading state
  const contentEl = document.getElementById(`device-group-content-${groupId}`);
  if (contentEl) {
    contentEl.classList.add('loading');
  }

  try {
    // Fetch updated section content from API
    const result = await solutionsApi.getDeviceGroupSection(
      currentSolution.id,
      groupId,
      selectedDevice,
      i18n.locale,
      selectedPresetId
    );

    if (result.section && contentEl) {
      contentEl.innerHTML = result.section.description || '';
    }
  } catch (error) {
    console.error('Failed to load device group section:', error);
    toast.error(t('common.error') + ': ' + error.message);
  } finally {
    if (contentEl) {
      contentEl.classList.remove('loading');
    }
  }
}

// ============================================
// UI Update Functions (wrappers for ui-updates.js)
// ============================================

/**
 * Update docker target UI when user switches between local/remote
 * Wrapper that passes the testSSHConnection handler
 */
export function updateDockerTargetUI(deviceId, container) {
  baseUpdateDockerTargetUI(deviceId, container, testSSHConnection);
}

/**
 * Update selected device section (single_choice mode)
 */
export function updateSelectedDevice(container) {
  const currentSolution = getCurrentSolution();
  const selectedDevice = getSelectedDevice();
  const deployment = currentSolution.deployment || {};
  const devices = deployment.devices || [];

  // Update radio options
  container.querySelectorAll('.deploy-choice-option').forEach(el => {
    const deviceId = el.dataset.deviceId;
    el.classList.toggle('selected', deviceId === selectedDevice);
    const radio = el.querySelector('input[type="radio"]');
    if (radio) radio.checked = (deviceId === selectedDevice);
  });

  // Update selected device section
  const selectedSection = container.querySelector('#selected-device-section');
  if (selectedSection) {
    const device = devices.find(d => d.id === selectedDevice);
    selectedSection.innerHTML = device ? renderSelectedDeviceContent(device) : '';

    // Re-attach event handlers for the new content
    setupSelectedDeviceHandlers(container);
  }
}
