/**
 * Deploy Module - Public API
 * Re-exports public functions from the deploy module
 */

// State management
export {
  getCurrentSolution,
  getDeviceStates,
  getDeviceState,
  getSelectedDevice,
  getSelectedPresetId,
  cleanupState,
} from './state.js';

// Rendering
export { renderDeployContent } from './renderers.js';

// Event handlers
export { setupEventHandlers, setupSelectedDeviceHandlers } from './handlers.js';

// Device operations
export { detectDevices, refreshSerialPorts, startDeployment, markDeviceComplete } from './devices.js';

// UI updates
export {
  updateSectionUI,
  toggleSection,
  expandNextSection,
  updateChoiceOptionUI,
  updateDockerTargetUI,
} from './ui-updates.js';

// WebSocket/Logs
export { connectLogsWebSocket, addLogToDevice, toggleLogs, refreshAllLogViewers } from './websocket.js';

// Preview
export { initPreviewWindow, handlePreviewButtonClick, markPreviewComplete } from './preview.js';
