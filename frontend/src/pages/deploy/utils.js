/**
 * Deploy Page - Utility Functions
 * Helper functions for the deployment page
 */

import { t, getLocalizedField } from '../../modules/i18n.js';
import {
  getCurrentSolution,
  getDeviceStates,
  getSelectedPresetId,
  getDeviceGroupSelections,
} from './state.js';

// ============================================
// Script Loading
// ============================================

/**
 * Load external script dynamically
 * @param {string} url - Script URL
 * @returns {Promise} Resolves when script is loaded
 */
export function loadScript(url) {
  return new Promise((resolve, reject) => {
    // Check if already loaded
    if (document.querySelector(`script[src="${url}"]`)) {
      resolve();
      return;
    }
    const script = document.createElement('script');
    script.src = url;
    script.onload = resolve;
    script.onerror = () => reject(new Error(`Failed to load script: ${url}`));
    document.head.appendChild(script);
  });
}

// ============================================
// Device & Preset Filtering
// ============================================

/**
 * Get device groups from selected preset
 */
export function getFilteredDeviceGroups(presets) {
  const selectedPresetId = getSelectedPresetId();
  if (!selectedPresetId || presets.length === 0) return [];
  const preset = presets.find(p => p.id === selectedPresetId);
  return preset?.device_groups || [];
}

/**
 * Get deployment devices for selected preset.
 * Uses preset.devices if available, otherwise falls back to global devices with show_when filtering.
 */
export function getFilteredDevices(devices) {
  const currentSolution = getCurrentSolution();
  const selectedPresetId = getSelectedPresetId();

  // Get selected preset from deployment data
  const presets = currentSolution?.deployment?.presets || [];
  const selectedPreset = presets.find(p => p.id === selectedPresetId);

  // If preset has its own devices list, use it directly
  if (selectedPreset?.devices && selectedPreset.devices.length > 0) {
    return selectedPreset.devices;
  }

  // Fallback: use global devices with show_when filtering (for backward compatibility)
  if (!selectedPresetId) return devices;
  return devices.filter(device => {
    // No show_when means always show
    if (!device.show_when) return true;
    // Check preset condition
    if (device.show_when.preset) {
      const presetCondition = device.show_when.preset;
      // Can be string or array
      if (Array.isArray(presetCondition)) {
        return presetCondition.includes(selectedPresetId);
      }
      return presetCondition === selectedPresetId;
    }
    return true;
  });
}

/**
 * Get the currently selected target for a docker_deploy device
 */
export function getSelectedTarget(device) {
  const deviceStates = getDeviceStates();
  const state = deviceStates[device.id] || {};
  const targets = device.targets || {};
  const selectedId = state.selectedTarget || 'local';
  return { id: selectedId, ...targets[selectedId] };
}

/**
 * Get selected model IDs for a device
 */
export function getSelectedModels(deviceId) {
  const checkboxes = document.querySelectorAll(
    `input[data-device="${deviceId}"]:checked`
  );
  return Array.from(checkboxes).map(cb => cb.value);
}

// ============================================
// Template Resolution
// ============================================

/**
 * Collect user inputs from all previous steps
 */
export function collectPreviousInputs(devices, currentIndex) {
  const deviceStates = getDeviceStates();
  const inputs = {};
  for (let i = 0; i < currentIndex; i++) {
    const device = devices[i];
    const state = deviceStates[device.id];
    if (state?.userInputs) {
      Object.assign(inputs, state.userInputs);
    }
  }
  return inputs;
}

/**
 * Resolve template variables in a string
 * Template format: {{variable_name}}
 */
export function resolveTemplate(template, inputs) {
  if (!template) return template;
  return template.replace(/\{\{(\w+)\}\}/g, (match, key) => {
    return inputs[key] !== undefined ? inputs[key] : match;
  });
}

// ============================================
// Device Lookup
// ============================================

/**
 * Find a device by ID from the current solution
 */
export function getDeviceById(deviceId) {
  const currentSolution = getCurrentSolution();
  const deployment = currentSolution?.deployment || {};
  const devices = deployment.devices || [];
  return devices.find(d => d.id === deviceId);
}

// ============================================
// Status & Style Functions
// ============================================

export function getStatusClass(state) {
  if (state.deploymentStatus === 'completed') return 'completed';
  if (state.deploymentStatus === 'failed') return 'failed';
  if (state.deploymentStatus === 'running') return 'running';
  if (state.detected) return 'ready';
  return 'pending';
}

export function getStatusIcon(state) {
  if (state.deploymentStatus === 'completed') {
    return '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>';
  }
  if (state.deploymentStatus === 'failed') {
    return '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>';
  }
  if (state.deploymentStatus === 'running') {
    return '<span class="spinner" style="width:14px;height:14px;border-width:2px;"></span>';
  }
  return '';
}

export function getStatusText(state) {
  if (state.deploymentStatus === 'completed') return t('deploy.status.completed');
  if (state.deploymentStatus === 'failed') return t('deploy.status.failed');
  if (state.deploymentStatus === 'running') return t('deploy.status.running');
  if (state.detected) return t('deploy.status.ready');
  return t('deploy.status.pending');
}

export function getButtonClass(state) {
  if (state.deploymentStatus === 'completed') return 'completed';
  if (state.deploymentStatus === 'running') return 'running';
  return '';
}

export function getDeployButtonContent(state, isManual) {
  if (state.deploymentStatus === 'running') {
    return `<span class="spinner" style="width:18px;height:18px;border-width:2px;"></span> ${t('deploy.status.running')}`;
  }
  if (state.deploymentStatus === 'completed') {
    return `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg> ${t('deploy.status.completed')}`;
  }
  if (state.deploymentStatus === 'failed') {
    return t('deploy.actions.retry');
  }
  if (isManual) {
    return t('deploy.actions.markDone');
  }
  return t('deploy.actions.deploy');
}

// ============================================
// Log Filtering
// ============================================

import { getShowDetailedLogs } from './state.js';

export function getFilteredLogs(logs) {
  if (getShowDetailedLogs()) {
    return logs;
  }
  // Only show key status logs: success, error, warning, and important info
  return logs.filter(log => {
    // Always show errors, warnings, and success
    if (log.level === 'error' || log.level === 'warning' || log.level === 'success') {
      return true;
    }
    // For info logs, only show key status messages
    if (log.level === 'info') {
      const msg = log.message.toLowerCase();
      // Show deployment start/complete, pre-check results, and key milestones
      if (msg.includes('started deployment') ||
          msg.includes('deployment completed') ||
          msg.includes('pre-check') ||
          msg.includes('检测') ||
          msg.includes('completed') ||
          msg.includes('failed') ||
          msg.includes('passed') ||
          msg.includes('flashing') ||
          msg.includes('烧录') ||
          msg.includes('uploading') ||
          msg.includes('pulling') ||
          msg.includes('starting service')) {
        return true;
      }
      return false;
    }
    return false;
  });
}

export function isKeyLogMessage(log) {
  // Helper to determine if a log should be shown in summary mode
  return log.level !== 'info' || getFilteredLogs([log]).length > 0;
}
