/**
 * Updater Module - OTA update functionality for Tauri desktop app
 */

import { t, i18n } from './i18n.js';
import { toast } from './toast.js';

class UpdateManager {
  constructor() {
    this.updateInfo = null;
    this.isChecking = false;
    this.isDownloading = false;
    this.downloadProgress = 0;
    this.modalElement = null;
  }

  /**
   * Check for updates silently on startup
   * Only shows notification if update is available
   */
  async checkForUpdates(silent = true) {
    // Only check in Tauri environment
    if (!window.__TAURI__) {
      console.log('[Updater] Not in Tauri environment, skipping update check');
      return null;
    }

    if (this.isChecking) {
      console.log('[Updater] Update check already in progress');
      return null;
    }

    this.isChecking = true;

    try {
      const { check } = await import('@tauri-apps/plugin-updater');

      console.log('[Updater] Checking for updates...');
      const update = await check();

      if (update) {
        console.log('[Updater] Update available:', update.version);
        this.updateInfo = update;

        if (!silent) {
          this.showUpdateDialog();
        } else {
          this.showUpdateNotification();
        }

        return update;
      } else {
        console.log('[Updater] No updates available');
        if (!silent) {
          toast.info(t('updater.noUpdates'));
        }
        return null;
      }
    } catch (error) {
      console.error('[Updater] Update check failed:', error);
      if (!silent) {
        toast.error(t('updater.checkFailed'));
      }
      return null;
    } finally {
      this.isChecking = false;
    }
  }

  /**
   * Show a subtle notification about available update
   */
  showUpdateNotification() {
    if (!this.updateInfo) return;

    const notification = document.createElement('div');
    notification.className = 'update-notification';
    notification.innerHTML = `
      <div class="update-notification-content">
        <span class="update-notification-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
        </span>
        <span class="update-notification-text">
          ${t('updater.updateAvailable', { version: this.updateInfo.version })}
        </span>
        <button class="update-notification-btn" id="update-view-btn">
          ${t('updater.viewUpdate')}
        </button>
        <button class="update-notification-close" id="update-dismiss-btn">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>
    `;

    document.body.appendChild(notification);

    // Add event listeners
    notification.querySelector('#update-view-btn').addEventListener('click', () => {
      notification.remove();
      this.showUpdateDialog();
    });

    notification.querySelector('#update-dismiss-btn').addEventListener('click', () => {
      notification.classList.add('dismissed');
      setTimeout(() => notification.remove(), 300);
    });
  }

  /**
   * Show update dialog with version info and download option
   */
  showUpdateDialog() {
    if (!this.updateInfo) return;

    // Remove existing modal if any
    if (this.modalElement) {
      this.modalElement.remove();
    }

    const modal = document.createElement('div');
    modal.className = 'modal-overlay update-modal';
    modal.innerHTML = `
      <div class="modal update-dialog">
        <div class="modal-header">
          <h3>${t('updater.title')}</h3>
          <button class="modal-close" id="update-modal-close">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
        <div class="modal-body">
          <div class="update-info">
            <div class="update-version">
              <span class="update-version-label">${t('updater.newVersion')}</span>
              <span class="update-version-number">${this.updateInfo.version}</span>
            </div>
            ${this.updateInfo.body ? `
              <div class="update-notes">
                <h4>${t('updater.releaseNotes')}</h4>
                <div class="update-notes-content">${this.formatReleaseNotes(this.updateInfo.body)}</div>
              </div>
            ` : ''}
          </div>
          <div class="update-progress hidden" id="update-progress-container">
            <div class="progress-bar">
              <div class="progress-fill" id="update-progress-fill" style="width: 0%"></div>
            </div>
            <span class="progress-text" id="update-progress-text">0%</span>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" id="update-later-btn">${t('updater.later')}</button>
          <button class="btn btn-primary" id="update-download-btn">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="7 10 12 15 17 10"/>
              <line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
            ${t('updater.downloadInstall')}
          </button>
        </div>
      </div>
    `;

    document.body.appendChild(modal);
    this.modalElement = modal;

    // Event listeners
    modal.querySelector('#update-modal-close').addEventListener('click', () => this.closeDialog());
    modal.querySelector('#update-later-btn').addEventListener('click', () => this.closeDialog());
    modal.querySelector('#update-download-btn').addEventListener('click', () => this.downloadAndInstall());

    // Close on overlay click
    modal.addEventListener('click', (e) => {
      if (e.target === modal) this.closeDialog();
    });
  }

  /**
   * Format release notes from markdown to HTML
   */
  formatReleaseNotes(notes) {
    // Simple markdown formatting
    return notes
      .replace(/^### (.+)$/gm, '<h5>$1</h5>')
      .replace(/^## (.+)$/gm, '<h4>$1</h4>')
      .replace(/^- (.+)$/gm, '<li>$1</li>')
      .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\n\n/g, '<br><br>')
      .replace(/\n/g, '<br>');
  }

  /**
   * Close the update dialog
   */
  closeDialog() {
    if (this.modalElement) {
      this.modalElement.classList.add('closing');
      setTimeout(() => {
        this.modalElement?.remove();
        this.modalElement = null;
      }, 200);
    }
  }

  /**
   * Download and install the update
   */
  async downloadAndInstall() {
    if (!this.updateInfo || this.isDownloading) return;

    this.isDownloading = true;

    const downloadBtn = this.modalElement?.querySelector('#update-download-btn');
    const laterBtn = this.modalElement?.querySelector('#update-later-btn');
    const progressContainer = this.modalElement?.querySelector('#update-progress-container');
    const progressFill = this.modalElement?.querySelector('#update-progress-fill');
    const progressText = this.modalElement?.querySelector('#update-progress-text');

    if (downloadBtn) {
      downloadBtn.disabled = true;
      downloadBtn.innerHTML = `
        <svg class="spinner" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10" stroke-dasharray="60" stroke-dashoffset="20"/>
        </svg>
        ${t('updater.downloading')}
      `;
    }
    if (laterBtn) laterBtn.disabled = true;
    if (progressContainer) progressContainer.classList.remove('hidden');

    try {
      let downloaded = 0;
      let contentLength = 0;

      // Download with progress tracking
      await this.updateInfo.downloadAndInstall((event) => {
        switch (event.event) {
          case 'Started':
            contentLength = event.data.contentLength || 0;
            console.log(`[Updater] Download started, total size: ${contentLength} bytes`);
            break;
          case 'Progress':
            downloaded += event.data.chunkLength;
            if (contentLength > 0) {
              this.downloadProgress = Math.round((downloaded / contentLength) * 100);
              if (progressFill) progressFill.style.width = `${this.downloadProgress}%`;
              if (progressText) progressText.textContent = `${this.downloadProgress}%`;
            }
            break;
          case 'Finished':
            console.log('[Updater] Download finished');
            if (progressFill) progressFill.style.width = '100%';
            if (progressText) progressText.textContent = '100%';
            break;
        }
      });

      // Show restart prompt
      if (downloadBtn) {
        downloadBtn.innerHTML = `
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="23 4 23 10 17 10"/>
            <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
          </svg>
          ${t('updater.restartNow')}
        `;
        downloadBtn.disabled = false;
        downloadBtn.onclick = async () => {
          const { relaunch } = await import('@tauri-apps/plugin-process');
          await relaunch();
        };
      }

      toast.success(t('updater.downloadComplete'));

    } catch (error) {
      console.error('[Updater] Download failed:', error);
      toast.error(t('updater.downloadFailed'));

      if (downloadBtn) {
        downloadBtn.disabled = false;
        downloadBtn.innerHTML = `
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          ${t('updater.retry')}
        `;
      }
      if (laterBtn) laterBtn.disabled = false;
    } finally {
      this.isDownloading = false;
    }
  }
}

// Export singleton
export const updater = new UpdateManager();

// Add styles for update UI
const style = document.createElement('style');
style.textContent = `
  /* Update notification banner */
  .update-notification {
    position: fixed;
    bottom: 24px;
    right: 24px;
    background: linear-gradient(135deg, #8CC63F 0%, #6BA32D 100%);
    color: white;
    padding: 12px 16px;
    border-radius: 12px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
    z-index: 10000;
    animation: slideInUp 0.3s ease;
  }

  .update-notification.dismissed {
    animation: slideOutDown 0.3s ease forwards;
  }

  .update-notification-content {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .update-notification-icon {
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .update-notification-text {
    font-size: 14px;
    font-weight: 500;
  }

  .update-notification-btn {
    background: rgba(255, 255, 255, 0.2);
    border: none;
    color: white;
    padding: 6px 12px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: background 0.2s;
  }

  .update-notification-btn:hover {
    background: rgba(255, 255, 255, 0.3);
  }

  .update-notification-close {
    background: none;
    border: none;
    color: rgba(255, 255, 255, 0.7);
    padding: 4px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 4px;
    transition: all 0.2s;
  }

  .update-notification-close:hover {
    background: rgba(255, 255, 255, 0.1);
    color: white;
  }

  /* Update dialog */
  .update-modal .modal {
    max-width: 480px;
    width: 90%;
  }

  .update-dialog .modal-header h3 {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .update-info {
    padding: 16px 0;
  }

  .update-version {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 16px;
    background: var(--bg-secondary, #f5f5f5);
    border-radius: 8px;
    margin-bottom: 16px;
  }

  .update-version-label {
    font-size: 14px;
    color: var(--text-secondary, #666);
  }

  .update-version-number {
    font-size: 18px;
    font-weight: 600;
    color: var(--primary, #8CC63F);
  }

  .update-notes {
    border-top: 1px solid var(--border, #e5e5e5);
    padding-top: 16px;
  }

  .update-notes h4 {
    font-size: 14px;
    font-weight: 600;
    margin-bottom: 12px;
    color: var(--text-primary, #1a1a1a);
  }

  .update-notes-content {
    font-size: 13px;
    line-height: 1.6;
    color: var(--text-secondary, #666);
    max-height: 200px;
    overflow-y: auto;
  }

  .update-notes-content h4,
  .update-notes-content h5 {
    margin: 12px 0 8px;
    color: var(--text-primary, #1a1a1a);
  }

  .update-notes-content ul {
    margin: 8px 0;
    padding-left: 20px;
  }

  .update-notes-content li {
    margin: 4px 0;
  }

  /* Progress bar */
  .update-progress {
    margin-top: 16px;
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .update-progress.hidden {
    display: none;
  }

  .progress-bar {
    flex: 1;
    height: 8px;
    background: var(--bg-secondary, #f0f0f0);
    border-radius: 4px;
    overflow: hidden;
  }

  .progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #8CC63F, #6BA32D);
    border-radius: 4px;
    transition: width 0.3s ease;
  }

  .progress-text {
    font-size: 13px;
    font-weight: 500;
    color: var(--text-secondary, #666);
    min-width: 40px;
    text-align: right;
  }

  /* Button spinner */
  .btn .spinner {
    animation: spin 1s linear infinite;
    margin-right: 4px;
  }

  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }

  @keyframes slideInUp {
    from {
      transform: translateY(100%);
      opacity: 0;
    }
    to {
      transform: translateY(0);
      opacity: 1;
    }
  }

  @keyframes slideOutDown {
    from {
      transform: translateY(0);
      opacity: 1;
    }
    to {
      transform: translateY(100%);
      opacity: 0;
    }
  }

  /* Modal closing animation */
  .modal-overlay.closing {
    animation: fadeOut 0.2s ease forwards;
  }

  .modal-overlay.closing .modal {
    animation: scaleOut 0.2s ease forwards;
  }

  @keyframes fadeOut {
    to { opacity: 0; }
  }

  @keyframes scaleOut {
    to {
      transform: scale(0.95);
      opacity: 0;
    }
  }
`;
document.head.appendChild(style);
