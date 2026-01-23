/**
 * Preview Module - Live Video + MQTT Inference Display
 *
 * Handles:
 * - RTSP stream playback via HLS proxy
 * - MQTT message forwarding via WebSocket
 * - Canvas overlay rendering for inference results
 */

import { t } from './i18n.js';

// ============================================
// Preview API
// ============================================

const API_BASE = '/api/preview';

export const previewApi = {
  /**
   * Start an RTSP to HLS stream
   */
  async startStream(rtspUrl, streamId = null) {
    const response = await fetch(`${API_BASE}/stream/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rtsp_url: rtspUrl, stream_id: streamId }),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to start stream');
    }
    return response.json();
  },

  /**
   * Stop a stream
   */
  async stopStream(streamId) {
    const response = await fetch(`${API_BASE}/stream/${streamId}/stop`, {
      method: 'POST',
    });
    return response.ok;
  },

  /**
   * Get stream status
   */
  async getStreamStatus(streamId) {
    const response = await fetch(`${API_BASE}/stream/${streamId}/status`);
    if (!response.ok) return null;
    return response.json();
  },

  /**
   * Get preview service status
   */
  async getStatus() {
    const response = await fetch(`${API_BASE}/status`);
    return response.json();
  },
};

// ============================================
// Preview Window Class
// ============================================

export class PreviewWindow {
  /**
   * Create a preview window
   * @param {HTMLElement} container - Container element
   * @param {Object} config - Preview configuration
   */
  constructor(container, config = {}) {
    this.container = container;
    this.config = {
      aspectRatio: config.aspectRatio || '16:9',
      autoStart: config.autoStart || false,
      showStats: config.showStats !== false,
      ...config,
    };

    this.video = null;
    this.canvas = null;
    this.hls = null;
    this.ws = null;
    this.streamId = null;
    this.isConnected = false;
    this.overlayRenderer = null;
    this.stats = {
      fps: 0,
      messageCount: 0,
      lastMessageTime: 0,
    };

    this._messageHandlers = [];
    this._statusHandlers = [];
    this._frameCount = 0;
    this._lastFpsUpdate = 0;

    this._render();
  }

  /**
   * Render the preview window UI
   */
  _render() {
    const [w, h] = this.config.aspectRatio.split(':').map(Number);
    const paddingBottom = (h / w * 100).toFixed(2);

    this.container.innerHTML = `
      <div class="preview-window">
        <div class="preview-header">
          <div class="preview-status-group">
            <div class="preview-status" id="preview-status-rtsp" title="RTSP Stream">
              <span class="preview-status-dot"></span>
              <span class="preview-status-text">RTSP</span>
            </div>
            <div class="preview-status" id="preview-status-mqtt" title="MQTT">
              <span class="preview-status-dot"></span>
              <span class="preview-status-text">MQTT</span>
            </div>
          </div>
          ${this.config.showStats ? `
            <div class="preview-stats" id="preview-stats">
              <span class="preview-stat">FPS: <span id="preview-fps">0</span></span>
              <span class="preview-stat">MSG: <span id="preview-msg-count">0</span></span>
            </div>
          ` : ''}
        </div>

        <div class="preview-container" style="padding-bottom: ${paddingBottom}%;">
          <video id="preview-video" class="preview-video" muted playsinline></video>
          <canvas id="preview-canvas" class="preview-canvas"></canvas>
          <div class="preview-overlay-info" id="preview-overlay-info"></div>
        </div>

        <div class="preview-controls">
          <button class="btn btn-primary preview-connect-btn" id="preview-connect-btn">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="5 3 19 12 5 21 5 3"/>
            </svg>
            <span>${t('preview.actions.connect')}</span>
          </button>
          <button class="btn btn-secondary preview-fullscreen-btn" id="preview-fullscreen-btn" disabled>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="15 3 21 3 21 9"/>
              <polyline points="9 21 3 21 3 15"/>
              <line x1="21" y1="3" x2="14" y2="10"/>
              <line x1="3" y1="21" x2="10" y2="14"/>
            </svg>
          </button>
        </div>
      </div>
    `;

    this.video = this.container.querySelector('#preview-video');
    this.canvas = this.container.querySelector('#preview-canvas');
    this._setupEventHandlers();
  }

  /**
   * Set up event handlers
   */
  _setupEventHandlers() {
    const connectBtn = this.container.querySelector('#preview-connect-btn');
    const fullscreenBtn = this.container.querySelector('#preview-fullscreen-btn');

    connectBtn?.addEventListener('click', () => {
      if (this.isConnected) {
        this.disconnect();
      } else {
        this._emitConnect();
      }
    });

    fullscreenBtn?.addEventListener('click', () => {
      this._toggleFullscreen();
    });

    // Resize canvas when video size changes
    this.video?.addEventListener('loadedmetadata', () => {
      this._resizeCanvas();
    });

    // Handle video errors
    this.video?.addEventListener('error', (e) => {
      console.error('Video error:', e);
      this._updateStatus('error', 'Video playback error');
    });
  }

  /**
   * Connect to stream and MQTT
   * @param {Object} options - Connection options
   */
  async connect(options = {}) {
    const { rtspUrl, mqttBroker, mqttPort, mqttTopic, mqttUsername, mqttPassword } = options;

    // Initialize both as connecting
    this._updateRtspStatus('connecting');
    this._updateMqttStatus('disconnected');

    try {
      // Start video stream if URL provided
      if (rtspUrl) {
        await this._connectVideo(rtspUrl);
        // Video connected - update UI immediately
        this.isConnected = true;
        this._updateRtspStatus('connected');
        this._updateConnectButton(true);
      }
    } catch (error) {
      console.error('Video connection failed:', error);
      this._updateRtspStatus('error', error.message);
      throw error;
    }

    // Connect to MQTT asynchronously (don't block UI)
    if (mqttBroker && mqttTopic) {
      this._updateMqttStatus('connecting');
      this._connectMqtt({
        broker: mqttBroker,
        port: mqttPort || 1883,
        topic: mqttTopic,
        username: mqttUsername,
        password: mqttPassword,
      }).then(() => {
        this._updateMqttStatus('connected');
      }).catch(error => {
        console.error('MQTT connection failed:', error);
        this._updateMqttStatus('error', error.message);
      });
    }
  }

  /**
   * Connect to HLS video stream
   */
  async _connectVideo(rtspUrl) {
    // Start stream proxy
    const result = await previewApi.startStream(rtspUrl);
    this.streamId = result.stream_id;

    // Wait for stream to be ready
    await this._waitForStream(this.streamId);

    // Connect HLS player
    const hlsUrl = result.hls_url;

    if (window.Hls && Hls.isSupported()) {
      this.hls = new Hls({
        liveDurationInfinity: true,
        liveBackBufferLength: 0,
        maxBufferLength: 2,
        maxMaxBufferLength: 3,
      });

      this.hls.loadSource(hlsUrl);
      this.hls.attachMedia(this.video);

      this.hls.on(Hls.Events.MANIFEST_PARSED, () => {
        this.video.play().catch(e => console.warn('Autoplay blocked:', e));
      });

      this.hls.on(Hls.Events.ERROR, (event, data) => {
        if (data.fatal) {
          console.error('HLS fatal error:', data);
          this._updateStatus('error', 'Stream error');
        }
      });
    } else if (this.video.canPlayType('application/vnd.apple.mpegurl')) {
      // Native HLS support (Safari)
      this.video.src = hlsUrl;
      this.video.play().catch(e => console.warn('Autoplay blocked:', e));
    } else {
      throw new Error('HLS playback not supported in this browser');
    }
  }

  /**
   * Wait for stream to be ready
   */
  async _waitForStream(streamId, maxWait = 10000) {
    const startTime = Date.now();
    while (Date.now() - startTime < maxWait) {
      const status = await previewApi.getStreamStatus(streamId);
      if (status?.status === 'running') {
        return;
      }
      if (status?.status === 'error') {
        throw new Error(status.error || 'Stream failed to start');
      }
      await new Promise(r => setTimeout(r, 500));
    }
    throw new Error('Stream startup timeout');
  }

  /**
   * Connect to MQTT via WebSocket
   */
  async _connectMqtt(config) {
    return new Promise((resolve, reject) => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/api/preview/ws/mqtt`;

      this.ws = new WebSocket(wsUrl);

      const timeout = setTimeout(() => {
        reject(new Error('MQTT connection timeout'));
      }, 10000);

      this.ws.onopen = () => {
        // Send connection request
        this.ws.send(JSON.stringify({
          action: 'connect',
          ...config,
        }));
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === 'status' && data.connected) {
            clearTimeout(timeout);
            resolve();
          } else if (data.type === 'error') {
            clearTimeout(timeout);
            reject(new Error(data.message));
          } else if (data.type === 'mqtt_message') {
            this._handleMqttMessage(data);
          }
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e);
        }
      };

      this.ws.onerror = (error) => {
        clearTimeout(timeout);
        reject(new Error('WebSocket connection failed'));
      };

      this.ws.onclose = () => {
        if (this.isConnected) {
          this._updateStatus('disconnected', 'MQTT connection closed');
        }
      };
    });
  }

  /**
   * Handle incoming MQTT message
   */
  _handleMqttMessage(message) {
    this.stats.messageCount++;
    this.stats.lastMessageTime = Date.now();

    // Update stats display
    const msgCountEl = this.container.querySelector('#preview-msg-count');
    if (msgCountEl) {
      msgCountEl.textContent = this.stats.messageCount;
    }

    // Notify handlers
    this._messageHandlers.forEach(handler => {
      try {
        handler(message.payload);
      } catch (e) {
        console.error('Message handler error:', e);
      }
    });

    // Render overlay if renderer is set
    if (this.overlayRenderer) {
      this._renderOverlay(message.payload);
    }
  }

  /**
   * Render overlay on canvas
   */
  _renderOverlay(data) {
    if (!this.canvas || !this.overlayRenderer) return;

    const ctx = this.canvas.getContext('2d');
    ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

    try {
      this.overlayRenderer(ctx, data, this.canvas, this.video);
      this._frameCount++;

      // Update FPS
      const now = Date.now();
      if (now - this._lastFpsUpdate > 1000) {
        this.stats.fps = Math.round(this._frameCount * 1000 / (now - this._lastFpsUpdate));
        this._frameCount = 0;
        this._lastFpsUpdate = now;

        const fpsEl = this.container.querySelector('#preview-fps');
        if (fpsEl) {
          fpsEl.textContent = this.stats.fps;
        }
      }
    } catch (e) {
      console.error('Overlay render error:', e);
    }
  }

  /**
   * Resize canvas to match video
   */
  _resizeCanvas() {
    if (!this.video || !this.canvas) return;

    const rect = this.video.getBoundingClientRect();
    this.canvas.width = rect.width;
    this.canvas.height = rect.height;
  }

  /**
   * Disconnect from stream and MQTT
   */
  async disconnect() {
    // Stop HLS
    if (this.hls) {
      this.hls.destroy();
      this.hls = null;
    }

    // Stop video
    if (this.video) {
      this.video.pause();
      this.video.src = '';
    }

    // Close WebSocket
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    // Stop stream proxy
    if (this.streamId) {
      await previewApi.stopStream(this.streamId).catch(() => {});
      this.streamId = null;
    }

    // Clear canvas
    if (this.canvas) {
      const ctx = this.canvas.getContext('2d');
      ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    }

    this.isConnected = false;
    this._updateRtspStatus('disconnected');
    this._updateMqttStatus('disconnected');
    this._updateConnectButton(false);
  }

  /**
   * Update RTSP status display
   */
  _updateRtspStatus(status, message = null) {
    const statusEl = this.container.querySelector('#preview-status-rtsp');
    if (!statusEl) return;

    statusEl.className = `preview-status ${status}`;
    const statusText = statusEl.querySelector('.preview-status-text');
    if (statusText) {
      if (status === 'error' && message) {
        statusText.textContent = message;
      } else {
        statusText.textContent = 'RTSP';
      }
    }
  }

  /**
   * Update MQTT status display
   */
  _updateMqttStatus(status, message = null) {
    const statusEl = this.container.querySelector('#preview-status-mqtt');
    if (!statusEl) return;

    statusEl.className = `preview-status ${status}`;
    const statusText = statusEl.querySelector('.preview-status-text');
    if (statusText) {
      if (status === 'error' && message) {
        statusText.textContent = message;
      } else {
        statusText.textContent = 'MQTT';
      }
    }
  }

  /**
   * Update status display (legacy - updates both)
   */
  _updateStatus(status, message = null) {
    // For backwards compatibility, update both if needed
    this._updateRtspStatus(status, message);
    this._updateMqttStatus(status, message);

    // Notify status handlers
    this._statusHandlers.forEach(handler => {
      try {
        handler(status, message);
      } catch (e) {
        console.error('Status handler error:', e);
      }
    });
  }

  /**
   * Update connect button state
   */
  _updateConnectButton(isConnected) {
    const btn = this.container.querySelector('#preview-connect-btn');
    const fullscreenBtn = this.container.querySelector('#preview-fullscreen-btn');

    if (btn) {
      if (isConnected) {
        btn.innerHTML = `
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="6" y="4" width="4" height="16"/>
            <rect x="14" y="4" width="4" height="16"/>
          </svg>
          <span>${t('preview.actions.disconnect')}</span>
        `;
        btn.classList.remove('btn-primary');
        btn.classList.add('btn-secondary');
      } else {
        btn.innerHTML = `
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="5 3 19 12 5 21 5 3"/>
          </svg>
          <span>${t('preview.actions.connect')}</span>
        `;
        btn.classList.remove('btn-secondary');
        btn.classList.add('btn-primary');
      }
    }

    if (fullscreenBtn) {
      fullscreenBtn.disabled = !isConnected;
    }
  }

  /**
   * Toggle fullscreen
   */
  _toggleFullscreen() {
    const container = this.container.querySelector('.preview-container');
    if (!container) return;

    if (document.fullscreenElement) {
      document.exitFullscreen();
    } else {
      container.requestFullscreen().catch(e => {
        console.warn('Fullscreen not supported:', e);
      });
    }
  }

  /**
   * Emit connect event (for external handling)
   */
  _emitConnect() {
    const event = new CustomEvent('preview:connect', {
      detail: { preview: this },
      bubbles: true,
    });
    this.container.dispatchEvent(event);
  }

  /**
   * Set overlay renderer function
   * @param {Function} renderer - Function(ctx, data, canvas, video)
   */
  setOverlayRenderer(renderer) {
    this.overlayRenderer = renderer;
  }

  /**
   * Add message handler
   * @param {Function} handler - Function(payload)
   */
  onMessage(handler) {
    this._messageHandlers.push(handler);
    return () => {
      this._messageHandlers = this._messageHandlers.filter(h => h !== handler);
    };
  }

  /**
   * Add status handler
   * @param {Function} handler - Function(status, message)
   */
  onStatus(handler) {
    this._statusHandlers.push(handler);
    return () => {
      this._statusHandlers = this._statusHandlers.filter(h => h !== handler);
    };
  }

  /**
   * Destroy the preview window
   */
  destroy() {
    this.disconnect();
    this._messageHandlers = [];
    this._statusHandlers = [];
    this.container.innerHTML = '';
  }
}

// ============================================
// Overlay Script Loader
// ============================================

/**
 * Load and execute a custom overlay script
 * @param {string} scriptContent - JavaScript code as string
 * @returns {Function} The overlay renderer function
 */
export function loadOverlayScript(scriptContent) {
  try {
    // Create a function from the script content
    // The script should define drawing operations using ctx, data, canvas, video
    const fn = new Function('ctx', 'data', 'canvas', 'video', scriptContent);
    return fn;
  } catch (e) {
    console.error('Failed to load overlay script:', e);
    return null;
  }
}

/**
 * Fetch and load overlay script from URL
 * @param {string} url - Script URL
 * @returns {Function} The overlay renderer function
 */
export async function fetchOverlayScript(url) {
  try {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Failed to fetch script: ${response.status}`);
    }
    const scriptContent = await response.text();
    return loadOverlayScript(scriptContent);
  } catch (e) {
    console.error('Failed to fetch overlay script:', e);
    return null;
  }
}
