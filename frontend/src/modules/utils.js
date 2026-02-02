/**
 * Utility functions
 */

// SVG placeholder as data URI (prevents infinite request loops)
// Note: Single quotes are URL-encoded (%27) to prevent breaking inline event handlers
export const PLACEHOLDER_IMAGE = `data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 width=%27400%27 height=%27300%27 viewBox=%270 0 400 300%27%3E%3Crect width=%27400%27 height=%27300%27 fill=%27%23f4f7f0%27/%3E%3Crect x=%27150%27 y=%27100%27 width=%27100%27 height=%2780%27 rx=%278%27 fill=%27%23e8f5d6%27 stroke=%27%238cc63f%27 stroke-width=%272%27/%3E%3Ctext x=%27200%27 y=%27220%27 text-anchor=%27middle%27 fill=%27%23999%27 font-family=%27sans-serif%27 font-size=%2714%27%3ENo Image%3C/text%3E%3C/svg%3E`;

export const DEVICE_PLACEHOLDER = `data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 width=%27100%27 height=%27100%27 viewBox=%270 0 100 100%27%3E%3Crect width=%27100%27 height=%27100%27 fill=%27%23f4f7f0%27/%3E%3Crect x=%2725%27 y=%2725%27 width=%2750%27 height=%2740%27 rx=%274%27 fill=%27%23e8f5d6%27 stroke=%27%238cc63f%27 stroke-width=%272%27/%3E%3Ccircle cx=%2750%27 cy=%2745%27 r=%2710%27 fill=%27%238cc63f%27/%3E%3C/svg%3E`;

/**
 * Handle image load error - sets placeholder and prevents infinite loops
 */
export function handleImageError(img) {
  if (!img.dataset.errorHandled) {
    img.dataset.errorHandled = 'true';
    img.src = PLACEHOLDER_IMAGE;
  }
}

/**
 * Escape HTML to prevent XSS
 */
export function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Process markdown HTML content to fix image and link paths
 * Converts relative paths like "gallery/image.png" or "assets/file.xlsx" to proper asset URLs
 * @param {string} html - HTML content from markdown conversion
 * @param {string} solutionId - Solution ID for building asset URLs
 * @param {function} getAssetUrl - Function to build asset URLs
 * @returns {string} HTML with fixed paths
 */
export function processMarkdownImages(html, solutionId, getAssetUrl) {
  if (!html || !solutionId) return html;

  // Helper to check if path needs processing
  const needsProcessing = (path) => {
    return path &&
           !path.startsWith('http://') &&
           !path.startsWith('https://') &&
           !path.startsWith('data:') &&
           !path.startsWith('/api/') &&
           !path.startsWith('#') &&
           !path.startsWith('mailto:') &&
           !path.startsWith('tel:');
  };

  // Process img tags
  let result = html.replace(
    /<img\s+([^>]*?)src=["']([^"']+)["']([^>]*?)>/gi,
    (match, before, src, after) => {
      if (!needsProcessing(src)) return match;
      const assetUrl = getAssetUrl(solutionId, src);
      return `<img ${before}src="${assetUrl}"${after}>`;
    }
  );

  // Process anchor tags with asset links (files like .xlsx, .pdf, .zip, etc.)
  result = result.replace(
    /<a\s+([^>]*?)href=["']([^"']+)["']([^>]*?)>/gi,
    (match, before, href, after) => {
      if (!needsProcessing(href)) return match;
      // Only process if it looks like an asset file (has extension)
      if (!/\.(xlsx|xls|pdf|zip|csv|doc|docx|ppt|pptx|png|jpg|jpeg|gif|mp4|mp3)$/i.test(href)) {
        return match;
      }
      const assetUrl = getAssetUrl(solutionId, href);
      // Add download attribute for file downloads
      const hasDownload = /download/i.test(before + after);
      const downloadAttr = hasDownload ? '' : ' download';
      return `<a ${before}href="${assetUrl}"${after}${downloadAttr}>`;
    }
  );

  return result;
}
