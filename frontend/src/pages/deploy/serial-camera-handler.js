/**
 * Serial Camera Handler - Connects SerialCameraCanvas and FaceDatabasePanel
 *
 * Manages session lifecycle and wires up the camera + panel components
 * for serial_camera type deployment steps.
 *
 * Supports three connection modes:
 * - Both ports: camera preview + face DB (full functionality)
 * - Camera only: preview without face DB
 * - CRUD only: face DB without preview (enrollment disabled)
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
 * Creates canvas and panel instances, wires up connect buttons
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
  setSerialCameraInstance(deviceId, { canvas, panel, sessionId: null, crudSessionId: null });

  // Wire camera connect button
  const connectBtn = cameraContainer.querySelector('#sc-connect-btn');
  if (connectBtn) {
    connectBtn.addEventListener('click', () => handleSerialCameraButtonClick(deviceId));
  }

  // Wire face DB connect button
  if (panel) {
    const fdbConnectBtn = panel.container.querySelector('#fdb-connect-btn');
    if (fdbConnectBtn) {
      fdbConnectBtn.addEventListener('click', () => handleFaceDatabaseButtonClick(deviceId));
    }
  }
}

/**
 * Handle camera connect/disconnect button click
 */
export async function handleSerialCameraButtonClick(deviceId) {
  const instance = getSerialCameraInstance(deviceId);
  if (!instance) return;

  if (instance.sessionId) {
    await disconnectSerialCamera(deviceId);
  } else {
    await connectSerialCamera(deviceId);
  }
}

/**
 * Handle face database connect/disconnect button click
 */
async function handleFaceDatabaseButtonClick(deviceId) {
  const instance = getSerialCameraInstance(deviceId);
  if (!instance || !instance.panel) return;

  if (instance.crudSessionId && !instance.sessionId) {
    // Disconnect CRUD-only session
    await disconnectFaceDatabase(deviceId);
  } else if (!instance.sessionId) {
    // No camera session — create CRUD-only session
    await connectFaceDatabase(deviceId);
  }
  // If camera session exists, the panel is already using that session
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
    // Don't block camera connect if CRUD port is missing
  }

  // If there's an existing CRUD-only session, close it first
  if (instance.crudSessionId) {
    try {
      await serialCameraApi.deleteSession(instance.crudSessionId);
    } catch { /* ignore */ }
    instance.crudSessionId = null;
  }

  // Show connecting state
  _updateConnectButton(deviceId, false, true);

  try {
    const result = await serialCameraApi.createSession(
      cameraPort, cameraBaudrate, crudPort, crudBaudrate
    );

    instance.sessionId = result.session_id;

    // Connect camera canvas WebSocket
    instance.canvas.connect(result.session_id);

    // Connect face database panel if CRUD port was included
    if (instance.panel) {
      if (crudPort) {
        instance.panel.setSessionId(result.session_id);
      }
      instance.panel.setCameraAvailable(true);
    }

    _updateConnectButton(deviceId, true);

  } catch (e) {
    _updateConnectButton(deviceId, false);
    toast.error(`Connection failed: ${e.message}`);
  }
}

/**
 * Connect face database only (CRUD-only session, no camera)
 */
async function connectFaceDatabase(deviceId) {
  const device = getDeviceById(deviceId);
  const instance = getSerialCameraInstance(deviceId);
  if (!device || !instance || !instance.panel) return;

  const serialCamera = device.serial_camera || {};
  const deviceStates = getDeviceStates();

  // Resolve CRUD port
  const panels = serialCamera.panels || [];
  const faceDbConfig = panels.find(p => p.type === 'face_database');
  if (!faceDbConfig?.database_port?.port_from_device) return;

  const dbRef = faceDbConfig.database_port.port_from_device;
  const crudPort = deviceStates[dbRef]?.port;
  const crudBaudrate = faceDbConfig.database_port?.baudrate || 115200;

  if (!crudPort) {
    toast.error(t('serialCamera.crudPortMissing', { step: dbRef }));
    return;
  }

  // Show connecting state
  const fdbConnectBtn = instance.panel.container.querySelector('#fdb-connect-btn');
  if (fdbConnectBtn) {
    fdbConnectBtn.textContent = t('faceDatabase.connecting');
    fdbConnectBtn.className = 'btn btn-sm btn-secondary';
    fdbConnectBtn.disabled = true;
  }

  try {
    const result = await serialCameraApi.createSession(
      null, 921600, crudPort, crudBaudrate
    );

    instance.crudSessionId = result.session_id;
    instance.panel.setSessionId(result.session_id);
    // No camera available — enrollment stays disabled
    instance.panel.setCameraAvailable(false);

    // Update the connect button in the panel to show "disconnect"
    if (fdbConnectBtn) {
      fdbConnectBtn.textContent = t('faceDatabase.disconnect');
      fdbConnectBtn.className = 'btn btn-sm btn-secondary';
      fdbConnectBtn.disabled = false;
    }

  } catch (e) {
    // Revert button to connect state
    if (fdbConnectBtn) {
      fdbConnectBtn.textContent = t('faceDatabase.connect');
      fdbConnectBtn.className = 'btn btn-sm btn-primary';
      fdbConnectBtn.disabled = false;
    }
    toast.error(`Database connection failed: ${e.message}`);
  }
}

/**
 * Disconnect face database CRUD-only session
 */
async function disconnectFaceDatabase(deviceId) {
  const instance = getSerialCameraInstance(deviceId);
  if (!instance) return;

  if (instance.crudSessionId) {
    try {
      await serialCameraApi.deleteSession(instance.crudSessionId);
    } catch { /* ignore */ }
    instance.crudSessionId = null;
  }

  if (instance.panel) {
    instance.panel.setSessionId(null);
    instance.panel.setCameraAvailable(false);

    const fdbConnectBtn = instance.panel.container.querySelector('#fdb-connect-btn');
    if (fdbConnectBtn) {
      fdbConnectBtn.textContent = t('faceDatabase.connect');
      fdbConnectBtn.className = 'btn btn-sm btn-primary';
    }
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

  if (instance.canvas) {
    instance.canvas.disconnect();
  }

  // Reset panel state
  if (instance.panel) {
    instance.panel.setSessionId(null);
    instance.panel.setCameraAvailable(false);
  }

  instance.sessionId = null;
  _updateConnectButton(deviceId, false);
}

/**
 * Update camera connect button text
 */
function _updateConnectButton(deviceId, connected, connecting = false) {
  const container = document.getElementById(`serial-camera-container-${deviceId}`);
  if (!container) return;

  const btn = container.querySelector('#sc-connect-btn');
  if (btn) {
    if (connecting) {
      btn.textContent = t('serialCamera.connecting');
      btn.className = 'btn btn-sm btn-secondary serial-camera-connect-btn';
      btn.disabled = true;
    } else {
      btn.textContent = connected ? t('serialCamera.disconnect') : t('serialCamera.connect');
      btn.className = connected
        ? 'btn btn-sm btn-secondary serial-camera-connect-btn'
        : 'btn btn-sm btn-primary serial-camera-connect-btn';
      btn.disabled = false;
    }
  }
}
