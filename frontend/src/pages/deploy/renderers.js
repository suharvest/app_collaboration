/**
 * Deploy Page - Rendering Functions
 * All UI rendering functions for the deployment page
 */

import { t, getLocalizedField } from '../../modules/i18n.js';
import { getAssetUrl } from '../../modules/api.js';
import { escapeHtml } from '../../modules/utils.js';
import {
  getCurrentSolution,
  getDeviceStates,
  getDeviceState,
  getSelectedDevice,
  getSelectedPresetId,
  getDeviceGroupSelections,
  getShowDetailedLogs,
} from './state.js';
import {
  getFilteredDeviceGroups,
  getFilteredDevices,
  getSelectedTarget,
  collectPreviousInputs,
  resolveTemplate,
  getStatusClass,
  getStatusIcon,
  getStatusText,
  getButtonClass,
  getDeployButtonContent,
  getFilteredLogs,
} from './utils.js';

// ============================================
// Main Content Renderer
// ============================================

export function renderDeployContent(container) {
  const currentSolution = getCurrentSolution();
  const deviceStates = getDeviceStates();
  const selectedDevice = getSelectedDevice();
  const selectedPresetId = getSelectedPresetId();

  const deployment = currentSolution.deployment || {};
  const devices = deployment.devices || [];
  const presets = deployment.presets || [];
  const name = getLocalizedField(currentSolution, 'name');
  const selectionMode = deployment.selection_mode || 'sequential';

  // Render device group sections (with template-based instructions)
  const filteredDeviceGroups = getFilteredDeviceGroups(presets);
  const deviceGroupSectionsHtml = renderDeviceGroupSections(filteredDeviceGroups);

  // Check if presets have sections (Level 1)
  const presetsWithSections = presets.filter(p => p.section);
  const hasPresetSections = presetsWithSections.length > 0;

  // Render preset selector and section (Level 1)
  const presetSelectorHtml = hasPresetSections ? renderPresetSelector(presets) : '';
  const presetSectionHtml = hasPresetSections ? renderPresetSectionContent(presets) : '';

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
        ${!hasPresetSections && deployment.guide ? `
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
        <!-- Level 1: Preset Selector + Section -->
        ${presetSelectorHtml}
        ${presetSectionHtml}

        <!-- Level 2: Device Group Sections (template-based instructions) -->
        <div id="deploy-device-groups-container">
          ${deviceGroupSectionsHtml}
        </div>

        <!-- Sequential Mode: Steps -->
        <div class="deploy-sections" id="deploy-sections-container">
          ${getFilteredDevices(devices).map((device, index) => renderDeploySection(device, index + 1)).join('')}
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

// ============================================
// Preset Selector (Level 1)
// ============================================

/**
 * Render preset selector (Level 1 tab group)
 * Only shown when multiple presets have sections
 */
export function renderPresetSelector(presets) {
  const selectedPresetId = getSelectedPresetId();
  const presetsWithSections = presets.filter(p => p.section);
  // Don't show selector for single preset
  if (presetsWithSections.length <= 1) return '';

  return `
    <div class="deploy-preset-selector">
      ${presetsWithSections.map(preset => {
        const isSelected = preset.id === selectedPresetId;
        const name = getLocalizedField(preset, 'name');
        const badge = getLocalizedField(preset, 'badge');
        return `
          <button class="deploy-preset-btn ${isSelected ? 'selected' : ''}"
                  data-preset-id="${preset.id}">
            ${escapeHtml(name)}
            ${badge ? `<span class="deploy-preset-badge">${escapeHtml(badge)}</span>` : ''}
          </button>
        `;
      }).join('')}
    </div>
  `;
}

/**
 * Render preset section content (Level 1 deployment guide)
 */
export function renderPresetSectionContent(presets) {
  const selectedPresetId = getSelectedPresetId();
  const selectedPreset = presets.find(p => p.id === selectedPresetId);
  if (!selectedPreset || !selectedPreset.section) return '';

  const section = selectedPreset.section;
  const title = section.title || '';
  const description = section.description || '';

  if (!description) return '';

  return `
    <div class="deploy-preset-section" id="deploy-preset-section">
      ${title ? `<h3 class="deploy-preset-section-title">${escapeHtml(title)}</h3>` : ''}
      <div class="deploy-preset-section-content markdown-content" id="deploy-preset-section-content">
        ${description}
      </div>
    </div>
  `;
}

// ============================================
// Device Group Sections (Level 2)
// ============================================

/**
 * Render device group sections with template-based instructions
 */
export function renderDeviceGroupSections(deviceGroups) {
  return deviceGroups
    .filter(group => group.section?.description)
    .map(group => {
      const section = group.section;
      const title = section.title || getLocalizedField(group, 'name');
      const hasMultipleOptions = group.options && group.options.length > 1;

      return `
        <div class="deploy-device-group-section" data-group-id="${group.id}">
          <div class="deploy-device-group-header">
            <h3 class="deploy-device-group-title">${escapeHtml(title)}</h3>
            ${hasMultipleOptions ? renderDeviceGroupSelector(group) : ''}
          </div>
          <div class="deploy-device-group-content markdown-content" id="device-group-content-${group.id}">
            ${section.description}
          </div>
        </div>
      `;
    })
    .join('');
}

/**
 * Render device selector for device group
 */
export function renderDeviceGroupSelector(group) {
  const deviceGroupSelections = getDeviceGroupSelections();
  const currentSelection = deviceGroupSelections[group.id] || group.default;

  return `
    <select class="device-group-selector" data-group-id="${group.id}">
      ${group.options.map(opt => {
        const deviceInfo = opt.device_info || {};
        const name = getLocalizedField(deviceInfo, 'name') || opt.label || opt.device_ref;
        const selected = opt.device_ref === currentSelection ? 'selected' : '';
        return `<option value="${opt.device_ref}" ${selected}>${escapeHtml(name)}</option>`;
      }).join('')}
    </select>
  `;
}

// ============================================
// Single Choice Mode Renderers
// ============================================

export function renderDeployOption(device) {
  const deviceStates = getDeviceStates();
  const selectedDevice = getSelectedDevice();
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

export function renderSelectedDeviceContent(device) {
  if (!device) return '';

  const deviceStates = getDeviceStates();
  const state = deviceStates[device.id] || {};
  const section = device.section || {};
  const sectionDescription = section.description || '';
  const sectionTroubleshoot = section.troubleshoot || '';
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

      <!-- Serial Port Selector (for ESP32/Himax devices) -->
      ${device.type === 'esp32_usb' || device.type === 'himax_usb' ? renderSerialPortSelector(device) : ''}

      <!-- Model Selection (for Himax devices with models) -->
      ${device.type === 'himax_usb' ? renderModelSelection(device) : ''}

      <!-- Deploy Action Area -->
      <div class="deploy-action-area">
        <button class="deploy-action-btn ${getButtonClass(state)}"
                id="deploy-btn-${device.id}"
                data-device-id="${device.id}"
                ${state.deploymentStatus === 'running' ? 'disabled' : ''}>
          ${getDeployButtonContent(state, false)}
        </button>
      </div>

      <!-- Troubleshoot Section (shown below deploy button) -->
      ${sectionTroubleshoot ? `
        <div class="deploy-troubleshoot">
          <div class="markdown-content">${sectionTroubleshoot}</div>
        </div>
      ` : ''}

      <!-- Logs Section -->
      ${renderLogsSection(device.id, state)}
    </div>
  `;
}

// ============================================
// Sequential Mode Section Renderer
// ============================================

export function renderDeploySection(device, stepNumber) {
  const deviceStates = getDeviceStates();
  const state = deviceStates[device.id] || {};
  const name = getLocalizedField(device, 'name');
  const section = device.section || {};
  const sectionTitle = getLocalizedField(section, 'title') || name;
  const sectionDescription = section.description || '';
  const sectionTroubleshoot = section.troubleshoot || '';
  const isManual = device.type === 'manual';
  const isScript = device.type === 'script';
  const isPreview = device.type === 'preview';
  const isDockerDeploy = device.type === 'docker_deploy' && device.targets;
  const isRecameraCppWithTargets = device.type === 'recamera_cpp' && device.targets;
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
        ${isManual ? renderManualSectionContent(device, state, sectionDescription) :
          isPreview ? renderPreviewSectionContent(device, sectionDescription) :
          isDockerDeploy ? renderDockerDeploySectionContent(device, state) :
          isRecameraCppWithTargets ? renderRecameraCppSectionContent(device, state) :
          renderAutoSectionContent(device, state, sectionDescription, isScript)}

        <!-- Troubleshoot Section (shown below deploy button) -->
        ${sectionTroubleshoot ? `
          <div class="deploy-troubleshoot">
            <div class="markdown-content">${sectionTroubleshoot}</div>
          </div>
        ` : ''}

        <!-- Logs Section (collapsible) -->
        ${renderLogsSection(device.id, state)}
      </div>
    </div>
  `;
}

// ============================================
// Section Content Helpers
// ============================================

function renderManualSectionContent(device, state, sectionDescription) {
  return `
    <!-- Manual: Instructions first, then mark done button -->
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
  `;
}

function renderPreviewSectionContent(device, sectionDescription) {
  return `
    <!-- Preview: Live video + MQTT inference display -->
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
  `;
}

function renderDockerDeploySectionContent(device, state) {
  return `
    <!-- Docker Deploy: local/remote target selector -->
    ${renderDockerTargetSelector(device)}

    <!-- Target-specific content (description, wiring, SSH form for remote) -->
    <div class="deploy-target-content" id="target-content-${device.id}">
      ${renderDockerTargetContent(device)}
    </div>

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
  `;
}

function renderRecameraCppSectionContent(device, state) {
  return `
    <!-- reCamera C++ with model targets: model selector + SSH + deploy -->
    ${renderDockerTargetSelector(device)}

    <!-- Service Switch Warning -->
    ${renderServiceSwitchWarning(device.type)}

    <!-- Connection Settings (SSH) -->
    ${renderSSHForm(device)}

    <!-- Target-specific content -->
    <div class="deploy-target-content" id="target-content-${device.id}">
      ${renderRecameraCppTargetContent(device)}
    </div>

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
  `;
}

function renderAutoSectionContent(device, state, sectionDescription, isScript) {
  return `
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

    <!-- Serial Port Selector (for ESP32/Himax USB devices) -->
    ${device.type === 'esp32_usb' || device.type === 'himax_usb' ? renderSerialPortSelector(device) : ''}

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
  `;
}

// ============================================
// Logs Section
// ============================================

function renderLogsSection(deviceId, state) {
  return `
    <div class="deploy-logs" id="logs-${deviceId}">
      <div class="deploy-logs-toggle" id="logs-toggle-${deviceId}" data-device-id="${deviceId}">
        <span class="deploy-logs-label">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
          </svg>
          ${t('deploy.logs.title')}
          <span class="deploy-logs-count" id="logs-count-${deviceId}">${getFilteredLogs(state.logs || []).length}</span>
        </span>
        <svg class="deploy-section-chevron ${state.logsExpanded ? 'expanded' : ''}"
             id="logs-chevron-${deviceId}"
             width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="6 9 12 15 18 9"/>
        </svg>
      </div>
      <div class="deploy-logs-panel ${state.logsExpanded ? 'expanded' : ''}" id="logs-panel-${deviceId}">
        <div class="deploy-logs-options">
          <label class="deploy-logs-detail-toggle">
            <input type="checkbox" id="detailed-logs-${deviceId}" ${getShowDetailedLogs() ? 'checked' : ''}>
            <span>${t('deploy.logs.detailed')}</span>
          </label>
        </div>
        <div class="deploy-logs-viewer" id="logs-viewer-${deviceId}">
          ${getFilteredLogs(state.logs || []).length === 0 ? `
            <div class="deploy-logs-empty">${t('deploy.logs.empty')}</div>
          ` : getFilteredLogs(state.logs || []).map(log => renderLogEntry(log)).join('')}
        </div>
      </div>
    </div>
  `;
}

export function renderLogEntry(log) {
  return `
    <div class="deploy-log-entry ${log.level}">
      <span class="time">${log.timestamp}</span>
      <span class="msg">${escapeHtml(log.message)}</span>
    </div>
  `;
}

// ============================================
// User Inputs
// ============================================

export function renderUserInputs(device, inputs, excludeIds = []) {
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

// ============================================
// Docker Target Selector
// ============================================

/**
 * Render target selector for docker_deploy type
 * Allows user to choose between local and remote deployment
 */
export function renderDockerTargetSelector(device) {
  const deviceStates = getDeviceStates();
  const state = deviceStates[device.id] || {};
  const targets = device.targets || {};
  const selectedTarget = state.selectedTarget || 'local';

  const targetEntries = Object.entries(targets);
  if (!targetEntries.length) return '';

  return `
    <div class="deploy-mode-selector">
      <div class="deploy-mode-options">
        ${targetEntries.map(([targetId, target]) => {
          const isSelected = selectedTarget === targetId;
          const targetName = getLocalizedField(target, 'name');
          const targetDesc = getLocalizedField(target, 'description');
          const isLocal = targetId === 'local';
          let icon;
          if (device.type === 'recamera_cpp') {
            // Model variant icon (AI chip)
            icon = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="4" y="4" width="16" height="16" rx="2"/>
                <rect x="9" y="9" width="6" height="6"/>
                <path d="M15 2v2M15 20v2M9 2v2M9 20v2M2 15h2M20 15h2M2 9h2M20 9h2"/>
              </svg>`;
          } else {
            icon = isLocal
              ? `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="2" y="7" width="20" height="14" rx="2"/>
                  <path d="M12 7V3M7 7V5M17 7V5"/>
                </svg>`
              : `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="2" y="2" width="20" height="8" rx="2"/>
                  <rect x="2" y="14" width="20" height="8" rx="2"/>
                  <line x1="6" y1="6" x2="6.01" y2="6"/>
                  <line x1="6" y1="18" x2="6.01" y2="18"/>
                </svg>`;
          }

          return `
            <label class="deploy-mode-option ${isSelected ? 'selected' : ''}"
                   data-device-id="${device.id}"
                   data-target-id="${targetId}">
              <input type="radio" name="target-${device.id}" value="${targetId}"
                     ${isSelected ? 'checked' : ''}>
              <div class="deploy-mode-radio"></div>
              <div class="deploy-mode-icon">${icon}</div>
              <div class="deploy-mode-info">
                <div class="deploy-mode-name">${escapeHtml(targetName)}</div>
                ${targetDesc ? `<div class="deploy-mode-desc">${escapeHtml(targetDesc)}</div>` : ''}
              </div>
            </label>
          `;
        }).join('')}
      </div>
    </div>
  `;
}

/**
 * Render content based on selected docker target
 * Includes: description, wiring instructions, SSH form for remote
 */
export function renderDockerTargetContent(device) {
  const currentSolution = getCurrentSolution();
  const target = getSelectedTarget(device);

  if (!target) return '';

  const targetSection = target.section || {};
  const description = targetSection.description || '';
  const wiring = targetSection.wiring || {};
  const wiringSteps = getLocalizedField(wiring, 'steps') || [];
  const isRemote = target.id === 'remote';

  let html = '';

  // Wiring instructions
  if (wiringSteps.length > 0) {
    html += `
      <div class="deploy-wiring-section">
        ${wiring.image ? `
          <div class="deploy-wiring-image">
            <img src="${getAssetUrl(currentSolution.id, wiring.image)}" alt="Wiring diagram">
          </div>
        ` : ''}
        <div class="deploy-wiring-steps">
          <ol>
            ${wiringSteps.map(step => `<li>${escapeHtml(step)}</li>`).join('')}
          </ol>
        </div>
      </div>
    `;
  }

  // SSH form for remote target
  if (isRemote) {
    html += renderSSHForm(device, target);
  }

  // Description content
  if (description) {
    html += `
      <div class="deploy-pre-instructions">
        <div class="markdown-content">
          ${description}
        </div>
      </div>
    `;
  }

  return html;
}

/**
 * Render content based on selected recamera_cpp target
 * Shows target-specific description (e.g., model performance info)
 */
export function renderRecameraCppTargetContent(device) {
  const target = getSelectedTarget(device);
  if (!target) return '';

  const targetSection = target.section || {};
  const description = targetSection.description || '';

  if (!description) return '';

  return `
    <div class="deploy-pre-instructions">
      <div class="markdown-content">
        ${description}
      </div>
    </div>
  `;
}

// ============================================
// SSH Form
// ============================================

export function renderSSHForm(device, mode = null) {
  const deviceStates = getDeviceStates();
  const state = deviceStates[device.id] || {};
  const conn = state.connection || {};

  // Get defaults from mode config or device config
  const defaultHost = mode?.ssh?.default_host || device.ssh?.default_host || '';
  const defaultUser = mode?.ssh?.default_user || device.ssh?.default_user || 'root';

  return `
    <div class="deploy-user-inputs">
      <div class="flex gap-4">
        <div class="form-group flex-1">
          <label>${t('deploy.connection.host')}</label>
          <input type="text" id="ssh-host-${device.id}" value="${conn.host || defaultHost}" placeholder="192.168.42.1">
        </div>
        <div class="form-group" style="width: 100px;">
          <label>${t('deploy.connection.port')}</label>
          <input type="number" id="ssh-port-${device.id}" value="${conn.port || 22}">
        </div>
      </div>
      <div class="flex gap-4">
        <div class="form-group flex-1">
          <label>${t('deploy.connection.username')}</label>
          <input type="text" id="ssh-user-${device.id}" value="${conn.username || defaultUser}">
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

// ============================================
// Serial Port Selector
// ============================================

export function renderSerialPortSelector(device) {
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

// ============================================
// Model Selection
// ============================================

/**
 * Render model selection UI for Himax devices
 */
export function renderModelSelection(device) {
  const models = device.details?.firmware?.flash_config?.models || [];
  if (!models.length) return '';

  return `
    <div class="model-selection" id="model-select-${device.id}">
      <label class="input-label">${t('deploy.models.title')}</label>
      <p class="input-desc text-xs text-text-muted mb-2">${t('deploy.models.description')}</p>
      <div class="model-list">
        ${models.map(model => {
          const modelName = getLocalizedField(model, 'name');
          const modelDesc = getLocalizedField(model, 'description');
          return `
            <label class="model-item ${model.required ? 'required' : ''}">
              <input type="checkbox"
                     name="model_${model.id}"
                     value="${model.id}"
                     data-device="${device.id}"
                     ${model.required || model.default ? 'checked' : ''}
                     ${model.required ? 'disabled' : ''}>
              <div class="model-info">
                <span class="model-name">${escapeHtml(modelName)}</span>
                ${model.size_hint ? `<span class="model-size">${model.size_hint}</span>` : ''}
                ${model.required ? `<span class="badge required">${t('deploy.models.required')}</span>` : ''}
              </div>
              ${modelDesc ? `<p class="model-desc">${escapeHtml(modelDesc)}</p>` : ''}
            </label>
          `;
        }).join('')}
      </div>
    </div>
  `;
}

// ============================================
// Preview Inputs
// ============================================

/**
 * Render user inputs for preview step with auto-fill from previous steps
 */
export function renderPreviewInputs(device) {
  const currentSolution = getCurrentSolution();
  const preview = device.preview || {};
  const userInputs = preview.user_inputs || [];

  if (!userInputs.length) return '';

  // Get previous inputs for template resolution
  // Use filtered devices to find current device (supports preset devices)
  const deployment = currentSolution.deployment || {};
  const globalDevices = deployment.devices || [];
  const filteredDevices = getFilteredDevices(globalDevices);
  const currentIndex = filteredDevices.findIndex(d => d.id === device.id);
  const previousInputs = collectPreviousInputs(filteredDevices, currentIndex);

  // Helper to render a single input field
  const renderInput = (input, extraClass = '') => {
    let defaultValue = input.default || '';
    if (input.default_template) {
      defaultValue = resolveTemplate(input.default_template, previousInputs);
    }
    return `
      <div class="form-group ${extraClass}">
        <label>${getLocalizedField(input, 'name')}</label>
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
  };

  // Group inputs by row for compact layout
  const getInput = (id) => userInputs.find(i => i.id === id);
  const rtspUrl = getInput('rtsp_url');
  const mqttBroker = getInput('mqtt_broker');
  const mqttPort = getInput('mqtt_port');
  const mqttTopic = getInput('mqtt_topic');
  const mqttUsername = getInput('mqtt_username');
  const mqttPassword = getInput('mqtt_password');

  // Check if we have the expected MQTT inputs for compact layout
  const hasCompactLayout = mqttBroker && mqttPort;

  if (hasCompactLayout) {
    return `
      <div class="deploy-user-inputs preview-inputs">
        ${rtspUrl ? renderInput(rtspUrl) : ''}
        <div class="flex gap-4">
          ${mqttBroker ? renderInput(mqttBroker, 'flex-1') : ''}
          ${mqttPort ? `<div class="form-group" style="width: 100px;">
            <label>${getLocalizedField(mqttPort, 'name')}</label>
            <input
              type="text"
              id="preview-input-${device.id}-${mqttPort.id}"
              class="preview-input"
              data-device-id="${device.id}"
              data-input-id="${mqttPort.id}"
              placeholder="${mqttPort.placeholder || ''}"
              value="${escapeHtml(mqttPort.default || '')}"
            />
          </div>` : ''}
        </div>
        ${mqttTopic ? renderInput(mqttTopic) : ''}
        ${(mqttUsername || mqttPassword) ? `
          <div class="flex gap-4">
            ${mqttUsername ? renderInput(mqttUsername, 'flex-1') : ''}
            ${mqttPassword ? renderInput(mqttPassword, 'flex-1') : ''}
          </div>
        ` : ''}
      </div>
    `;
  }

  // Fallback: render all inputs vertically
  return `
    <div class="deploy-user-inputs preview-inputs">
      ${userInputs.map(input => renderInput(input)).join('')}
    </div>
  `;
}

// ============================================
// Service Switch Warning
// ============================================

/**
 * Check if a device type requires showing service switch warning
 */
export function shouldShowServiceSwitchWarning(deviceType) {
  return deviceType === 'recamera_nodered' ||
         deviceType === 'recamera_cpp';
}

/**
 * Render service switch warning banner
 */
export function renderServiceSwitchWarning(deviceType) {
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

// ============================================
// Device Type Icons
// ============================================

export function getDeviceTypeIcon(type) {
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
