/**
 * Overlay Renderers - Built-in renderers for common inference result formats
 *
 * Each renderer is a function that draws on a canvas:
 * renderer(ctx, data, canvas, video)
 *
 * Renderers handle:
 * - Scaling between frame coordinates and canvas coordinates
 * - Drawing bounding boxes, labels, keypoints, etc.
 * - Customizable styles (colors, fonts, line widths)
 */

// ============================================
// Style Configuration
// ============================================

const DEFAULT_STYLES = {
  // Bounding box styles
  boxColor: '#8CC63F',
  boxLineWidth: 2,
  boxFillAlpha: 0.1,

  // Label styles
  labelFont: '14px Inter, sans-serif',
  labelColor: '#ffffff',
  labelBgColor: '#8CC63F',
  labelPadding: 4,

  // Keypoint styles
  keypointColor: '#8CC63F',
  keypointRadius: 4,
  skeletonColor: '#8CC63F',
  skeletonLineWidth: 2,

  // Mask styles
  maskAlpha: 0.4,

  // Colors for multiple classes
  classColors: [
    '#8CC63F', // Primary green
    '#FF6B6B', // Red
    '#4ECDC4', // Teal
    '#FFE66D', // Yellow
    '#95E1D3', // Mint
    '#F38181', // Coral
    '#AA96DA', // Purple
    '#FCBAD3', // Pink
    '#A8D8EA', // Light blue
    '#FF9F43', // Orange
  ],
};

// ============================================
// Utility Functions
// ============================================

/**
 * Get scale factors for converting frame coordinates to canvas coordinates
 */
function getScaleFactors(data, canvas) {
  const frameWidth = data.frame_width || data.width || 640;
  const frameHeight = data.frame_height || data.height || 480;
  return {
    scaleX: canvas.width / frameWidth,
    scaleY: canvas.height / frameHeight,
  };
}

/**
 * Get color for a class index
 */
function getClassColor(classIndex, styles = DEFAULT_STYLES) {
  return styles.classColors[classIndex % styles.classColors.length];
}

/**
 * Draw a label with background
 */
function drawLabel(ctx, text, x, y, styles = DEFAULT_STYLES) {
  ctx.font = styles.labelFont;
  const metrics = ctx.measureText(text);
  const padding = styles.labelPadding;

  // Draw background
  ctx.fillStyle = styles.labelBgColor;
  ctx.fillRect(
    x - padding,
    y - metrics.actualBoundingBoxAscent - padding,
    metrics.width + padding * 2,
    metrics.actualBoundingBoxAscent + metrics.actualBoundingBoxDescent + padding * 2
  );

  // Draw text
  ctx.fillStyle = styles.labelColor;
  ctx.fillText(text, x, y);
}

// ============================================
// Bounding Box Renderer
// ============================================

/**
 * Render bounding box detections
 *
 * Expected data format:
 * {
 *   detections: [
 *     {
 *       bbox: [x, y, width, height] or [x1, y1, x2, y2],
 *       class: "person",
 *       class_id: 0,
 *       confidence: 0.95
 *     }
 *   ],
 *   frame_width: 640,
 *   frame_height: 480
 * }
 */
export function bboxRenderer(ctx, data, canvas, video, customStyles = {}) {
  const styles = { ...DEFAULT_STYLES, ...customStyles };
  const { scaleX, scaleY } = getScaleFactors(data, canvas);

  const detections = data.detections || data.boxes || data.results || [];

  detections.forEach((det, index) => {
    // Parse bounding box (support multiple formats)
    let x, y, w, h;
    if (det.bbox) {
      if (det.bbox.length === 4) {
        [x, y, w, h] = det.bbox;
        // Check if it's [x1, y1, x2, y2] format
        if (w < x || h < y) {
          w = w - x;
          h = h - y;
        }
      }
    } else if (det.x !== undefined) {
      x = det.x;
      y = det.y;
      w = det.width || det.w;
      h = det.height || det.h;
    } else if (det.x1 !== undefined) {
      x = det.x1;
      y = det.y1;
      w = det.x2 - det.x1;
      h = det.y2 - det.y1;
    }

    if (x === undefined) return;

    // Scale to canvas
    const sx = x * scaleX;
    const sy = y * scaleY;
    const sw = w * scaleX;
    const sh = h * scaleY;

    // Get color
    const color = getClassColor(det.class_id || index, styles);

    // Draw filled background
    ctx.fillStyle = color;
    ctx.globalAlpha = styles.boxFillAlpha;
    ctx.fillRect(sx, sy, sw, sh);
    ctx.globalAlpha = 1;

    // Draw border
    ctx.strokeStyle = color;
    ctx.lineWidth = styles.boxLineWidth;
    ctx.strokeRect(sx, sy, sw, sh);

    // Draw label
    const className = det.class || det.label || det.name || `Class ${det.class_id || index}`;
    const confidence = det.confidence || det.score || det.prob;
    const label = confidence !== undefined
      ? `${className} ${Math.round(confidence * 100)}%`
      : className;

    drawLabel(ctx, label, sx, sy - 4, { ...styles, labelBgColor: color });
  });
}

// ============================================
// Keypoint / Pose Renderer
// ============================================

// COCO keypoint skeleton connections
const COCO_SKELETON = [
  [0, 1], [0, 2], [1, 3], [2, 4],     // Head
  [5, 6], [5, 7], [7, 9], [6, 8], [8, 10],  // Arms
  [5, 11], [6, 12], [11, 12],        // Torso
  [11, 13], [13, 15], [12, 14], [14, 16]   // Legs
];

/**
 * Render pose keypoints and skeleton
 *
 * Expected data format:
 * {
 *   poses: [
 *     {
 *       keypoints: [[x, y, confidence], ...],
 *       bbox: [x, y, w, h]  // optional
 *     }
 *   ],
 *   frame_width: 640,
 *   frame_height: 480
 * }
 */
export function poseRenderer(ctx, data, canvas, video, customStyles = {}) {
  const styles = { ...DEFAULT_STYLES, ...customStyles };
  const { scaleX, scaleY } = getScaleFactors(data, canvas);

  const poses = data.poses || data.keypoints || [];
  const skeleton = data.skeleton || COCO_SKELETON;

  poses.forEach((pose, poseIndex) => {
    const keypoints = pose.keypoints || pose;
    const color = getClassColor(poseIndex, styles);

    // Draw skeleton connections
    ctx.strokeStyle = color;
    ctx.lineWidth = styles.skeletonLineWidth;

    skeleton.forEach(([i, j]) => {
      const kp1 = keypoints[i];
      const kp2 = keypoints[j];

      if (!kp1 || !kp2) return;

      const conf1 = kp1[2] !== undefined ? kp1[2] : 1;
      const conf2 = kp2[2] !== undefined ? kp2[2] : 1;

      if (conf1 < 0.5 || conf2 < 0.5) return;

      ctx.beginPath();
      ctx.moveTo(kp1[0] * scaleX, kp1[1] * scaleY);
      ctx.lineTo(kp2[0] * scaleX, kp2[1] * scaleY);
      ctx.stroke();
    });

    // Draw keypoints
    keypoints.forEach((kp) => {
      if (!kp) return;

      const [x, y, conf] = kp;
      if (conf !== undefined && conf < 0.5) return;

      ctx.beginPath();
      ctx.arc(x * scaleX, y * scaleY, styles.keypointRadius, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.fill();
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 1;
      ctx.stroke();
    });

    // Draw bounding box if available
    if (pose.bbox) {
      const [x, y, w, h] = pose.bbox;
      ctx.strokeStyle = color;
      ctx.lineWidth = styles.boxLineWidth;
      ctx.strokeRect(x * scaleX, y * scaleY, w * scaleX, h * scaleY);
    }
  });
}

// ============================================
// Segmentation Mask Renderer
// ============================================

/**
 * Render segmentation masks
 *
 * Expected data format:
 * {
 *   masks: [
 *     {
 *       mask: [[0,0,1,1,...], ...],  // 2D binary or probability mask
 *       class: "person",
 *       class_id: 0,
 *       confidence: 0.95
 *     }
 *   ],
 *   frame_width: 640,
 *   frame_height: 480
 * }
 */
export function segmentationRenderer(ctx, data, canvas, video, customStyles = {}) {
  const styles = { ...DEFAULT_STYLES, ...customStyles };
  const { scaleX, scaleY } = getScaleFactors(data, canvas);

  const masks = data.masks || data.segments || [];

  masks.forEach((maskData, index) => {
    const mask = maskData.mask || maskData;
    const color = getClassColor(maskData.class_id || index, styles);

    // Parse color
    const r = parseInt(color.slice(1, 3), 16);
    const g = parseInt(color.slice(3, 5), 16);
    const b = parseInt(color.slice(5, 7), 16);

    // Create image data for mask
    const imageData = ctx.createImageData(canvas.width, canvas.height);
    const pixels = imageData.data;

    for (let y = 0; y < mask.length; y++) {
      for (let x = 0; x < mask[y].length; x++) {
        const value = mask[y][x];
        if (value > 0.5) {
          const cx = Math.floor(x * scaleX);
          const cy = Math.floor(y * scaleY);
          const idx = (cy * canvas.width + cx) * 4;

          pixels[idx] = r;
          pixels[idx + 1] = g;
          pixels[idx + 2] = b;
          pixels[idx + 3] = Math.floor(styles.maskAlpha * 255);
        }
      }
    }

    ctx.putImageData(imageData, 0, 0);

    // Draw label if class info available
    if (maskData.class) {
      const label = maskData.confidence !== undefined
        ? `${maskData.class} ${Math.round(maskData.confidence * 100)}%`
        : maskData.class;

      drawLabel(ctx, label, 10, 20 + index * 24, { ...styles, labelBgColor: color });
    }
  });
}

// ============================================
// Text/Classification Renderer
// ============================================

/**
 * Render classification results as text overlay
 *
 * Expected data format:
 * {
 *   classifications: [
 *     { class: "cat", confidence: 0.95 },
 *     { class: "dog", confidence: 0.03 }
 *   ]
 * }
 * Or simple:
 * {
 *   class: "cat",
 *   confidence: 0.95
 * }
 */
export function classificationRenderer(ctx, data, canvas, video, customStyles = {}) {
  const styles = { ...DEFAULT_STYLES, ...customStyles };

  let classifications = data.classifications || data.predictions || [];

  // Handle single result format
  if (data.class && classifications.length === 0) {
    classifications = [{ class: data.class, confidence: data.confidence }];
  }

  // Draw results in top-left corner
  let y = 30;
  classifications.slice(0, 5).forEach((result, index) => {
    const color = getClassColor(index, styles);
    const label = result.confidence !== undefined
      ? `${result.class}: ${Math.round(result.confidence * 100)}%`
      : result.class;

    // Draw bar background
    ctx.fillStyle = 'rgba(0, 0, 0, 0.5)';
    ctx.fillRect(10, y - 16, 200, 20);

    // Draw confidence bar
    if (result.confidence !== undefined) {
      ctx.fillStyle = color;
      ctx.fillRect(10, y - 16, 200 * result.confidence, 20);
    }

    // Draw text
    ctx.font = styles.labelFont;
    ctx.fillStyle = '#ffffff';
    ctx.fillText(label, 14, y);

    y += 26;
  });
}

// ============================================
// Heatmap Renderer
// ============================================

/**
 * Render heatmap overlay
 *
 * Expected data format:
 * {
 *   heatmap: [[0.0, 0.1, ...], ...],  // 2D array of values 0-1
 *   frame_width: 640,
 *   frame_height: 480
 * }
 */
export function heatmapRenderer(ctx, data, canvas, video, customStyles = {}) {
  const styles = { ...DEFAULT_STYLES, ...customStyles };

  const heatmap = data.heatmap || data.attention || data.saliency;
  if (!heatmap || !heatmap.length) return;

  const { scaleX, scaleY } = getScaleFactors(data, canvas);

  // Color scale: blue -> green -> yellow -> red
  function valueToColor(value) {
    const v = Math.max(0, Math.min(1, value));
    if (v < 0.25) {
      return [0, Math.floor(v * 4 * 255), 255];
    } else if (v < 0.5) {
      return [0, 255, Math.floor((1 - (v - 0.25) * 4) * 255)];
    } else if (v < 0.75) {
      return [Math.floor((v - 0.5) * 4 * 255), 255, 0];
    } else {
      return [255, Math.floor((1 - (v - 0.75) * 4) * 255), 0];
    }
  }

  const imageData = ctx.createImageData(canvas.width, canvas.height);
  const pixels = imageData.data;

  for (let y = 0; y < heatmap.length; y++) {
    for (let x = 0; x < heatmap[y].length; x++) {
      const value = heatmap[y][x];
      if (value < 0.1) continue; // Skip low values

      const [r, g, b] = valueToColor(value);
      const cx = Math.floor(x * scaleX);
      const cy = Math.floor(y * scaleY);
      const idx = (cy * canvas.width + cx) * 4;

      pixels[idx] = r;
      pixels[idx + 1] = g;
      pixels[idx + 2] = b;
      pixels[idx + 3] = Math.floor(value * styles.maskAlpha * 255);
    }
  }

  ctx.putImageData(imageData, 0, 0);
}

// ============================================
// Auto-detect Renderer
// ============================================

/**
 * Automatically detect and apply appropriate renderer based on data structure
 */
export function autoRenderer(ctx, data, canvas, video, customStyles = {}) {
  // Detect data type and apply appropriate renderer
  if (data.detections || data.boxes || (data.results && data.results[0]?.bbox)) {
    bboxRenderer(ctx, data, canvas, video, customStyles);
  } else if (data.poses || (data.keypoints && Array.isArray(data.keypoints[0]))) {
    poseRenderer(ctx, data, canvas, video, customStyles);
  } else if (data.masks || data.segments) {
    segmentationRenderer(ctx, data, canvas, video, customStyles);
  } else if (data.heatmap || data.attention || data.saliency) {
    heatmapRenderer(ctx, data, canvas, video, customStyles);
  } else if (data.classifications || data.predictions || data.class) {
    classificationRenderer(ctx, data, canvas, video, customStyles);
  }
  // If no known format, do nothing
}

// ============================================
// Exports
// ============================================

export const renderers = {
  bbox: bboxRenderer,
  pose: poseRenderer,
  segmentation: segmentationRenderer,
  classification: classificationRenderer,
  heatmap: heatmapRenderer,
  auto: autoRenderer,
};

export { DEFAULT_STYLES };
