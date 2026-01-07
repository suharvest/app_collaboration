/**
 * Deploy Page - Wiki-style Device Deployment
 */

import { solutionsApi, devicesApi, deploymentsApi, LogsWebSocket } from '../modules/api.js';
import { t, getLocalizedField, i18n } from '../modules/i18n.js';
import { router } from '../modules/router.js';
import { toast } from '../modules/toast.js';
import { escapeHtml } from '../modules/utils.js';

let currentSolution = null;
let deviceStates = {};
let logsWsMap = {};

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

      <div class="deploy-sections">
        ${devices.map((device, index) => renderDeploySection(device, index + 1)).join('')}
      </div>

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

function renderDeploySection(device, stepNumber) {
  const state = deviceStates[device.id] || {};
  const name = getLocalizedField(device, 'name');
  const section = device.section || {};
  const sectionTitle = section.title || name;
  const sectionDescription = section.description || '';
  const isManual = device.type === 'manual';
  const isScript = device.type === 'script';
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
        ` : `
          <!-- Auto: Deploy button first, then instructions -->
          <!-- User Inputs (for script type) -->
          ${isScript && state.details?.user_inputs ? renderUserInputs(device, state.details.user_inputs) : ''}

          <!-- Connection Settings (for SSH devices) -->
          ${device.type === 'ssh_deb' ? renderSSHForm(device) : ''}

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

          <!-- Markdown Content from section.description (post-deployment instructions) -->
          ${sectionDescription ? `
            <div class="deploy-post-instructions">
              <div class="deploy-post-title">${t('deploy.postInstructions')}</div>
              <div class="markdown-content">
                ${sectionDescription}
              </div>
            </div>
          ` : ''}
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
              <span class="deploy-logs-count" id="logs-count-${device.id}">${state.logs.length}</span>
            </span>
            <svg class="deploy-section-chevron ${state.logsExpanded ? 'expanded' : ''}"
                 id="logs-chevron-${device.id}"
                 width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="6 9 12 15 18 9"/>
            </svg>
          </div>
          <div class="deploy-logs-panel ${state.logsExpanded ? 'expanded' : ''}" id="logs-panel-${device.id}">
            <div class="deploy-logs-viewer" id="logs-viewer-${device.id}">
              ${state.logs.length === 0 ? `
                <div class="deploy-logs-empty">${t('deploy.logs.empty')}</div>
              ` : state.logs.map(log => renderLogEntry(log)).join('')}
            </div>
          </div>
        </div>
      </div>
    </div>
  `;
}

function renderUserInputs(device, inputs) {
  if (!inputs || !inputs.length) return '';

  return `
    <div class="deploy-user-inputs">
      ${inputs.map(input => `
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
      `).join('')}
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

async function refreshSerialPorts() {
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
          select.innerHTML = `<option value="">${t('deploy.connection.selectPort')}...</option>`;
          ports.forEach(port => {
            const option = document.createElement('option');
            option.value = port.device;
            option.textContent = `${port.device} - ${port.description || 'Unknown'}`;
            select.appendChild(option);
          });
          if (currentValue) select.value = currentValue;
        }
      }
    });
  } catch (error) {
    console.error('Failed to refresh ports:', error);
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
  state.logs.push({ timestamp, level, message });

  const viewer = document.getElementById(`logs-viewer-${deviceId}`);
  if (viewer) {
    const empty = viewer.querySelector('.deploy-logs-empty');
    if (empty) empty.remove();

    const entry = document.createElement('div');
    entry.className = `deploy-log-entry ${level}`;
    entry.innerHTML = `<span class="time">${timestamp}</span><span class="msg">${escapeHtml(message)}</span>`;
    viewer.appendChild(entry);
    viewer.scrollTop = viewer.scrollHeight;
  }

  // Update count
  const logsCount = document.getElementById(`logs-count-${deviceId}`);
  if (logsCount) {
    logsCount.textContent = state.logs.length;
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

function toggleLogs(deviceId, forceExpand = null) {
  const state = deviceStates[deviceId];
  if (!state) return;

  state.logsExpanded = forceExpand !== null ? forceExpand : !state.logsExpanded;

  const panel = document.getElementById(`logs-panel-${deviceId}`);
  const chevron = document.getElementById(`logs-chevron-${deviceId}`);

  if (panel) panel.classList.toggle('expanded', state.logsExpanded);
  if (chevron) chevron.classList.toggle('expanded', state.logsExpanded);
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

  const params = {
    solution_id: currentSolution.id,
    device_id: deviceId,
  };

  // Collect user inputs
  if (device.type === 'script') {
    const inputs = state.details?.user_inputs || [];
    params.user_inputs = {};
    inputs.forEach(input => {
      const el = document.getElementById(`input-${deviceId}-${input.id}`);
      if (el) params.user_inputs[input.id] = el.value;
    });
  }

  // Add connection info based on device type
  if (device.type === 'esp32_usb') {
    const select = document.getElementById(`serial-port-${deviceId}`);
    params.port = select?.value || state.port;
  } else if (device.type === 'ssh_deb') {
    params.connection = {
      host: document.getElementById(`ssh-host-${deviceId}`)?.value,
      port: parseInt(document.getElementById(`ssh-port-${deviceId}`)?.value || '22'),
      username: document.getElementById(`ssh-user-${deviceId}`)?.value,
      password: document.getElementById(`ssh-pass-${deviceId}`)?.value,
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

  ws.on('status', (data) => {
    const state = deviceStates[deviceId];
    if (state) {
      state.deploymentStatus = data.status;
      state.progress = data.progress || 0;
      updateSectionUI(deviceId);

      if (data.status === 'completed') {
        addLogToDevice(deviceId, 'success', t('deploy.status.completed'));
        toast.success(`${getDeviceById(deviceId)?.name}: ${t('deploy.status.completed')}`);

        // Auto-expand next section
        expandNextSection(deviceId);
      } else if (data.status === 'failed') {
        addLogToDevice(deviceId, 'error', t('deploy.status.failed'));
        toast.error(`${getDeviceById(deviceId)?.name}: ${t('deploy.status.failed')}`);
      }
    }
  });

  ws.on('error', () => {
    addLogToDevice(deviceId, 'error', 'Connection error');
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

function setupEventHandlers(container) {
  // Back button
  container.querySelector('#back-btn')?.addEventListener('click', () => {
    cleanupDeployPage();
    router.navigate('solution', { id: currentSolution.id });
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
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      refreshSerialPorts();
    });
  });

  // Test SSH connection
  container.querySelectorAll('[id^="test-ssh-"]').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const deviceId = btn.dataset.deviceId;
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
}

export function cleanupDeployPage() {
  Object.values(logsWsMap).forEach(ws => ws?.disconnect());
  logsWsMap = {};
}

// Re-render when language changes
i18n.onLocaleChange(() => {
  if (router.currentRoute === 'deploy' && currentSolution) {
    renderDeployPage({ id: currentSolution.id });
  }
});
