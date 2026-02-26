/**
 * Deploy Page - WebSocket & Logs Management
 * Handles WebSocket connections and log display
 */

import { t } from '../../modules/i18n.js';
import { LogsWebSocket } from '../../modules/api.js';
import { escapeHtml } from '../../modules/utils.js';
import { toast } from '../../modules/toast.js';
import {
  getDeviceStates,
  getDeviceState,
  getLogsWs,
  setLogsWs,
  getShowDetailedLogs,
} from './state.js';
import { getDeviceById, getFilteredLogs, isKeyLogMessage } from './utils.js';
import { renderLogEntry } from './renderers.js';
import { updateSectionUI, updateChoiceOptionUI, expandNextSection } from './ui-updates.js';
import { handleDockerNotInstalled } from './docker.js';

// ============================================
// WebSocket Connection
// ============================================

/**
 * Connect to deployment logs WebSocket
 */
export function connectLogsWebSocket(deploymentId, deviceId) {
  const existingWs = getLogsWs(deviceId);
  if (existingWs) {
    existingWs.disconnect();
  }

  const ws = new LogsWebSocket(deploymentId);

  ws.on('log', (data) => {
    addLogToDevice(deviceId, data.level || 'info', data.message);
  });

  ws.on('docker_not_installed', (data) => {
    // Docker not installed on remote device - ask user for confirmation
    handleDockerNotInstalled(deviceId, data);
  });

  ws.on('status', (data) => {
    const state = getDeviceState(deviceId);
    if (state) {
      state.deploymentStatus = data.status;
      state.progress = data.progress || 0;
      updateSectionUI(deviceId);
      updateChoiceOptionUI(deviceId); // Update single_choice option if applicable

      if (data.status === 'completed') {
        addLogToDevice(deviceId, 'success', t('deploy.status.completed'));
        toast.success(`${getDeviceById(deviceId)?.name}: ${t('deploy.status.completed')}`);

        // Auto-expand next section (only for sequential mode)
        expandNextSection(deviceId);
      } else if (data.status === 'failed') {
        // Suppress generic failure toast when docker install dialog is showing
        if (!state.dockerInstallPending) {
          addLogToDevice(deviceId, 'error', t('deploy.status.failed'));
          toast.error(`${getDeviceById(deviceId)?.name}: ${t('deploy.status.failed')}`);
        }
      }
    }
  });

  ws.on('error', () => {
    addLogToDevice(deviceId, 'error', 'Connection error');
  });

  ws.on('close', (event) => {
    const state = getDeviceState(deviceId);
    // If deployment was still running when WebSocket closed, mark as failed
    if (state && state.deploymentStatus === 'running') {
      state.deploymentStatus = 'failed';
      updateSectionUI(deviceId);
      updateChoiceOptionUI(deviceId);
      addLogToDevice(deviceId, 'error', t('deploy.status.failed') + (event.reason ? `: ${event.reason}` : ''));
      toast.error(`${getDeviceById(deviceId)?.name}: ${t('deploy.status.failed')}`);
    }
  });

  ws.connect();
  setLogsWs(deviceId, ws);
}

// ============================================
// Log Management
// ============================================

/**
 * Add a log entry to a device's log list
 */
export function addLogToDevice(deviceId, level, message) {
  const state = getDeviceState(deviceId);
  if (!state) return;

  const timestamp = new Date().toLocaleTimeString();
  const logEntry = { timestamp, level, message };
  state.logs.push(logEntry);

  const viewer = document.getElementById(`logs-viewer-${deviceId}`);
  if (viewer) {
    // Only add to DOM if it passes the filter
    const shouldShow = getShowDetailedLogs() || isKeyLogMessage(logEntry);

    if (shouldShow) {
      const empty = viewer.querySelector('.deploy-logs-empty');
      if (empty) empty.remove();

      const entry = document.createElement('div');
      entry.className = `deploy-log-entry ${level}`;
      entry.innerHTML = `<span class="time">${timestamp}</span><span class="msg">${escapeHtml(message)}</span>`;
      viewer.appendChild(entry);
      viewer.scrollTop = viewer.scrollHeight;
    }
  }

  // Update count (filtered count)
  const logsCount = document.getElementById(`logs-count-${deviceId}`);
  if (logsCount) {
    logsCount.textContent = getFilteredLogs(state.logs).length;
  }

  // Auto-expand logs when running
  if (!state.logsExpanded && state.deploymentStatus === 'running') {
    toggleLogs(deviceId, true);
  }
}

/**
 * Toggle logs panel visibility
 */
export function toggleLogs(deviceId, forceExpand = null) {
  const state = getDeviceState(deviceId);
  if (!state) return;

  state.logsExpanded = forceExpand !== null ? forceExpand : !state.logsExpanded;

  const panel = document.getElementById(`logs-panel-${deviceId}`);
  const chevron = document.getElementById(`logs-chevron-${deviceId}`);

  if (panel) panel.classList.toggle('expanded', state.logsExpanded);
  if (chevron) chevron.classList.toggle('expanded', state.logsExpanded);
}

/**
 * Refresh all log viewers to apply filter change
 */
export function refreshAllLogViewers() {
  const deviceStates = getDeviceStates();

  Object.entries(deviceStates).forEach(([deviceId, state]) => {
    const viewer = document.getElementById(`logs-viewer-${deviceId}`);
    const logsCount = document.getElementById(`logs-count-${deviceId}`);

    if (viewer) {
      const filteredLogs = getFilteredLogs(state.logs);
      if (filteredLogs.length === 0) {
        viewer.innerHTML = `<div class="deploy-logs-empty">${t('deploy.logs.empty')}</div>`;
      } else {
        viewer.innerHTML = filteredLogs.map(log => renderLogEntry(log)).join('');
        viewer.scrollTop = viewer.scrollHeight;
      }
    }

    if (logsCount) {
      logsCount.textContent = getFilteredLogs(state.logs).length;
    }

    // Sync checkbox state
    const checkbox = document.getElementById(`detailed-logs-${deviceId}`);
    if (checkbox) {
      checkbox.checked = getShowDetailedLogs();
    }
  });
}
