/**
 * Deployments History Page
 */

import { deploymentsApi } from '../modules/api.js';
import { t, i18n } from '../modules/i18n.js';
import { router } from '../modules/router.js';
import { toast } from '../modules/toast.js';

export async function renderDeploymentsPage() {
  const container = document.getElementById('content-area');

  container.innerHTML = `
    <div class="page-header">
      <h1 class="page-title" data-i18n="deployments.title">${t('deployments.title')}</h1>
    </div>

    <div class="deployment-summary mb-6">
      <div class="deployment-summary-header">
        <h2 class="deployment-summary-title">${t('deployments.stats.total')}</h2>
      </div>
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

  try {
    const deployments = await deploymentsApi.list();
    renderDeploymentsList(deployments);
    updateStats(deployments);
  } catch (error) {
    console.error('Failed to load deployments:', error);
    toast.error(t('common.error') + ': ' + error.message);
    document.getElementById('deployments-list').innerHTML = renderEmptyState();
  }
}

function renderDeploymentsList(deployments) {
  const listContainer = document.getElementById('deployments-list');

  if (!deployments || deployments.length === 0) {
    listContainer.innerHTML = renderEmptyState();
    return;
  }

  listContainer.innerHTML = `
    <div class="device-list">
      ${deployments.map(renderDeploymentItem).join('')}
    </div>
  `;
}

function renderDeploymentItem(deployment) {
  const statusClass = deployment.status === 'completed' ? 'ready' :
                      deployment.status === 'failed' ? 'failed' : 'running';

  const date = new Date(deployment.created_at).toLocaleString();

  return `
    <div class="device-card">
      <div class="device-card-header">
        <div class="device-card-title">
          ${deployment.solution_id} / ${deployment.device_id}
        </div>
        <span class="status-badge ${statusClass}">
          ${deployment.status}
        </span>
      </div>
      <div class="text-sm text-text-secondary">
        ${date}
      </div>
    </div>
  `;
}

function updateStats(deployments) {
  const total = deployments.length;
  const success = deployments.filter(d => d.status === 'completed').length;
  const failed = deployments.filter(d => d.status === 'failed').length;

  document.getElementById('stat-total').textContent = total;
  document.getElementById('stat-success').textContent = success;
  document.getElementById('stat-failed').textContent = failed;
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
