/**
 * Deploy Page - State Management
 * Centralized state for the deployment page
 */

// Current solution data
let currentSolution = null;

// Device states: { deviceId: { status, detected, connection, logs, ... } }
let deviceStates = {};

// WebSocket connections for logs: { deviceId: LogsWebSocket }
let logsWsMap = {};

// Selected device for single_choice mode
let selectedDevice = null;

// Toggle for detailed vs summary logs
let showDetailedLogs = false;

// Preview window instances: { deviceId: PreviewWindow }
let previewInstances = {};

// Device group selections: { groupId: deviceRef }
let deviceGroupSelections = {};

// Selected preset ID for Level 1 sections
let selectedPresetId = null;

// ============================================
// Getters
// ============================================

export function getCurrentSolution() {
  return currentSolution;
}

export function getDeviceStates() {
  return deviceStates;
}

export function getDeviceState(deviceId) {
  return deviceStates[deviceId];
}

export function getLogsWsMap() {
  return logsWsMap;
}

export function getSelectedDevice() {
  return selectedDevice;
}

export function getShowDetailedLogs() {
  return showDetailedLogs;
}

export function getPreviewInstances() {
  return previewInstances;
}

export function getPreviewInstance(deviceId) {
  return previewInstances[deviceId];
}

export function getDeviceGroupSelections() {
  return deviceGroupSelections;
}

export function getDeviceGroupSelection(groupId) {
  return deviceGroupSelections[groupId];
}

export function getSelectedPresetId() {
  return selectedPresetId;
}

// ============================================
// Setters
// ============================================

export function setCurrentSolution(solution) {
  currentSolution = solution;
}

export function setDeviceStates(states) {
  deviceStates = states;
}

export function setDeviceState(deviceId, state) {
  deviceStates[deviceId] = state;
}

export function updateDeviceState(deviceId, updates) {
  if (deviceStates[deviceId]) {
    Object.assign(deviceStates[deviceId], updates);
  }
}

export function setLogsWs(deviceId, ws) {
  logsWsMap[deviceId] = ws;
}

export function getLogsWs(deviceId) {
  return logsWsMap[deviceId];
}

export function setSelectedDevice(deviceId) {
  selectedDevice = deviceId;
}

export function setShowDetailedLogs(value) {
  showDetailedLogs = value;
}

export function setPreviewInstance(deviceId, instance) {
  previewInstances[deviceId] = instance;
}

export function setDeviceGroupSelection(groupId, deviceRef) {
  deviceGroupSelections[groupId] = deviceRef;
}

export function setSelectedPresetId(presetId) {
  selectedPresetId = presetId;
}

// ============================================
// State Initialization
// ============================================

/**
 * Create initial device state for a device
 */
export function createInitialDeviceState(device, index) {
  // For docker_deploy type: find default target (local/remote)
  let defaultTarget = 'local';
  if (device.targets) {
    const targetEntries = Object.entries(device.targets);
    const defaultEntry = targetEntries.find(([_, t]) => t.default);
    defaultTarget = defaultEntry ? defaultEntry[0] : targetEntries[0]?.[0] || 'local';
  }

  return {
    status: 'pending',
    detected: false,
    connection: null,
    deploymentStatus: null,
    progress: 0,
    logs: [],
    logsExpanded: false,
    sectionExpanded: index === 0, // First section expanded
    selectedTarget: (device.type === 'docker_deploy' || (device.type === 'recamera_cpp' && device.targets)) ? defaultTarget : null,
  };
}

/**
 * Reset all state for a new solution
 */
export function resetState() {
  deviceStates = {};
  selectedDevice = null;
  deviceGroupSelections = {};
  selectedPresetId = null;
}

/**
 * Cleanup all state when leaving the page
 */
export function cleanupState() {
  // Disconnect all WebSockets
  Object.values(logsWsMap).forEach(ws => ws?.disconnect());
  logsWsMap = {};

  // Reset selection state
  selectedDevice = null;
  selectedPresetId = null;

  // Cleanup preview instances
  Object.values(previewInstances).forEach(preview => preview?.destroy());
  previewInstances = {};
}
