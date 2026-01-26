/**
 * Preview Module - Live Video + MQTT Inference Display
 *
 * Handles:
 * - RTSP stream playback via MJPEG proxy (low latency)
 * - MQTT message forwarding via WebSocket
 * - Canvas overlay rendering for inference results
 */

import { t } from './i18n.js';
import { getApiBase, getWsBase } from './api.js';

// ============================================
// Preview API
// ============================================

// Dynamic API base for Tauri compatibility
function getPreviewApiBase() {
  const apiBase = getApiBase();
  return `${apiBase.replace('/api', '')}/api/preview`;
}

export const previewApi = {
  /**
   * Start an RTSP to MJPEG stream
   */
  async startMjpegStream(rtspUrl, streamId = null, fps = 10, quality = 5) {
    const response = await fetch(`${getPreviewApiBase()}/mjpeg/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rtsp_url: rtspUrl, stream_id: streamId, fps, quality }),
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
    const response = await fetch(`${getPreviewApiBase()}/stream/${streamId}/stop`, {
      method: 'POST',
    });
    return response.ok;
  },

  /**
   * Get stream status
   */
  async getStreamStatus(streamId) {
    const response = await fetch(`${getPreviewApiBase()}/stream/${streamId}/status`);
    if (!response.ok) return null;
    return response.json();
  },

  /**
   * Get preview service status
   */
  async getStatus() {
    const response = await fetch(`${getPreviewApiBase()}/status`);
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

    this.img = null;
    this.canvas = null;
    this.ws = null;
    this.streamId = null;
    this.isConnected = false;
    this.overlayRenderer = null;
    this._abortController = null;
    this._lastBlobUrl = null;
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
          <img id="preview-img" class="preview-video" style="visibility:hidden" alt="">
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

    this.img = this.container.querySelector('#preview-img');
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

    // Handle MJPEG frame events
    if (this.img) {
      this.img.addEventListener('load', () => {
        this.img.style.visibility = 'visible';
        this._resizeCanvas();
        // First frame received - stream is live
        if (this.isConnected) {
          this._updateRtspStatus('connected');
        }
      });

      this.img.addEventListener('error', (e) => {
        if (this.isConnected) {
          console.error('MJPEG stream error:', e);
          this._updateRtspStatus('error', 'Stream error');
        }
      });
    }
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
        // Process started, img.src set - enable disconnect button
        // Status stays "connecting" until first frame loads (img.load event)
        this.isConnected = true;
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
   * Connect to MJPEG video stream
   */
  async _connectVideo(rtspUrl) {
    // Start MJPEG stream proxy
    const result = await previewApi.startMjpegStream(rtspUrl);
    this.streamId = result.stream_id;

    // Use fetch + ReadableStream to parse MJPEG frames.
    // This works through proxies (Vite dev server) unlike native
    // multipart/x-mixed-replace which requires direct connection.
    this._abortController = new AbortController();
    this._startMjpegReader(result.mjpeg_url);
  }

  /**
   * Start reading MJPEG frames from the streaming endpoint
   */
  _startMjpegReader(url) {
    // Build full URL for the MJPEG stream
    // In Tauri mode or dev mode, we need the full URL
    let fullUrl = url;
    const isTauri = window.__TAURI__ !== undefined;

    if (isTauri) {
      // Tauri mode: use backend port
      const backendPort = window.__BACKEND_PORT__ || 3260;
      fullUrl = `http://127.0.0.1:${backendPort}${url}`;
    } else if (window.location.port === '5173') {
      // Dev mode: connect directly to backend at port 3260
      fullUrl = `http://${window.location.hostname}:3260${url}`;
    }
    console.log('[MJPEG] Starting stream:', fullUrl);

    // For Tauri/Safari, use native img.src with MJPEG URL directly
    // This works better than fetch+ReadableStream which has WebKit issues
    // For dev mode through Vite proxy, we need fetch+parser approach
    const useNativeImg = isTauri || (window.location.port !== '5173');

    if (useNativeImg) {
      // Native MJPEG: set img.src directly
      // Browsers handle multipart/x-mixed-replace automatically
      console.log('[MJPEG] Using native img.src approach');
      this.img.src = fullUrl;
      // First frame will trigger img.onload event which is already handled
      return;
    }

    // For dev mode with Vite proxy: use fetch + manual frame parsing
    // because Vite proxy doesn't handle multipart/x-mixed-replace well
    console.log('[MJPEG] Using fetch+parser approach (dev mode)');
    fetch(fullUrl, { signal: this._abortController.signal, mode: 'cors' })
      .then(response => {
        console.log('[MJPEG] Response:', response.status, response.headers.get('content-type'));
        if (!response.ok) {
          throw new Error(`Stream request failed: ${response.status}`);
        }
        const reader = response.body.getReader();
        this._readMjpegFrames(reader);
      })
      .catch(err => {
        if (err.name !== 'AbortError') {
          console.error('MJPEG fetch error:', err);
          this._updateRtspStatus('error', 'Stream failed');
        }
      });
  }

  /**
   * Parse JPEG frames from a ReadableStream and display them
   */
  async _readMjpegFrames(reader) {
    let buffer = new Uint8Array(0);
    let frameCount = 0;

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          console.log('[MJPEG] Stream ended');
          break;
        }

        // Append chunk to buffer
        const newBuffer = new Uint8Array(buffer.length + value.length);
        newBuffer.set(buffer);
        newBuffer.set(value, buffer.length);
        buffer = newBuffer;

        if (frameCount === 0) {
          console.log('[MJPEG] First chunk received:', value.length, 'bytes, buffer now:', buffer.length);
        }

        // Find complete JPEG frames (SOI: 0xFF 0xD8, EOI: 0xFF 0xD9)
        while (true) {
          const soiIdx = this._findMarker(buffer, 0xFF, 0xD8);
          if (soiIdx < 0) break;

          const eoiIdx = this._findMarker(buffer, 0xFF, 0xD9, soiIdx + 2);
          if (eoiIdx < 0) break;

          // Extract complete JPEG frame
          const frameEnd = eoiIdx + 2;
          const frame = buffer.slice(soiIdx, frameEnd);

          frameCount++;
          if (frameCount <= 3) {
            console.log(`[MJPEG] Frame ${frameCount}: ${frame.length} bytes, SOI@${soiIdx}, EOI@${eoiIdx}`);
          }

          // Display frame as blob URL
          const blob = new Blob([frame], { type: 'image/jpeg' });
          const blobUrl = URL.createObjectURL(blob);
          if (this._lastBlobUrl) {
            URL.revokeObjectURL(this._lastBlobUrl);
          }
          this._lastBlobUrl = blobUrl;
          this.img.src = blobUrl;

          // Advance buffer past this frame
          buffer = buffer.slice(frameEnd);
        }

        // Trim buffer: discard data before the last potential SOI start
        if (buffer.length > 0) {
          const lastSoi = this._findMarker(buffer, 0xFF, 0xD8);
          if (lastSoi > 0) {
            buffer = buffer.slice(lastSoi);
          }
        }
      }
    } catch (err) {
      if (err.name !== 'AbortError') {
        console.error('MJPEG reader error:', err);
        if (this.isConnected) {
          this._updateRtspStatus('error', 'Stream ended');
        }
      }
    }
  }

  /**
   * Find a 2-byte marker in a Uint8Array
   */
  _findMarker(buffer, b0, b1, startIdx = 0) {
    for (let i = startIdx; i < buffer.length - 1; i++) {
      if (buffer[i] === b0 && buffer[i + 1] === b1) {
        return i;
      }
    }
    return -1;
  }

  /**
   * Connect to MQTT via WebSocket
   */
  async _connectMqtt(config) {
    return new Promise((resolve, reject) => {
      const wsUrl = `${getWsBase()}/api/preview/ws/mqtt`;

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

    // Ensure canvas resolution matches display size
    const displayRect = this.canvas.getBoundingClientRect();
    if (this.canvas.width !== Math.round(displayRect.width) ||
        this.canvas.height !== Math.round(displayRect.height)) {
      this._resizeCanvas();
    }

    const ctx = this.canvas.getContext('2d');
    // Note: Don't clear canvas here - overlay script handles its own clearing
    // via double buffering to prevent flicker

    try {
      this.overlayRenderer(ctx, data, this.canvas, this.img);
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
   * Resize canvas to match video or container
   * Only updates dimensions if they actually changed (to avoid clearing canvas)
   */
  _resizeCanvas() {
    if (!this.canvas) return;

    // Use img dimensions if loaded, otherwise use canvas display size
    const rect = (this.img && this.img.naturalWidth)
      ? this.img.getBoundingClientRect()
      : this.canvas.getBoundingClientRect();

    const newWidth = Math.round(rect.width);
    const newHeight = Math.round(rect.height);

    // Only set dimensions if changed - setting canvas.width/height clears it!
    if (this.canvas.width !== newWidth || this.canvas.height !== newHeight) {
      this.canvas.width = newWidth;
      this.canvas.height = newHeight;
    }
  }

  /**
   * Disconnect from stream and MQTT
   */
  async disconnect() {
    // Abort MJPEG fetch
    if (this._abortController) {
      this._abortController.abort();
      this._abortController = null;
    }

    // Clean up blob URL and img
    if (this._lastBlobUrl) {
      URL.revokeObjectURL(this._lastBlobUrl);
      this._lastBlobUrl = null;
    }
    if (this.img) {
      this.img.style.visibility = 'hidden';
      this.img.src = '';
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
   * @param {Function} renderer - Function(ctx, data, canvas, img)
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
    // The script should define drawing operations using ctx, data, canvas, img
    const fn = new Function('ctx', 'data', 'canvas', 'img', scriptContent);
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
