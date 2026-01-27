/**
 * Deploy Page - Wiki-style Device Deployment
 * Main entry point - orchestrates modular components
 */

import { solutionsApi } from '../modules/api.js';
import { t, i18n } from '../modules/i18n.js';
import { router } from '../modules/router.js';
import { toast } from '../modules/toast.js';

// Import state management
import {
  getCurrentSolution,
  setCurrentSolution,
  getDeviceStates,
  setDeviceState,
  getSelectedPresetId,
  setSelectedPresetId,
  setDeviceGroupSelection,
  createInitialDeviceState,
  resetState,
  cleanupState,
} from './deploy/state.js';

// Import rendering functions
import { renderDeployContent } from './deploy/renderers.js';

// Import event handlers
import { setupEventHandlers } from './deploy/handlers.js';

// Import device operations
import { detectDevices } from './deploy/devices.js';
import { getFilteredDevices } from './deploy/utils.js';

// ============================================
// Main Page Entry Point
// ============================================

/**
 * Render the deploy page for a solution
 * @param {Object} params - Route params { id: solutionId, preset?: presetId }
 */
export async function renderDeployPage(params) {
  const { id, preset: initialPreset } = params;
  const container = document.getElementById('content-area');

  // Show loading
  container.innerHTML = `
    <div class="back-btn" id="back-btn">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M19 12H5M12 19l-7-7 7-7"/>
      </svg>
      <span>${t('deploy.back')}</span>
    </div>
    <div class="flex items-center justify-center py-16">
      <div class="spinner spinner-lg"></div>
    </div>
  `;

  try {
    const [solutionInfo, deploymentInfo] = await Promise.all([
      solutionsApi.get(id, i18n.locale),
      solutionsApi.getDeployment(id, i18n.locale)
    ]);

    // Store solution in state
    setCurrentSolution({
      ...solutionInfo,
      deployment: deploymentInfo
    });

    const currentSolution = getCurrentSolution();

    // Reset state for new solution
    resetState();

    // Initialize selected preset
    // Priority: 1. Passed from detail page, 2. First preset with section, 3. First preset
    const presets = deploymentInfo.presets || [];
    if (presets.length > 0) {
      // Check if initialPreset is valid
      const passedPreset = initialPreset && presets.find(p => p.id === initialPreset);
      if (passedPreset) {
        setSelectedPresetId(initialPreset);
      } else {
        const presetWithSection = presets.find(p => p.section);
        setSelectedPresetId(presetWithSection ? presetWithSection.id : presets[0].id);
      }
    }

    // Initialize device group selections from selected preset's device groups
    const selectedPresetId = getSelectedPresetId();
    const selectedPreset = presets.find(p => p.id === selectedPresetId);
    const deviceGroups = selectedPreset?.device_groups || [];
    deviceGroups.forEach(group => {
      if (group.type === 'single' && group.default) {
        setDeviceGroupSelection(group.id, group.default);
      } else if (group.type === 'multiple' && group.default_selections?.length > 0) {
        setDeviceGroupSelection(group.id, group.default_selections[0]);
      }
    });

    const devices = deploymentInfo.devices || [];

    // Initialize device states for filtered devices (preset-specific or global)
    // This ensures states exist for devices that will actually be rendered
    const filteredDevices = getFilteredDevices(devices);
    filteredDevices.forEach((device, index) => {
      setDeviceState(device.id, createInitialDeviceState(device, index));
    });

    // Render content and setup handlers
    renderDeployContent(container);
    setupEventHandlers(container);

    // Auto-detect devices
    await detectDevices();
  } catch (error) {
    console.error('Failed to load solution:', error);
    toast.error(t('common.error') + ': ' + error.message);
  }
}

// ============================================
// Cleanup
// ============================================

/**
 * Clean up resources when leaving the deploy page
 */
export function cleanupDeployPage() {
  cleanupState();
}

// ============================================
// Language Change Handler
// ============================================

// Re-render when language changes
i18n.onLocaleChange(() => {
  const currentSolution = getCurrentSolution();
  if (router.currentRoute === 'deploy' && currentSolution) {
    renderDeployPage({ id: currentSolution.id });
  }
});
