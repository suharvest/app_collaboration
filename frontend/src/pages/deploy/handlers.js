/**
 * Deploy Page - Event Handlers
 * All event handling and UI update functions
 */

import { t, getLocalizedField, i18n } from '../../modules/i18n.js';
import { solutionsApi, devicesApi } from '../../modules/api.js';
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

  // Initialize preview windows for filtered devices (including preset devices)
  const deployment = currentSolution.deployment || {};
  const globalDevices = deployment.devices || [];
  const filteredDevices = getFilteredDevices(globalDevices);
  filteredDevices.forEach(device => {
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

  // mDNS scan buttons
  container.querySelectorAll('[id^="scan-mdns-"]').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const deviceId = btn.dataset.deviceId;
      await scanMdnsDevices(deviceId, btn);
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

  // Docker deploy target options (local/remote) in selected section
  container.querySelectorAll('.deploy-selected-card .deploy-mode-option[data-target-id]').forEach(el => {
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

  // mDNS scan in selected section
  container.querySelectorAll('.deploy-selected-card [id^="scan-mdns-"]').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const deviceId = btn.dataset.deviceId;
      await scanMdnsDevices(deviceId, btn);
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

  // mDNS scan
  container.querySelectorAll('[id^="scan-mdns-"]').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const deviceId = btn.dataset.deviceId;
      await scanMdnsDevices(deviceId, btn);
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

  // Initialize preview windows for filtered devices
  filteredDevices.forEach(device => {
    if (device.type === 'preview') {
      initPreviewWindow(device.id);
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
 * Wrapper that passes the testSSHConnection and scanMdnsDevices handlers
 */
export function updateDockerTargetUI(deviceId, container) {
  baseUpdateDockerTargetUI(deviceId, container, testSSHConnection, scanMdnsDevices);
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

// ============================================
// mDNS Device Discovery
// ============================================

/**
 * Scan for devices on the local network using mDNS
 * @param {string} deviceId - The device ID for the SSH form
 * @param {HTMLElement} btn - The scan button element
 */
async function scanMdnsDevices(deviceId, btn) {
  const originalContent = btn.innerHTML;
  const dropdown = document.getElementById(`mdns-dropdown-${deviceId}`);
  const hostInput = document.getElementById(`ssh-host-${deviceId}`);

  // Show loading state
  btn.disabled = true;
  btn.innerHTML = `<span class="spinner spinner-sm"></span> ${t('deploy.connection.scanning')}`;

  try {
    const result = await devicesApi.scanMdns({ timeout: 3, filterKnown: true });
    const devices = result.devices || [];
    const suggestedHosts = result.suggested_hosts || [];

    if (!dropdown) return;

    if (devices.length === 0) {
      // No devices found - show suggested hosts if available
      if (suggestedHosts.length > 0) {
        dropdown.innerHTML = `
          <div class="mdns-empty" style="border-bottom: 1px solid var(--border-color); padding-bottom: 8px; margin-bottom: 8px;">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="8" x2="12" y2="12"/>
              <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            <span>${t('deploy.connection.noDevicesFound')}</span>
          </div>
          <div class="mdns-header">${t('deploy.connection.suggestedHosts')}</div>
          <div class="mdns-hint" style="font-size: 12px; color: var(--text-secondary); padding: 4px 12px 8px;">${t('deploy.connection.suggestedHostsHint')}</div>
          ${suggestedHosts.map(host => `
            <div class="mdns-device mdns-suggested" data-hostname="${host.hostname}">
              <span class="mdns-device-icon">${getMdnsDeviceIcon(host.device_id)}</span>
              <span class="mdns-device-name">${host.hostname}</span>
              <span class="mdns-device-ip" style="color: var(--text-tertiary);">${i18n.locale === 'zh' ? host.device_name_zh : host.device_name}</span>
            </div>
          `).join('')}
        `;
        dropdown.style.display = 'block';

        // Setup click handlers for suggested hosts
        dropdown.querySelectorAll('.mdns-suggested').forEach(el => {
          el.addEventListener('click', () => {
            const hostname = el.dataset.hostname;
            if (hostInput) {
              hostInput.value = hostname;
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
      } else {
        // No devices and no suggestions
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
      }
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
            // Trigger input event for any listeners
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

/**
 * Get icon for mDNS device type
 * Supports both short types (raspberry, jetson) and full device IDs (recomputer_r1100)
 */
function getMdnsDeviceIcon(deviceType) {
  if (!deviceType) {
    return '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="2" width="20" height="8" rx="2"/><rect x="2" y="14" width="20" height="8" rx="2"/><circle cx="6" cy="6" r="1"/><circle cx="6" cy="18" r="1"/></svg>';
  }

  const type = deviceType.toLowerCase();

  // Raspberry Pi
  if (type === 'raspberry' || type.startsWith('raspberry_')) {
    return '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="4" width="16" height="16" rx="2"/><circle cx="9" cy="9" r="1"/><circle cx="15" cy="9" r="1"/><circle cx="9" cy="15" r="1"/><circle cx="15" cy="15" r="1"/></svg>';
  }

  // Jetson / reComputer J-series
  if (type === 'jetson' || type.startsWith('recomputer_j')) {
    return '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><path d="M15 2v2M15 20v2M9 2v2M9 20v2M2 15h2M20 15h2M2 9h2M20 9h2"/></svg>';
  }

  // reComputer / reTerminal / reCamera
  if (type === 'recomputer' || type === 'recamera' || type.startsWith('recomputer_') || type.startsWith('reterminal') || type.startsWith('recamera')) {
    return '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/></svg>';
  }

  // Default server icon
  return '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="2" width="20" height="8" rx="2"/><rect x="2" y="14" width="20" height="8" rx="2"/><circle cx="6" cy="6" r="1"/><circle cx="6" cy="18" r="1"/></svg>';
}
