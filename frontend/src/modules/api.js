/**
 * API Module - Backend Communication
 *
 * Organized by business domain for better maintainability.
 * Reference: sensecraftAppStore/website-device-management-platform/src/config/envApi.js
 */

// ============================================
// Configuration
// ============================================

// Detect Tauri environment
const isTauri = window.__TAURI__ !== undefined;

// Backend port - will be set dynamically in Tauri mode
let backendPort = null;

// Initialize backend port for Tauri mode
async function initBackendPort() {
  if (!isTauri) return;

  // First check if already injected
  if (window.__BACKEND_PORT__) {
    backendPort = window.__BACKEND_PORT__;
    return;
  }

  // Try to get port via Tauri invoke command (Tauri 2 API)
  try {
    const invoke = window.__TAURI__?.core?.invoke;
    if (invoke) {
      const port = await invoke('get_backend_port');
      if (port > 0) {
        backendPort = port;
        window.__BACKEND_PORT__ = port;
        return;
      }
    }
  } catch (e) {
    console.warn('Failed to get backend port via invoke:', e);
  }

  // Wait for port to be injected (up to 5 seconds)
  for (let i = 0; i < 50; i++) {
    if (window.__BACKEND_PORT__) {
      backendPort = window.__BACKEND_PORT__;
      return;
    }
    await new Promise(r => setTimeout(r, 100));
  }

  // Fallback to default
  console.warn('Backend port not available, using default 3260');
  backendPort = 3260;
}

// Get the current backend port (sync version, may return cached or default)
function getBackendPort() {
  if (backendPort) return backendPort;
  if (window.__BACKEND_PORT__) {
    backendPort = window.__BACKEND_PORT__;
    return backendPort;
  }
  return 3260; // fallback
}

// API base URL - computed dynamically for Tauri
function getApiBaseUrl() {
  if (isTauri) {
    return `http://127.0.0.1:${getBackendPort()}/api`;
  }
  return '/api';
}

// Legacy constant for backwards compatibility (initialized on first use)
let API_BASE = '/api';
if (isTauri) {
  // Initial value, will be updated when port is known
  API_BASE = `http://127.0.0.1:${getBackendPort()}/api`;
}

// Export for use in WebSocket connections
export function getApiBase() {
  if (isTauri) {
    return `http://127.0.0.1:${getBackendPort()}/api`;
  }
  return '/api';
}

export function getWsBase() {
  if (isTauri) {
    return `ws://127.0.0.1:${getBackendPort()}`;
  }
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}`;
}

// Backend ready promise for Tauri mode
let backendReadyPromise = null;
let backendReady = !isTauri; // Non-Tauri is always ready

// Initialize on module load
if (isTauri) {
  backendReadyPromise = initBackendPort().then(() => {
    API_BASE = getApiBaseUrl();
    backendReady = true;
  });
}

// Wait for backend to be ready (for use in app initialization)
export async function waitForBackendReady() {
  if (!isTauri) return true;
  if (backendReady) return true;
  if (backendReadyPromise) {
    await backendReadyPromise;
  }

  // Wait for backend health check to pass
  const healthUrl = `http://127.0.0.1:${getBackendPort()}/api/health`;
  for (let i = 0; i < 50; i++) {  // Up to 10 seconds
    try {
      const response = await fetch(healthUrl, { method: 'GET' });
      if (response.ok) {
        return true;
      }
    } catch (e) {
      // Backend not ready yet
    }
    await new Promise(r => setTimeout(r, 200));
  }

  console.warn('Backend health check timeout, proceeding anyway');
  return backendReady;
}

// Request timeout in milliseconds
const REQUEST_TIMEOUT = 30000;

// ============================================
// Error Handling
// ============================================

class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.status = status;
    this.data = data;
    this.name = 'ApiError';
  }
}

// ============================================
// Base Request Function
// ============================================

async function request(endpoint, options = {}) {
  // Use dynamic API base to handle Tauri port initialization
  const apiBase = isTauri ? getApiBaseUrl() : '/api';
  const url = `${apiBase}${endpoint}`;

  const config = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  };

  // Add timeout support
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), options.timeout || REQUEST_TIMEOUT);
  config.signal = controller.signal;

  try {
    const response = await fetch(url, config);
    clearTimeout(timeoutId);

    if (!response.ok) {
      let errorData;
      try {
        errorData = await response.json();
      } catch {
        errorData = { detail: response.statusText };
      }
      throw new ApiError(
        errorData.detail || 'Request failed',
        response.status,
        errorData
      );
    }

    // Handle empty responses
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      return await response.json();
    }
    return await response.text();
  } catch (error) {
    clearTimeout(timeoutId);
    if (error.name === 'AbortError') {
      throw new ApiError('Request timeout', 408, null);
    }
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(error.message, 0, null);
  }
}

// ============================================
// Solutions API
// Solution catalog and detail management
// ============================================

export const solutionsApi = {
  /**
   * Get list of all solutions
   * @param {string} lang - Language code ('en' or 'zh')
   */
  list(lang = 'en') {
    return request(`/solutions?lang=${lang}`);
  },

  /**
   * Get solution detail by ID
   * @param {string} id - Solution ID
   * @param {string} lang - Language code
   */
  get(id, lang = 'en') {
    return request(`/solutions/${id}?lang=${lang}`);
  },

  /**
   * Get deployment configuration for a solution
   * @param {string} id - Solution ID
   * @param {string} lang - Language code
   */
  getDeployment(id, lang = 'en') {
    return request(`/solutions/${id}/deployment?lang=${lang}`);
  },

  /**
   * Get markdown/text content file
   * @param {string} id - Solution ID
   * @param {string} path - Content file path
   */
  getContent(id, path) {
    return request(`/solutions/${id}/content/${path}`);
  },

  /**
   * Get device group section content with template variables replaced
   * @param {string} id - Solution ID
   * @param {string} groupId - Device group ID
   * @param {string} selectedDevice - Selected device ref
   * @param {string} lang - Language code
   * @param {string} presetId - Optional preset ID
   */
  getDeviceGroupSection(id, groupId, selectedDevice, lang = 'en', presetId = null) {
    let url = `/solutions/${id}/device-group/${groupId}/section?selected_device=${encodeURIComponent(selectedDevice)}&lang=${lang}`;
    if (presetId) {
      url += `&preset_id=${encodeURIComponent(presetId)}`;
    }
    return request(url);
  },

  /**
   * Get preset section content
   * @param {string} id - Solution ID
   * @param {string} presetId - Preset ID
   * @param {string} lang - Language code
   */
  getPresetSection(id, presetId, lang = 'en') {
    return request(`/solutions/${id}/preset/${presetId}/section?lang=${lang}`);
  },

  // ============================================
  // Solution Management Methods
  // ============================================

  /**
   * Create a new solution
   * @param {Object} data - Solution data
   * @param {string} data.id - Solution ID (lowercase letters, numbers, underscore)
   * @param {string} data.name - English name
   * @param {string} data.name_zh - Chinese name (optional)
   * @param {string} data.summary - English summary
   * @param {string} data.summary_zh - Chinese summary (optional)
   * @param {string} data.category - Category (default: "general")
   * @param {string} data.difficulty - Difficulty level (default: "beginner")
   * @param {string} data.estimated_time - Estimated time (default: "30min")
   */
  create(data) {
    return request('/solutions/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  /**
   * Update an existing solution
   * @param {string} id - Solution ID
   * @param {Object} data - Fields to update
   */
  update(id, data) {
    return request(`/solutions/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  /**
   * Delete a solution
   * @param {string} id - Solution ID
   * @param {boolean} permanent - Permanently delete (default: false, moves to trash)
   */
  delete(id, permanent = false) {
    const params = permanent ? '?permanent=true' : '';
    return request(`/solutions/${id}${params}`, {
      method: 'DELETE',
    });
  },

  /**
   * Upload an asset file to a solution
   * @param {string} solutionId - Solution ID
   * @param {File} file - File to upload
   * @param {string} path - Relative path within solution directory
   * @param {string} updateField - Optional YAML field to update with this path
   */
  async uploadAsset(solutionId, file, path, updateField = null) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('path', path);
    if (updateField) {
      formData.append('update_field', updateField);
    }

    const apiBase = isTauri ? getApiBaseUrl() : '/api';
    const url = `${apiBase}/solutions/${solutionId}/assets`;
    const response = await fetch(url, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      let errorData;
      try {
        errorData = await response.json();
      } catch {
        errorData = { detail: response.statusText };
      }
      throw new ApiError(
        errorData.detail || 'Upload failed',
        response.status,
        errorData
      );
    }

    return response.json();
  },

  // ============================================
  // Structured Management API
  // ============================================

  /**
   * Get complete solution structure for management UI
   * @param {string} id - Solution ID
   */
  getStructure(id) {
    return request(`/solutions/${id}/structure`);
  },

  /**
   * List all files in a solution
   * @param {string} id - Solution ID
   */
  listFiles(id) {
    return request(`/solutions/${id}/files`);
  },

  /**
   * Delete a file from a solution
   * @param {string} id - Solution ID
   * @param {string} path - Relative file path
   */
  deleteFile(id, path) {
    return request(`/solutions/${id}/files/${encodeURIComponent(path)}`, {
      method: 'DELETE',
    });
  },

  /**
   * Create or update a text file in a solution
   * @param {string} id - Solution ID
   * @param {string} path - Relative file path
   * @param {string} content - File content
   */
  saveTextFile(id, path, content) {
    return request(`/solutions/${id}/files/${encodeURIComponent(path)}`, {
      method: 'PUT',
      body: JSON.stringify({ content }),
    });
  },

  /**
   * Add a new preset to a solution
   * @param {string} id - Solution ID
   * @param {Object} data - Preset data
   */
  addPreset(id, data) {
    return request(`/solutions/${id}/presets`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  /**
   * Update an existing preset
   * @param {string} id - Solution ID
   * @param {string} presetId - Preset ID
   * @param {Object} data - Updated preset data
   */
  updatePreset(id, presetId, data) {
    return request(`/solutions/${id}/presets/${encodeURIComponent(presetId)}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  /**
   * Delete a preset
   * @param {string} id - Solution ID
   * @param {string} presetId - Preset ID
   */
  deletePreset(id, presetId) {
    return request(`/solutions/${id}/presets/${encodeURIComponent(presetId)}`, {
      method: 'DELETE',
    });
  },

  /**
   * Add a device/step to a preset
   * @param {string} id - Solution ID
   * @param {string} presetId - Preset ID
   * @param {Object} data - Device data
   */
  addPresetDevice(id, presetId, data) {
    return request(`/solutions/${id}/presets/${encodeURIComponent(presetId)}/devices`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  /**
   * Update a device/step in a preset
   * @param {string} id - Solution ID
   * @param {string} presetId - Preset ID
   * @param {string} deviceId - Device ID
   * @param {Object} data - Updated device data
   */
  updatePresetDevice(id, presetId, deviceId, data) {
    return request(`/solutions/${id}/presets/${encodeURIComponent(presetId)}/devices/${encodeURIComponent(deviceId)}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },

  /**
   * Delete a device/step from a preset
   * @param {string} id - Solution ID
   * @param {string} presetId - Preset ID
   * @param {string} deviceId - Device ID
   */
  deletePresetDevice(id, presetId, deviceId) {
    return request(`/solutions/${id}/presets/${encodeURIComponent(presetId)}/devices/${encodeURIComponent(deviceId)}`, {
      method: 'DELETE',
    });
  },

  /**
   * Update solution links
   * @param {string} id - Solution ID
   * @param {Object} links - Links object (wiki, github, etc.)
   */
  updateLinks(id, links) {
    return request(`/solutions/${id}/links`, {
      method: 'PUT',
      body: JSON.stringify(links),
    });
  },

  /**
   * Update solution tags
   * @param {string} id - Solution ID
   * @param {string[]} tags - Array of tags
   */
  updateTags(id, tags) {
    return request(`/solutions/${id}/tags`, {
      method: 'PUT',
      body: JSON.stringify(tags),
    });
  },

  /**
   * Validate guide structure consistency between EN and ZH
   * @param {string} id - Solution ID
   * @returns {Promise<Object>} Validation result with errors and warnings
   */
  validateGuides(id) {
    return request(`/solutions/${id}/validate-guides`);
  },

  /**
   * Get parsed guide structure for management UI
   * @param {string} id - Solution ID
   * @returns {Promise<Object>} Guide structure with presets and steps
   */
  getGuideStructure(id) {
    return request(`/solutions/${id}/guide-structure`);
  },

  // ============================================
  // Content File Management (Simplified API)
  // ============================================

  /**
   * Upload a core content file (guide.md, description.md, etc.)
   * @param {string} id - Solution ID
   * @param {string} filename - One of: guide.md, guide_zh.md, description.md, description_zh.md
   * @param {string} content - File content
   */
  uploadContentFile(id, filename, content) {
    return request(`/solutions/${id}/content/${encodeURIComponent(filename)}`, {
      method: 'POST',
      body: JSON.stringify({ content }),
    });
  },

  /**
   * Get structure preview parsed from guide.md
   * @param {string} id - Solution ID
   * @returns {Promise<Object>} Structure with presets, steps, validation
   */
  getPreviewStructure(id) {
    return request(`/solutions/${id}/preview-structure`);
  },

  /**
   * Update required devices from catalog IDs
   * @param {string} id - Solution ID
   * @param {string[]} deviceIds - Array of device IDs from catalog
   */
  updateRequiredDevices(id, deviceIds) {
    return request(`/solutions/${id}/required-devices`, {
      method: 'PUT',
      body: JSON.stringify({ device_ids: deviceIds }),
    });
  },
};

// ============================================
// Devices API
// Device detection and connection management
// ============================================

export const devicesApi = {
  /**
   * Get device catalog for dropdown selectors
   * @returns {Promise<Object>} Catalog with devices array
   */
  getCatalog() {
    return request('/devices/catalog');
  },

  /**
   * Detect connected devices for a solution
   * @param {string} solutionId - Solution ID
   * @param {string} [presetId] - Optional preset ID
   */
  detect(solutionId, presetId = null) {
    const params = new URLSearchParams();
    if (presetId) params.append('preset', presetId);
    const query = params.toString();
    return request(`/devices/detect/${solutionId}${query ? '?' + query : ''}`);
  },

  /**
   * Get available serial ports
   */
  getPorts() {
    return request('/devices/ports');
  },

  /**
   * Test device connection
   * @param {Object} config - Connection configuration
   */
  testConnection(config) {
    return request('/devices/test-connection', {
      method: 'POST',
      body: JSON.stringify(config),
    });
  },

  /**
   * Scan for SSH devices on the local network using mDNS
   * @param {Object} options - Scan options
   * @param {number} options.timeout - Scan timeout in seconds (default: 3)
   * @param {boolean} options.filterKnown - Only return known IoT devices (default: true)
   * @returns {Promise<Object>} Object with devices array
   */
  scanMdns(options = {}) {
    const params = new URLSearchParams();
    if (options.timeout) params.append('timeout', options.timeout);
    if (options.filterKnown !== undefined) params.append('filter_known', options.filterKnown);
    const query = params.toString();
    return request(`/devices/scan-mdns${query ? '?' + query : ''}`, { timeout: 10000 });
  },
};

// ============================================
// Deployments API
// Deployment execution and status management
// ============================================

export const deploymentsApi = {
  /**
   * Start a new deployment
   * @param {Object} params - Deployment parameters
   * @param {string} params.solutionId - Solution ID
   * @param {string} params.deviceId - Device step ID
   * @param {Object} params.config - Additional configuration
   */
  start(params) {
    return request('/deployments/start', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  },

  /**
   * Get deployment status and details
   * @param {string} deploymentId - Deployment ID
   */
  get(deploymentId) {
    return request(`/deployments/${deploymentId}`);
  },

  /**
   * List all deployments
   * @param {string} lang - Language code ('en' or 'zh')
   */
  list(lang = 'en') {
    return request(`/deployments?lang=${lang}`);
  },

  /**
   * Cancel a running deployment
   * @param {string} deploymentId - Deployment ID
   */
  cancel(deploymentId) {
    return request(`/deployments/${deploymentId}/cancel`, {
      method: 'POST',
    });
  },

  /**
   * Retry a failed deployment
   * @param {string} deploymentId - Deployment ID
   */
  retry(deploymentId) {
    return request(`/deployments/${deploymentId}/retry`, {
      method: 'POST',
    });
  },

  /**
   * Delete a deployment record
   * @param {string} deploymentId - Deployment ID
   */
  delete(deploymentId) {
    return request(`/deployments/${deploymentId}`, {
      method: 'DELETE',
    });
  },
};

// ============================================
// Versions API
// Version management and update checking
// ============================================

export const versionsApi = {
  /**
   * Get version information for all devices in a solution
   * @param {string} solutionId - Solution ID
   */
  getSolutionVersions(solutionId) {
    return request(`/solutions/${solutionId}/versions`);
  },

  /**
   * Get version information for a specific device
   * @param {string} solutionId - Solution ID
   * @param {string} deviceId - Device ID
   */
  getDeviceVersion(solutionId, deviceId) {
    return request(`/solutions/${solutionId}/devices/${deviceId}/version`);
  },

  /**
   * Check for available updates for all devices
   * @param {string} solutionId - Solution ID
   */
  checkUpdates(solutionId) {
    return request(`/solutions/${solutionId}/check-updates`, {
      method: 'POST',
    });
  },

  /**
   * Check for update for a specific device
   * @param {string} solutionId - Solution ID
   * @param {string} deviceId - Device ID
   */
  checkDeviceUpdate(solutionId, deviceId) {
    return request(`/solutions/${solutionId}/devices/${deviceId}/check-update`);
  },

  /**
   * Get deployment history for a solution
   * @param {string} solutionId - Solution ID
   * @param {Object} options - Query options
   * @param {string} options.deviceId - Filter by device ID
   * @param {number} options.limit - Max records to return
   */
  getHistory(solutionId, options = {}) {
    const params = new URLSearchParams();
    if (options.deviceId) params.append('device_id', options.deviceId);
    if (options.limit) params.append('limit', options.limit);
    const query = params.toString();
    return request(`/solutions/${solutionId}/deployment-history${query ? '?' + query : ''}`);
  },

  /**
   * Get deployment statistics for a solution
   * @param {string} solutionId - Solution ID
   */
  getStats(solutionId) {
    return request(`/solutions/${solutionId}/deployment-stats`);
  },
};

// ============================================
// Device Management API
// Deployed application management
// ============================================

export const deviceManagementApi = {
  /**
   * List all active/deployed applications
   * @param {string} solutionId - Optional filter by solution
   */
  listActive(solutionId = null) {
    const params = solutionId ? `?solution_id=${solutionId}` : '';
    return request(`/device-management/active${params}`);
  },

  /**
   * Get deployment status
   * @param {string} deploymentId - Deployment ID
   */
  getStatus(deploymentId) {
    return request(`/device-management/${deploymentId}/status`);
  },

  /**
   * Perform action on deployment (start/stop/restart/update)
   * @param {string} deploymentId - Deployment ID
   * @param {string} action - Action to perform
   * @param {string} password - SSH password for remote deployments
   */
  performAction(deploymentId, action, password = null) {
    return request(`/device-management/${deploymentId}/action`, {
      method: 'POST',
      body: JSON.stringify({ action, password }),
    });
  },

  deleteDeployment(deploymentId) {
    return request(`/device-management/${deploymentId}`, { method: 'DELETE' });
  },

  /**
   * Get Kiosk mode status
   * @param {string} deploymentId - Deployment ID
   */
  getKioskStatus(deploymentId) {
    return request(`/device-management/${deploymentId}/kiosk`);
  },

  /**
   * Configure Kiosk mode
   * @param {string} deploymentId - Deployment ID
   * @param {Object} config - Kiosk configuration
   * @param {boolean} config.enabled - Enable or disable Kiosk
   * @param {string} config.kiosk_user - System user for Kiosk mode
   * @param {string} config.password - SSH password for remote deployments
   */
  configureKiosk(deploymentId, config) {
    return request(`/device-management/${deploymentId}/kiosk`, {
      method: 'POST',
      body: JSON.stringify(config),
    });
  },

  /**
   * Update a deployed application
   * @param {string} deploymentId - Deployment ID
   * @param {string} password - SSH password for remote deployments
   */
  updateDeployment(deploymentId, password = null) {
    return request(`/device-management/${deploymentId}/update`, {
      method: 'POST',
      body: JSON.stringify({ password }),
    });
  },
};

// ============================================
// Docker Devices API
// Remote Docker container management
// ============================================

export const dockerDevicesApi = {
  // ============================================
  // Local Docker (no SSH required)
  // ============================================

  /**
   * Check if Docker is available locally
   */
  checkLocal() {
    return request('/docker-devices/local/check');
  },

  /**
   * List containers on local machine
   */
  listLocalContainers() {
    return request('/docker-devices/local/containers', { timeout: 15000 });
  },

  /**
   * List SenseCraft-managed apps on local machine
   */
  listLocalManagedApps() {
    return request('/docker-devices/local/managed-apps', { timeout: 15000 });
  },

  /**
   * Perform action on a local container
   */
  localContainerAction(containerName, action) {
    return request(`/docker-devices/local/container-action?container_name=${encodeURIComponent(containerName)}&action=${action}`, {
      method: 'POST',
    });
  },

  // ============================================
  // Remote Docker (SSH)
  // ============================================

  /**
   * Test SSH connection and verify Docker availability
   * @param {Object} connection - Connection parameters
   */
  connect(connection) {
    return request('/docker-devices/connect', {
      method: 'POST',
      body: JSON.stringify(connection),
    });
  },

  /**
   * List containers on connected device
   * @param {Object} connection - Connection parameters
   */
  listContainers(connection) {
    return request('/docker-devices/containers', {
      method: 'POST',
      body: JSON.stringify(connection),
      timeout: 15000,
    });
  },

  /**
   * Upgrade a container (pull + recreate)
   * @param {Object} params - Upgrade parameters
   */
  upgrade(params) {
    return request('/docker-devices/upgrade', {
      method: 'POST',
      body: JSON.stringify(params),
      timeout: 180000,
    });
  },

  /**
   * Perform action on a container (start/stop/restart)
   * @param {Object} connection - Connection parameters
   * @param {string} containerName - Container name
   * @param {string} action - Action to perform
   */
  containerAction(connection, containerName, action) {
    return request(`/docker-devices/container-action?container_name=${encodeURIComponent(containerName)}&action=${action}`, {
      method: 'POST',
      body: JSON.stringify(connection),
    });
  },

  /**
   * List SenseCraft-managed applications on device
   * Returns only containers deployed through this platform
   * @param {Object} connection - Connection parameters
   */
  listManagedApps(connection) {
    return request('/docker-devices/managed-apps', {
      method: 'POST',
      body: JSON.stringify(connection),
      timeout: 15000,
    });
  },

  // ============================================
  // App Removal & Image Pruning
  // ============================================

  /**
   * Remove all containers for an app on local machine
   * @param {string} solutionId - Solution ID
   * @param {string} containerNames - Comma-separated container names
   * @param {boolean} removeImages - Also remove associated images
   */
  localRemoveApp(solutionId, containerNames, removeImages = false, removeVolumes = false) {
    const params = new URLSearchParams({
      solution_id: solutionId,
      container_names: containerNames,
      remove_images: removeImages.toString(),
      remove_volumes: removeVolumes.toString(),
    });
    return request(`/docker-devices/local/remove-app?${params}`, {
      method: 'POST',
      timeout: 60000,
    });
  },

  /**
   * Remove all unused Docker images on local machine
   */
  localPruneImages() {
    return request('/docker-devices/local/prune-images', {
      method: 'POST',
      timeout: 120000,
    });
  },

  /**
   * Remove all containers for an app on remote device
   * @param {Object} connection - Connection parameters
   * @param {string} solutionId - Solution ID
   * @param {string} containerNames - Comma-separated container names
   * @param {boolean} removeImages - Also remove associated images
   */
  removeApp(connection, solutionId, containerNames, removeImages = false, removeVolumes = false) {
    const params = new URLSearchParams({
      solution_id: solutionId,
      container_names: containerNames,
      remove_images: removeImages.toString(),
      remove_volumes: removeVolumes.toString(),
    });
    return request(`/docker-devices/remove-app?${params}`, {
      method: 'POST',
      body: JSON.stringify(connection),
      timeout: 60000,
    });
  },

  /**
   * Remove all unused Docker images on remote device
   * @param {Object} connection - Connection parameters
   */
  pruneImages(connection) {
    return request('/docker-devices/prune-images', {
      method: 'POST',
      body: JSON.stringify(connection),
      timeout: 120000,
    });
  },
};

// ============================================
// Restore API
// Device factory restore operations
// ============================================

export const restoreApi = {
  /**
   * Get list of devices that support factory restore
   * @param {string} lang - Language code ('en' or 'zh')
   */
  getDevices(lang = 'en') {
    return request(`/restore/devices?lang=${lang}`);
  },

  /**
   * Get available serial ports for USB restore
   */
  getPorts() {
    return request('/restore/ports');
  },

  /**
   * Start a restore operation
   * @param {string} deviceType - Device type (sensecap_watcher, recamera)
   * @param {Object} connection - Connection parameters
   */
  start(deviceType, connection) {
    return request('/restore/start', {
      method: 'POST',
      body: JSON.stringify({
        device_type: deviceType,
        connection,
      }),
    });
  },

  /**
   * Get restore operation status
   * @param {string} operationId - Operation ID
   */
  getStatus(operationId) {
    return request(`/restore/${operationId}/status`);
  },
};

// ============================================
// System API
// System information and health checks
// ============================================

export const systemApi = {
  /**
   * Get system health status
   */
  health() {
    return request('/health');
  },

  /**
   * Get system information
   */
  info() {
    return request('/system/info');
  },
};

// ============================================
// WebSocket for Real-time Logs
// ============================================

export class LogsWebSocket {
  constructor(deploymentId) {
    this.deploymentId = deploymentId;
    this.ws = null;
    this.listeners = {
      log: [],
      status: [],
      progress: [],
      docker_not_installed: [],
      error: [],
      close: [],
      open: [],
    };
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectDelay = 1000;
  }

  connect() {
    const wsBase = getWsBase();
    const wsUrl = `${wsBase}/ws/logs/${this.deploymentId}`;

    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      this.emit('open', { connected: true });
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        switch (data.type) {
          case 'log':
            this.emit('log', data);
            break;
          case 'status':
            this.emit('status', data);
            break;
          case 'progress':
            // Progress is used for UI updates (progress bars, etc.)
            // Don't convert to log - backend sends separate log messages
            this.emit('progress', data);
            break;
          case 'device_started':
            // Backend now sends separate log message
            break;
          case 'pre_check_started':
            // Backend now sends separate log message
            break;
          case 'pre_check_passed':
            // Backend now sends separate log message
            break;
          case 'pre_check_failed':
            // Backend now sends separate log message
            // Also emit status to mark as failed
            this.emit('status', { status: 'failed' });
            break;
          case 'device_completed':
            this.emit('status', { status: data.status });
            break;
          case 'deployment_completed':
            this.emit('status', { status: data.status });
            break;
          case 'docker_not_installed':
            // Docker not installed on remote device - needs user confirmation
            this.emit('docker_not_installed', data);
            break;
          case 'ping':
          case 'pong':
            // Ignore heartbeat messages
            break;
          default:
            console.log('Unknown WebSocket message type:', data.type, data);
        }
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      this.emit('error', error);
    };

    this.ws.onclose = (event) => {
      this.emit('close', event);

      // Attempt to reconnect if not a normal close
      if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1); // Exponential backoff
        setTimeout(() => this.connect(), delay);
      }
    };
  }

  on(event, callback) {
    if (this.listeners[event]) {
      this.listeners[event].push(callback);
    }
    return () => this.off(event, callback);
  }

  off(event, callback) {
    if (this.listeners[event]) {
      this.listeners[event] = this.listeners[event].filter(cb => cb !== callback);
    }
  }

  emit(event, data) {
    if (this.listeners[event]) {
      this.listeners[event].forEach(cb => cb(data));
    }
  }

  send(data) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }
  }

  get isConnected() {
    return this.ws && this.ws.readyState === WebSocket.OPEN;
  }
}

// ============================================
// Utility Functions
// ============================================

/**
 * Get asset URL for solution resources
 * @param {string} solutionId - Solution ID
 * @param {string} path - Asset path
 * @returns {string} Full asset URL
 */
export function getAssetUrl(solutionId, path) {
  if (!path) return '';
  // Handle absolute URLs
  if (path.startsWith('http://') || path.startsWith('https://')) {
    return path;
  }
  // Handle paths that already include /api/
  if (path.startsWith('/api/')) {
    // In Tauri mode, convert to full URL
    if (isTauri) {
      const backendPort = window.__BACKEND_PORT__ || 3260;
      return `http://127.0.0.1:${backendPort}${path}`;
    }
    return path;
  }
  // Build full asset URL
  const assetPath = `/api/solutions/${solutionId}/assets/${path}`;
  if (isTauri) {
    const backendPort = window.__BACKEND_PORT__ || 3260;
    return `http://127.0.0.1:${backendPort}${assetPath}`;
  }
  return assetPath;
}

/**
 * Build query string from object
 * @param {Object} params - Query parameters
 * @returns {string} Query string
 */
export function buildQueryString(params) {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      searchParams.append(key, value);
    }
  });
  const queryString = searchParams.toString();
  return queryString ? `?${queryString}` : '';
}

// ============================================
// Exports
// ============================================

export { ApiError, request };
