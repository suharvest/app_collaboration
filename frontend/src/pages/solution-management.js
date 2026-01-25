/**
 * Solution Management Page
 * Provides CRUD operations for solutions with file upload support
 */

import { solutionsApi } from '../modules/api.js';
import { t, i18n, getLocalizedField } from '../modules/i18n.js';
import { toast } from '../modules/toast.js';

// State
let solutions = [];
let isLoading = false;
let editingSolution = null; // null for new, solution object for edit

// Solution ID validation pattern
const SOLUTION_ID_PATTERN = /^[a-z][a-z0-9_]*$/;

// Categories available
const CATEGORIES = ['general', 'voice_ai', 'sensing', 'automation', 'vision', 'smart_building', 'industrial_iot'];
const DIFFICULTIES = ['beginner', 'intermediate', 'advanced'];

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

  // Bind events
  document.getElementById('btn-new-solution').addEventListener('click', () => openModal());

  // Load solutions
  await loadSolutions();

  // Listen for language changes
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
                ${solution.cover_image ? `<img src="${solution.cover_image}" alt="" class="solution-thumb">` : ''}
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

  // Bind table action events
  container.querySelectorAll('[data-action]').forEach(btn => {
    btn.addEventListener('click', (e) => {
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
function openModal(solution = null) {
  editingSolution = solution;
  const isEdit = !!solution;

  const modalHtml = `
    <div class="modal" id="solution-modal">
      <div class="modal-content modal-lg">
        <div class="modal-header">
          <h3>${isEdit ? t('management.editSolution') : t('management.newSolution')}</h3>
          <button class="close-btn" id="modal-close">&times;</button>
        </div>
        <div class="modal-body">
          <form id="solution-form">
            <!-- Basic Info Section -->
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

            <!-- File Uploads Section (only for edit mode) -->
            ${isEdit ? `
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
                    ${solution?.cover_image ? `<span class="file-uploaded">${t('management.form.uploaded')}: cover.png</span>` : ''}
                  </div>
                  <input type="file" class="file-input" accept="image/*">
                </div>
              </div>

              <div class="form-row">
                <div class="form-group">
                  <label>${t('management.form.descEn')}</label>
                  <div class="file-upload-area" data-path="intro/description.md" data-accept=".md">
                    <div class="file-upload-content">
                      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                        <path d="M14 2v6h6"/>
                      </svg>
                      <p class="text-sm">${t('management.form.dropOrClick')}</p>
                      ${solution?.has_description ? `<span class="file-uploaded">${t('management.form.uploaded')}: description.md</span>` : ''}
                    </div>
                    <input type="file" class="file-input" accept=".md">
                  </div>
                </div>
                <div class="form-group">
                  <label>${t('management.form.descZh')}</label>
                  <div class="file-upload-area" data-path="intro/description_zh.md" data-accept=".md">
                    <div class="file-upload-content">
                      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                        <path d="M14 2v6h6"/>
                      </svg>
                      <p class="text-sm">${t('management.form.dropOrClick')}</p>
                      ${solution?.has_description_zh ? `<span class="file-uploaded">${t('management.form.uploaded')}: description_zh.md</span>` : ''}
                    </div>
                    <input type="file" class="file-input" accept=".md">
                  </div>
                </div>
              </div>

              <div class="form-row">
                <div class="form-group">
                  <label>${t('management.form.guideEn')}</label>
                  <div class="file-upload-area" data-path="deploy/guide.md" data-accept=".md">
                    <div class="file-upload-content">
                      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                        <path d="M14 2v6h6"/>
                      </svg>
                      <p class="text-sm">${t('management.form.dropOrClick')}</p>
                      ${solution?.has_guide ? `<span class="file-uploaded">${t('management.form.uploaded')}: guide.md</span>` : ''}
                    </div>
                    <input type="file" class="file-input" accept=".md">
                  </div>
                </div>
                <div class="form-group">
                  <label>${t('management.form.guideZh')}</label>
                  <div class="file-upload-area" data-path="deploy/guide_zh.md" data-accept=".md">
                    <div class="file-upload-content">
                      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                        <path d="M14 2v6h6"/>
                      </svg>
                      <p class="text-sm">${t('management.form.dropOrClick')}</p>
                      ${solution?.has_guide_zh ? `<span class="file-uploaded">${t('management.form.uploaded')}: guide_zh.md</span>` : ''}
                    </div>
                    <input type="file" class="file-input" accept=".md">
                  </div>
                </div>
              </div>
            </div>
            ` : ''}
          </form>
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

  // Add modal to DOM
  const modalContainer = document.getElementById('modal-container');
  modalContainer.innerHTML = modalHtml;

  // Bind modal events
  document.getElementById('modal-close').addEventListener('click', closeModal);
  document.getElementById('btn-cancel').addEventListener('click', closeModal);
  document.getElementById('btn-save').addEventListener('click', saveSolution);

  // Close on overlay click
  document.getElementById('solution-modal').addEventListener('click', (e) => {
    if (e.target.id === 'solution-modal') closeModal();
  });

  // Setup file upload areas
  if (isEdit) {
    setupFileUploads();
  }

  // Validate ID on input
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
}

/**
 * Setup file upload areas with drag & drop
 */
function setupFileUploads() {
  const uploadAreas = document.querySelectorAll('.file-upload-area');

  uploadAreas.forEach(area => {
    const input = area.querySelector('.file-input');
    const content = area.querySelector('.file-upload-content');

    // Click to select
    area.addEventListener('click', () => input.click());

    // Drag events
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

    // File input change
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

  // Show uploading state
  area.classList.add('uploading');
  const content = area.querySelector('.file-upload-content');
  const originalHtml = content.innerHTML;
  content.innerHTML = `<div class="spinner"></div><p>${t('common.loading')}</p>`;

  try {
    await solutionsApi.uploadAsset(editingSolution.id, file, path, updateField);

    // Update UI to show success
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

  // Validate ID for new solutions
  if (!editingSolution && !SOLUTION_ID_PATTERN.test(data.id)) {
    toast.error(t('management.messages.invalidId'));
    return;
  }

  const saveBtn = document.getElementById('btn-save');
  saveBtn.disabled = true;
  saveBtn.innerHTML = `<span class="spinner-sm"></span> ${t('common.loading')}`;

  try {
    if (editingSolution) {
      // Update existing
      await solutionsApi.update(editingSolution.id, data);
      toast.success(t('management.messages.updateSuccess'));
    } else {
      // Create new
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

  // Bind events
  document.getElementById('btn-cancel-delete').addEventListener('click', closeDeleteDialog);
  document.getElementById('btn-confirm-delete').addEventListener('click', () => deleteSolution(solutionId));
  document.getElementById('delete-dialog').addEventListener('click', (e) => {
    if (e.target.id === 'delete-dialog') closeDeleteDialog();
  });
}

/**
 * Close delete dialog
 */
function closeDeleteDialog() {
  const modalContainer = document.getElementById('modal-container');
  modalContainer.innerHTML = '';
}

/**
 * Delete solution
 */
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
