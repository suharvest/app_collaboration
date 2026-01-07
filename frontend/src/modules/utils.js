/**
 * Utility functions
 */

// SVG placeholder as data URI (prevents infinite request loops)
export const PLACEHOLDER_IMAGE = `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='300' viewBox='0 0 400 300'%3E%3Crect width='400' height='300' fill='%23f4f7f0'/%3E%3Crect x='150' y='100' width='100' height='80' rx='8' fill='%23e8f5d6' stroke='%238cc63f' stroke-width='2'/%3E%3Ctext x='200' y='220' text-anchor='middle' fill='%23999' font-family='sans-serif' font-size='14'%3ENo Image%3C/text%3E%3C/svg%3E`;

export const DEVICE_PLACEHOLDER = `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='100' height='100' viewBox='0 0 100 100'%3E%3Crect width='100' height='100' fill='%23f4f7f0'/%3E%3Crect x='25' y='25' width='50' height='40' rx='4' fill='%23e8f5d6' stroke='%238cc63f' stroke-width='2'/%3E%3Ccircle cx='50' cy='45' r='10' fill='%238cc63f'/%3E%3C/svg%3E`;

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
