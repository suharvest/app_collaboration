/* global global */
/**
 * Utils Module Tests
 *
 * Tests for processMarkdownImages (asset link/image rewriting)
 * and window.__downloadAsset (JS-based file download).
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { processMarkdownImages, escapeHtml } from '../utils.js'

// Simple mock for getAssetUrl
const mockGetAssetUrl = (solutionId, path) =>
  `/api/solutions/${solutionId}/assets/${path}`;

describe('processMarkdownImages', () => {
  describe('image processing', () => {
    it('should rewrite relative image src to asset URL', () => {
      const html = '<img src="gallery/photo.png">';
      const result = processMarkdownImages(html, 'my_solution', mockGetAssetUrl);
      expect(result).toBe('<img src="/api/solutions/my_solution/assets/gallery/photo.png">');
    });

    it('should skip external image URLs', () => {
      const html = '<img src="https://example.com/photo.png">';
      const result = processMarkdownImages(html, 'my_solution', mockGetAssetUrl);
      expect(result).toBe(html);
    });

    it('should skip data: image URLs', () => {
      const html = '<img src="data:image/png;base64,abc">';
      const result = processMarkdownImages(html, 'my_solution', mockGetAssetUrl);
      expect(result).toBe(html);
    });
  });

  describe('anchor link processing', () => {
    it('should rewrite .xlsx link and add onclick handler', () => {
      const html = '<a href="assets/inventory.xlsx">Download</a>';
      const result = processMarkdownImages(html, 'test_sol', mockGetAssetUrl);
      expect(result).toContain('href="/api/solutions/test_sol/assets/assets/inventory.xlsx"');
      expect(result).toContain("onclick=\"event.preventDefault();window.__downloadAsset(");
      expect(result).toContain('Download</a>');
    });

    it('should rewrite .pdf link with onclick handler', () => {
      const html = '<a href="docs/manual.pdf">Manual</a>';
      const result = processMarkdownImages(html, 'sol1', mockGetAssetUrl);
      expect(result).toContain('href="/api/solutions/sol1/assets/docs/manual.pdf"');
      expect(result).toContain('__downloadAsset');
    });

    it('should handle all supported file extensions', () => {
      const extensions = ['xlsx', 'xls', 'pdf', 'zip', 'csv', 'doc', 'docx', 'ppt', 'pptx', 'png', 'jpg', 'mp4'];
      for (const ext of extensions) {
        const html = `<a href="file.${ext}">Link</a>`;
        const result = processMarkdownImages(html, 's', mockGetAssetUrl);
        expect(result).toContain('__downloadAsset');
      }
    });

    it('should NOT process non-asset links (no file extension)', () => {
      const html = '<a href="some/page">Link</a>';
      const result = processMarkdownImages(html, 's', mockGetAssetUrl);
      expect(result).toBe(html);
    });

    it('should NOT process external URLs', () => {
      const html = '<a href="https://example.com/file.xlsx">Link</a>';
      const result = processMarkdownImages(html, 's', mockGetAssetUrl);
      expect(result).toBe(html);
    });

    it('should NOT process mailto links', () => {
      const html = '<a href="mailto:test@test.com">Email</a>';
      const result = processMarkdownImages(html, 's', mockGetAssetUrl);
      expect(result).toBe(html);
    });

    it('should NOT process anchor links', () => {
      const html = '<a href="#section">Jump</a>';
      const result = processMarkdownImages(html, 's', mockGetAssetUrl);
      expect(result).toBe(html);
    });

    it('should NOT process /api/ prefixed links', () => {
      const html = '<a href="/api/solutions/s/assets/file.xlsx">Link</a>';
      const result = processMarkdownImages(html, 's', mockGetAssetUrl);
      expect(result).toBe(html);
    });

    it('should escape single quotes in onclick handler', () => {
      const getUrl = (sid, path) => `/api/sol's/${path}`;
      const html = '<a href="file.xlsx">Link</a>';
      const result = processMarkdownImages(html, 's', getUrl);
      // The onclick string should have escaped quotes
      expect(result).toContain("__downloadAsset(");
      expect(result).toMatch(/onclick="[^"]*\\'/);
    });
  });

  describe('edge cases', () => {
    it('should return html unchanged if solutionId is empty', () => {
      const html = '<img src="photo.png">';
      expect(processMarkdownImages(html, '', mockGetAssetUrl)).toBe(html);
    });

    it('should return falsy html as-is', () => {
      expect(processMarkdownImages(null, 's', mockGetAssetUrl)).toBeNull();
      expect(processMarkdownImages('', 's', mockGetAssetUrl)).toBe('');
    });

    it('should process both images and links in same HTML', () => {
      const html = '<img src="gallery/img.png"><a href="assets/file.xlsx">DL</a>';
      const result = processMarkdownImages(html, 's', mockGetAssetUrl);
      expect(result).toContain('/api/solutions/s/assets/gallery/img.png');
      expect(result).toContain('__downloadAsset');
    });
  });
});

describe('window.__downloadAsset', () => {
  let originalFetch;
  let originalCreateObjectURL;
  let originalRevokeObjectURL;
  let originalOpen;

  beforeEach(() => {
    originalFetch = global.fetch;
    originalCreateObjectURL = URL.createObjectURL;
    originalRevokeObjectURL = URL.revokeObjectURL;
    originalOpen = window.open;

    // Mirror the implementation from main.js for testing
    window.__downloadAsset = async (url) => {
      const filename = url.split('/').pop()?.split('?')[0] || 'download';
      try {
        const resp = await fetch(url);
        if (!resp.ok) throw new Error(`Download failed: ${resp.status}`);
        const blob = await resp.blob();
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob) + '#' + encodeURIComponent(filename);
        a.download = filename;
        a.style.display = 'none';
        document.body.appendChild(a);
        a.click();
        setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 200);
      } catch (e) {
        console.error('Download error:', e);
        window.open(url, '_blank');
      }
    };
  });

  afterEach(() => {
    global.fetch = originalFetch;
    URL.createObjectURL = originalCreateObjectURL;
    URL.revokeObjectURL = originalRevokeObjectURL;
    window.open = originalOpen;
    delete window.__downloadAsset;
  });

  it('should fetch the URL and create a blob download with filename in fragment', async () => {
    const mockBlob = new Blob(['data'], { type: 'application/octet-stream' });
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      blob: () => Promise.resolve(mockBlob),
    });
    URL.createObjectURL = vi.fn().mockReturnValue('blob:http://localhost/abc');
    URL.revokeObjectURL = vi.fn();

    let capturedHref = '';
    const clickSpy = vi.fn();
    const origCreateElement = document.createElement.bind(document);
    vi.spyOn(document, 'createElement').mockImplementation((tag) => {
      const el = origCreateElement(tag);
      if (tag === 'a') {
        el.click = clickSpy;
        const origSet = Object.getOwnPropertyDescriptor(HTMLAnchorElement.prototype, 'href')?.set;
        if (origSet) {
          Object.defineProperty(el, 'href', {
            set(v) { capturedHref = v; origSet.call(el, v); },
            get() { return capturedHref; },
          });
        }
      }
      return el;
    });

    await window.__downloadAsset('http://127.0.0.1:3260/api/solutions/s/assets/file.xlsx');

    expect(global.fetch).toHaveBeenCalledWith('http://127.0.0.1:3260/api/solutions/s/assets/file.xlsx');
    expect(URL.createObjectURL).toHaveBeenCalledWith(mockBlob);
    expect(capturedHref).toContain('#file.xlsx');
    expect(clickSpy).toHaveBeenCalled();
  });

  it('should extract filename from URL', async () => {
    const mockBlob = new Blob(['data']);
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      blob: () => Promise.resolve(mockBlob),
    });
    URL.createObjectURL = vi.fn().mockReturnValue('blob:x');
    URL.revokeObjectURL = vi.fn();

    let downloadAttr = '';
    const origCreateElement = document.createElement.bind(document);
    vi.spyOn(document, 'createElement').mockImplementation((tag) => {
      const el = origCreateElement(tag);
      if (tag === 'a') {
        el.click = vi.fn();
        Object.defineProperty(el, 'download', {
          set(v) { downloadAttr = v; },
          get() { return downloadAttr; },
        });
      }
      return el;
    });

    await window.__downloadAsset('http://localhost/api/solutions/s/assets/inventory.xlsx');
    expect(downloadAttr).toBe('inventory.xlsx');
  });

  it('should strip query params from filename', async () => {
    const mockBlob = new Blob(['data']);
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      blob: () => Promise.resolve(mockBlob),
    });
    URL.createObjectURL = vi.fn().mockReturnValue('blob:x');
    URL.revokeObjectURL = vi.fn();

    // Track the anchor element that gets appended
    let capturedAnchor = null;
    const origAppend = document.body.appendChild.bind(document.body);
    vi.spyOn(document.body, 'appendChild').mockImplementation((el) => {
      if (el.tagName === 'A') {
        capturedAnchor = el;
        el.click = vi.fn();
      }
      return origAppend(el);
    });

    await window.__downloadAsset('http://localhost/file.pdf?v=123');
    expect(capturedAnchor).not.toBeNull();
    expect(capturedAnchor.download).toBe('file.pdf');
  });

  it('should fallback to window.open on fetch error', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('Network error'));
    window.open = vi.fn();

    await window.__downloadAsset('http://localhost/file.xlsx');

    expect(window.open).toHaveBeenCalledWith('http://localhost/file.xlsx', '_blank');
  });

  it('should fallback to window.open on non-ok response', async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: false, status: 404 });
    window.open = vi.fn();

    await window.__downloadAsset('http://localhost/file.xlsx');

    expect(window.open).toHaveBeenCalledWith('http://localhost/file.xlsx', '_blank');
  });
});

describe('escapeHtml', () => {
  it('should escape HTML entities', () => {
    expect(escapeHtml('<script>alert("xss")</script>')).toBe(
      '&lt;script&gt;alert("xss")&lt;/script&gt;'
    );
  });

  it('should return empty string for falsy input', () => {
    expect(escapeHtml(null)).toBe('');
    expect(escapeHtml('')).toBe('');
  });
});
