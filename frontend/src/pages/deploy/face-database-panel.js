/**
 * Face Database Panel - CRUD interface for face recognition database
 *
 * Handles:
 * - Table display of enrolled faces
 * - Face registration workflow (inline enrollment panel)
 * - Rename/delete operations
 */

import { t } from '../../modules/i18n.js';
import { serialCameraApi } from '../../modules/api.js';

export class FaceDatabasePanel {
  /**
   * @param {HTMLElement} container
   * @param {Object} config
   * @param {string} config.sessionId - Backend session ID
   */
  constructor(container, config = {}) {
    this.container = container;
    this.sessionId = config.sessionId || null;
    this._faces = [];
    this._maxFaces = 20;
    this._enrolling = false;
    this._enrollmentData = null;
    this._frameCallback = null;

    this._render();
    this._bindEvents();
  }

  setSessionId(id) {
    this.sessionId = id;
    if (id) this.refresh();
  }

  /**
   * Register frame callback to track enrollment progress from camera
   * @param {Function} callback - Sets up the frame watcher
   */
  onFrameUpdate(data) {
    if (data.enrollment) {
      this._updateEnrollmentProgress(data.enrollment);
    }
  }

  async refresh() {
    if (!this.sessionId) return;

    try {
      const result = await serialCameraApi.listFaces(this.sessionId);
      if (result.ok !== false) {
        this._faces = result.faces || [];
        this._maxFaces = result.max || 20;
        this._renderTable();
      }
    } catch (e) {
      console.error('Failed to refresh face list:', e);
    }
  }

  destroy() {
    this.container.innerHTML = '';
  }

  // ============================================
  // Rendering
  // ============================================

  _render() {
    this.container.innerHTML = `
      <div class="face-database-panel">
        <div class="face-database-header">
          <h4 class="face-database-title">${t('faceDatabase.title')}</h4>
          <button class="btn btn-sm btn-primary" id="fdb-register-btn">
            + ${t('faceDatabase.register')}
          </button>
        </div>
        <div id="fdb-table-container">
          <div class="face-database-empty">${t('faceDatabase.empty')}</div>
        </div>
        <div class="face-database-count" id="fdb-count"></div>
        <div id="fdb-enrollment-panel" style="display:none">
          <div class="enrollment-panel">
            <div class="enrollment-input-row">
              <label>${t('faceDatabase.name')}:</label>
              <input type="text" id="fdb-name-input" class="form-input" placeholder="${t('faceDatabase.namePlaceholder')}" />
              <button class="btn btn-sm btn-primary" id="fdb-start-capture-btn">
                ${t('faceDatabase.startCapture')}
              </button>
              <button class="btn btn-sm btn-secondary" id="fdb-cancel-btn">
                ${t('common.cancel')}
              </button>
            </div>
            <div id="fdb-enrollment-progress" style="display:none">
              <div class="enrollment-progress">
                <div class="enrollment-progress-bar" id="fdb-progress-bar" style="width:0%"></div>
              </div>
              <div class="enrollment-status" id="fdb-enrollment-status"></div>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  _renderTable() {
    const container = this.container.querySelector('#fdb-table-container');
    const countEl = this.container.querySelector('#fdb-count');

    if (!this._faces.length) {
      container.innerHTML = `<div class="face-database-empty">${t('faceDatabase.empty')}</div>`;
      countEl.textContent = t('faceDatabase.enrolled', { count: 0, max: this._maxFaces });
      return;
    }

    const rows = this._faces.map(face => `
      <tr>
        <td>${face.index}</td>
        <td>${this._escapeHtml(face.name)}</td>
        <td class="face-database-actions">
          <button class="btn btn-xs btn-secondary fdb-rename-btn" data-name="${this._escapeHtml(face.name)}">${t('faceDatabase.rename')}</button>
          <button class="btn btn-xs btn-danger fdb-delete-btn" data-name="${this._escapeHtml(face.name)}">${t('faceDatabase.delete')}</button>
        </td>
      </tr>
    `).join('');

    container.innerHTML = `
      <table class="face-database-table">
        <thead>
          <tr>
            <th>#</th>
            <th>${t('faceDatabase.nameColumn')}</th>
            <th>${t('faceDatabase.actionsColumn')}</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    `;

    countEl.textContent = t('faceDatabase.enrolled', { count: this._faces.length, max: this._maxFaces });

    // Bind action buttons
    container.querySelectorAll('.fdb-rename-btn').forEach(btn => {
      btn.addEventListener('click', () => this._handleRename(btn.dataset.name));
    });
    container.querySelectorAll('.fdb-delete-btn').forEach(btn => {
      btn.addEventListener('click', () => this._handleDelete(btn.dataset.name));
    });
  }

  // ============================================
  // Event Handlers
  // ============================================

  _bindEvents() {
    this.container.querySelector('#fdb-register-btn')?.addEventListener('click', () => {
      this._showEnrollmentPanel(true);
    });

    this.container.querySelector('#fdb-start-capture-btn')?.addEventListener('click', () => {
      this._handleStartCapture();
    });

    this.container.querySelector('#fdb-cancel-btn')?.addEventListener('click', () => {
      this._handleCancelCapture();
    });
  }

  _showEnrollmentPanel(show) {
    const panel = this.container.querySelector('#fdb-enrollment-panel');
    if (panel) panel.style.display = show ? '' : 'none';

    if (show) {
      const input = this.container.querySelector('#fdb-name-input');
      if (input) {
        input.value = '';
        input.focus();
      }
    }

    // Reset progress
    const progress = this.container.querySelector('#fdb-enrollment-progress');
    if (progress) progress.style.display = 'none';
  }

  async _handleStartCapture() {
    const nameInput = this.container.querySelector('#fdb-name-input');
    const name = nameInput?.value?.trim();

    if (!name) {
      nameInput?.focus();
      return;
    }

    if (!this.sessionId) return;

    try {
      this._enrolling = true;
      const progress = this.container.querySelector('#fdb-enrollment-progress');
      if (progress) progress.style.display = '';

      const startBtn = this.container.querySelector('#fdb-start-capture-btn');
      if (startBtn) {
        startBtn.disabled = true;
        startBtn.textContent = t('faceDatabase.capturing');
      }

      await serialCameraApi.startEnrollment(this.sessionId, name);

      // Enrollment progress will be tracked via frame updates
      this._enrollmentData = { name, startTime: Date.now() };

    } catch (e) {
      console.error('Failed to start enrollment:', e);
      this._resetEnrollmentUI();
    }
  }

  async _handleCancelCapture() {
    if (this._enrolling && this.sessionId) {
      try {
        await serialCameraApi.cancelEnrollment(this.sessionId);
      } catch {
        // ignore
      }
    }
    this._enrolling = false;
    this._enrollmentData = null;
    this._showEnrollmentPanel(false);
    this._resetEnrollmentUI();
  }

  _updateEnrollmentProgress(enrollment) {
    if (!enrollment.active && this._enrolling) {
      // Enrollment finished
      this._enrolling = false;
      this._enrollmentData = null;
      this._resetEnrollmentUI();
      this._showEnrollmentPanel(false);

      // Refresh table to show new face
      setTimeout(() => this.refresh(), 500);
      return;
    }

    if (!enrollment.active) return;

    const progressBar = this.container.querySelector('#fdb-progress-bar');
    const statusEl = this.container.querySelector('#fdb-enrollment-status');

    if (progressBar && enrollment.min_samples > 0) {
      const pct = Math.min(100, (enrollment.samples / enrollment.min_samples) * 100);
      progressBar.style.width = `${pct}%`;
    }

    if (statusEl) {
      statusEl.textContent = t('faceDatabase.capturingStatus', {
        samples: enrollment.samples,
        minSamples: enrollment.min_samples,
        seconds: enrollment.remaining_seconds,
      });
    }
  }

  _resetEnrollmentUI() {
    const startBtn = this.container.querySelector('#fdb-start-capture-btn');
    if (startBtn) {
      startBtn.disabled = false;
      startBtn.textContent = t('faceDatabase.startCapture');
    }

    const progressBar = this.container.querySelector('#fdb-progress-bar');
    if (progressBar) progressBar.style.width = '0%';
  }

  async _handleDelete(name) {
    if (!confirm(t('faceDatabase.deleteConfirm', { name }))) return;
    if (!this.sessionId) return;

    try {
      await serialCameraApi.deleteFace(this.sessionId, name);
      await this.refresh();
    } catch (e) {
      console.error('Failed to delete face:', e);
    }
  }

  async _handleRename(name) {
    const newName = prompt(t('faceDatabase.renamePrompt', { name }));
    if (!newName || newName === name) return;
    if (!this.sessionId) return;

    try {
      await serialCameraApi.renameFace(this.sessionId, name, newName);
      await this.refresh();
    } catch (e) {
      console.error('Failed to rename face:', e);
    }
  }

  _escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }
}
