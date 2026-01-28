/**
 * Deploy Page - Device Detection & Deployment
 * Handles device detection, serial ports, and deployment actions
 */

import { t } from '../../modules/i18n.js';
import { devicesApi, deploymentsApi } from '../../modules/api.js';
import { toast } from '../../modules/toast.js';
import {
  getCurrentSolution,
  getDeviceState,
  getDeviceStates,
  getSelectedPresetId,
} from './state.js';
import { getDeviceById, getSelectedTarget, getSelectedModels, getFilteredDevices } from './utils.js';
import { updateSectionUI, toggleSection } from './ui-updates.js';
import { addLogToDevice, toggleLogs, connectLogsWebSocket } from './websocket.js';

// ============================================
// Device Detection
// ============================================

/**
 * Auto-detect devices for the current solution
 */
export async function detectDevices() {
  const currentSolution = getCurrentSolution();
  const deviceStates = getDeviceStates();

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

// ============================================
// Serial Port Management
// ============================================

/**
 * Refresh available serial ports
 */
export async function refreshSerialPorts(clickedBtn = null) {
  const currentSolution = getCurrentSolution();
  const deviceStates = getDeviceStates();

  // Add spinning animation to button
  if (clickedBtn) {
    clickedBtn.classList.add('spinning');
    clickedBtn.disabled = true;
  }

  try {
    console.log('[SerialPorts] Fetching ports...');
    const result = await devicesApi.getPorts();
    console.log('[SerialPorts] API result:', result);
    const ports = result.ports || [];
    console.log('[SerialPorts] Found ports:', ports.length, ports);

    // Get devices from current preset or fallback to deployment.devices
    const deployment = currentSolution.deployment || {};
    const allDevices = deployment.devices || [];
    const devices = getFilteredDevices(allDevices);
    console.log('[SerialPorts] Devices to update:', devices.map(d => ({ id: d.id, type: d.type })));

    devices.forEach(device => {
      console.log(`[SerialPorts] Checking device ${device.id}, type: ${device.type}`);
      if (device.type === 'esp32_usb' || device.type === 'himax_usb') {
        const select = document.getElementById(`serial-port-${device.id}`);
        console.log(`[SerialPorts] Select element for ${device.id}:`, select);
        if (select) {
          const currentValue = select.value;
          const state = deviceStates[device.id] || {};
          // Check if we have a detected port from device detection
          const detectedPort = state?.details?.port;

          select.innerHTML = `<option value="">${t('deploy.connection.selectPort')}...</option>`;
          ports.forEach(port => {
            const option = document.createElement('option');
            option.value = port.device;
            option.textContent = `${port.device} - ${port.description || 'Unknown'}`;
            select.appendChild(option);
          });

          // Auto-select logic:
          // 1. Prefer detected port from device detection
          // 2. Try VID/PID matching for known devices
          // 3. Fall back to single available port
          // 4. Keep current value

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

          // Find ports by VID/PID for known USB-serial chips
          const findPortByVidPid = (vid, pid) => {
            const matches = ports.filter(p =>
              p.vid?.toLowerCase() === vid.toLowerCase() &&
              p.pid?.toLowerCase() === pid.toLowerCase()
            );
            // If multiple matches, prefer the one with higher COM number (Windows) or ending with higher number
            if (matches.length > 0) {
              matches.sort((a, b) => {
                const numA = parseInt(a.device.replace(/\D/g, '')) || 0;
                const numB = parseInt(b.device.replace(/\D/g, '')) || 0;
                return numB - numA; // Higher number first
              });
              return matches[0].device;
            }
            return null;
          };

          let selectedPort = null;

          // 1. Try detected port first
          selectedPort = findMatchingPort(detectedPort);

          // 2. Try VID/PID + description matching for ESP32 devices (WCH CH342/CH340 chip)
          if (!selectedPort && device.type === 'esp32_usb') {
            // CH342 dual-serial: SERIAL-B = ESP32, SERIAL-A = Himax
            // macOS: wchusbserial = ESP32
            const ch342Ports = ports.filter(p =>
              p.vid?.toLowerCase() === '0x1a86' &&
              (p.pid?.toLowerCase() === '0x55d2' || p.pid?.toLowerCase() === '0x7523')
            );
            // Prefer SERIAL-B (Windows) or wchusbserial (macOS)
            const esp32Port = ch342Ports.find(p =>
              p.description?.toUpperCase().includes('SERIAL-B') ||
              p.device?.toLowerCase().includes('wchusbserial')
            ) || ch342Ports[0];
            selectedPort = esp32Port?.device;
            console.log(`[SerialPorts] ESP32 match: ${selectedPort}`);
          }

          // 3. Try VID/PID + description matching for Himax devices
          if (!selectedPort && device.type === 'himax_usb') {
            // CH342 dual-serial: SERIAL-A = Himax, SERIAL-B = ESP32
            // macOS: usbmodem = Himax
            const ch342Ports = ports.filter(p =>
              p.vid?.toLowerCase() === '0x1a86' && p.pid?.toLowerCase() === '0x55d2'
            );
            // Prefer SERIAL-A (Windows) or usbmodem (macOS)
            const himaxPort = ch342Ports.find(p =>
              p.description?.toUpperCase().includes('SERIAL-A') ||
              p.device?.toLowerCase().includes('usbmodem')
            ) || ch342Ports[0];
            selectedPort = himaxPort?.device;
            console.log(`[SerialPorts] Himax match: ${selectedPort}`);
          }

          // 4. Fall back to single USB port (filter out Bluetooth and system ports)
          if (!selectedPort) {
            const usbPorts = ports.filter(p => p.vid && p.pid); // Only USB devices have VID/PID
            if (usbPorts.length === 1) {
              selectedPort = usbPorts[0].device;
              console.log(`[SerialPorts] Single USB port: ${selectedPort}`);
            }
          }

          // 5. Keep current value
          if (!selectedPort && currentValue) {
            selectedPort = currentValue;
          }

          if (selectedPort) {
            select.value = selectedPort;
            if (!deviceStates[device.id]) deviceStates[device.id] = {};
            deviceStates[device.id].port = selectedPort;
            deviceStates[device.id].detected = true;
            updateSectionUI(device.id);
            console.log(`[SerialPorts] Auto-selected: ${selectedPort}`);
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

// ============================================
// SSH Connection Test
// ============================================

/**
 * Test SSH connection for a device
 */
export async function testSSHConnection(deviceId, btn) {
  const deviceStates = getDeviceStates();
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

// ============================================
// Deployment
// ============================================

/**
 * Start deployment for a device
 */
export async function startDeployment(deviceId) {
  const device = getDeviceById(deviceId);
  if (!device) return;

  const currentSolution = getCurrentSolution();
  const state = getDeviceState(deviceId);
  state.deploymentStatus = 'running';
  state.logs = [];
  updateSectionUI(deviceId);

  // Expand section and logs
  if (!state.sectionExpanded) toggleSection(deviceId);
  toggleLogs(deviceId, true);

  addLogToDevice(deviceId, 'info', t('deploy.logs.starting'));

  // Determine effective device type (handle docker_deploy with targets)
  let effectiveType = device.type;
  let selectedTarget = null;

  if (device.targets) {
    selectedTarget = getSelectedTarget(device);
    if (device.type === 'docker_deploy') {
      // Map target id to deployment type
      effectiveType = selectedTarget?.id === 'remote' ? 'docker_remote' : 'docker_local';
    }
  }

  // Build params in the format expected by backend
  const params = {
    solution_id: currentSolution.id,
    preset_id: getSelectedPresetId(),  // Include preset ID for preset-based solutions
    selected_devices: [deviceId],
    device_connections: {},
    options: {},
  };

  // If using docker_deploy with targets, specify the selected target and config file
  if (selectedTarget) {
    params.options.deploy_target = selectedTarget.id;
    params.options.config_file = selectedTarget.config_file;
  }

  // Collect user inputs
  if (device.type === 'script') {
    const inputs = state.details?.user_inputs || [];
    params.options.user_inputs = {};
    inputs.forEach(input => {
      const el = document.getElementById(`input-${deviceId}-${input.id}`);
      if (el) params.options.user_inputs[input.id] = el.value;
    });
  }

  // Add connection info based on effective device type
  if (effectiveType === 'esp32_usb') {
    const select = document.getElementById(`serial-port-${deviceId}`);
    params.device_connections[deviceId] = {
      port: select?.value || state.port,
    };
  } else if (effectiveType === 'himax_usb') {
    const select = document.getElementById(`serial-port-${deviceId}`);
    const selectedModels = getSelectedModels(deviceId);
    params.device_connections[deviceId] = {
      port: select?.value || state.port,
      selected_models: selectedModels,
    };
  } else if (effectiveType === 'ssh_deb' || effectiveType === 'docker_remote') {
    params.device_connections[deviceId] = {
      host: document.getElementById(`ssh-host-${deviceId}`)?.value,
      port: parseInt(document.getElementById(`ssh-port-${deviceId}`)?.value || '22'),
      username: document.getElementById(`ssh-user-${deviceId}`)?.value,
      password: document.getElementById(`ssh-pass-${deviceId}`)?.value,
    };
  } else if (effectiveType === 'recamera_nodered') {
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

// ============================================
// Device Completion
// ============================================

/**
 * Mark a device as complete (for manual steps)
 * Note: expandNextSection is called from handlers.js to avoid circular dependency
 */
export function markDeviceComplete(deviceId, expandNext = null) {
  const state = getDeviceState(deviceId);
  if (state) {
    state.deploymentStatus = 'completed';
    updateSectionUI(deviceId);
    toast.success(t('deploy.status.completed'));

    // Call expandNext if provided (injected from handlers.js)
    if (expandNext) {
      expandNext(deviceId);
    }
  }
}
