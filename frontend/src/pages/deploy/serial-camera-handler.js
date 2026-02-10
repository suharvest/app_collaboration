/**
 * Serial Camera Handler - Connects SerialCameraCanvas and FaceDatabasePanel
 *
 * Manages session lifecycle and wires up the camera + panel components
 * for serial_camera type deployment steps.
 */

import { t } from '../../modules/i18n.js';
import { serialCameraApi } from '../../modules/api.js';
import { SerialCameraCanvas } from '../../modules/serial-camera.js';
import { FaceDatabasePanel } from './face-database-panel.js';
import { toast } from '../../modules/toast.js';
import {
  getDeviceStates,
  getSerialCameraInstance,
  setSerialCameraInstance,
} from './state.js';
import { getDeviceById } from './utils.js';

/**
 * Initialize serial camera step UI
 * Creates canvas and panel instances, wires up connect button
 */
export function initSerialCameraStep(deviceId) {
  const device = getDeviceById(deviceId);
  if (!device || device.type !== 'serial_camera') return;

  const serialCamera = device.serial_camera || {};
  const display = serialCamera.display || {};

  // Create camera canvas
  const cameraContainer = document.getElementById(`serial-camera-container-${deviceId}`);
  if (!cameraContainer) return;

  const canvas = new SerialCameraCanvas(cameraContainer, {
    aspectRatio: display.aspect_ratio || '4:3',
    showLandmarks: display.show_landmarks !== false,
    showStats: display.show_stats !== false,
  });

  // Create face database panel if configured
  let panel = null;
  const panels = serialCamera.panels || [];
  const faceDbConfig = panels.find(p => p.type === 'face_database');

  if (faceDbConfig) {
    const panelContainer = document.getElementById(`serial-camera-panel-${deviceId}`);
    if (panelContainer) {
      panel = new FaceDatabasePanel(panelContainer);

      // Wire frame updates from camera to panel (for enrollment progress)
      canvas.onFrame((data) => panel.onFrameUpdate(data));
    }
  }

  // Store instances
  setSerialCameraInstance(deviceId, { canvas, panel, sessionId: null });

  // Wire connect button
  const connectBtn = cameraContainer.querySelector('#sc-connect-btn');
  if (connectBtn) {
    connectBtn.addEventListener('click', () => handleSerialCameraButtonClick(deviceId));
  }
}

/**
 * Handle connect/disconnect button click
 */
export async function handleSerialCameraButtonClick(deviceId) {
  const instance = getSerialCameraInstance(deviceId);
  if (!instance) return;

  if (instance.sessionId) {
    // Disconnect
    await disconnectSerialCamera(deviceId);
  } else {
    // Connect
    await connectSerialCamera(deviceId);
  }
}

/**
 * Connect: resolve ports from previous steps, create session, connect WebSocket
 */
async function connectSerialCamera(deviceId) {
  const device = getDeviceById(deviceId);
  const instance = getSerialCameraInstance(deviceId);
  if (!device || !instance) return;

  const serialCamera = device.serial_camera || {};
  const deviceStates = getDeviceStates();

  // Resolve camera port from referenced device
  const cameraRef = serialCamera.camera_port?.port_from_device;
  const cameraPort = cameraRef ? deviceStates[cameraRef]?.port : null;
  const cameraBaudrate = serialCamera.camera_port?.baudrate || 921600;

  if (!cameraPort) {
    toast.error(t('serialCamera.portMissing', { step: cameraRef || '?' }));
    return;
  }

  // Resolve CRUD port from panel config
  let crudPort = null;
  let crudBaudrate = 115200;
  const panels = serialCamera.panels || [];
  const faceDbConfig = panels.find(p => p.type === 'face_database');
  if (faceDbConfig?.database_port?.port_from_device) {
    const dbRef = faceDbConfig.database_port.port_from_device;
    crudPort = deviceStates[dbRef]?.port;
    crudBaudrate = faceDbConfig.database_port?.baudrate || 115200;

    if (!crudPort) {
      toast.error(t('serialCamera.portMissing', { step: dbRef }));
      return;
    }
  }

  try {
    // Create backend session
    const result = await serialCameraApi.createSession(
      cameraPort, cameraBaudrate, crudPort, crudBaudrate
    );

    instance.sessionId = result.session_id;

    // Connect camera canvas WebSocket
    instance.canvas.connect(result.session_id);

    // Connect face database panel
    if (instance.panel) {
      instance.panel.setSessionId(result.session_id);
    }

    // Update button text
    _updateConnectButton(deviceId, true);

  } catch (e) {
    toast.error(`Connection failed: ${e.message}`);
  }
}

/**
 * Disconnect: close session, disconnect WebSocket
 */
async function disconnectSerialCamera(deviceId) {
  const instance = getSerialCameraInstance(deviceId);
  if (!instance) return;

  if (instance.sessionId) {
    try {
      await serialCameraApi.deleteSession(instance.sessionId);
    } catch {
      // ignore cleanup errors
    }
  }

  instance.canvas.disconnect();
  instance.sessionId = null;
  _updateConnectButton(deviceId, false);
}

/**
 * Update connect button text
 */
function _updateConnectButton(deviceId, connected) {
  const container = document.getElementById(`serial-camera-container-${deviceId}`);
  if (!container) return;

  const btn = container.querySelector('#sc-connect-btn');
  if (btn) {
    btn.textContent = connected ? t('serialCamera.disconnect') : t('serialCamera.connect');
    btn.className = connected
      ? 'btn btn-sm btn-secondary serial-camera-connect-btn'
      : 'btn btn-sm btn-primary serial-camera-connect-btn';
  }
}
