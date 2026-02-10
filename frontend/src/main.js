/**
 * Provisioning Station - Main Application Entry
 */

import './main.css';
import { router } from './modules/router.js';
import { i18n, t } from './modules/i18n.js';
import { toast } from './modules/toast.js';
import { waitForBackendReady } from './modules/api.js';
import { updater } from './modules/updater.js';

// Import pages
import { renderSolutionsPage } from './pages/solutions.js';
import { renderSolutionDetailPage } from './pages/solution-detail.js';
import { renderDeployPage, cleanupDeployPage } from './pages/deploy.js';
import { renderDeploymentsPage } from './pages/deployments.js';
import { renderDevicesPage } from './pages/devices.js';
import { renderManagementPage } from './pages/solution-management.js';
import { renderSettingsPage } from './pages/settings.js';

// Initialize application
async function initApp() {
  const splash = document.getElementById('splash-screen');
  const splashStatus = document.getElementById('splash-status');
  const app = document.getElementById('app');

  const updateStatus = (msg) => {
    if (splashStatus) splashStatus.textContent = msg;
  };

  try {
    // Show backend startup message in Tauri mode
    if (window.__TAURI__) {
      updateStatus('Starting backend...');
    }

    // Wait for backend to be ready (Tauri mode)
    await waitForBackendReady();
    updateStatus('Loading...');

    // Initialize i18n
    i18n.updateDOM();

    // Setup language toggle
    const langToggle = document.getElementById('lang-toggle');
    const currentLangEl = document.getElementById('current-lang');

    if (langToggle && currentLangEl) {
      currentLangEl.textContent = i18n.locale.toUpperCase();

      langToggle.addEventListener('click', () => {
        i18n.toggle();
        currentLangEl.textContent = i18n.locale.toUpperCase();
      });
    }

    // Setup navigation
    setupNavigation();

    // Setup router
    setupRouter();

    // Start router
    router.init();

    // Hide splash and show app
    if (splash && app) {
      splash.classList.add('hidden');
      app.style.display = '';
      // Remove splash from DOM after transition
      setTimeout(() => splash.remove(), 400);
    }

    // Check for updates silently after app is ready (Tauri only)
    if (window.__TAURI__) {
      // Delay update check to not interfere with startup
      setTimeout(() => {
        updater.checkForUpdates(true);
      }, 3000);
    }
  } catch (error) {
    console.error('Application initialization failed:', error);
    updateStatus('Failed to start. Please restart the application.');
  }
}

function setupNavigation() {
  const navItems = document.querySelectorAll('.nav-item[data-page]');

  navItems.forEach(item => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      const page = item.dataset.page;
      router.navigate(page);
    });
  });
}

function setupRouter() {
  // Register routes
  router
    .register('solutions', renderSolutionsPage)
    .register('solution', renderSolutionDetailPage)
    .register('deploy', renderDeployPage)
    .register('devices', renderDevicesPage)
    .register('deployments', renderDeploymentsPage)
    .register('management', renderManagementPage)
    .register('settings', renderSettingsPage);

  // Before each navigation
  router.beforeEach((to, params, from) => {
    // Cleanup previous page if needed
    if (from === 'deploy') {
      cleanupDeployPage();
    }
    return true;
  });

  // After each navigation
  router.afterEach((to, params) => {
    // Update page title
    updatePageTitle(to);

    // Update active nav item
    updateActiveNavItem(to);
  });
}

function updatePageTitle(route) {
  const titles = {
    solutions: 'nav.solutions',
    solution: 'nav.solutions',
    deploy: 'deploy.title',
    devices: 'nav.devices',
    deployments: 'nav.deployments',
    management: 'nav.management',
    settings: 'nav.settings',
  };

  const titleKey = titles[route] || 'nav.solutions';
  const pageTitle = document.getElementById('page-title');

  if (pageTitle) {
    pageTitle.textContent = t(titleKey);
    pageTitle.setAttribute('data-i18n', titleKey);
  }

  document.title = `${t(titleKey)} - SenseCraft Solution`;
}

function updateActiveNavItem(route) {
  const navItems = document.querySelectorAll('.nav-item[data-page]');

  navItems.forEach(item => {
    const page = item.dataset.page;
    const isActive = page === route ||
                     (route === 'solution' && page === 'solutions') ||
                     (route === 'deploy' && page === 'solutions');

    item.classList.toggle('active', isActive);
  });
}

// Wait for DOM to be ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => initApp());
} else {
  initApp();
}

// Handle errors
window.addEventListener('error', (event) => {
  console.error('Application error:', event.error);
  toast.error('An error occurred. Please check the console.');
});

window.addEventListener('unhandledrejection', (event) => {
  console.error('Unhandled promise rejection:', event.reason);
  toast.error('An error occurred. Please check the console.');
});
