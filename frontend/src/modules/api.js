/**
 * API Module - Backend Communication
 *
 * Organized by business domain for better maintainability.
 * Reference: sensecraftAppStore/website-device-management-platform/src/config/envApi.js
 */

// ============================================
// Configuration
// ============================================

const API_BASE = '/api';

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
  const url = `${API_BASE}${endpoint}`;

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
   */
  getDeviceGroupSection(id, groupId, selectedDevice, lang = 'en') {
    return request(`/solutions/${id}/device-group/${groupId}/section?selected_device=${encodeURIComponent(selectedDevice)}&lang=${lang}`);
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
};

// ============================================
// Devices API
// Device detection and connection management
// ============================================

export const devicesApi = {
  /**
   * Detect connected devices for a solution
   * @param {string} solutionId - Solution ID
   */
  detect(solutionId) {
    return request(`/devices/detect/${solutionId}`);
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
   */
  list() {
    return request('/deployments');
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
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/logs/${this.deploymentId}`;

    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log('WebSocket connected');
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
      console.log('WebSocket closed:', event.code, event.reason);
      this.emit('close', event);

      // Attempt to reconnect if not a normal close
      if (event.code !== 1000 && this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1); // Exponential backoff
        console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
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
    return path;
  }
  return `/api/solutions/${solutionId}/assets/${path}`;
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
