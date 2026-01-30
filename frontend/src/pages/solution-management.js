/**
 * Solution Management Page
 * Provides structured management for solutions with tab-based UI
 * - Basic Info: name, summary, category, tags, links, required devices
 * - Content Files: 4 core markdown files (guide.md, description.md)
 * - Assets: file browser for solution resources
 * - Preview: structure preview from guide.md
 */

import { solutionsApi, devicesApi, getAssetUrl } from '../modules/api.js';
import { t, i18n, getLocalizedField } from '../modules/i18n.js';
import { toast } from '../modules/toast.js';

// State
let solutions = [];
let isLoading = false;
let editingSolution = null;
let solutionStructure = null;
let deviceCatalog = [];
let activeTab = 'basic';

// Constants
const SOLUTION_ID_PATTERN = /^[a-z][a-z0-9_]*$/;
const CATEGORIES = ['general', 'voice_ai', 'sensing', 'automation', 'vision', 'smart_building', 'industrial_iot'];
const DIFFICULTIES = ['beginner', 'intermediate', 'advanced'];
const CONTENT_FILES = [
  { name: 'guide.md', label: 'Deploy Guide (EN)', group: 'deploy' },
  { name: 'guide_zh.md', label: 'Deploy Guide (ZH)', group: 'deploy' },
  { name: 'description.md', label: 'Introduction (EN)', group: 'intro' },
  { name: 'description_zh.md', label: 'Introduction (ZH)', group: 'intro' },
];

/**
 * Flatten tree structure to flat array of files
 * @param {Array} tree - Tree structure from list_files API
 * @returns {Array} Flat array of files with path, name, size, type
 */
function flattenFileTree(tree) {
  const files = [];
  function traverse(items) {
    for (const item of items) {
      if (item.type === 'directory' && item.children) {
        traverse(item.children);
      } else if (item.type === 'file') {
        files.push({
          path: item.path,
          name: item.name,
          size: item.size || 0,
          type: item.extension && ['.md', '.txt', '.yaml', '.yml', '.json', '.js', '.py', '.html', '.css'].includes(item.extension) ? 'text' : 'binary'
        });
      }
    }
  }
  traverse(tree || []);
  return files;
}

/**
 * Load solution structure with files list
 * @param {string} solutionId - Solution ID
 * @returns {Promise<Object>} Structure with files array
 */
async function loadSolutionStructure(solutionId) {
  const [structure, filesResult] = await Promise.all([
    solutionsApi.getStructure(solutionId),
    solutionsApi.listFiles(solutionId)
  ]);
  structure.files = flattenFileTree(filesResult.files);
  return structure;
}

/**
 * Load device catalog
 */
async function loadDeviceCatalog() {
  if (deviceCatalog.length > 0) return deviceCatalog;
  try {
    const result = await devicesApi.getCatalog();
    deviceCatalog = result.devices || [];
    return deviceCatalog;
  } catch (error) {
    console.error('Failed to load device catalog:', error);
    return [];
  }
}

/**
 * Render the Solution Management page
 */
export async function renderManagementPage() {
  const container = document.getElementById('content-area');
  container.innerHTML = `
    <div class="management-page">
      <div class="page-header">
        <div>
          <h1 class="page-title">${t('management.title')}</h1>
          <p class="page-subtitle text-text-secondary">${t('management.subtitle')}</p>
        </div>
        <button class="btn btn-primary" id="btn-new-solution">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
          ${t('management.newSolution')}
        </button>
      </div>

      <div class="management-table-container" id="solutions-table-container">
        <div class="loading-spinner">${t('common.loading')}</div>
      </div>
    </div>
  `;

  document.getElementById('btn-new-solution').addEventListener('click', () => openModal());
  await loadSolutions();
  i18n.onLocaleChange(() => renderManagementPage());
}

/**
 * Load solutions list
 */
async function loadSolutions() {
  isLoading = true;
  const container = document.getElementById('solutions-table-container');

  try {
    solutions = await solutionsApi.list(i18n.locale);
    renderSolutionsTable();
  } catch (error) {
    console.error('Failed to load solutions:', error);
    container.innerHTML = `
      <div class="empty-state">
        <p class="text-danger">${t('common.error')}: ${error.message}</p>
        <button class="btn btn-secondary" onclick="location.reload()">
          ${t('common.retry')}
        </button>
      </div>
    `;
  } finally {
    isLoading = false;
  }
}

/**
 * Render the solutions table
 */
function renderSolutionsTable() {
  const container = document.getElementById('solutions-table-container');
  if (!container) return;

  if (solutions.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="text-text-muted mb-4">
          <rect x="3" y="3" width="18" height="18" rx="2"/>
          <line x1="12" y1="8" x2="12" y2="16"/>
          <line x1="8" y1="12" x2="16" y2="12"/>
        </svg>
        <p class="text-text-secondary">${t('solutions.empty')}</p>
        <p class="text-sm text-text-muted">${t('solutions.emptyDescription')}</p>
      </div>
    `;
    return;
  }

  container.innerHTML = `
    <table class="management-table">
      <thead>
        <tr>
          <th>${t('management.table.id')}</th>
          <th>${t('management.table.name')}</th>
          <th>${t('management.table.category')}</th>
          <th>${t('management.table.difficulty')}</th>
          <th>${t('management.table.actions')}</th>
        </tr>
      </thead>
      <tbody>
        ${solutions.map(solution => `
          <tr data-id="${solution.id}">
            <td class="font-mono text-sm">${solution.id}</td>
            <td>
              <div class="solution-name-cell">
                ${solution.cover_image ? `<img src="${getAssetUrl(solution.id, solution.cover_image)}" alt="" class="solution-thumb">` : ''}
                <span>${getLocalizedField(solution, 'name')}</span>
              </div>
            </td>
            <td>
              <span class="category-badge category-${solution.category}">
                ${t(`management.categories.${solution.category}`) || solution.category}
              </span>
            </td>
            <td>
              <span class="difficulty-badge difficulty-${solution.difficulty}">
                ${t(`solutions.difficulty.${solution.difficulty}`)}
              </span>
            </td>
            <td>
              <div class="table-actions">
                <button class="btn-icon" title="${t('management.actions.edit')}" data-action="edit" data-id="${solution.id}">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                  </svg>
                </button>
                <button class="btn-icon btn-icon-danger" title="${t('management.actions.delete')}" data-action="delete" data-id="${solution.id}">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="3 6 5 6 21 6"/>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                  </svg>
                </button>
              </div>
            </td>
          </tr>
        `).join('')}
      </tbody>
    </table>
  `;

  container.querySelectorAll('[data-action]').forEach(btn => {
    btn.addEventListener('click', () => {
      const action = btn.dataset.action;
      const id = btn.dataset.id;
      if (action === 'edit') {
        const solution = solutions.find(s => s.id === id);
        openModal(solution);
      } else if (action === 'delete') {
        confirmDelete(id);
      }
    });
  });
}

/**
 * Open create/edit modal
 */
async function openModal(solution = null) {
  editingSolution = solution;
  solutionStructure = null;
  activeTab = 'basic';
  const isEdit = !!solution;

  // Load device catalog
  await loadDeviceCatalog();

  // Load structure and files for edit mode
  if (isEdit) {
    try {
      solutionStructure = await loadSolutionStructure(solution.id);
    } catch (error) {
      console.error('Failed to load solution structure:', error);
      toast.error(t('common.error'));
      return;
    }
  }

  renderModal(isEdit);
}

/**
 * Render modal content
 */
function renderModal(isEdit) {
  const solution = editingSolution;
  const structure = solutionStructure;

  // Tab structure: Basic Info always, others only in edit mode
  const tabs = isEdit
    ? ['basic', 'contentFiles', 'assets', 'preview']
    : ['basic'];

  const modalHtml = `
    <div class="modal" id="solution-modal">
      <div class="modal-content modal-xl">
        <div class="modal-header">
          <h3>${isEdit ? t('management.editSolution') : t('management.newSolution')}</h3>
          <button class="close-btn" id="modal-close">&times;</button>
        </div>

        ${isEdit ? `
        <div class="modal-tabs">
          <button class="tab-btn ${activeTab === 'basic' ? 'active' : ''}" data-tab="basic">
            ${t('management.tabs.basicInfo')}
          </button>
          <button class="tab-btn ${activeTab === 'contentFiles' ? 'active' : ''}" data-tab="contentFiles">
            ${t('management.tabs.contentFiles')}
          </button>
          <button class="tab-btn ${activeTab === 'assets' ? 'active' : ''}" data-tab="assets">
            ${t('management.tabs.assets')}
          </button>
          <button class="tab-btn ${activeTab === 'preview' ? 'active' : ''}" data-tab="preview">
            ${t('management.tabs.preview')}
          </button>
        </div>
        ` : ''}

        <div class="modal-body">
          <div class="tab-content ${activeTab === 'basic' ? 'active' : ''}" data-tab-content="basic">
            ${renderBasicInfoTab(solution, structure)}
          </div>
          ${isEdit ? `
          <div class="tab-content ${activeTab === 'contentFiles' ? 'active' : ''}" data-tab-content="contentFiles">
            ${renderContentFilesTab(structure)}
          </div>
          <div class="tab-content ${activeTab === 'assets' ? 'active' : ''}" data-tab-content="assets">
            ${renderAssetsTab(structure)}
          </div>
          <div class="tab-content ${activeTab === 'preview' ? 'active' : ''}" data-tab-content="preview">
            ${renderPreviewTab(structure)}
          </div>
          ` : ''}
        </div>

        <div class="modal-footer">
          <button class="btn btn-secondary" id="btn-cancel">${t('management.actions.cancel')}</button>
          <button class="btn btn-primary" id="btn-save">
            ${isEdit ? t('management.actions.save') : t('management.actions.create')}
          </button>
        </div>
      </div>
    </div>
  `;

  const modalContainer = document.getElementById('modal-container');
  modalContainer.innerHTML = modalHtml;

  // Bind events
  document.getElementById('modal-close').addEventListener('click', closeModal);
  document.getElementById('btn-cancel').addEventListener('click', closeModal);
  document.getElementById('btn-save').addEventListener('click', saveSolution);
  document.getElementById('solution-modal').addEventListener('click', (e) => {
    if (e.target.id === 'solution-modal') closeModal();
  });

  // Tab switching
  if (isEdit) {
    document.querySelectorAll('.tab-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        activeTab = btn.dataset.tab;
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        btn.classList.add('active');
        document.querySelector(`[data-tab-content="${activeTab}"]`).classList.add('active');

        // Load preview when tab is activated
        if (activeTab === 'preview') {
          loadPreviewStructure();
        }
      });
    });

    setupContentFilesTab();
    setupAssetsTab();
  }

  // ID validation for new solutions
  const idInput = document.getElementById('solution-id');
  if (idInput && !isEdit) {
    idInput.addEventListener('input', (e) => {
      const value = e.target.value;
      if (value && !SOLUTION_ID_PATTERN.test(value)) {
        idInput.setCustomValidity(t('management.messages.invalidId'));
      } else {
        idInput.setCustomValidity('');
      }
    });
  }

  // Setup tags, links, and required devices in basic info
  if (isEdit) {
    setupTagsEditor();
    setupLinksEditor();
    setupRequiredDevicesSelector();
    setupFileUploads();
  }
}

/**
 * Render Basic Info tab content
 */
function renderBasicInfoTab(solution, structure) {
  const isEdit = !!solution;
  const tags = structure?.intro?.tags || [];
  const links = structure?.intro?.links || {};
  const requiredDevices = structure?.intro?.required_devices || [];

  return `
    <form id="solution-form">
      <div class="form-section">
        <h4 class="form-section-title">${t('management.form.basicInfo')}</h4>

        <div class="form-group">
          <label for="solution-id">${t('management.form.id')} *</label>
          <input type="text" id="solution-id" name="id"
                 value="${solution?.id || ''}"
                 ${isEdit ? 'disabled' : ''}
                 placeholder="my_solution_name"
                 pattern="^[a-z][a-z0-9_]*$"
                 required>
          <p class="form-hint">${t('management.form.idHint')}</p>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label for="solution-name">${t('management.form.nameEn')} *</label>
            <input type="text" id="solution-name" name="name"
                   value="${solution?.name || ''}" required>
          </div>
          <div class="form-group">
            <label for="solution-name-zh">${t('management.form.nameZh')}</label>
            <input type="text" id="solution-name-zh" name="name_zh"
                   value="${solution?.name_zh || ''}">
          </div>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label for="solution-summary">${t('management.form.summaryEn')} *</label>
            <textarea id="solution-summary" name="summary" rows="2" required>${solution?.summary || ''}</textarea>
          </div>
          <div class="form-group">
            <label for="solution-summary-zh">${t('management.form.summaryZh')}</label>
            <textarea id="solution-summary-zh" name="summary_zh" rows="2">${solution?.summary_zh || ''}</textarea>
          </div>
        </div>

        <div class="form-row form-row-3">
          <div class="form-group">
            <label for="solution-category">${t('management.form.category')}</label>
            <select id="solution-category" name="category">
              ${CATEGORIES.map(cat => `
                <option value="${cat}" ${solution?.category === cat ? 'selected' : ''}>
                  ${t(`management.categories.${cat}`)}
                </option>
              `).join('')}
            </select>
          </div>
          <div class="form-group">
            <label for="solution-difficulty">${t('management.form.difficulty')}</label>
            <select id="solution-difficulty" name="difficulty">
              ${DIFFICULTIES.map(diff => `
                <option value="${diff}" ${solution?.difficulty === diff ? 'selected' : ''}>
                  ${t(`solutions.difficulty.${diff}`)}
                </option>
              `).join('')}
            </select>
          </div>
          <div class="form-group">
            <label for="solution-time">${t('management.form.estimatedTime')}</label>
            <input type="text" id="solution-time" name="estimated_time"
                   value="${solution?.estimated_time || '30min'}" placeholder="30min">
          </div>
        </div>
      </div>

      ${isEdit ? `
      <div class="form-section">
        <h4 class="form-section-title">${t('management.devices.title')}</h4>
        <p class="form-hint mb-4">${t('management.devices.subtitle')}</p>
        <div class="required-devices-editor" id="required-devices-editor">
          <div class="required-devices-list" id="required-devices-list">
            ${requiredDevices.map(device => renderRequiredDeviceItem(device)).join('')}
          </div>
          <div class="add-device-wrapper">
            <select id="add-device-select" class="device-select">
              <option value="">${t('management.devices.searchDevices')}</option>
              ${deviceCatalog.map(d => `
                <option value="${d.id}">${d.name} (${d.id})</option>
              `).join('')}
            </select>
            <button type="button" class="btn btn-sm btn-secondary" id="btn-add-device">
              + ${t('management.devices.addDevice')}
            </button>
          </div>
        </div>
      </div>

      <div class="form-section">
        <h4 class="form-section-title">${t('management.form.tags')}</h4>
        <div class="tags-editor" id="tags-editor">
          <div class="tags-list">
            ${tags.map(tag => `
              <span class="tag-item">
                ${tag}
                <button type="button" class="tag-remove" data-tag="${tag}">&times;</button>
              </span>
            `).join('')}
          </div>
          <div class="tag-input-wrapper">
            <input type="text" id="new-tag-input" placeholder="${t('management.form.addTag')}">
            <button type="button" class="btn btn-sm btn-secondary" id="btn-add-tag">+</button>
          </div>
        </div>
      </div>

      <div class="form-section">
        <h4 class="form-section-title">${t('management.form.links')}</h4>
        <div class="form-row">
          <div class="form-group">
            <label for="link-wiki">Wiki URL</label>
            <input type="url" id="link-wiki" value="${links.wiki || ''}" placeholder="https://wiki.seeedstudio.com/...">
          </div>
          <div class="form-group">
            <label for="link-github">GitHub URL</label>
            <input type="url" id="link-github" value="${links.github || ''}" placeholder="https://github.com/...">
          </div>
        </div>
        <button type="button" class="btn btn-secondary btn-sm" id="btn-save-links">${t('management.actions.saveLinks')}</button>
      </div>

      <div class="form-section">
        <h4 class="form-section-title">${t('management.form.files')}</h4>
        <div class="form-group">
          <label>${t('management.form.coverImage')}</label>
          <div class="file-upload-area" data-field="intro.cover_image" data-path="gallery/cover.png" data-accept="image/*">
            <div class="file-upload-content">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="3" width="18" height="18" rx="2"/>
                <circle cx="8.5" cy="8.5" r="1.5"/>
                <path d="m21 15-5-5L5 21"/>
              </svg>
              <p>${t('management.form.dropOrClick')}</p>
              ${solution?.cover_image ? `<span class="file-uploaded">${t('management.form.uploaded')}: ${solution.cover_image}</span>` : ''}
            </div>
            <input type="file" class="file-input" accept="image/*">
          </div>
        </div>
      </div>
      ` : ''}
    </form>
  `;
}

/**
 * Render a required device item
 */
function renderRequiredDeviceItem(device) {
  return `
    <div class="required-device-item" data-device-id="${device.id || device}">
      <div class="device-info">
        <span class="device-name">${device.name || device.id || device}</span>
        <span class="device-id text-text-muted">${device.id || device}</span>
      </div>
      <button type="button" class="btn-icon btn-icon-sm btn-icon-danger remove-device" data-device-id="${device.id || device}">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="18" y1="6" x2="6" y2="18"></line>
          <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>
      </button>
    </div>
  `;
}

/**
 * Setup required devices selector
 */
function setupRequiredDevicesSelector() {
  const container = document.getElementById('required-devices-editor');
  if (!container) return;

  const addBtn = document.getElementById('btn-add-device');
  const select = document.getElementById('add-device-select');

  addBtn?.addEventListener('click', async () => {
    const deviceId = select.value;
    if (!deviceId) {
      toast.error(t('management.devices.selectFirst'));
      return;
    }

    // Get current device IDs
    const currentIds = Array.from(
      document.querySelectorAll('#required-devices-list .required-device-item')
    ).map(el => el.dataset.deviceId);

    if (currentIds.includes(deviceId)) {
      toast.error(t('management.devices.alreadyAdded'));
      return;
    }

    const newIds = [...currentIds, deviceId];

    try {
      const updatedDevices = await solutionsApi.updateRequiredDevices(editingSolution.id, newIds);
      solutionStructure.intro.required_devices = updatedDevices;

      // Find the device in catalog
      const device = deviceCatalog.find(d => d.id === deviceId) || { id: deviceId, name: deviceId };
      const list = document.getElementById('required-devices-list');
      list.insertAdjacentHTML('beforeend', renderRequiredDeviceItem(device));

      select.value = '';
      toast.success(t('management.messages.devicesUpdated'));
    } catch (error) {
      toast.error(error.message);
    }
  });

  // Remove device
  container.addEventListener('click', async (e) => {
    const removeBtn = e.target.closest('.remove-device');
    if (!removeBtn) return;

    const deviceId = removeBtn.dataset.deviceId;
    const currentIds = Array.from(
      document.querySelectorAll('#required-devices-list .required-device-item')
    ).map(el => el.dataset.deviceId);

    const newIds = currentIds.filter(id => id !== deviceId);

    try {
      const updatedDevices = await solutionsApi.updateRequiredDevices(editingSolution.id, newIds);
      solutionStructure.intro.required_devices = updatedDevices;
      removeBtn.closest('.required-device-item').remove();
      toast.success(t('management.messages.devicesUpdated'));
    } catch (error) {
      toast.error(error.message);
    }
  });
}

/**
 * Render Content Files tab
 */
function renderContentFilesTab(structure) {
  const files = structure?.files || [];
  const existingFiles = new Set(files.map(f => f.path));

  return `
    <div class="content-files-container">
      <div class="content-files-header">
        <h4>${t('management.contentFiles.title')}</h4>
        <p class="text-sm text-text-muted">${t('management.contentFiles.subtitle')}</p>
      </div>

      <div class="content-files-sections">
        <!-- Deploy Guides -->
        <div class="content-files-group">
          <h5 class="group-title">${t('management.contentFiles.deployGuides')}</h5>
          <div class="content-files-list">
            ${CONTENT_FILES.filter(f => f.group === 'deploy').map(file => {
              const exists = existingFiles.has(file.name);
              return `
                <div class="content-file-item" data-filename="${file.name}">
                  <div class="file-info">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                    </svg>
                    <span class="file-name">${file.name}</span>
                    <span class="file-label text-text-muted">${file.label}</span>
                  </div>
                  <div class="file-status">
                    ${exists
                      ? `<span class="status-badge status-exists">${t('management.contentFiles.exists')}</span>`
                      : `<span class="status-badge status-missing">${t('management.contentFiles.missing')}</span>`
                    }
                  </div>
                  <div class="file-actions">
                    <button class="btn btn-sm btn-secondary" data-action="edit-content" data-filename="${file.name}">
                      ${t('management.contentFiles.edit')}
                    </button>
                    <button class="btn btn-sm btn-secondary" data-action="upload-content" data-filename="${file.name}">
                      ${t('management.contentFiles.upload')}
                    </button>
                    ${exists ? `
                      <button class="btn btn-sm btn-secondary" data-action="view-content" data-filename="${file.name}">
                        ${t('management.contentFiles.view')}
                      </button>
                    ` : ''}
                  </div>
                </div>
              `;
            }).join('')}
          </div>
        </div>

        <!-- Introduction Pages -->
        <div class="content-files-group">
          <h5 class="group-title">${t('management.contentFiles.introPages')}</h5>
          <div class="content-files-list">
            ${CONTENT_FILES.filter(f => f.group === 'intro').map(file => {
              const exists = existingFiles.has(file.name);
              return `
                <div class="content-file-item" data-filename="${file.name}">
                  <div class="file-info">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                    </svg>
                    <span class="file-name">${file.name}</span>
                    <span class="file-label text-text-muted">${file.label}</span>
                  </div>
                  <div class="file-status">
                    ${exists
                      ? `<span class="status-badge status-exists">${t('management.contentFiles.exists')}</span>`
                      : `<span class="status-badge status-missing">${t('management.contentFiles.missing')}</span>`
                    }
                  </div>
                  <div class="file-actions">
                    <button class="btn btn-sm btn-secondary" data-action="edit-content" data-filename="${file.name}">
                      ${t('management.contentFiles.edit')}
                    </button>
                    <button class="btn btn-sm btn-secondary" data-action="upload-content" data-filename="${file.name}">
                      ${t('management.contentFiles.upload')}
                    </button>
                    ${exists ? `
                      <button class="btn btn-sm btn-secondary" data-action="view-content" data-filename="${file.name}">
                        ${t('management.contentFiles.view')}
                      </button>
                    ` : ''}
                  </div>
                </div>
              `;
            }).join('')}
          </div>
        </div>
      </div>

      <div class="content-validation" id="content-validation">
        <div class="validation-loading">
          <span class="spinner-sm"></span>
          <span>${t('common.loading')}</span>
        </div>
      </div>
    </div>
  `;
}

/**
 * Setup Content Files tab
 */
function setupContentFilesTab() {
  const container = document.querySelector('[data-tab-content="contentFiles"]');
  if (!container) return;

  // Load validation status
  loadContentValidation();

  // Handle action buttons
  container.addEventListener('click', async (e) => {
    const btn = e.target.closest('[data-action]');
    if (!btn) return;

    const action = btn.dataset.action;
    const filename = btn.dataset.filename;

    switch (action) {
      case 'edit-content':
        openContentEditDialog(filename);
        break;
      case 'upload-content':
        openContentUploadDialog(filename);
        break;
      case 'view-content':
        openContentViewDialog(filename);
        break;
    }
  });
}

/**
 * Load content validation
 */
async function loadContentValidation() {
  const container = document.getElementById('content-validation');
  if (!container || !editingSolution) return;

  try {
    const result = await solutionsApi.validateGuides(editingSolution.id);
    container.innerHTML = renderContentValidationResult(result);
  } catch (error) {
    console.error('Failed to load validation:', error);
    container.innerHTML = `
      <div class="validation-box validation-error">
        <div class="validation-header">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          <span>${t('management.validation.loadError')}</span>
        </div>
      </div>
    `;
  }
}

/**
 * Render content validation result
 */
function renderContentValidationResult(result) {
  if (result.warnings?.length > 0) {
    const warningMsg = result.warnings[0]?.message || '';
    if (warningMsg.includes('No guide files found')) {
      return `
        <div class="validation-box validation-warning">
          <div class="validation-header">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
              <line x1="12" y1="9" x2="12" y2="13"/>
              <line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
            <span>${t('management.contentFiles.noGuides')}</span>
          </div>
        </div>
      `;
    }
    if (warningMsg.includes('Chinese guide not found')) {
      return `
        <div class="validation-box validation-warning">
          <div class="validation-header">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
              <line x1="12" y1="9" x2="12" y2="13"/>
              <line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
            <span>${t('management.contentFiles.enOnly')}</span>
          </div>
        </div>
      `;
    }
  }

  if (result.valid) {
    const presetCount = result.en_presets?.length || 0;
    let totalSteps = 0;
    if (result.en_steps_by_preset) {
      for (const steps of Object.values(result.en_steps_by_preset)) {
        totalSteps += steps?.length || 0;
      }
    }

    return `
      <div class="validation-box validation-success">
        <div class="validation-header">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
            <polyline points="22 4 12 14.01 9 11.01"/>
          </svg>
          <span>${t('management.contentFiles.validated')}</span>
        </div>
        <div class="validation-detail text-sm text-text-muted">
          ${t('management.contentFiles.presetsFound', { count: presetCount })},
          ${t('management.contentFiles.stepsFound', { count: totalSteps })}
        </div>
      </div>
    `;
  }

  const errorCount = result.errors?.length || 0;
  return `
    <div class="validation-box validation-errors">
      <div class="validation-header">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/>
          <line x1="15" y1="9" x2="9" y2="15"/>
          <line x1="9" y1="9" x2="15" y2="15"/>
        </svg>
        <span>${t('management.contentFiles.errorCount', { count: errorCount })}</span>
      </div>
      <div class="validation-error-list">
        ${result.errors.map(err => `
          <div class="validation-error-item">
            <strong>${err.type}</strong>: ${err.message}
          </div>
        `).join('')}
      </div>
    </div>
  `;
}

/**
 * Open content edit dialog
 */
async function openContentEditDialog(filename) {
  let content = '';
  try {
    content = await solutionsApi.getContent(editingSolution.id, filename);
  } catch (error) {
    // File doesn't exist, start with empty content
    content = '';
  }

  const dialogHtml = `
    <div class="dialog-overlay" id="content-edit-dialog">
      <div class="dialog dialog-lg">
        <div class="dialog-header">
          <h3>${t('management.contentFiles.edit')}: ${filename}</h3>
        </div>
        <div class="dialog-body">
          <div class="form-group">
            <textarea id="content-textarea" rows="25" class="code-editor">${escapeHtml(content)}</textarea>
          </div>
        </div>
        <div class="dialog-actions">
          <button class="btn btn-secondary" id="btn-cancel-content">${t('management.actions.cancel')}</button>
          <button class="btn btn-primary" id="btn-save-content">${t('management.actions.save')}</button>
        </div>
      </div>
    </div>
  `;

  const modalBody = document.querySelector('.modal-body');
  const dialogContainer = document.createElement('div');
  dialogContainer.id = 'nested-dialog-container';
  dialogContainer.innerHTML = dialogHtml;
  modalBody.appendChild(dialogContainer);

  document.getElementById('btn-cancel-content').addEventListener('click', closeContentDialog);
  document.getElementById('btn-save-content').addEventListener('click', () => saveContentFile(filename));
  document.getElementById('content-edit-dialog').addEventListener('click', (e) => {
    if (e.target.id === 'content-edit-dialog') closeContentDialog();
  });
}

function closeContentDialog() {
  document.getElementById('nested-dialog-container')?.remove();
}

async function saveContentFile(filename) {
  const content = document.getElementById('content-textarea').value;

  try {
    await solutionsApi.uploadContentFile(editingSolution.id, filename, content);

    // Reload structure to update file list
    solutionStructure = await loadSolutionStructure(editingSolution.id);
    document.querySelector('[data-tab-content="contentFiles"]').innerHTML = renderContentFilesTab(solutionStructure);
    setupContentFilesTab();

    closeContentDialog();
    toast.success(t('management.messages.contentFileSaved'));
  } catch (error) {
    toast.error(error.message);
  }
}

/**
 * Open content upload dialog
 */
function openContentUploadDialog(filename) {
  const dialogHtml = `
    <div class="dialog-overlay" id="content-upload-dialog">
      <div class="dialog dialog-md">
        <div class="dialog-header">
          <h3>${t('management.contentFiles.upload')}: ${filename}</h3>
        </div>
        <div class="dialog-body">
          <div class="form-group">
            <label>${t('management.files.selectFile')}</label>
            <div class="file-upload-area" id="content-upload-area">
              <div class="file-upload-content">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                  <polyline points="17 8 12 3 7 8"/>
                  <line x1="12" y1="3" x2="12" y2="15"/>
                </svg>
                <p>${t('management.form.dropOrClick')}</p>
              </div>
              <input type="file" class="file-input" id="content-file-input" accept=".md,.markdown,text/markdown">
            </div>
          </div>
        </div>
        <div class="dialog-actions">
          <button class="btn btn-secondary" id="btn-cancel-upload">${t('management.actions.cancel')}</button>
          <button class="btn btn-primary" id="btn-do-upload">${t('management.files.upload')}</button>
        </div>
      </div>
    </div>
  `;

  const modalBody = document.querySelector('.modal-body');
  const dialogContainer = document.createElement('div');
  dialogContainer.id = 'nested-dialog-container';
  dialogContainer.innerHTML = dialogHtml;
  modalBody.appendChild(dialogContainer);

  const uploadArea = document.getElementById('content-upload-area');
  const fileInput = document.getElementById('content-file-input');

  uploadArea.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', (e) => {
    if (e.target.files[0]) {
      uploadArea.querySelector('.file-upload-content p').textContent = e.target.files[0].name;
    }
  });

  document.getElementById('btn-cancel-upload').addEventListener('click', closeContentDialog);
  document.getElementById('btn-do-upload').addEventListener('click', () => doContentUpload(filename));
  document.getElementById('content-upload-dialog').addEventListener('click', (e) => {
    if (e.target.id === 'content-upload-dialog') closeContentDialog();
  });
}

async function doContentUpload(filename) {
  const fileInput = document.getElementById('content-file-input');
  const file = fileInput.files[0];

  if (!file) {
    toast.error(t('management.messages.requiredFields'));
    return;
  }

  try {
    const content = await file.text();
    await solutionsApi.uploadContentFile(editingSolution.id, filename, content);

    solutionStructure = await loadSolutionStructure(editingSolution.id);
    document.querySelector('[data-tab-content="contentFiles"]').innerHTML = renderContentFilesTab(solutionStructure);
    setupContentFilesTab();

    closeContentDialog();
    toast.success(t('management.messages.contentFileSaved'));
  } catch (error) {
    toast.error(error.message);
  }
}

/**
 * Open content view dialog
 */
async function openContentViewDialog(filename) {
  let content = '';
  try {
    content = await solutionsApi.getContent(editingSolution.id, filename);
  } catch (error) {
    toast.error(error.message);
    return;
  }

  const dialogHtml = `
    <div class="dialog-overlay" id="content-view-dialog">
      <div class="dialog dialog-lg">
        <div class="dialog-header">
          <h3>${t('management.contentFiles.view')}: ${filename}</h3>
        </div>
        <div class="dialog-body">
          <div class="form-group">
            <textarea readonly rows="25" class="code-editor">${escapeHtml(content)}</textarea>
          </div>
        </div>
        <div class="dialog-actions">
          <button class="btn btn-secondary" id="btn-close-view">${t('management.actions.close')}</button>
        </div>
      </div>
    </div>
  `;

  const modalBody = document.querySelector('.modal-body');
  const dialogContainer = document.createElement('div');
  dialogContainer.id = 'nested-dialog-container';
  dialogContainer.innerHTML = dialogHtml;
  modalBody.appendChild(dialogContainer);

  document.getElementById('btn-close-view').addEventListener('click', closeContentDialog);
  document.getElementById('content-view-dialog').addEventListener('click', (e) => {
    if (e.target.id === 'content-view-dialog') closeContentDialog();
  });
}

/**
 * Render Assets tab content (formerly Files tab)
 */
function renderAssetsTab(structure) {
  const files = structure?.files || [];

  // Filter out the 4 content files
  const contentFileNames = CONTENT_FILES.map(f => f.name);
  const assetFiles = files.filter(f => !contentFileNames.includes(f.path));

  // Group files by directory
  const grouped = {};
  assetFiles.forEach(file => {
    const parts = file.path.split('/');
    const dir = parts.length > 1 ? parts.slice(0, -1).join('/') : '.';
    if (!grouped[dir]) grouped[dir] = [];
    grouped[dir].push(file);
  });

  return `
    <div class="files-container">
      <div class="files-header">
        <h4>${t('management.tabs.assets')}</h4>
        <div class="files-actions">
          <button class="btn btn-secondary btn-sm" id="btn-upload-file">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
            ${t('management.files.upload')}
          </button>
        </div>
      </div>

      <div class="files-tree" id="files-tree">
        ${Object.keys(grouped).length === 0 ? `
          <div class="empty-state-sm">
            <p>${t('management.files.empty')}</p>
          </div>
        ` : Object.entries(grouped).map(([dir, dirFiles]) => `
          <div class="file-group">
            <div class="file-group-header">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
              </svg>
              <span>${dir}</span>
            </div>
            <div class="file-group-items">
              ${dirFiles.map(file => `
                <div class="file-item" data-path="${file.path}">
                  <div class="file-info">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                    </svg>
                    <span class="file-name">${file.name}</span>
                    <span class="file-size text-text-muted">${formatFileSize(file.size)}</span>
                  </div>
                  <div class="file-actions">
                    ${file.type === 'text' ? `
                      <button class="btn-icon btn-icon-sm" title="${t('management.actions.edit')}" data-action="edit-file" data-path="${file.path}">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                        </svg>
                      </button>
                    ` : ''}
                    <button class="btn-icon btn-icon-sm btn-icon-danger" title="${t('management.actions.delete')}" data-action="delete-file" data-path="${file.path}">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <polyline points="3 6 5 6 21 6"/>
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                      </svg>
                    </button>
                  </div>
                </div>
              `).join('')}
            </div>
          </div>
        `).join('')}
      </div>
    </div>
  `;
}

/**
 * Format file size for display
 */
function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

/**
 * Setup Assets tab event handlers
 */
function setupAssetsTab() {
  const container = document.querySelector('[data-tab-content="assets"]');
  if (!container) return;

  // File upload button
  container.querySelector('#btn-upload-file')?.addEventListener('click', openFileUploadDialog);

  // File action buttons
  container.addEventListener('click', async (e) => {
    const btn = e.target.closest('[data-action]');
    if (!btn) return;

    const action = btn.dataset.action;
    const path = btn.dataset.path;

    if (action === 'edit-file') {
      openFileEditDialog(path);
    } else if (action === 'delete-file') {
      if (!confirm(t('management.confirm.deleteFile'))) return;
      try {
        await solutionsApi.deleteFile(editingSolution.id, path);
        solutionStructure = await loadSolutionStructure(editingSolution.id);
        document.querySelector('[data-tab-content="assets"]').innerHTML = renderAssetsTab(solutionStructure);
        setupAssetsTab();
        toast.success(t('management.messages.fileDeleted'));
      } catch (error) {
        toast.error(error.message);
      }
    }
  });
}

function openFileUploadDialog() {
  const dialogHtml = `
    <div class="dialog-overlay" id="upload-dialog">
      <div class="dialog dialog-md">
        <div class="dialog-header">
          <h3>${t('management.files.upload')}</h3>
        </div>
        <div class="dialog-body">
          <div class="form-group">
            <label for="upload-path">${t('management.files.path')}</label>
            <input type="text" id="upload-path" placeholder="gallery/image.png" required>
            <p class="form-hint">${t('management.files.pathHint')}</p>
          </div>
          <div class="form-group">
            <label>${t('management.files.selectFile')}</label>
            <div class="file-upload-area" id="upload-area">
              <div class="file-upload-content">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                  <polyline points="17 8 12 3 7 8"/>
                  <line x1="12" y1="3" x2="12" y2="15"/>
                </svg>
                <p>${t('management.form.dropOrClick')}</p>
              </div>
              <input type="file" class="file-input" id="upload-file-input">
            </div>
          </div>
        </div>
        <div class="dialog-actions">
          <button class="btn btn-secondary" id="btn-cancel-upload">${t('management.actions.cancel')}</button>
          <button class="btn btn-primary" id="btn-do-upload">${t('management.files.upload')}</button>
        </div>
      </div>
    </div>
  `;

  const modalBody = document.querySelector('.modal-body');
  const dialogContainer = document.createElement('div');
  dialogContainer.id = 'nested-dialog-container';
  dialogContainer.innerHTML = dialogHtml;
  modalBody.appendChild(dialogContainer);

  const uploadArea = document.getElementById('upload-area');
  const fileInput = document.getElementById('upload-file-input');

  uploadArea.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', (e) => {
    if (e.target.files[0]) {
      uploadArea.querySelector('.file-upload-content p').textContent = e.target.files[0].name;
    }
  });

  document.getElementById('btn-cancel-upload').addEventListener('click', closeUploadDialog);
  document.getElementById('btn-do-upload').addEventListener('click', doFileUpload);
  document.getElementById('upload-dialog').addEventListener('click', (e) => {
    if (e.target.id === 'upload-dialog') closeUploadDialog();
  });
}

function closeUploadDialog() {
  document.getElementById('nested-dialog-container')?.remove();
}

async function doFileUpload() {
  const path = document.getElementById('upload-path').value.trim();
  const fileInput = document.getElementById('upload-file-input');
  const file = fileInput.files[0];

  if (!path || !file) {
    toast.error(t('management.messages.requiredFields'));
    return;
  }

  try {
    await solutionsApi.uploadAsset(editingSolution.id, file, path);
    solutionStructure = await loadSolutionStructure(editingSolution.id);
    document.querySelector('[data-tab-content="assets"]').innerHTML = renderAssetsTab(solutionStructure);
    setupAssetsTab();
    closeUploadDialog();
    toast.success(t('management.messages.uploadSuccess'));
  } catch (error) {
    toast.error(error.message);
  }
}

async function openFileEditDialog(path) {
  let content = '';
  try {
    content = await solutionsApi.getContent(editingSolution.id, path);
  } catch (error) {
    toast.error(error.message);
    return;
  }

  const dialogHtml = `
    <div class="dialog-overlay" id="edit-file-dialog">
      <div class="dialog dialog-lg">
        <div class="dialog-header">
          <h3>${t('management.files.edit')}: ${path}</h3>
        </div>
        <div class="dialog-body">
          <div class="form-group">
            <textarea id="file-content" rows="20" class="code-editor">${escapeHtml(content)}</textarea>
          </div>
        </div>
        <div class="dialog-actions">
          <button class="btn btn-secondary" id="btn-cancel-edit-file">${t('management.actions.cancel')}</button>
          <button class="btn btn-primary" id="btn-save-file">${t('management.actions.save')}</button>
        </div>
      </div>
    </div>
  `;

  const modalBody = document.querySelector('.modal-body');
  const dialogContainer = document.createElement('div');
  dialogContainer.id = 'nested-dialog-container';
  dialogContainer.innerHTML = dialogHtml;
  modalBody.appendChild(dialogContainer);

  document.getElementById('btn-cancel-edit-file').addEventListener('click', closeEditFileDialog);
  document.getElementById('btn-save-file').addEventListener('click', () => saveFileContent(path));
  document.getElementById('edit-file-dialog').addEventListener('click', (e) => {
    if (e.target.id === 'edit-file-dialog') closeEditFileDialog();
  });
}

function closeEditFileDialog() {
  document.getElementById('nested-dialog-container')?.remove();
}

async function saveFileContent(path) {
  const content = document.getElementById('file-content').value;

  try {
    await solutionsApi.saveTextFile(editingSolution.id, path, content);
    closeEditFileDialog();
    toast.success(t('management.messages.fileSaved'));
  } catch (error) {
    toast.error(error.message);
  }
}

/**
 * Render Preview tab
 */
function renderPreviewTab(structure) {
  return `
    <div class="preview-container">
      <div class="preview-header">
        <h4>${t('management.preview.title')}</h4>
        <p class="text-sm text-text-muted">${t('management.preview.subtitle')}</p>
        <button class="btn btn-secondary btn-sm" id="btn-refresh-preview">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="23 4 23 10 17 10"></polyline>
            <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"></path>
          </svg>
          ${t('management.preview.refresh')}
        </button>
      </div>
      <div class="preview-content" id="preview-content">
        <div class="loading-spinner">${t('common.loading')}</div>
      </div>
    </div>
  `;
}

/**
 * Load and render preview structure
 */
async function loadPreviewStructure() {
  const container = document.getElementById('preview-content');
  if (!container || !editingSolution) return;

  try {
    const preview = await solutionsApi.getPreviewStructure(editingSolution.id);
    container.innerHTML = renderPreviewContent(preview);

    // Setup refresh button
    document.getElementById('btn-refresh-preview')?.addEventListener('click', loadPreviewStructure);
  } catch (error) {
    console.error('Failed to load preview:', error);
    container.innerHTML = `
      <div class="empty-state-sm">
        <p class="text-danger">${t('management.preview.loadError')}: ${error.message}</p>
      </div>
    `;
  }
}

/**
 * Render preview content
 */
function renderPreviewContent(preview) {
  if (!preview || !preview.presets || preview.presets.length === 0) {
    return `
      <div class="empty-state-sm">
        <p>${t('management.preview.noPresets')}</p>
        <p class="text-sm text-text-muted">${t('management.preview.addGuide')}</p>
      </div>
    `;
  }

  return `
    <div class="preview-presets">
      ${preview.presets.map(preset => `
        <div class="preview-preset">
          <div class="preset-header">
            <span class="preset-name">${preset.name}</span>
            <span class="preset-id text-text-muted">#${preset.id}</span>
            ${preset.is_default ? `<span class="badge badge-primary">${t('management.preview.default')}</span>` : ''}
          </div>
          ${preset.description ? `<p class="preset-description text-sm text-text-muted">${preset.description}</p>` : ''}

          <div class="preset-steps">
            ${(preset.steps || []).map((step, index) => `
              <div class="preview-step">
                <span class="step-index">${index + 1}</span>
                <div class="step-info">
                  <span class="step-name">${step.name}</span>
                  <span class="step-type badge badge-sm">${step.type}</span>
                  ${step.required ? `<span class="badge badge-sm badge-warning">${t('management.preview.required')}</span>` : ''}
                </div>
                ${step.targets && step.targets.length > 0 ? `
                  <div class="step-targets">
                    ${step.targets.map(target => `
                      <span class="target-badge ${target.is_default ? 'target-default' : ''}"
                            title="${target.is_default ? t('management.preview.defaultTarget') : ''}">
                        ${target.name} (#${target.id})
                      </span>
                    `).join('')}
                  </div>
                ` : ''}
              </div>
            `).join('')}
          </div>
        </div>
      `).join('')}
    </div>

    ${preview.post_deployment ? `
      <div class="preview-section">
        <h5>${t('management.preview.postDeployment')}</h5>
        ${preview.post_deployment.success_message ? `
          <div class="post-deployment-message">
            <strong>${t('management.preview.successMessage')}:</strong>
            <p>${preview.post_deployment.success_message}</p>
          </div>
        ` : ''}
        ${preview.post_deployment.next_steps && preview.post_deployment.next_steps.length > 0 ? `
          <div class="post-deployment-steps">
            <strong>${t('management.preview.nextSteps')}:</strong>
            <ul>
              ${preview.post_deployment.next_steps.map(step => `<li>${step.label || step.text}</li>`).join('')}
            </ul>
          </div>
        ` : ''}
      </div>
    ` : ''}

    ${preview.validation ? `
      <div class="preview-section">
        <h5>${t('management.preview.validation')}</h5>
        <div class="validation-box ${preview.validation.valid ? 'validation-success' : 'validation-errors'}">
          ${preview.validation.valid
            ? `<span class="text-success">${t('management.preview.validationPassed')}</span>`
            : `<span class="text-danger">${t('management.preview.validationFailed')}</span>`
          }
        </div>
      </div>
    ` : ''}
  `;
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Setup tags editor
 */
function setupTagsEditor() {
  const tagsEditor = document.getElementById('tags-editor');
  if (!tagsEditor) return;

  // Remove tag
  tagsEditor.addEventListener('click', async (e) => {
    const removeBtn = e.target.closest('.tag-remove');
    if (!removeBtn) return;

    const tag = removeBtn.dataset.tag;
    const currentTags = solutionStructure?.intro?.tags || [];
    const newTags = currentTags.filter(t => t !== tag);

    try {
      await solutionsApi.updateTags(editingSolution.id, newTags);
      solutionStructure.intro.tags = newTags;
      removeBtn.closest('.tag-item').remove();
      toast.success(t('management.messages.tagRemoved'));
    } catch (error) {
      toast.error(error.message);
    }
  });

  // Add tag
  const addBtn = document.getElementById('btn-add-tag');
  const input = document.getElementById('new-tag-input');

  const addTag = async () => {
    const tag = input.value.trim().toLowerCase();
    if (!tag) return;

    const currentTags = solutionStructure?.intro?.tags || [];
    if (currentTags.includes(tag)) {
      toast.error(t('management.messages.tagExists'));
      return;
    }

    try {
      const newTags = [...currentTags, tag];
      await solutionsApi.updateTags(editingSolution.id, newTags);
      solutionStructure.intro.tags = newTags;

      const tagsList = tagsEditor.querySelector('.tags-list');
      const tagHtml = `
        <span class="tag-item">
          ${tag}
          <button type="button" class="tag-remove" data-tag="${tag}">&times;</button>
        </span>
      `;
      tagsList.insertAdjacentHTML('beforeend', tagHtml);
      input.value = '';
      toast.success(t('management.messages.tagAdded'));
    } catch (error) {
      toast.error(error.message);
    }
  };

  addBtn?.addEventListener('click', addTag);
  input?.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addTag();
    }
  });
}

/**
 * Setup links editor
 */
function setupLinksEditor() {
  document.getElementById('btn-save-links')?.addEventListener('click', saveLinks);
}

async function saveLinks() {
  const wiki = document.getElementById('link-wiki')?.value || '';
  const github = document.getElementById('link-github')?.value || '';

  try {
    await solutionsApi.updateLinks(editingSolution.id, { wiki, github });
    toast.success(t('management.messages.linksSaved'));
  } catch (error) {
    toast.error(error.message);
  }
}

/**
 * Setup file upload areas with drag & drop
 */
function setupFileUploads() {
  const uploadAreas = document.querySelectorAll('.file-upload-area');

  uploadAreas.forEach(area => {
    const input = area.querySelector('.file-input');
    if (!input) return;

    area.addEventListener('click', () => input.click());

    area.addEventListener('dragover', (e) => {
      e.preventDefault();
      area.classList.add('drag-over');
    });

    area.addEventListener('dragleave', () => {
      area.classList.remove('drag-over');
    });

    area.addEventListener('drop', (e) => {
      e.preventDefault();
      area.classList.remove('drag-over');
      if (e.dataTransfer.files.length > 0) {
        handleFileUpload(area, e.dataTransfer.files[0]);
      }
    });

    input.addEventListener('change', (e) => {
      if (e.target.files.length > 0) {
        handleFileUpload(area, e.target.files[0]);
      }
    });
  });
}

/**
 * Handle file upload
 */
async function handleFileUpload(area, file) {
  const path = area.dataset.path;
  const updateField = area.dataset.field || null;

  if (!editingSolution) return;

  area.classList.add('uploading');
  const content = area.querySelector('.file-upload-content');
  const originalHtml = content.innerHTML;
  content.innerHTML = `<div class="spinner"></div><p>${t('common.loading')}</p>`;

  try {
    await solutionsApi.uploadAsset(editingSolution.id, file, path, updateField);

    content.innerHTML = `
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-success">
        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
        <polyline points="22 4 12 14.01 9 11.01"/>
      </svg>
      <p class="text-success">${t('management.form.uploaded')}: ${file.name}</p>
    `;

    toast.success(t('management.messages.uploadSuccess'));
  } catch (error) {
    console.error('Upload failed:', error);
    content.innerHTML = originalHtml;
    toast.error(`${t('management.messages.uploadError')}: ${error.message}`);
  } finally {
    area.classList.remove('uploading');
  }
}

/**
 * Save solution (create or update)
 */
async function saveSolution() {
  const form = document.getElementById('solution-form');
  if (!form.checkValidity()) {
    form.reportValidity();
    return;
  }

  const formData = new FormData(form);
  const data = Object.fromEntries(formData.entries());

  if (!editingSolution && !SOLUTION_ID_PATTERN.test(data.id)) {
    toast.error(t('management.messages.invalidId'));
    return;
  }

  const saveBtn = document.getElementById('btn-save');
  saveBtn.disabled = true;
  saveBtn.innerHTML = `<span class="spinner-sm"></span> ${t('common.loading')}`;

  try {
    if (editingSolution) {
      await solutionsApi.update(editingSolution.id, data);
      toast.success(t('management.messages.updateSuccess'));
    } else {
      await solutionsApi.create(data);
      toast.success(t('management.messages.createSuccess'));
    }

    closeModal();
    await loadSolutions();
  } catch (error) {
    console.error('Save failed:', error);
    const errorMsg = editingSolution
      ? t('management.messages.updateError')
      : t('management.messages.createError');
    toast.error(`${errorMsg}: ${error.message}`);
  } finally {
    saveBtn.disabled = false;
    saveBtn.innerHTML = editingSolution
      ? t('management.actions.save')
      : t('management.actions.create');
  }
}

/**
 * Close modal
 */
function closeModal() {
  const modalContainer = document.getElementById('modal-container');
  modalContainer.innerHTML = '';
  editingSolution = null;
  solutionStructure = null;
}

/**
 * Confirm delete dialog
 */
function confirmDelete(solutionId) {
  const solution = solutions.find(s => s.id === solutionId);
  if (!solution) return;

  const dialogHtml = `
    <div class="dialog-overlay" id="delete-dialog">
      <div class="dialog">
        <div class="dialog-header">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
            <line x1="12" y1="9" x2="12" y2="13"/>
            <line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
          <h3>${t('management.confirm.deleteTitle')}</h3>
        </div>
        <div class="dialog-body">
          <p>${t('management.confirm.deleteMessage')}</p>
          <p class="mt-2"><strong>${solution.id}</strong>: ${getLocalizedField(solution, 'name')}</p>
          <label class="checkbox-label mt-4">
            <input type="checkbox" id="delete-permanent">
            <span>${t('management.confirm.deletePermanent')}</span>
          </label>
        </div>
        <div class="dialog-actions">
          <button class="btn btn-secondary" id="btn-cancel-delete">${t('management.actions.cancel')}</button>
          <button class="btn btn-danger" id="btn-confirm-delete">${t('management.actions.delete')}</button>
        </div>
      </div>
    </div>
  `;

  const modalContainer = document.getElementById('modal-container');
  modalContainer.innerHTML = dialogHtml;

  document.getElementById('btn-cancel-delete').addEventListener('click', closeDeleteDialog);
  document.getElementById('btn-confirm-delete').addEventListener('click', () => deleteSolution(solutionId));
  document.getElementById('delete-dialog').addEventListener('click', (e) => {
    if (e.target.id === 'delete-dialog') closeDeleteDialog();
  });
}

function closeDeleteDialog() {
  const modalContainer = document.getElementById('modal-container');
  modalContainer.innerHTML = '';
}

async function deleteSolution(solutionId) {
  const permanent = document.getElementById('delete-permanent')?.checked || false;
  const deleteBtn = document.getElementById('btn-confirm-delete');

  deleteBtn.disabled = true;
  deleteBtn.innerHTML = `<span class="spinner-sm"></span>`;

  try {
    await solutionsApi.delete(solutionId, permanent);
    toast.success(t('management.messages.deleteSuccess'));
    closeDeleteDialog();
    await loadSolutions();
  } catch (error) {
    console.error('Delete failed:', error);
    toast.error(`${t('management.messages.deleteError')}: ${error.message}`);
  } finally {
    deleteBtn.disabled = false;
    deleteBtn.innerHTML = t('management.actions.delete');
  }
}
