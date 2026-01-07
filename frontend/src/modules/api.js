/**
 * API Module - Backend Communication
 */

const API_BASE = '/api';

class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.status = status;
    this.data = data;
    this.name = 'ApiError';
  }
}

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;

  const config = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  };

  try {
    const response = await fetch(url, config);

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
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(error.message, 0, null);
  }
}

// Solutions API
export const solutionsApi = {
  list(lang = 'en') {
    return request(`/solutions?lang=${lang}`);
  },

  get(id, lang = 'en') {
    return request(`/solutions/${id}?lang=${lang}`);
  },

  getDeployment(id, lang = 'en') {
    return request(`/solutions/${id}/deployment?lang=${lang}`);
  },

  getContent(id, path) {
    return request(`/solutions/${id}/content/${path}`);
  },
};

// Devices API
export const devicesApi = {
  detect(solutionId) {
    return request(`/devices/detect/${solutionId}`);
  },

  getPorts() {
    return request('/devices/ports');
  },

  testConnection(config) {
    return request('/devices/test-connection', {
      method: 'POST',
      body: JSON.stringify(config),
    });
  },
};

// Deployments API
export const deploymentsApi = {
  start(params) {
    return request('/deployments/start', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  },

  get(deploymentId) {
    return request(`/deployments/${deploymentId}`);
  },

  list() {
    return request('/deployments');
  },

  cancel(deploymentId) {
    return request(`/deployments/${deploymentId}/cancel`, {
      method: 'POST',
    });
  },
};

// WebSocket for real-time logs
export class LogsWebSocket {
  constructor(deploymentId) {
    this.deploymentId = deploymentId;
    this.ws = null;
    this.listeners = {
      log: [],
      status: [],
      error: [],
      close: [],
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
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === 'log') {
          this.emit('log', data);
        } else if (data.type === 'status') {
          this.emit('status', data);
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
        setTimeout(() => this.connect(), this.reconnectDelay * this.reconnectAttempts);
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

  disconnect() {
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }
  }
}

// Asset URL helper
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

export { ApiError };
