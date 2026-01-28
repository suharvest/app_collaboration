/**
 * Solution Management Page
 * Provides structured management for solutions with tab-based UI
 * - Basic Info: name, summary, category, tags, links
 * - Presets: deployment presets with structured device/step management
 * - Files: file browser for solution resources
 */

import { solutionsApi, getAssetUrl } from '../modules/api.js';
import { t, i18n, getLocalizedField } from '../modules/i18n.js';
import { toast } from '../modules/toast.js';

// State
let solutions = [];
let isLoading = false;
let editingSolution = null;
let solutionStructure = null;
let activeTab = 'basic';

// Constants
const SOLUTION_ID_PATTERN = /^[a-z][a-z0-9_]*$/;
const CATEGORIES = ['general', 'voice_ai', 'sensing', 'automation', 'vision', 'smart_building', 'industrial_iot'];
const DIFFICULTIES = ['beginner', 'intermediate', 'advanced'];
const DEVICE_TYPES = ['manual', 'esp32_usb', 'himax_usb', 'docker_deploy', 'script', 'preview'];

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

  // Load structure for edit mode
  if (isEdit) {
    try {
      solutionStructure = await solutionsApi.getStructure(solution.id);
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
          <button class="tab-btn ${activeTab === 'presets' ? 'active' : ''}" data-tab="presets">
            ${t('management.tabs.presets')}
          </button>
          <button class="tab-btn ${activeTab === 'files' ? 'active' : ''}" data-tab="files">
            ${t('management.tabs.files')}
          </button>
        </div>
        ` : ''}

        <div class="modal-body">
          <div class="tab-content ${activeTab === 'basic' ? 'active' : ''}" data-tab-content="basic">
            ${renderBasicInfoTab(solution, structure)}
          </div>
          ${isEdit ? `
          <div class="tab-content ${activeTab === 'presets' ? 'active' : ''}" data-tab-content="presets">
            ${renderPresetsTab(structure)}
          </div>
          <div class="tab-content ${activeTab === 'files' ? 'active' : ''}" data-tab-content="files">
            ${renderFilesTab(structure)}
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
      });
    });

    setupPresetsTab();
    setupFilesTab();
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

  // Setup file uploads for basic info
  if (isEdit) {
    setupFileUploads();
  }
}

/**
 * Render Basic Info tab content
 */
function renderBasicInfoTab(solution, structure) {
  const isEdit = !!solution;
  const tags = structure?.tags || [];
  const links = structure?.links || {};

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
          <div class="file-upload-area" data-field="intro.cover_image" data-path="intro/gallery/cover.png" data-accept="image/*">
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
 * Render Presets tab content
 */
function renderPresetsTab(structure) {
  const presets = structure?.presets || [];

  return `
    <div class="presets-container">
      <div class="presets-header">
        <h4>${t('management.presets.title')}</h4>
        <button class="btn btn-primary btn-sm" id="btn-add-preset">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
          ${t('management.presets.add')}
        </button>
      </div>

      <div class="presets-list" id="presets-list">
        ${presets.length === 0 ? `
          <div class="empty-state-sm">
            <p>${t('management.presets.empty')}</p>
          </div>
        ` : presets.map((preset, index) => renderPresetCard(preset, index)).join('')}
      </div>
    </div>
  `;
}

/**
 * Render a single preset card
 */
function renderPresetCard(preset, index) {
  const devices = preset.devices || [];
  const isDefault = preset.default === true;

  return `
    <div class="preset-card" data-preset-id="${preset.id}">
      <div class="preset-header">
        <div class="preset-info">
          <span class="preset-index">${index + 1}</span>
          <div>
            <h5 class="preset-name">${preset.name || preset.id}</h5>
            ${preset.name_zh ? `<span class="preset-name-zh">${preset.name_zh}</span>` : ''}
          </div>
          ${isDefault ? `<span class="badge badge-primary">${t('management.presets.default')}</span>` : ''}
        </div>
        <div class="preset-actions">
          <button class="btn-icon" title="${t('management.actions.edit')}" data-action="edit-preset" data-preset-id="${preset.id}">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
            </svg>
          </button>
          <button class="btn-icon btn-icon-danger" title="${t('management.actions.delete')}" data-action="delete-preset" data-preset-id="${preset.id}">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6"/>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
            </svg>
          </button>
        </div>
      </div>

      <div class="preset-devices">
        <div class="devices-header">
          <span class="text-sm text-text-secondary">${t('management.presets.steps')} (${devices.length})</span>
          <button class="btn btn-sm btn-secondary" data-action="add-device" data-preset-id="${preset.id}">
            + ${t('management.presets.addStep')}
          </button>
        </div>

        <div class="devices-list">
          ${devices.length === 0 ? `
            <p class="text-sm text-text-muted">${t('management.presets.noSteps')}</p>
          ` : devices.map((device, deviceIndex) => renderDeviceRow(preset.id, device, deviceIndex)).join('')}
        </div>
      </div>
    </div>
  `;
}

/**
 * Render a device/step row within a preset
 */
function renderDeviceRow(presetId, device, index) {
  const section = device.section || {};

  return `
    <div class="device-row" data-device-id="${device.id}">
      <div class="device-info">
        <span class="device-index">${index + 1}</span>
        <div class="device-details">
          <span class="device-name">${device.name || device.id}</span>
          <span class="device-type badge badge-sm">${device.type}</span>
          ${device.required ? '<span class="badge badge-sm badge-warning">Required</span>' : ''}
        </div>
      </div>
      <div class="device-files">
        ${section.description_file ? `
          <span class="file-badge" title="${section.description_file}">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            </svg>
            ${section.description_file.split('/').pop()}
          </span>
        ` : ''}
      </div>
      <div class="device-actions">
        <button class="btn-icon btn-icon-sm" title="${t('management.actions.edit')}"
                data-action="edit-device" data-preset-id="${presetId}" data-device-id="${device.id}">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
          </svg>
        </button>
        <button class="btn-icon btn-icon-sm btn-icon-danger" title="${t('management.actions.delete')}"
                data-action="delete-device" data-preset-id="${presetId}" data-device-id="${device.id}">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3 6 5 6 21 6"/>
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
          </svg>
        </button>
      </div>
    </div>
  `;
}

/**
 * Render Files tab content
 */
function renderFilesTab(structure) {
  const files = structure?.files || [];

  // Group files by directory
  const grouped = {};
  files.forEach(file => {
    const parts = file.path.split('/');
    const dir = parts.length > 1 ? parts.slice(0, -1).join('/') : '.';
    if (!grouped[dir]) grouped[dir] = [];
    grouped[dir].push(file);
  });

  return `
    <div class="files-container">
      <div class="files-header">
        <h4>${t('management.files.title')}</h4>
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
 * Setup Presets tab event handlers
 */
function setupPresetsTab() {
  const container = document.querySelector('[data-tab-content="presets"]');
  if (!container) return;

  // Add preset button
  container.querySelector('#btn-add-preset')?.addEventListener('click', () => openPresetModal());

  // Preset and device action buttons
  container.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-action]');
    if (!btn) return;

    const action = btn.dataset.action;
    const presetId = btn.dataset.presetId;
    const deviceId = btn.dataset.deviceId;

    switch (action) {
      case 'edit-preset':
        openPresetModal(presetId);
        break;
      case 'delete-preset':
        confirmDeletePreset(presetId);
        break;
      case 'add-device':
        openDeviceModal(presetId);
        break;
      case 'edit-device':
        openDeviceModal(presetId, deviceId);
        break;
      case 'delete-device':
        confirmDeleteDevice(presetId, deviceId);
        break;
    }
  });

  // Tags functionality
  setupTagsEditor();

  // Links save button
  document.getElementById('btn-save-links')?.addEventListener('click', saveLinks);
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
    const currentTags = solutionStructure?.tags || [];
    const newTags = currentTags.filter(t => t !== tag);

    try {
      await solutionsApi.updateTags(editingSolution.id, newTags);
      solutionStructure.tags = newTags;
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

    const currentTags = solutionStructure?.tags || [];
    if (currentTags.includes(tag)) {
      toast.error(t('management.messages.tagExists'));
      return;
    }

    try {
      const newTags = [...currentTags, tag];
      await solutionsApi.updateTags(editingSolution.id, newTags);
      solutionStructure.tags = newTags;

      // Add to UI
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
 * Save links
 */
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
 * Open preset modal for create/edit
 */
function openPresetModal(presetId = null) {
  const preset = presetId ? solutionStructure?.presets?.find(p => p.id === presetId) : null;
  const isEdit = !!preset;

  const dialogHtml = `
    <div class="dialog-overlay" id="preset-dialog">
      <div class="dialog dialog-md">
        <div class="dialog-header">
          <h3>${isEdit ? t('management.presets.edit') : t('management.presets.add')}</h3>
        </div>
        <div class="dialog-body">
          <form id="preset-form">
            <div class="form-group">
              <label for="preset-id">ID *</label>
              <input type="text" id="preset-id" value="${preset?.id || ''}" ${isEdit ? 'disabled' : ''} required
                     pattern="^[a-z][a-z0-9_]*$" placeholder="preset_id">
            </div>
            <div class="form-row">
              <div class="form-group">
                <label for="preset-name">${t('management.form.nameEn')} *</label>
                <input type="text" id="preset-name" value="${preset?.name || ''}" required>
              </div>
              <div class="form-group">
                <label for="preset-name-zh">${t('management.form.nameZh')}</label>
                <input type="text" id="preset-name-zh" value="${preset?.name_zh || ''}">
              </div>
            </div>
            <div class="form-group">
              <label class="checkbox-label">
                <input type="checkbox" id="preset-default" ${preset?.default ? 'checked' : ''}>
                <span>${t('management.presets.setDefault')}</span>
              </label>
            </div>
          </form>
        </div>
        <div class="dialog-actions">
          <button class="btn btn-secondary" id="btn-cancel-preset">${t('management.actions.cancel')}</button>
          <button class="btn btn-primary" id="btn-save-preset">${t('management.actions.save')}</button>
        </div>
      </div>
    </div>
  `;

  // Insert into modal container (nested dialog)
  const modalBody = document.querySelector('.modal-body');
  const dialogContainer = document.createElement('div');
  dialogContainer.id = 'nested-dialog-container';
  dialogContainer.innerHTML = dialogHtml;
  modalBody.appendChild(dialogContainer);

  document.getElementById('btn-cancel-preset').addEventListener('click', closePresetDialog);
  document.getElementById('btn-save-preset').addEventListener('click', () => savePreset(presetId));
  document.getElementById('preset-dialog').addEventListener('click', (e) => {
    if (e.target.id === 'preset-dialog') closePresetDialog();
  });
}

function closePresetDialog() {
  document.getElementById('nested-dialog-container')?.remove();
}

async function savePreset(existingPresetId = null) {
  const id = document.getElementById('preset-id').value.trim();
  const name = document.getElementById('preset-name').value.trim();
  const name_zh = document.getElementById('preset-name-zh').value.trim();
  const isDefault = document.getElementById('preset-default').checked;

  if (!id || !name) {
    toast.error(t('management.messages.requiredFields'));
    return;
  }

  const data = { id, name, name_zh, default: isDefault };

  try {
    if (existingPresetId) {
      await solutionsApi.updatePreset(editingSolution.id, existingPresetId, data);
    } else {
      await solutionsApi.addPreset(editingSolution.id, data);
    }

    // Reload structure and refresh presets tab
    solutionStructure = await solutionsApi.getStructure(editingSolution.id);
    document.querySelector('[data-tab-content="presets"]').innerHTML = renderPresetsTab(solutionStructure);
    setupPresetsTab();
    closePresetDialog();
    toast.success(existingPresetId ? t('management.messages.presetUpdated') : t('management.messages.presetAdded'));
  } catch (error) {
    toast.error(error.message);
  }
}

async function confirmDeletePreset(presetId) {
  if (!confirm(t('management.confirm.deletePreset'))) return;

  try {
    await solutionsApi.deletePreset(editingSolution.id, presetId);
    solutionStructure = await solutionsApi.getStructure(editingSolution.id);
    document.querySelector('[data-tab-content="presets"]').innerHTML = renderPresetsTab(solutionStructure);
    setupPresetsTab();
    toast.success(t('management.messages.presetDeleted'));
  } catch (error) {
    toast.error(error.message);
  }
}

/**
 * Open device modal for create/edit
 */
function openDeviceModal(presetId, deviceId = null) {
  const preset = solutionStructure?.presets?.find(p => p.id === presetId);
  const device = deviceId ? preset?.devices?.find(d => d.id === deviceId) : null;
  const isEdit = !!device;
  const section = device?.section || {};

  const dialogHtml = `
    <div class="dialog-overlay" id="device-dialog">
      <div class="dialog dialog-lg">
        <div class="dialog-header">
          <h3>${isEdit ? t('management.presets.editStep') : t('management.presets.addStep')}</h3>
        </div>
        <div class="dialog-body">
          <form id="device-form">
            <div class="form-row">
              <div class="form-group">
                <label for="device-id">ID *</label>
                <input type="text" id="device-id" value="${device?.id || ''}" ${isEdit ? 'disabled' : ''} required
                       pattern="^[a-z][a-z0-9_]*$" placeholder="step_id">
              </div>
              <div class="form-group">
                <label for="device-type">${t('management.form.type')} *</label>
                <select id="device-type" required>
                  ${DEVICE_TYPES.map(type => `
                    <option value="${type}" ${device?.type === type ? 'selected' : ''}>${type}</option>
                  `).join('')}
                </select>
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label for="device-name">${t('management.form.nameEn')} *</label>
                <input type="text" id="device-name" value="${device?.name || ''}" required>
              </div>
              <div class="form-group">
                <label for="device-name-zh">${t('management.form.nameZh')}</label>
                <input type="text" id="device-name-zh" value="${device?.name_zh || ''}">
              </div>
            </div>
            <div class="form-group">
              <label class="checkbox-label">
                <input type="checkbox" id="device-required" ${device?.required !== false ? 'checked' : ''}>
                <span>${t('management.presets.required')}</span>
              </label>
            </div>

            <hr class="form-divider">
            <h4 class="form-section-title">${t('management.presets.sectionFiles')}</h4>

            <div class="form-row">
              <div class="form-group">
                <label for="section-title">${t('management.form.sectionTitle')}</label>
                <input type="text" id="section-title" value="${section.title || ''}" placeholder="Section title">
              </div>
              <div class="form-group">
                <label for="section-title-zh">${t('management.form.sectionTitleZh')}</label>
                <input type="text" id="section-title-zh" value="${section.title_zh || ''}">
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label for="section-desc-file">${t('management.form.descFile')}</label>
                <input type="text" id="section-desc-file" value="${section.description_file || ''}"
                       placeholder="deploy/sections/step1.md">
              </div>
              <div class="form-group">
                <label for="section-desc-file-zh">${t('management.form.descFileZh')}</label>
                <input type="text" id="section-desc-file-zh" value="${section.description_file_zh || ''}"
                       placeholder="deploy/sections/step1_zh.md">
              </div>
            </div>
          </form>
        </div>
        <div class="dialog-actions">
          <button class="btn btn-secondary" id="btn-cancel-device">${t('management.actions.cancel')}</button>
          <button class="btn btn-primary" id="btn-save-device">${t('management.actions.save')}</button>
        </div>
      </div>
    </div>
  `;

  const modalBody = document.querySelector('.modal-body');
  const dialogContainer = document.createElement('div');
  dialogContainer.id = 'nested-dialog-container';
  dialogContainer.innerHTML = dialogHtml;
  modalBody.appendChild(dialogContainer);

  document.getElementById('btn-cancel-device').addEventListener('click', closeDeviceDialog);
  document.getElementById('btn-save-device').addEventListener('click', () => saveDevice(presetId, deviceId));
  document.getElementById('device-dialog').addEventListener('click', (e) => {
    if (e.target.id === 'device-dialog') closeDeviceDialog();
  });
}

function closeDeviceDialog() {
  document.getElementById('nested-dialog-container')?.remove();
}

async function saveDevice(presetId, existingDeviceId = null) {
  const id = document.getElementById('device-id').value.trim();
  const type = document.getElementById('device-type').value;
  const name = document.getElementById('device-name').value.trim();
  const name_zh = document.getElementById('device-name-zh').value.trim();
  const required = document.getElementById('device-required').checked;

  const section = {
    title: document.getElementById('section-title').value.trim(),
    title_zh: document.getElementById('section-title-zh').value.trim(),
    description_file: document.getElementById('section-desc-file').value.trim(),
    description_file_zh: document.getElementById('section-desc-file-zh').value.trim(),
  };

  if (!id || !name) {
    toast.error(t('management.messages.requiredFields'));
    return;
  }

  const data = { id, type, name, name_zh, required, section };

  try {
    if (existingDeviceId) {
      await solutionsApi.updatePresetDevice(editingSolution.id, presetId, existingDeviceId, data);
    } else {
      await solutionsApi.addPresetDevice(editingSolution.id, presetId, data);
    }

    solutionStructure = await solutionsApi.getStructure(editingSolution.id);
    document.querySelector('[data-tab-content="presets"]').innerHTML = renderPresetsTab(solutionStructure);
    setupPresetsTab();
    closeDeviceDialog();
    toast.success(existingDeviceId ? t('management.messages.stepUpdated') : t('management.messages.stepAdded'));
  } catch (error) {
    toast.error(error.message);
  }
}

async function confirmDeleteDevice(presetId, deviceId) {
  if (!confirm(t('management.confirm.deleteStep'))) return;

  try {
    await solutionsApi.deletePresetDevice(editingSolution.id, presetId, deviceId);
    solutionStructure = await solutionsApi.getStructure(editingSolution.id);
    document.querySelector('[data-tab-content="presets"]').innerHTML = renderPresetsTab(solutionStructure);
    setupPresetsTab();
    toast.success(t('management.messages.stepDeleted'));
  } catch (error) {
    toast.error(error.message);
  }
}

/**
 * Setup Files tab event handlers
 */
function setupFilesTab() {
  const container = document.querySelector('[data-tab-content="files"]');
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
        solutionStructure = await solutionsApi.getStructure(editingSolution.id);
        document.querySelector('[data-tab-content="files"]').innerHTML = renderFilesTab(solutionStructure);
        setupFilesTab();
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
            <input type="text" id="upload-path" placeholder="deploy/sections/new_file.md" required>
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
    solutionStructure = await solutionsApi.getStructure(editingSolution.id);
    document.querySelector('[data-tab-content="files"]').innerHTML = renderFilesTab(solutionStructure);
    setupFilesTab();
    closeUploadDialog();
    toast.success(t('management.messages.uploadSuccess'));
  } catch (error) {
    toast.error(error.message);
  }
}

async function openFileEditDialog(path) {
  // Load file content
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

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
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
