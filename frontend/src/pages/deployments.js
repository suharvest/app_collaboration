/**
 * Deployments History Page
 * Shows deployment records as expandable cards with step progress
 */

import { deploymentsApi } from '../modules/api.js';
import { t, i18n } from '../modules/i18n.js';
import { router } from '../modules/router.js';
import { toast } from '../modules/toast.js';

let pollInterval = null;

export async function renderDeploymentsPage() {
  const container = document.getElementById('content-area');

  container.innerHTML = `
    <div class="page-header">
      <h1 class="page-title" data-i18n="deployments.title">${t('deployments.title')}</h1>
    </div>

    <div class="deployment-summary mb-6">
      <div class="deployment-summary-stats" id="deployment-stats">
        <div class="deployment-stat">
          <div class="deployment-stat-value" id="stat-total">-</div>
          <div class="deployment-stat-label">${t('deployments.stats.total')}</div>
        </div>
        <div class="deployment-stat">
          <div class="deployment-stat-value text-success" id="stat-success">-</div>
          <div class="deployment-stat-label">${t('deployments.stats.success')}</div>
        </div>
        <div class="deployment-stat">
          <div class="deployment-stat-value text-danger" id="stat-failed">-</div>
          <div class="deployment-stat-label">${t('deployments.stats.failed')}</div>
        </div>
      </div>
    </div>

    <div id="deployments-list">
      <div class="flex items-center justify-center py-8">
        <div class="spinner spinner-lg"></div>
      </div>
    </div>
  `;

  await loadDeployments();
  startPolling();
}

async function loadDeployments() {
  try {
    const deployments = await deploymentsApi.list();
    renderDeploymentsList(deployments);
    updateStats(deployments);

    // Check if any are still running
    const hasActive = deployments.some(d => d.status === 'running' || d.status === 'pending');
    if (!hasActive) {
      stopPolling();
    }
  } catch (error) {
    console.error('Failed to load deployments:', error);
    toast.error(t('common.error') + ': ' + error.message);
    document.getElementById('deployments-list').innerHTML = renderEmptyState();
    stopPolling();
  }
}

function startPolling() {
  stopPolling();
  pollInterval = setInterval(() => {
    if (router.currentRoute === 'deployments') {
      loadDeployments();
    } else {
      stopPolling();
    }
  }, 3000);
}

function stopPolling() {
  if (pollInterval) {
    clearInterval(pollInterval);
    pollInterval = null;
  }
}

function renderDeploymentsList(deployments) {
  const listContainer = document.getElementById('deployments-list');

  if (!deployments || deployments.length === 0) {
    listContainer.innerHTML = renderEmptyState();
    return;
  }

  listContainer.innerHTML = `
    <div class="deployment-records">
      ${deployments.map(renderDeploymentCard).join('')}
    </div>
  `;

  // Setup expand/collapse handlers
  setupCardHandlers();
}

function renderDeploymentCard(deployment) {
  const statusClass = deployment.status === 'completed' ? 'ready' :
                      deployment.status === 'failed' ? 'failed' :
                      deployment.status === 'running' ? 'running' : 'pending';

  const statusText = t(`deployments.status.${deployment.status}`) || deployment.status;
  const date = new Date(deployment.started_at).toLocaleString();

  // Step progress summary
  const totalSteps = deployment.steps ? deployment.steps.length : 0;
  const completedSteps = deployment.steps ? deployment.steps.filter(s => s.status === 'completed').length : 0;
  const stepSummary = totalSteps > 0 ? `${completedSteps}/${totalSteps}` : '';

  const hasSteps = totalSteps > 0;

  return `
    <div class="deployment-record-card" data-deployment-id="${deployment.id}">
      <div class="deployment-record-header">
        <div class="deployment-record-info">
          <div class="deployment-record-title">${deployment.solution_name}</div>
          <div class="deployment-record-meta">
            ${deployment.device_id ? `<span class="deployment-record-device">${deployment.device_id}</span>` : ''}
            <span class="deployment-record-date">${date}</span>
          </div>
        </div>
        <div class="deployment-record-right">
          ${stepSummary ? `<span class="deployment-record-progress">${stepSummary}</span>` : ''}
          <span class="status-badge ${statusClass}">${statusText}</span>
          ${hasSteps ? `
            <button class="deployment-record-expand" data-deployment-id="${deployment.id}">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="6 9 12 15 18 9"/>
              </svg>
            </button>
          ` : ''}
          <button class="deployment-record-delete" data-deployment-id="${deployment.id}" title="${t('devices.actions.delete')}">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2m3 0v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6h14"/>
            </svg>
          </button>
        </div>
      </div>
      ${hasSteps ? `
        <div class="deployment-record-steps" id="steps-${deployment.id}" style="display: none;">
          ${deployment.steps.map(renderStepItem).join('')}
        </div>
      ` : ''}
    </div>
  `;
}

function renderStepItem(step) {
  const iconMap = {
    completed: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" class="text-success"><polyline points="20 6 9 17 4 12"/></svg>`,
    failed: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" class="text-danger"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`,
    running: `<div class="spinner spinner-sm"></div>`,
    skipped: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-text-muted"><path d="M5 12h14M12 5l7 7-7 7"/></svg>`,
    pending: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-text-muted"><circle cx="12" cy="12" r="10"/></svg>`,
  };

  const icon = iconMap[step.status] || iconMap.pending;
  const statusClass = step.status;

  return `
    <div class="step-item ${statusClass}">
      <div class="step-item-icon">${icon}</div>
      <div class="step-item-name">${step.name}</div>
      <div class="step-item-status">${t(`deployments.steps.${step.status}`) || step.status}</div>
    </div>
  `;
}

function setupCardHandlers() {
  // Expand/collapse buttons
  document.querySelectorAll('.deployment-record-expand').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const id = btn.dataset.deploymentId;
      const stepsEl = document.getElementById(`steps-${id}`);
      if (stepsEl) {
        const isExpanded = stepsEl.style.display !== 'none';
        stepsEl.style.display = isExpanded ? 'none' : 'block';
        btn.classList.toggle('expanded', !isExpanded);
      }
    });
  });

  // Delete buttons
  document.querySelectorAll('.deployment-record-delete').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const id = btn.dataset.deploymentId;
      if (!confirm(t('devices.actions.confirmDelete'))) return;

      try {
        await deploymentsApi.delete(id);
        const card = btn.closest('.deployment-record-card');
        if (card) card.remove();
        toast.success(t('devices.actions.deleted'));
      } catch (error) {
        toast.error(t('common.error') + ': ' + error.message);
      }
    });
  });
}

function updateStats(deployments) {
  const total = deployments.length;
  const success = deployments.filter(d => d.status === 'completed').length;
  const failed = deployments.filter(d => d.status === 'failed').length;

  const totalEl = document.getElementById('stat-total');
  const successEl = document.getElementById('stat-success');
  const failedEl = document.getElementById('stat-failed');

  if (totalEl) totalEl.textContent = total;
  if (successEl) successEl.textContent = success;
  if (failedEl) failedEl.textContent = failed;
}

function renderEmptyState() {
  return `
    <div class="empty-state">
      <svg class="empty-state-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M12 2L2 7l10 5 10-5-10-5z"/>
        <path d="M2 17l10 5 10-5"/>
        <path d="M2 12l10 5 10-5"/>
      </svg>
      <h3 class="empty-state-title" data-i18n="deployments.empty">${t('deployments.empty')}</h3>
      <p class="empty-state-description" data-i18n="deployments.emptyDescription">${t('deployments.emptyDescription')}</p>
    </div>
  `;
}

// Re-render when language changes
i18n.onLocaleChange(() => {
  if (router.currentRoute === 'deployments') {
    renderDeploymentsPage();
  }
});

// Cleanup on page leave
const origRender = renderDeploymentsPage;
export function cleanupDeploymentsPage() {
  stopPolling();
}
