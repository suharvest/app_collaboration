/**
 * Solution Detail Page - Introduction View
 */

import { solutionsApi, getAssetUrl } from '../modules/api.js';
import { t, getLocalizedField, i18n } from '../modules/i18n.js';
import { router } from '../modules/router.js';
import { toast } from '../modules/toast.js';
import { PLACEHOLDER_IMAGE, DEVICE_PLACEHOLDER, escapeHtml } from '../modules/utils.js';

let currentSolution = null;

export async function renderSolutionDetailPage(params) {
  const { id } = params;
  const container = document.getElementById('content-area');

  // Show loading state
  container.innerHTML = `
    <div class="back-btn" id="back-btn">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M19 12H5M12 19l-7-7 7-7"/>
      </svg>
      <span data-i18n="deploy.back">${t('deploy.back')}</span>
    </div>
    <div class="solution-intro">
      <div class="skeleton skeleton-image mb-6" style="height: 256px;"></div>
      <div class="skeleton skeleton-title mb-4" style="width: 60%;"></div>
      <div class="skeleton skeleton-text mb-2"></div>
      <div class="skeleton skeleton-text mb-2"></div>
      <div class="skeleton skeleton-text" style="width: 80%;"></div>
    </div>
  `;

  try {
    currentSolution = await solutionsApi.get(id, i18n.locale);

    // Description is included in the solution response (already localized by API)
    const descriptionHtml = currentSolution.description || '';

    container.innerHTML = renderSolutionIntro(currentSolution, descriptionHtml);
    setupEventHandlers(container, id);
  } catch (error) {
    console.error('Failed to load solution:', error);
    toast.error(t('common.error') + ': ' + error.message);
    container.innerHTML = renderErrorState(error.message);
  }
}

function renderSolutionIntro(solution, descriptionHtml) {
  const name = getLocalizedField(solution, 'name');
  // API returns fields directly on solution, not nested under intro
  const summary = getLocalizedField(solution, 'summary');
  const stats = solution.stats || {};
  const requiredDevices = solution.required_devices || [];
  const partners = solution.partners || [];
  const gallery = solution.gallery || [];

  // cover_image URL is already complete from API
  const coverImage = solution.cover_image || PLACEHOLDER_IMAGE;

  return `
    <div class="back-btn" id="back-btn">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M19 12H5M12 19l-7-7 7-7"/>
      </svg>
      <span data-i18n="deploy.back">${t('deploy.back')}</span>
    </div>

    <div class="solution-intro animate-fade-in">
      <!-- Hero Section -->
      <div class="solution-hero">
        <img
          class="solution-hero-image"
          src="${coverImage}"
          alt="${escapeHtml(name)}"
          onerror="if(!this.dataset.err){this.dataset.err='1';this.src='${PLACEHOLDER_IMAGE}';}"
        />
        <!-- Title Row with Deploy Button -->
        <div class="flex flex-wrap items-start justify-between gap-4 mb-4">
          <div class="flex-1 min-w-0">
            <h1 class="solution-title mb-2">${escapeHtml(name)}</h1>
            <p class="solution-summary mb-0">${escapeHtml(summary)}</p>
          </div>
          <button class="btn-deploy-hero flex-shrink-0" id="start-deploy-btn">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2L2 7l10 5 10-5-10-5z"/>
              <path d="M2 17l10 5 10-5"/>
              <path d="M2 12l10 5 10-5"/>
            </svg>
            ${t('solutions.startDeploy')}
          </button>
        </div>

        <!-- Stats -->
        <div class="solution-stats">
          ${stats.difficulty ? `
            <div class="solution-stat">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 2L2 7l10 5 10-5-10-5z"/>
              </svg>
              <span>${t('solutions.difficulty.' + stats.difficulty)}</span>
            </div>
          ` : ''}
          ${stats.estimated_time ? `
            <div class="solution-stat">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
                <polyline points="12 6 12 12 16 14"/>
              </svg>
              <span>${stats.estimated_time}</span>
            </div>
          ` : ''}
          ${stats.deployed_count !== undefined ? `
            <div class="solution-stat">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                <polyline points="22 4 12 14.01 9 11.01"/>
              </svg>
              <span>${stats.deployed_count} ${t('solutions.deployedCount')}</span>
            </div>
          ` : ''}
        </div>

        <!-- Required Devices (after stats) -->
        ${requiredDevices.length > 0 ? `
          <div class="solution-devices-inline">
            ${requiredDevices.map(device => renderRequiredDeviceInline(solution.id, device)).join('')}
          </div>
        ` : ''}
      </div>

      <!-- Gallery -->
      ${gallery.length > 0 ? `
        <div class="gallery">
          ${gallery.map((item, index) => renderGalleryItem(solution.id, item, index)).join('')}
        </div>
      ` : ''}

      <!-- Description -->
      ${descriptionHtml ? `
        <div class="markdown-content markdown-content-intro mb-8">
          ${descriptionHtml}
        </div>
      ` : ''}

      <!-- External Links -->
      ${(solution.links?.wiki || solution.links?.github) ? `
        <div class="flex flex-wrap items-center gap-3 mb-8">
          ${solution.links?.wiki ? `
            <a href="${solution.links.wiki}" target="_blank" class="btn btn-secondary">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/>
                <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
              </svg>
              Wiki
            </a>
          ` : ''}
          ${solution.links?.github ? `
            <a href="${solution.links.github}" target="_blank" class="btn btn-secondary">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"/>
              </svg>
              GitHub
            </a>
          ` : ''}
        </div>
      ` : ''}

      <!-- Deployment Partners -->
      <div class="section-header">
        <h2 class="section-title" data-i18n="solutions.deploymentPartners">${t('solutions.deploymentPartners')}</h2>
      </div>
      <p class="partners-description">${t('solutions.partnersDescription')}</p>
      ${partners.length > 0 ? `
        <div class="partners-grid">
          ${partners.map(partner => renderPartner(partner)).join('')}
        </div>
      ` : ''}
      <div class="partner-register-box">
        <div class="partner-register-info">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
            <circle cx="8.5" cy="7" r="4"/>
            <line x1="20" y1="8" x2="20" y2="14"/>
            <line x1="23" y1="11" x2="17" y2="11"/>
          </svg>
          <span>${t('solutions.partnerRegisterHint')}</span>
        </div>
        <a href="https://www.seeedstudio.com/partner-program" target="_blank" class="btn btn-primary btn-sm">
          ${t('solutions.becomePartner')}
        </a>
      </div>
    </div>
  `;
}

function renderGalleryItem(solutionId, item, index) {
  // API returns full URLs for gallery items
  const src = item.src || PLACEHOLDER_IMAGE;
  const caption = getLocalizedField(item, 'caption');

  if (item.type === 'video') {
    const thumbnail = item.thumbnail || PLACEHOLDER_IMAGE;

    return `
      <div class="gallery-item gallery-video" data-index="${index}" data-type="video" data-src="${src}">
        <img class="gallery-image" src="${thumbnail}" alt="${escapeHtml(caption)}" onerror="if(!this.dataset.err){this.dataset.err='1';this.src='${PLACEHOLDER_IMAGE}';}" />
      </div>
    `;
  }

  return `
    <div class="gallery-item" data-index="${index}" data-type="image" data-src="${src}">
      <img class="gallery-image" src="${src}" alt="${escapeHtml(caption)}" onerror="if(!this.dataset.err){this.dataset.err='1';this.src='${PLACEHOLDER_IMAGE}';}" />
    </div>
  `;
}

function renderRequiredDevice(solutionId, device) {
  const name = getLocalizedField(device, 'name');
  const description = getLocalizedField(device, 'description');
  // API returns full URL for device image
  const image = device.image || DEVICE_PLACEHOLDER;

  return `
    <div class="required-device">
      <img class="required-device-image" src="${image}" alt="${escapeHtml(name)}" onerror="if(!this.dataset.err){this.dataset.err='1';this.src='${DEVICE_PLACEHOLDER}';}" />
      <div class="required-device-info">
        <div class="required-device-name">${escapeHtml(name)}</div>
        <div class="required-device-desc">${escapeHtml(description)}</div>
      </div>
      ${device.purchase_url ? `
        <a href="${device.purchase_url}" target="_blank" class="btn btn-secondary btn-sm">
          ${t('solutions.purchase')}
        </a>
      ` : ''}
    </div>
  `;
}

function renderRequiredDeviceInline(solutionId, device) {
  const name = getLocalizedField(device, 'name');
  const image = device.image || DEVICE_PLACEHOLDER;

  return `
    <a href="${device.purchase_url || '#'}" target="${device.purchase_url ? '_blank' : '_self'}" class="device-chip">
      <img src="${image}" alt="${escapeHtml(name)}" onerror="if(!this.dataset.err){this.dataset.err='1';this.src='${DEVICE_PLACEHOLDER}';}" />
      <span>${escapeHtml(name)}</span>
    </a>
  `;
}

function renderPartner(partner) {
  const name = getLocalizedField(partner, 'name');
  const regions = partner.regions || [];

  return `
    <div class="partner-card">
      <div class="partner-header">
        ${partner.logo ? `
          <img class="partner-logo" src="${partner.logo}" alt="${escapeHtml(name)}" onerror="this.style.display='none'" />
        ` : `
          <div class="partner-logo-placeholder">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
              <polyline points="9 22 9 12 15 12 15 22"/>
            </svg>
          </div>
        `}
        <div class="partner-name">${escapeHtml(name)}</div>
      </div>
      <div class="partner-regions">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
          <circle cx="12" cy="10" r="3"/>
        </svg>
        <span>${regions.map(r => escapeHtml(r)).join(', ')}</span>
      </div>
      <div class="partner-actions">
        ${partner.contact ? `
          <a href="mailto:${partner.contact}" class="partner-contact" title="${t('solutions.contactPartner')}">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
              <polyline points="22,6 12,13 2,6"/>
            </svg>
            ${escapeHtml(partner.contact)}
          </a>
        ` : ''}
        ${partner.website ? `
          <a href="${partner.website}" target="_blank" class="partner-website" title="${t('solutions.visitWebsite')}">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="2" y1="12" x2="22" y2="12"/>
              <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
            </svg>
            ${t('solutions.visitWebsite')}
          </a>
        ` : ''}
      </div>
    </div>
  `;
}

function renderErrorState(message) {
  return `
    <div class="back-btn" id="back-btn">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M19 12H5M12 19l-7-7 7-7"/>
      </svg>
      <span data-i18n="deploy.back">${t('deploy.back')}</span>
    </div>
    <div class="empty-state">
      <svg class="empty-state-icon text-danger" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <circle cx="12" cy="12" r="10"/>
        <line x1="12" y1="8" x2="12" y2="12"/>
        <line x1="12" y1="16" x2="12.01" y2="16"/>
      </svg>
      <h3 class="empty-state-title">${t('common.error')}</h3>
      <p class="empty-state-description">${escapeHtml(message)}</p>
    </div>
  `;
}

function setupEventHandlers(container, solutionId) {
  // Back button
  const backBtn = container.querySelector('#back-btn');
  if (backBtn) {
    backBtn.addEventListener('click', () => {
      router.navigate('solutions');
    });
  }

  // Start deploy button
  const deployBtn = container.querySelector('#start-deploy-btn');
  if (deployBtn) {
    deployBtn.addEventListener('click', () => {
      router.navigate('deploy', { id: solutionId });
    });
  }

  // Gallery items
  container.querySelectorAll('.gallery-item').forEach(item => {
    item.addEventListener('click', () => {
      const type = item.dataset.type;
      const src = item.dataset.src;
      openMediaModal(type, src);
    });
  });
}

function openMediaModal(type, src) {
  const modalContainer = document.getElementById('modal-container');

  if (type === 'video') {
    modalContainer.innerHTML = `
      <div class="modal" id="media-modal">
        <div class="modal-content" style="max-width: 800px;">
          <div class="modal-header">
            <h3>Video</h3>
            <button class="close-btn" id="close-modal">&times;</button>
          </div>
          <div class="modal-body p-0">
            <video controls autoplay style="width: 100%;">
              <source src="${src}" type="video/mp4">
              Your browser does not support video.
            </video>
          </div>
        </div>
      </div>
    `;
  } else {
    modalContainer.innerHTML = `
      <div class="modal" id="media-modal">
        <div class="modal-content" style="max-width: 900px;">
          <div class="modal-header">
            <h3>Image</h3>
            <button class="close-btn" id="close-modal">&times;</button>
          </div>
          <div class="modal-body p-0">
            <img src="${src}" style="width: 100%;" />
          </div>
        </div>
      </div>
    `;
  }

  // Close modal handlers
  const modal = document.getElementById('media-modal');
  const closeBtn = document.getElementById('close-modal');

  closeBtn.addEventListener('click', () => {
    modalContainer.innerHTML = '';
  });

  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      modalContainer.innerHTML = '';
    }
  });
}

// Re-render when language changes
i18n.onLocaleChange(() => {
  if (router.currentRoute === 'solution' && currentSolution) {
    renderSolutionDetailPage({ id: currentSolution.id });
  }
});
