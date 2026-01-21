/**
 * Deploy Page - Wiki-style Device Deployment
 */

import { solutionsApi, devicesApi, deploymentsApi, LogsWebSocket, getAssetUrl } from '../modules/api.js';
import { t, getLocalizedField, i18n } from '../modules/i18n.js';
import { router } from '../modules/router.js';
import { toast } from '../modules/toast.js';
import { escapeHtml } from '../modules/utils.js';
import { PreviewWindow, fetchOverlayScript } from '../modules/preview.js';
import { renderers } from '../modules/overlay-renderers.js';

let currentSolution = null;
let deviceStates = {};
let logsWsMap = {};
let selectedDevice = null; // For single_choice mode
let showDetailedLogs = false; // Toggle for detailed vs summary logs
let previewInstances = {}; // Track preview window instances

export async function renderDeployPage(params) {
  const { id } = params;
  const container = document.getElementById('content-area');

  // Show loading
  container.innerHTML = `
    <div class="back-btn" id="back-btn">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M19 12H5M12 19l-7-7 7-7"/>
      </svg>
      <span>${t('deploy.back')}</span>
    </div>
    <div class="flex items-center justify-center py-16">
      <div class="spinner spinner-lg"></div>
    </div>
  `;

  try {
    const [solutionInfo, deploymentInfo] = await Promise.all([
      solutionsApi.get(id, i18n.locale),
      solutionsApi.getDeployment(id, i18n.locale)
    ]);

    currentSolution = {
      ...solutionInfo,
      deployment: deploymentInfo
    };

    deviceStates = {};
    selectedDevice = null; // Reset for new solution
    const devices = deploymentInfo.devices || [];

    // Initialize device states - first section expanded by default
    devices.forEach((device, index) => {
      deviceStates[device.id] = {
        status: 'pending',
        detected: false,
        connection: null,
        deploymentStatus: null,
        progress: 0,
        logs: [],
        logsExpanded: false,
        sectionExpanded: index === 0, // First section expanded
      };
    });

    renderDeployContent(container);
    setupEventHandlers(container);

    // Auto-detect devices
    await detectDevices();
  } catch (error) {
    console.error('Failed to load solution:', error);
    toast.error(t('common.error') + ': ' + error.message);
  }
}

function renderDeployContent(container) {
  const deployment = currentSolution.deployment || {};
  const devices = deployment.devices || [];
  const name = getLocalizedField(currentSolution, 'name');
  const selectionMode = deployment.selection_mode || 'sequential';

  // For single_choice mode, select first device by default
  if (selectionMode === 'single_choice' && !selectedDevice && devices.length > 0) {
    selectedDevice = devices[0].id;
  }

  container.innerHTML = `
    <div class="back-btn" id="back-btn">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M19 12H5M12 19l-7-7 7-7"/>
      </svg>
      <span>${t('deploy.back')}</span>
    </div>

    <div class="deploy-page">
      <div class="page-header">
        <h1 class="page-title">${t('deploy.title')}: ${escapeHtml(name)}</h1>
        ${deployment.guide ? `
          <p class="text-sm text-text-secondary mt-2">${escapeHtml(currentSolution.summary || '')}</p>
        ` : ''}
      </div>

      ${selectionMode === 'single_choice' ? `
        <!-- Single Choice Mode: Radio options -->
        <div class="deploy-choice-section">
          <div class="deploy-choice-header">
            <h3 class="deploy-choice-title">${t('deploy.selectMode')}</h3>
            <p class="deploy-choice-desc">${t('deploy.selectModeDesc')}</p>
          </div>
          <div class="deploy-choice-options">
            ${devices.map(device => renderDeployOption(device)).join('')}
          </div>
        </div>

        <!-- Selected device details -->
        <div class="deploy-selected-section" id="selected-device-section">
          ${selectedDevice ? renderSelectedDeviceContent(devices.find(d => d.id === selectedDevice)) : ''}
        </div>
      ` : `
        <!-- Sequential Mode: Steps -->
        <div class="deploy-sections">
          ${devices.map((device, index) => renderDeploySection(device, index + 1)).join('')}
        </div>
      `}

      ${currentSolution.wiki_url ? `
        <div class="mt-6 text-center">
          <a href="${currentSolution.wiki_url}" target="_blank" class="btn btn-secondary">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/>
              <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
            </svg>
            ${t('deploy.viewWiki')}
          </a>
        </div>
      ` : ''}
    </div>
  `;
}

function renderDeployOption(device) {
  const state = deviceStates[device.id] || {};
  const name = getLocalizedField(device, 'name');
  const section = device.section || {};
  const sectionTitle = getLocalizedField(section, 'title') || name;
  const isSelected = selectedDevice === device.id;
  const isCompleted = state.deploymentStatus === 'completed';

  // Get icon based on device type
  const icon = getDeviceTypeIcon(device.type);

  return `
    <label class="deploy-choice-option ${isSelected ? 'selected' : ''} ${isCompleted ? 'completed' : ''}"
           data-device-id="${device.id}">
      <input type="radio" name="deploy-choice" value="${device.id}"
             ${isSelected ? 'checked' : ''} ${isCompleted ? 'disabled' : ''}>
      <div class="deploy-choice-radio">
        ${isCompleted ? `
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="20 6 9 17 4 12"/>
          </svg>
        ` : ''}
      </div>
      <div class="deploy-choice-content">
        <div class="deploy-choice-icon">${icon}</div>
        <div class="deploy-choice-info">
          <div class="deploy-choice-name">${escapeHtml(sectionTitle)}</div>
          <div class="deploy-choice-type">${escapeHtml(name)}</div>
        </div>
      </div>
      ${isCompleted ? `
        <div class="deploy-choice-status completed">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="20 6 9 17 4 12"/>
          </svg>
          <span>${t('deploy.status.completed')}</span>
        </div>
      ` : ''}
    </label>
  `;
}

/**
 * Check if a device type requires showing service switch warning
 */
function shouldShowServiceSwitchWarning(deviceType) {
  return deviceType === 'recamera_nodered' ||
         deviceType === 'recamera_cpp';
}

/**
 * Render service switch warning banner
 */
function renderServiceSwitchWarning(deviceType) {
  if (!shouldShowServiceSwitchWarning(deviceType)) {
    return '';
  }

  const isReCamera = deviceType.startsWith('recamera_');
  const warningText = isReCamera
    ? t('deploy.warnings.recameraSwitch')
    : t('deploy.warnings.serviceSwitch');

  return `
    <div class="deploy-warning-banner">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
        <line x1="12" y1="9" x2="12" y2="13"/>
        <line x1="12" y1="17" x2="12.01" y2="17"/>
      </svg>
      <span>${warningText}</span>
    </div>
  `;
}

function getDeviceTypeIcon(type) {
  switch (type) {
    case 'docker_local':
      return `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="2" y="7" width="20" height="14" rx="2"/>
        <path d="M12 7V3M7 7V5M17 7V5"/>
      </svg>`;
    case 'docker_remote':
      return `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="2" y="2" width="20" height="8" rx="2"/>
        <rect x="2" y="14" width="20" height="8" rx="2"/>
        <line x1="6" y1="6" x2="6.01" y2="6"/>
        <line x1="6" y1="18" x2="6.01" y2="18"/>
      </svg>`;
    case 'esp32_usb':
      return `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="4" y="4" width="16" height="16" rx="2"/>
        <circle cx="9" cy="9" r="1"/><circle cx="15" cy="9" r="1"/>
        <circle cx="9" cy="15" r="1"/><circle cx="15" cy="15" r="1"/>
      </svg>`;
    case 'preview':
      return `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="2" y="3" width="20" height="14" rx="2"/>
        <polygon points="10 8 16 11 10 14 10 8"/>
        <line x1="8" y1="21" x2="16" y2="21"/>
        <line x1="12" y1="17" x2="12" y2="21"/>
      </svg>`;
    default:
      return `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M12 2L2 7l10 5 10-5-10-5z"/>
        <path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/>
      </svg>`;
  }
}

function renderSelectedDeviceContent(device) {
  if (!device) return '';

  const state = deviceStates[device.id] || {};
  const section = device.section || {};
  const sectionDescription = section.description || '';
  const isCompleted = state.deploymentStatus === 'completed';

  return `
    <div class="deploy-selected-card" data-device-id="${device.id}">
      <!-- Service Switch Warning -->
      ${renderServiceSwitchWarning(device.type)}

      <!-- Pre-deployment Instructions -->
      ${sectionDescription ? `
        <div class="deploy-pre-instructions">
          <div class="markdown-content">${sectionDescription}</div>
        </div>
      ` : ''}

      <!-- Connection Settings -->
      ${device.type === 'ssh_deb' || device.type === 'docker_remote' || device.type === 'recamera_cpp' || device.type === 'recamera_nodered' ? renderSSHForm(device) : ''}

      <!-- Serial Port Selector (for ESP32 devices) -->
      ${device.type === 'esp32_usb' ? renderSerialPortSelector(device) : ''}

      <!-- Deploy Action Area -->
      <div class="deploy-action-area">
        <button class="deploy-action-btn ${getButtonClass(state)}"
                id="deploy-btn-${device.id}"
                data-device-id="${device.id}"
                ${state.deploymentStatus === 'running' ? 'disabled' : ''}>
          ${getDeployButtonContent(state, false)}
        </button>
      </div>

      <!-- Logs Section -->
      <div class="deploy-logs" id="logs-${device.id}">
        <div class="deploy-logs-toggle" id="logs-toggle-${device.id}" data-device-id="${device.id}">
          <span class="deploy-logs-label">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
            </svg>
            ${t('deploy.logs.title')}
            <span class="deploy-logs-count" id="logs-count-${device.id}">${getFilteredLogs(state.logs).length}</span>
          </span>
          <svg class="deploy-section-chevron ${state.logsExpanded ? 'expanded' : ''}"
               id="logs-chevron-${device.id}"
               width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="6 9 12 15 18 9"/>
          </svg>
        </div>
        <div class="deploy-logs-panel ${state.logsExpanded ? 'expanded' : ''}" id="logs-panel-${device.id}">
          <div class="deploy-logs-options">
            <label class="deploy-logs-detail-toggle">
              <input type="checkbox" id="detailed-logs-${device.id}" ${showDetailedLogs ? 'checked' : ''}>
              <span>${t('deploy.logs.detailed')}</span>
            </label>
          </div>
          <div class="deploy-logs-viewer" id="logs-viewer-${device.id}">
            ${getFilteredLogs(state.logs).length === 0 ? `
              <div class="deploy-logs-empty">${t('deploy.logs.empty')}</div>
            ` : getFilteredLogs(state.logs).map(log => renderLogEntry(log)).join('')}
          </div>
        </div>
      </div>
    </div>
  `;
}

function renderDeploySection(device, stepNumber) {
  const state = deviceStates[device.id] || {};
  const name = getLocalizedField(device, 'name');
  const section = device.section || {};
  const sectionTitle = section.title || name;
  const sectionDescription = section.description || '';
  const isManual = device.type === 'manual';
  const isScript = device.type === 'script';
  const isPreview = device.type === 'preview';
  const isCompleted = state.deploymentStatus === 'completed';

  return `
    <div class="deploy-section ${isCompleted ? 'completed' : ''}" id="section-${device.id}" data-device-id="${device.id}">
      <!-- Section Header (clickable to expand/collapse) -->
      <div class="deploy-section-header" id="section-header-${device.id}" data-device-id="${device.id}">
        <div class="deploy-section-step ${isCompleted ? 'completed' : ''}" id="step-${device.id}">
          ${isCompleted ? `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
          ` : stepNumber}
        </div>
        <div class="deploy-section-info">
          <div class="deploy-section-title">${escapeHtml(sectionTitle)}</div>
          <div class="deploy-section-subtitle">${escapeHtml(name)}</div>
        </div>
        <div class="deploy-section-status ${getStatusClass(state)}" id="status-${device.id}">
          ${getStatusIcon(state)}
          <span>${getStatusText(state)}</span>
        </div>
        <svg class="deploy-section-chevron ${state.sectionExpanded ? 'expanded' : ''}"
             id="chevron-${device.id}"
             width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="6 9 12 15 18 9"/>
        </svg>
      </div>

      <!-- Section Content (collapsible) -->
      <div class="deploy-section-content ${state.sectionExpanded ? 'expanded' : ''}" id="content-${device.id}">
        ${isManual ? `
          <!-- Manual: Instructions first, then mark done button -->
          <!-- Markdown Content from section.description -->
          ${sectionDescription ? `
            <div class="markdown-content">
              ${sectionDescription}
            </div>
          ` : ''}

          <!-- Deploy Action Area -->
          <div class="deploy-action-area">
            <div class="deploy-action-title">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="9 11 12 14 22 4"/>
                <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>
              </svg>
              ${t('deploy.actions.manual')}
            </div>
            <p class="deploy-action-desc">${t('deploy.actions.manualDesc')}</p>
            <button class="deploy-action-btn ${getButtonClass(state)}"
                    id="deploy-btn-${device.id}"
                    data-device-id="${device.id}">
              ${getDeployButtonContent(state, true)}
            </button>
          </div>
        ` : isPreview ? `
          <!-- Preview: Live video + MQTT inference display -->
          <!-- Markdown Content from section.description (pre-instructions) -->
          ${sectionDescription ? `
            <div class="deploy-pre-instructions">
              <div class="markdown-content">
                ${sectionDescription}
              </div>
            </div>
          ` : ''}

          <!-- Preview User Inputs (auto-filled from previous steps) -->
          ${renderPreviewInputs(device)}

          <!-- Preview Window Container -->
          <div class="preview-container-wrapper" id="preview-container-${device.id}"></div>

          <!-- Deploy Action Area -->
          <div class="deploy-action-area">
            <div class="deploy-action-title">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="2" y="3" width="20" height="14" rx="2"/>
                <polygon points="10 8 16 11 10 14 10 8"/>
              </svg>
              ${t('preview.title')}
            </div>
            <p class="deploy-action-desc">${t('preview.description')}</p>
            <button class="deploy-action-btn ${getButtonClass(state)}"
                    id="deploy-btn-${device.id}"
                    data-device-id="${device.id}">
              ${getPreviewButtonContent(state)}
            </button>
          </div>
        ` : `
          <!-- Auto: Deploy button first, then instructions -->
          <!-- Service Switch Warning -->
          ${renderServiceSwitchWarning(device.type)}

          <!-- User Inputs (for script type) -->
          ${isScript && state.details?.user_inputs ? renderUserInputs(device, state.details.user_inputs) : ''}

          <!-- Connection Settings (for SSH-based devices) -->
          ${device.type === 'ssh_deb' || device.type === 'docker_remote' || device.type === 'recamera_cpp' || device.type === 'recamera_nodered' ? renderSSHForm(device) : ''}

          <!-- Additional User Inputs (for docker_remote devices, excluding SSH fields) -->
          ${device.type === 'docker_remote' && state.details?.user_inputs ? renderUserInputs(device, state.details.user_inputs, ['host', 'username', 'password', 'port']) : ''}

          <!-- Markdown Content from section.description (pre-deployment instructions) -->
          ${sectionDescription ? `
            <div class="deploy-pre-instructions">
              <div class="markdown-content">
                ${sectionDescription}
              </div>
            </div>
          ` : ''}

          <!-- Serial Port Selector (for ESP32 devices) -->
          ${device.type === 'esp32_usb' ? renderSerialPortSelector(device) : ''}

          <!-- Deploy Action Area -->
          <div class="deploy-action-area">
            <div class="deploy-action-title">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                <path d="M2 17l10 5 10-5"/>
                <path d="M2 12l10 5 10-5"/>
              </svg>
              ${t('deploy.actions.auto')}
            </div>
            <p class="deploy-action-desc">${t('deploy.actions.autoDesc')}</p>
            <button class="deploy-action-btn ${getButtonClass(state)}"
                    id="deploy-btn-${device.id}"
                    data-device-id="${device.id}"
                    ${state.deploymentStatus === 'running' ? 'disabled' : ''}>
              ${getDeployButtonContent(state, false)}
            </button>
          </div>
        `}

        <!-- Logs Section (collapsible) -->
        <div class="deploy-logs" id="logs-${device.id}">
          <div class="deploy-logs-toggle" id="logs-toggle-${device.id}" data-device-id="${device.id}">
            <span class="deploy-logs-label">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
                <line x1="16" y1="13" x2="8" y2="13"/>
                <line x1="16" y1="17" x2="8" y2="17"/>
              </svg>
              ${t('deploy.logs.title')}
              <span class="deploy-logs-count" id="logs-count-${device.id}">${getFilteredLogs(state.logs).length}</span>
            </span>
            <svg class="deploy-section-chevron ${state.logsExpanded ? 'expanded' : ''}"
                 id="logs-chevron-${device.id}"
                 width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="6 9 12 15 18 9"/>
            </svg>
          </div>
          <div class="deploy-logs-panel ${state.logsExpanded ? 'expanded' : ''}" id="logs-panel-${device.id}">
            <div class="deploy-logs-options">
              <label class="deploy-logs-detail-toggle">
                <input type="checkbox" id="detailed-logs-${device.id}" ${showDetailedLogs ? 'checked' : ''}>
                <span>${t('deploy.logs.detailed')}</span>
              </label>
            </div>
            <div class="deploy-logs-viewer" id="logs-viewer-${device.id}">
              ${getFilteredLogs(state.logs).length === 0 ? `
                <div class="deploy-logs-empty">${t('deploy.logs.empty')}</div>
              ` : getFilteredLogs(state.logs).map(log => renderLogEntry(log)).join('')}
            </div>
          </div>
        </div>
      </div>
    </div>
  `;
}

function renderUserInputs(device, inputs, excludeIds = []) {
  if (!inputs || !inputs.length) return '';

  // Filter out excluded inputs (e.g., those already handled by SSH form)
  const filteredInputs = inputs.filter(input => !excludeIds.includes(input.id));
  if (!filteredInputs.length) return '';

  return `
    <div class="deploy-user-inputs">
      ${filteredInputs.map(input => {
        if (input.type === 'checkbox') {
          const isChecked = input.default === 'true' || input.default === true;
          return `
            <div class="form-group form-group-checkbox">
              <label class="checkbox-label">
                <input
                  type="checkbox"
                  id="input-${device.id}-${input.id}"
                  ${isChecked ? 'checked' : ''}
                />
                <span>${getLocalizedField(input, 'name')}</span>
              </label>
              ${input.description ? `<p class="text-xs text-text-muted">${getLocalizedField(input, 'description')}</p>` : ''}
            </div>
          `;
        }
        return `
          <div class="form-group">
            <label>${getLocalizedField(input, 'name')}</label>
            ${input.description ? `<p class="text-xs text-text-muted mb-1">${getLocalizedField(input, 'description')}</p>` : ''}
            <input
              type="${input.type === 'password' ? 'password' : 'text'}"
              id="input-${device.id}-${input.id}"
              placeholder="${input.placeholder || ''}"
              value="${input.default || ''}"
              ${input.required ? 'required' : ''}
            />
          </div>
        `;
      }).join('')}
    </div>
  `;
}

function renderSSHForm(device) {
  const state = deviceStates[device.id] || {};
  const conn = state.connection || {};

  return `
    <div class="deploy-user-inputs">
      <div class="flex gap-4">
        <div class="form-group flex-1">
          <label>${t('deploy.connection.host')}</label>
          <input type="text" id="ssh-host-${device.id}" value="${conn.host || ''}" placeholder="192.168.1.100">
        </div>
        <div class="form-group" style="width: 100px;">
          <label>${t('deploy.connection.port')}</label>
          <input type="number" id="ssh-port-${device.id}" value="${conn.port || 22}">
        </div>
      </div>
      <div class="flex gap-4">
        <div class="form-group flex-1">
          <label>${t('deploy.connection.username')}</label>
          <input type="text" id="ssh-user-${device.id}" value="${conn.username || 'root'}">
        </div>
        <div class="form-group flex-1">
          <label>${t('deploy.connection.password')}</label>
          <input type="password" id="ssh-pass-${device.id}" value="${conn.password || ''}">
        </div>
      </div>
      <button class="btn btn-secondary w-full" id="test-ssh-${device.id}" data-device-id="${device.id}">
        ${t('deploy.connection.test')}
      </button>
    </div>
  `;
}

function renderSerialPortSelector(device) {
  return `
    <div class="deploy-user-inputs">
      <div class="form-group">
        <label>${t('deploy.connection.selectPort')}</label>
        <div class="flex gap-2">
          <select id="serial-port-${device.id}" class="flex-1">
            <option value="">${t('deploy.connection.selectPort')}...</option>
          </select>
          <button class="btn btn-secondary" id="refresh-ports-${device.id}" data-device-id="${device.id}">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M23 4v6h-6M1 20v-6h6"/>
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
            </svg>
          </button>
        </div>
      </div>
    </div>
  `;
}

function renderLogEntry(log) {
  return `
    <div class="deploy-log-entry ${log.level}">
      <span class="time">${log.timestamp}</span>
      <span class="msg">${escapeHtml(log.message)}</span>
    </div>
  `;
}

function getFilteredLogs(logs) {
  if (showDetailedLogs) {
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

function isKeyLogMessage(log) {
  // Helper to determine if a log should be shown in summary mode
  return log.level !== 'info' || getFilteredLogs([log]).length > 0;
}

function getStatusClass(state) {
  if (state.deploymentStatus === 'completed') return 'completed';
  if (state.deploymentStatus === 'failed') return 'failed';
  if (state.deploymentStatus === 'running') return 'running';
  if (state.detected) return 'ready';
  return 'pending';
}

function getStatusIcon(state) {
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

function getStatusText(state) {
  if (state.deploymentStatus === 'completed') return t('deploy.status.completed');
  if (state.deploymentStatus === 'failed') return t('deploy.status.failed');
  if (state.deploymentStatus === 'running') return t('deploy.status.running');
  if (state.detected) return t('deploy.status.ready');
  return t('deploy.status.pending');
}

function getButtonClass(state) {
  if (state.deploymentStatus === 'completed') return 'completed';
  if (state.deploymentStatus === 'running') return 'running';
  return '';
}

function getDeployButtonContent(state, isManual) {
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
// Preview Helper Functions
// ============================================

/**
 * Collect user inputs from all previous steps
 */
function collectPreviousInputs(devices, currentIndex) {
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
function resolveTemplate(template, inputs) {
  if (!template) return template;
  return template.replace(/\{\{(\w+)\}\}/g, (match, key) => {
    return inputs[key] !== undefined ? inputs[key] : match;
  });
}

/**
 * Render user inputs for preview step with auto-fill from previous steps
 */
function renderPreviewInputs(device) {
  const preview = device.preview || {};
  const userInputs = preview.user_inputs || [];

  if (!userInputs.length) return '';

  // Get previous inputs for template resolution
  const deployment = currentSolution.deployment || {};
  const devices = deployment.devices || [];
  const currentIndex = devices.findIndex(d => d.id === device.id);
  const previousInputs = collectPreviousInputs(devices, currentIndex);

  return `
    <div class="deploy-user-inputs preview-inputs">
      ${userInputs.map(input => {
        // Resolve template for default value
        let defaultValue = input.default || '';
        if (input.default_template) {
          defaultValue = resolveTemplate(input.default_template, previousInputs);
        }

        return `
          <div class="form-group">
            <label>${getLocalizedField(input, 'name')}</label>
            ${input.description ? `<p class="text-xs text-text-muted mb-1">${getLocalizedField(input, 'description')}</p>` : ''}
            <input
              type="${input.type === 'password' ? 'password' : 'text'}"
              id="preview-input-${device.id}-${input.id}"
              class="preview-input"
              data-device-id="${device.id}"
              data-input-id="${input.id}"
              placeholder="${input.placeholder || ''}"
              value="${escapeHtml(defaultValue)}"
              ${input.required ? 'required' : ''}
            />
          </div>
        `;
      }).join('')}
    </div>
  `;
}

/**
 * Get button content for preview step
 */
function getPreviewButtonContent(state) {
  if (state.previewConnected) {
    return `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <rect x="6" y="4" width="4" height="16"/>
      <rect x="14" y="4" width="4" height="16"/>
    </svg> ${t('preview.actions.disconnect')}`;
  }
  if (state.deploymentStatus === 'completed') {
    return `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg> ${t('deploy.status.completed')}`;
  }
  return `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    <polygon points="5 3 19 12 5 21 5 3"/>
  </svg> ${t('preview.actions.connect')}`;
}

/**
 * Initialize preview window for a device
 */
async function initPreviewWindow(deviceId) {
  const device = getDeviceById(deviceId);
  if (!device || device.type !== 'preview') return;

  const container = document.getElementById(`preview-container-${deviceId}`);
  if (!container) return;

  const preview = device.preview || {};
  const state = deviceStates[deviceId];

  // Create preview window
  const previewWindow = new PreviewWindow(container, {
    aspectRatio: preview.display?.aspect_ratio || '16:9',
    showStats: preview.display?.show_stats !== false,
  });

  // Set up overlay renderer
  if (preview.overlay?.script_file) {
    // Load custom script
    const scriptUrl = getAssetUrl(currentSolution.id, preview.overlay.script_file);
    const renderer = await fetchOverlayScript(scriptUrl);
    if (renderer) {
      previewWindow.setOverlayRenderer(renderer);
    }
  } else if (preview.overlay?.renderer) {
    // Use built-in renderer
    const renderer = renderers[preview.overlay.renderer] || renderers.auto;
    previewWindow.setOverlayRenderer(renderer);
  } else {
    // Default to auto renderer
    previewWindow.setOverlayRenderer(renderers.auto);
  }

  // Handle status changes
  previewWindow.onStatus((status, message) => {
    state.previewConnected = status === 'connected';
    updatePreviewUI(deviceId);
  });

  // Handle connect button click from preview window
  container.addEventListener('preview:connect', async () => {
    await startPreview(deviceId, previewWindow);
  });

  // Store instance for cleanup
  previewInstances[deviceId] = previewWindow;
}

/**
 * Start preview connection
 */
async function startPreview(deviceId, previewWindow) {
  const device = getDeviceById(deviceId);
  if (!device) return;

  const preview = device.preview || {};
  const state = deviceStates[deviceId];

  // Collect inputs from the form
  const inputs = {};
  const userInputs = preview.user_inputs || [];
  userInputs.forEach(input => {
    const el = document.getElementById(`preview-input-${deviceId}-${input.id}`);
    if (el) {
      inputs[input.id] = el.value;
    }
  });

  // Store inputs in state
  state.userInputs = { ...state.userInputs, ...inputs };

  // Build connection options
  const options = {};

  // Resolve RTSP URL
  if (preview.video?.rtsp_url_template) {
    options.rtspUrl = resolveTemplate(preview.video.rtsp_url_template, inputs);
  } else if (inputs.rtsp_url) {
    options.rtspUrl = inputs.rtsp_url;
  }

  // Resolve MQTT config
  if (preview.mqtt?.broker_template) {
    options.mqttBroker = resolveTemplate(preview.mqtt.broker_template, inputs);
  } else if (inputs.mqtt_broker) {
    options.mqttBroker = inputs.mqtt_broker;
  }

  options.mqttPort = preview.mqtt?.port || inputs.mqtt_port || 1883;

  if (preview.mqtt?.topic_template) {
    options.mqttTopic = resolveTemplate(preview.mqtt.topic_template, inputs);
  } else if (inputs.mqtt_topic) {
    options.mqttTopic = inputs.mqtt_topic;
  } else {
    options.mqttTopic = preview.mqtt?.topic || 'inference/results';
  }

  if (preview.mqtt?.username || inputs.mqtt_username) {
    options.mqttUsername = preview.mqtt?.username || inputs.mqtt_username;
    options.mqttPassword = preview.mqtt?.password || inputs.mqtt_password;
  }

  try {
    await previewWindow.connect(options);
    toast.success(t('preview.connected'));
  } catch (error) {
    console.error('Preview connection failed:', error);
    toast.error(t('preview.connectionFailed') + ': ' + error.message);
  }
}

/**
 * Update preview UI elements
 */
function updatePreviewUI(deviceId) {
  const state = deviceStates[deviceId];
  if (!state) return;

  const btn = document.getElementById(`deploy-btn-${deviceId}`);
  if (btn) {
    btn.innerHTML = getPreviewButtonContent(state);
  }
}

/**
 * Handle preview button click
 */
async function handlePreviewButtonClick(deviceId) {
  const device = getDeviceById(deviceId);
  if (!device || device.type !== 'preview') return;

  const state = deviceStates[deviceId];
  const previewWindow = previewInstances[deviceId];

  if (!previewWindow) {
    // Initialize preview if not done
    await initPreviewWindow(deviceId);
    return;
  }

  if (state.previewConnected) {
    // Disconnect
    await previewWindow.disconnect();
    state.previewConnected = false;
    updatePreviewUI(deviceId);
  } else {
    // Connect
    await startPreview(deviceId, previewWindow);
  }
}

/**
 * Mark preview step as complete
 */
function markPreviewComplete(deviceId) {
  const state = deviceStates[deviceId];
  if (state) {
    state.deploymentStatus = 'completed';
    updateSectionUI(deviceId);
    toast.success(t('deploy.status.completed'));
    expandNextSection(deviceId);
  }
}

async function detectDevices() {
  try {
    const detected = await devicesApi.detect(currentSolution.id);

    detected.forEach(device => {
      if (deviceStates[device.config_id]) {
        deviceStates[device.config_id].detected = device.status === 'detected' || device.status === 'manual_required';
        deviceStates[device.config_id].details = device.details;
        updateSectionUI(device.config_id);
      }
    });

    await refreshSerialPorts();
  } catch (error) {
    console.error('Device detection failed:', error);
  }
}

async function refreshSerialPorts(clickedBtn = null) {
  // Add spinning animation to button
  if (clickedBtn) {
    clickedBtn.classList.add('spinning');
    clickedBtn.disabled = true;
  }

  try {
    const result = await devicesApi.getPorts();
    const ports = result.ports || [];
    const deployment = currentSolution.deployment || {};
    const devices = deployment.devices || [];

    devices.forEach(device => {
      if (device.type === 'esp32_usb') {
        const select = document.getElementById(`serial-port-${device.id}`);
        if (select) {
          const currentValue = select.value;
          const state = deviceStates[device.id];
          // Check if we have a detected port from device detection
          const detectedPort = state?.details?.port;

          select.innerHTML = `<option value="">${t('deploy.connection.selectPort')}...</option>`;
          ports.forEach(port => {
            const option = document.createElement('option');
            option.value = port.device;
            option.textContent = `${port.device} - ${port.description || 'Unknown'}`;
            select.appendChild(option);
          });

          // Auto-select: prefer detected port, then single available port, then current value
          // On macOS, tty.* and cu.* are equivalent - match by suffix
          const findMatchingPort = (detected) => {
            if (!detected) return null;
            // Direct match
            let match = ports.find(p => p.device === detected);
            if (match) return match.device;
            // Try tty <-> cu conversion (macOS)
            const suffix = detected.replace(/^\/dev\/(tty|cu)\./, '');
            match = ports.find(p => p.device.endsWith(suffix));
            return match ? match.device : null;
          };

          const matchedPort = findMatchingPort(detectedPort);
          if (matchedPort) {
            select.value = matchedPort;
            state.port = matchedPort;
            state.detected = true;
            updateSectionUI(device.id);
          } else if (ports.length === 1) {
            // Only one port available, auto-select it
            select.value = ports[0].device;
            state.port = ports[0].device;
            state.detected = true;
            updateSectionUI(device.id);
          } else if (currentValue) {
            select.value = currentValue;
          }
        }
      }
    });
  } catch (error) {
    console.error('Failed to refresh ports:', error);
    toast.error('Failed to refresh ports');
  } finally {
    // Remove spinning animation
    if (clickedBtn) {
      clickedBtn.classList.remove('spinning');
      clickedBtn.disabled = false;
    }
  }
}

function updateChoiceOptionUI(deviceId) {
  const state = deviceStates[deviceId];
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
  const container = document.getElementById('content-area');
  if (container && selectedDevice === deviceId) {
    const selectedSection = container.querySelector('#selected-device-section');
    if (selectedSection) {
      const device = getDeviceById(deviceId);
      selectedSection.innerHTML = device ? renderSelectedDeviceContent(device) : '';
      setupSelectedDeviceHandlers(container);
    }
  }
}

function updateSectionUI(deviceId) {
  const state = deviceStates[deviceId];
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
}

function addLogToDevice(deviceId, level, message) {
  const state = deviceStates[deviceId];
  if (!state) return;

  const timestamp = new Date().toLocaleTimeString();
  const logEntry = { timestamp, level, message };
  state.logs.push(logEntry);

  const viewer = document.getElementById(`logs-viewer-${deviceId}`);
  if (viewer) {
    // Only add to DOM if it passes the filter
    const shouldShow = showDetailedLogs || isKeyLogMessage(logEntry);

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

function toggleSection(deviceId) {
  const state = deviceStates[deviceId];
  if (!state) return;

  state.sectionExpanded = !state.sectionExpanded;

  const content = document.getElementById(`content-${deviceId}`);
  const chevron = document.getElementById(`chevron-${deviceId}`);

  if (content) content.classList.toggle('expanded', state.sectionExpanded);
  if (chevron) chevron.classList.toggle('expanded', state.sectionExpanded);
}

function updateSelectedDevice(container) {
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

function setupSelectedDeviceHandlers(container) {
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
      showDetailedLogs = checkbox.checked;
      refreshAllLogViewers();
    });
  });
}

async function testSSHConnection(deviceId, btn) {
  const config = {
    host: document.getElementById(`ssh-host-${deviceId}`)?.value,
    port: parseInt(document.getElementById(`ssh-port-${deviceId}`)?.value || '22'),
    username: document.getElementById(`ssh-user-${deviceId}`)?.value,
    password: document.getElementById(`ssh-pass-${deviceId}`)?.value,
  };

  btn.disabled = true;
  btn.innerHTML = '<span class="spinner" style="width:14px;height:14px;border-width:2px;"></span>';

  try {
    await devicesApi.testConnection(config);
    deviceStates[deviceId].detected = true;
    deviceStates[deviceId].connection = config;
    updateSectionUI(deviceId);
    toast.success(t('common.success'));
  } catch (error) {
    toast.error(t('common.error') + ': ' + error.message);
  } finally {
    btn.disabled = false;
    btn.textContent = t('deploy.connection.test');
  }
}

function toggleLogs(deviceId, forceExpand = null) {
  const state = deviceStates[deviceId];
  if (!state) return;

  state.logsExpanded = forceExpand !== null ? forceExpand : !state.logsExpanded;

  const panel = document.getElementById(`logs-panel-${deviceId}`);
  const chevron = document.getElementById(`logs-chevron-${deviceId}`);

  if (panel) panel.classList.toggle('expanded', state.logsExpanded);
  if (chevron) chevron.classList.toggle('expanded', state.logsExpanded);
}

function refreshAllLogViewers() {
  // Refresh all log viewers to apply filter change
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
      checkbox.checked = showDetailedLogs;
    }
  });
}

async function startDeployment(deviceId) {
  const device = getDeviceById(deviceId);
  if (!device) return;

  const state = deviceStates[deviceId];
  state.deploymentStatus = 'running';
  state.logs = [];
  updateSectionUI(deviceId);

  // Expand section and logs
  if (!state.sectionExpanded) toggleSection(deviceId);
  toggleLogs(deviceId, true);

  addLogToDevice(deviceId, 'info', t('deploy.logs.starting'));

  // Build params in the format expected by backend
  const params = {
    solution_id: currentSolution.id,
    selected_devices: [deviceId],
    device_connections: {},
    options: {},
  };

  // Collect user inputs
  if (device.type === 'script') {
    const inputs = state.details?.user_inputs || [];
    params.options.user_inputs = {};
    inputs.forEach(input => {
      const el = document.getElementById(`input-${deviceId}-${input.id}`);
      if (el) params.options.user_inputs[input.id] = el.value;
    });
  }

  // Add connection info based on device type
  if (device.type === 'esp32_usb') {
    const select = document.getElementById(`serial-port-${deviceId}`);
    params.device_connections[deviceId] = {
      port: select?.value || state.port,
    };
  } else if (device.type === 'ssh_deb' || device.type === 'docker_remote') {
    params.device_connections[deviceId] = {
      host: document.getElementById(`ssh-host-${deviceId}`)?.value,
      port: parseInt(document.getElementById(`ssh-port-${deviceId}`)?.value || '22'),
      username: document.getElementById(`ssh-user-${deviceId}`)?.value,
      password: document.getElementById(`ssh-pass-${deviceId}`)?.value,
    };
  } else if (device.type === 'recamera_nodered') {
    // reCamera Node-RED deployment - need IP for Node-RED API and optional SSH for service cleanup
    const host = document.getElementById(`ssh-host-${deviceId}`)?.value;
    params.device_connections[deviceId] = {
      recamera_ip: host,
      nodered_host: host,
      ssh_username: document.getElementById(`ssh-user-${deviceId}`)?.value || 'recamera',
      ssh_password: document.getElementById(`ssh-pass-${deviceId}`)?.value,
      ssh_port: parseInt(document.getElementById(`ssh-port-${deviceId}`)?.value || '22'),
    };
  } else if (device.type === 'recamera_cpp') {
    // reCamera C++ deployment - need SSH credentials
    params.device_connections[deviceId] = {
      host: document.getElementById(`ssh-host-${deviceId}`)?.value,
      port: parseInt(document.getElementById(`ssh-port-${deviceId}`)?.value || '22'),
      username: document.getElementById(`ssh-user-${deviceId}`)?.value || 'recamera',
      password: document.getElementById(`ssh-pass-${deviceId}`)?.value,
    };
  } else {
    // For local docker or other types, include empty connection
    params.device_connections[deviceId] = {};
  }

  try {
    const result = await deploymentsApi.start(params);
    connectLogsWebSocket(result.deployment_id, deviceId);
    addLogToDevice(deviceId, 'info', `Deployment ID: ${result.deployment_id}`);
  } catch (error) {
    console.error('Deployment failed:', error);
    state.deploymentStatus = 'failed';
    updateSectionUI(deviceId);
    addLogToDevice(deviceId, 'error', error.message);
    toast.error(t('common.error') + ': ' + error.message);
  }
}

function connectLogsWebSocket(deploymentId, deviceId) {
  if (logsWsMap[deviceId]) {
    logsWsMap[deviceId].disconnect();
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
    const state = deviceStates[deviceId];
    if (state) {
      state.deploymentStatus = data.status;
      state.progress = data.progress || 0;
      updateSectionUI(deviceId);
      updateChoiceOptionUI(deviceId); // Update single_choice option if applicable

      if (data.status === 'completed') {
        addLogToDevice(deviceId, 'success', t('deploy.status.completed'));
        toast.success(`${getDeviceById(deviceId)?.name}: ${t('deploy.status.completed')}`);

        // Auto-expand next section (only for sequential mode)
        const deployment = currentSolution.deployment || {};
        if (deployment.selection_mode !== 'single_choice') {
          expandNextSection(deviceId);
        }
      } else if (data.status === 'failed') {
        addLogToDevice(deviceId, 'error', t('deploy.status.failed'));
        toast.error(`${getDeviceById(deviceId)?.name}: ${t('deploy.status.failed')}`);
      }
    }
  });

  ws.on('error', () => {
    addLogToDevice(deviceId, 'error', 'Connection error');
  });

  ws.on('close', (event) => {
    const state = deviceStates[deviceId];
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
  logsWsMap[deviceId] = ws;
}

function expandNextSection(currentDeviceId) {
  const deployment = currentSolution.deployment || {};
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

function getDeviceById(deviceId) {
  const deployment = currentSolution.deployment || {};
  const devices = deployment.devices || [];
  return devices.find(d => d.id === deviceId);
}

function markDeviceComplete(deviceId) {
  const state = deviceStates[deviceId];
  if (state) {
    state.deploymentStatus = 'completed';
    updateSectionUI(deviceId);
    toast.success(t('deploy.status.completed'));
    expandNextSection(deviceId);
  }
}

function handleDockerNotInstalled(deviceId, data) {
  const state = deviceStates[deviceId];
  if (!state) return;

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

function showDockerInstallDialog(deviceId, message, fixAction) {
  // Create dialog overlay
  const overlay = document.createElement('div');
  overlay.className = 'dialog-overlay';
  overlay.id = 'docker-install-dialog';

  const actionText = fixAction === 'install_docker' ? t('deploy.docker.installAction') :
                     fixAction === 'fix_docker_permission' ? t('deploy.docker.fixPermissionAction') :
                     fixAction === 'start_docker' ? t('deploy.docker.startAction') :
                     t('deploy.docker.fixAction');

  overlay.innerHTML = `
    <div class="dialog">
      <div class="dialog-header">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
          <line x1="12" y1="9" x2="12" y2="13"/>
          <line x1="12" y1="17" x2="12.01" y2="17"/>
        </svg>
        <h3>${t('deploy.docker.notInstalled')}</h3>
      </div>
      <div class="dialog-body">
        <p>${escapeHtml(message)}</p>
        <p class="dialog-hint">${t('deploy.docker.installHint')}</p>
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

  // Handle confirm - restart deployment with auto_install_docker flag
  overlay.querySelector('#dialog-confirm').addEventListener('click', () => {
    overlay.remove();
    addLogToDevice(deviceId, 'info', t('deploy.docker.installing'));
    startDeploymentWithDockerInstall(deviceId);
  });

  // Click outside to close
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) {
      overlay.remove();
      addLogToDevice(deviceId, 'warning', t('deploy.docker.installCancelled'));
    }
  });
}

async function startDeploymentWithDockerInstall(deviceId) {
  const device = getDeviceById(deviceId);
  if (!device) return;

  const state = deviceStates[deviceId];
  state.deploymentStatus = 'running';
  updateSectionUI(deviceId);
  updateChoiceOptionUI(deviceId);

  // Build params with auto_install_docker flag
  const params = {
    solution_id: currentSolution.id,
    selected_devices: [deviceId],
    device_connections: {},
    options: {},
  };

  // Add connection info with auto_install_docker flag
  if (device.type === 'docker_remote') {
    params.device_connections[deviceId] = {
      host: document.getElementById(`ssh-host-${deviceId}`)?.value,
      port: parseInt(document.getElementById(`ssh-port-${deviceId}`)?.value || '22'),
      username: document.getElementById(`ssh-user-${deviceId}`)?.value,
      password: document.getElementById(`ssh-pass-${deviceId}`)?.value,
      auto_install_docker: true,  // Key flag for auto-install
    };
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

function setupEventHandlers(container) {
  // Back button
  container.querySelector('#back-btn')?.addEventListener('click', () => {
    cleanupDeployPage();
    router.navigate('solution', { id: currentSolution.id });
  });

  // Radio options for single_choice mode
  container.querySelectorAll('.deploy-choice-option').forEach(el => {
    el.addEventListener('click', () => {
      const deviceId = el.dataset.deviceId;
      if (selectedDevice !== deviceId) {
        selectedDevice = deviceId;
        // Re-render the options and selected section
        updateSelectedDevice(container);
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
        markDeviceComplete(deviceId);
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
      showDetailedLogs = checkbox.checked;
      // Re-render all log viewers to apply filter
      refreshAllLogViewers();
    });
  });
}

export function cleanupDeployPage() {
  Object.values(logsWsMap).forEach(ws => ws?.disconnect());
  logsWsMap = {};
  selectedDevice = null;

  // Cleanup preview instances
  Object.values(previewInstances).forEach(preview => preview?.destroy());
  previewInstances = {};
}

// Re-render when language changes
i18n.onLocaleChange(() => {
  if (router.currentRoute === 'deploy' && currentSolution) {
    renderDeployPage({ id: currentSolution.id });
  }
});
