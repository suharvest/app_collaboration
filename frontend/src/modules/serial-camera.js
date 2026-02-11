/**
 * Serial Camera Module - Canvas-based serial camera preview
 *
 * Handles:
 * - WebSocket connection for SSCMA frame data
 * - Canvas rendering of camera frames with face detection overlays
 * - FPS statistics display
 */

import { t } from './i18n.js';
import { getWsBase } from './api.js';

// ============================================
// SerialCameraCanvas Class
// ============================================

export class SerialCameraCanvas {
  /**
   * Create a serial camera canvas
   * @param {HTMLElement} container - Container element
   * @param {Object} config - Configuration
   */
  constructor(container, config = {}) {
    this.container = container;
    this.config = {
      aspectRatio: config.aspectRatio || '4:3',
      showLandmarks: config.showLandmarks !== false,
      showStats: config.showStats !== false,
      bboxColors: config.bboxColors || {
        recognized: '#4ade80',  // green
        unknown: '#facc15',     // yellow
      },
      ...config,
    };

    this.canvas = null;
    this.ctx = null;
    this.ws = null;
    this.isConnected = false;
    this._img = new Image();
    this._frameCallbacks = [];
    this._statusCallbacks = [];

    // Canvas dimensions (cached, only updated on resize)
    this._canvasW = 0;
    this._canvasH = 0;
    this._resizeObserver = null;

    // Stats
    this._frameCount = 0;
    this._lastFpsTime = performance.now();
    this._fps = 0;

    this._render();
  }

  /**
   * Render the camera UI
   */
  _render() {
    const [w, h] = this.config.aspectRatio.split(':').map(Number);
    const paddingBottom = ((h / w) * 100).toFixed(2);

    this.container.innerHTML = `
      <div class="serial-camera-window">
        <div class="serial-camera-header">
          <div class="serial-camera-status" id="sc-status">
            <span class="status-dot"></span>
            <span class="status-text">${t('serialCamera.status.disconnected')}</span>
          </div>
          <div class="serial-camera-stats" id="sc-stats" style="display:none">
            FPS: <span id="sc-fps">0</span>
          </div>
        </div>
        <div class="serial-camera-container" style="padding-bottom: ${paddingBottom}%;">
          <canvas class="serial-camera-canvas" id="sc-canvas"></canvas>
          <div class="serial-camera-placeholder" id="sc-placeholder">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
              <circle cx="12" cy="13" r="4"/>
            </svg>
            <span>${t('serialCamera.clickConnect')}</span>
          </div>
        </div>
        <div class="serial-camera-controls">
          <button class="btn btn-sm btn-primary serial-camera-connect-btn" id="sc-connect-btn">
            ${t('serialCamera.connect')}
          </button>
        </div>
      </div>
    `;

    this.canvas = this.container.querySelector('#sc-canvas');
    this.ctx = this.canvas.getContext('2d');

    // Set initial canvas size and watch for resizes
    this._updateCanvasSize();
    this._resizeObserver = new ResizeObserver(() => this._updateCanvasSize());
    this._resizeObserver.observe(this.canvas.parentElement);
  }

  /**
   * Update canvas backing size (only on init/resize, NOT every frame)
   */
  _updateCanvasSize() {
    const rect = this.canvas.parentElement.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    const newW = Math.round(rect.width * dpr);
    const newH = Math.round(rect.height * dpr);

    if (newW !== this._canvasW || newH !== this._canvasH) {
      this._canvasW = newW;
      this._canvasH = newH;
      this.canvas.width = newW;
      this.canvas.height = newH;
    }
  }

  /**
   * Connect to WebSocket frame stream
   * @param {string} sessionId - Session ID from backend
   */
  connect(sessionId) {
    if (this.ws) {
      this.disconnect();
    }

    const wsBase = getWsBase();
    const url = `${wsBase}/api/serial-camera/ws/${sessionId}`;

    this._setStatus('connecting');
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      this.isConnected = true;
      this._setStatus('connected');
      this._showPlaceholder(false);
      if (this.config.showStats) {
        this.container.querySelector('#sc-stats').style.display = '';
      }
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'frame') {
          this._drawFrame(data);
          this._updateFps();

          // Notify frame callbacks
          for (const cb of this._frameCallbacks) {
            try { cb(data); } catch { /* ignore */ }
          }
        } else if (data.type === 'status') {
          this._setStatus(data.status, data.message);
        }
      } catch {
        // ignore parse errors
      }
    };

    this.ws.onclose = () => {
      this.isConnected = false;
      this._setStatus('disconnected');
      this._notifyStatus('disconnected');
    };

    this.ws.onerror = () => {
      this._setStatus('error', 'WebSocket error');
      this._notifyStatus('error', 'WebSocket connection failed');
    };
  }

  /**
   * Disconnect from WebSocket
   */
  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.isConnected = false;
    this._setStatus('disconnected');
    this._showPlaceholder(true);
    this.container.querySelector('#sc-stats').style.display = 'none';
  }

  /**
   * Register frame callback
   * @param {Function} callback - (frameData) => {}
   */
  onFrame(callback) {
    this._frameCallbacks.push(callback);
  }

  /**
   * Register status callback
   * @param {Function} callback - (status, message) => {}
   */
  onStatus(callback) {
    this._statusCallbacks.push(callback);
  }

  /**
   * Destroy the instance
   */
  destroy() {
    this.disconnect();
    if (this._resizeObserver) {
      this._resizeObserver.disconnect();
      this._resizeObserver = null;
    }
    this._frameCallbacks = [];
    this._statusCallbacks = [];
    this.container.innerHTML = '';
  }

  // ============================================
  // Internal: Drawing
  // ============================================

  _drawFrame(data) {
    const { image, resolution, faces = [] } = data;

    const ctx = this.ctx;

    if (image) {
      // Image mode: decode base64 and draw
      const img = this._img;
      img.onload = () => {
        this._drawWithContext((cw, ch) => {
          const imgW = resolution?.[0] || img.naturalWidth;
          const imgH = resolution?.[1] || img.naturalHeight;
          const scale = Math.min(cw / imgW, ch / imgH);
          const drawW = imgW * scale;
          const drawH = imgH * scale;
          const offsetX = (cw - drawW) / 2;
          const offsetY = (ch - drawH) / 2;

          ctx.clearRect(0, 0, cw, ch);
          ctx.drawImage(img, offsetX, offsetY, drawW, drawH);

          for (const face of faces) {
            this._drawFace(ctx, face, scale, offsetX, offsetY);
          }
          if (data.enrollment?.active) {
            this._drawEnrollmentOverlay(ctx, data.enrollment, cw, ch);
          }
        });
      };
      img.onerror = () => {
        console.error('[serial-camera] Image decode failed, base64 length:', image?.length);
      };
      img.src = `data:image/jpeg;base64,${image}`;
    } else {
      // No image: draw text-based status display
      this._drawWithContext((cw, ch) => {
        ctx.clearRect(0, 0, cw, ch);
        ctx.fillStyle = '#1a1a2e';
        ctx.fillRect(0, 0, cw, ch);

        // Face count indicator
        const faceCount = faces.length;
        ctx.fillStyle = faceCount > 0 ? '#4ade80' : '#666';
        ctx.font = 'bold 48px sans-serif';
        ctx.textAlign = 'center';
        const icon = faceCount > 0 ? `${faceCount}` : '0';
        ctx.fillText(icon, cw / 2, ch / 2 - 20);

        ctx.font = '14px sans-serif';
        ctx.fillStyle = '#999';
        ctx.fillText(
          faceCount > 0
            ? `${faceCount} face${faceCount > 1 ? 's' : ''} detected`
            : t('serialCamera.noPreview'),
          cw / 2, ch / 2 + 20
        );
        ctx.textAlign = 'left';

        // Draw face info as text
        let y = ch / 2 + 50;
        for (const face of faces) {
          const name = face.recognized_name || 'unknown';
          const conf = (face.confidence * 100).toFixed(0);
          ctx.fillStyle = face.recognized_name ? '#4ade80' : '#facc15';
          ctx.font = '13px sans-serif';
          ctx.textAlign = 'center';
          ctx.fillText(`${name} (${conf}%)`, cw / 2, y);
          y += 20;
        }
        ctx.textAlign = 'left';

        if (data.enrollment?.active) {
          this._drawEnrollmentOverlay(ctx, data.enrollment, cw, ch);
        }
      });
    }
  }

  _drawWithContext(drawFn) {
    const ctx = this.ctx;
    const dpr = window.devicePixelRatio || 1;
    const cw = this._canvasW / dpr;
    const ch = this._canvasH / dpr;

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    drawFn(cw, ch);
    ctx.setTransform(1, 0, 0, 1, 0, 0);
  }

  _drawFace(ctx, face, scale, offsetX, offsetY) {
    const [x, y, w, h] = face.bbox;
    const sx = x * scale + offsetX;
    const sy = y * scale + offsetY;
    const sw = w * scale;
    const sh = h * scale;

    const isRecognized = face.recognized_name && face.recognized_name !== 'unknown';
    const color = isRecognized
      ? this.config.bboxColors.recognized
      : this.config.bboxColors.unknown;

    // Draw bbox
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.strokeRect(sx, sy, sw, sh);

    // Draw label
    const label = isRecognized
      ? `${face.recognized_name} (${(face.similarity * 100).toFixed(0)}%)`
      : `${(face.confidence * 100).toFixed(0)}%`;

    ctx.font = '12px sans-serif';
    const textWidth = ctx.measureText(label).width;

    ctx.fillStyle = 'rgba(0,0,0,0.6)';
    ctx.fillRect(sx, sy - 20, textWidth + 8, 20);

    ctx.fillStyle = color;
    ctx.fillText(label, sx + 4, sy - 6);

    // Draw landmarks
    if (this.config.showLandmarks && face.landmarks?.length) {
      ctx.fillStyle = '#22d3ee'; // cyan
      for (const [lx, ly] of face.landmarks) {
        ctx.beginPath();
        ctx.arc(lx * scale + offsetX, ly * scale + offsetY, 2, 0, Math.PI * 2);
        ctx.fill();
      }
    }
  }

  _drawEnrollmentOverlay(ctx, enrollment, cw, _ch) {
    // Semi-transparent banner at top
    ctx.fillStyle = 'rgba(0,0,0,0.7)';
    ctx.fillRect(0, 0, cw, 40);

    ctx.fillStyle = '#4ade80';
    ctx.font = 'bold 14px sans-serif';
    const text = `${t('serialCamera.enrolling')}: ${enrollment.name} — ${enrollment.samples}/${enrollment.min_samples} samples (${enrollment.remaining_seconds}s)`;
    ctx.fillText(text, 10, 26);
  }

  // ============================================
  // Internal: UI helpers
  // ============================================

  _setStatus(status, message = '') {
    const el = this.container.querySelector('#sc-status');
    if (!el) return;

    el.className = `serial-camera-status ${status}`;
    const text = el.querySelector('.status-text');
    if (text) {
      text.textContent = message || t(`serialCamera.status.${status}`) || status;
    }
  }

  _showPlaceholder(show) {
    const ph = this.container.querySelector('#sc-placeholder');
    if (ph) ph.style.display = show ? '' : 'none';
  }

  _updateFps() {
    this._frameCount++;
    const now = performance.now();
    if (now - this._lastFpsTime >= 1000) {
      this._fps = Math.round(this._frameCount * 1000 / (now - this._lastFpsTime));
      this._frameCount = 0;
      this._lastFpsTime = now;

      const el = this.container.querySelector('#sc-fps');
      if (el) el.textContent = this._fps;
    }
  }

  _notifyStatus(status, message = '') {
    for (const cb of this._statusCallbacks) {
      try { cb(status, message); } catch { /* ignore */ }
    }
  }
}
