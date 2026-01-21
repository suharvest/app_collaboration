/**
 * YOLO26 Heatmap Overlay Renderer
 *
 * Renders people flow heatmap and tracking visualization on canvas.
 * Depends on: simpleheat (https://github.com/mourner/simpleheat)
 *
 * Input (data): YOLO26 MQTT tracking message
 * {
 *   timestamp: 1768969602957,
 *   frame_id: 107,
 *   inference_time_ms: 308.0,
 *   zone_occupancy: { total: 1, browsing: 0, engaged: 1, assistance: 0 },
 *   persons: [{
 *     track_id: 1,
 *     confidence: 0.363,
 *     bbox: { x: 0.5, y: 0.4, w: 0.2, h: 0.5 },  // normalized center coords
 *     speed_px_s: 0.2,
 *     speed_normalized: 0.2,
 *     state: "engaged",  // transient | dwelling | engaged | assistance
 *     dwell_duration_sec: 8.9
 *   }]
 * }
 *
 * Variables: ctx, data, canvas, video (provided by PreviewWindow)
 */

// ========== Configuration ==========
const CONFIG = {
  // Heatmap settings
  pointRadius: 35,
  blurRadius: 25,
  maxHeatValue: 100,
  decayRate: 0.985,

  // Weight by state
  stateWeights: {
    transient: 0.5,
    dwelling: 1.5,
    browsing: 1.5,
    engaged: 3.0,
    assistance: 5.0,
  },

  // Heatmap gradient (blue -> cyan -> lime -> yellow -> red)
  gradient: {
    0.0: 'rgba(0, 0, 255, 0)',
    0.2: 'blue',
    0.4: 'cyan',
    0.6: 'lime',
    0.8: 'yellow',
    1.0: 'red'
  },

  // State colors for bounding boxes
  stateColors: {
    transient: '#9CA3AF',   // Gray
    dwelling: '#3B82F6',    // Blue
    browsing: '#3B82F6',    // Blue
    engaged: '#F59E0B',     // Amber
    assistance: '#EF4444',  // Red
  },

  // UI settings
  boxLineWidth: 2,
  labelFont: 'bold 12px Inter, sans-serif',
  statsFont: '12px Inter, sans-serif',
  statsHeaderFont: 'bold 14px Inter, sans-serif',
};

// ========== State Management ==========
// Persistent state across frames
if (!window._heatmapState) {
  window._heatmapState = {
    heat: null,
    points: new Map(),  // track_id -> { x, y, heat }
    initialized: false,
    lastCanvasSize: { w: 0, h: 0 },
  };
}
const state = window._heatmapState;

// ========== Initialize / Reset Heatmap ==========
function initHeatmap() {
  if (typeof simpleheat === 'undefined') {
    console.warn('simpleheat library not loaded');
    return false;
  }

  state.heat = simpleheat(canvas);
  state.heat.radius(CONFIG.pointRadius, CONFIG.blurRadius);
  state.heat.gradient(CONFIG.gradient);
  state.heat.max(CONFIG.maxHeatValue);
  state.initialized = true;
  state.lastCanvasSize = { w: canvas.width, h: canvas.height };
  return true;
}

// Reinitialize if canvas size changed
if (state.initialized &&
    (state.lastCanvasSize.w !== canvas.width || state.lastCanvasSize.h !== canvas.height)) {
  state.initialized = false;
  state.points.clear();
}

// Initialize on first run
if (!state.initialized) {
  if (!initHeatmap()) {
    // Fallback: just draw boxes without heatmap
    ctx.fillStyle = 'rgba(255, 0, 0, 0.5)';
    ctx.font = '16px sans-serif';
    ctx.fillText('Loading heatmap...', 10, 30);
  }
}

// ========== Parse Data ==========
const persons = data?.persons || [];
const zoneOccupancy = data?.zone_occupancy || { total: 0, browsing: 0, engaged: 0, assistance: 0 };
const inferenceTime = data?.inference_time_ms || 0;

// ========== Update Heatmap Points ==========
// Decay existing points
state.points.forEach((point, trackId) => {
  point.heat *= CONFIG.decayRate;
  if (point.heat < 0.5) {
    state.points.delete(trackId);
  }
});

// Update/add current frame persons
for (const person of persons) {
  const { bbox, track_id, state: personState, dwell_duration_sec = 0 } = person;
  if (!bbox) continue;

  // Convert normalized center coordinates to canvas pixels
  const x = bbox.x * canvas.width;
  const y = bbox.y * canvas.height;

  // Calculate heat increment based on state and dwell time
  const baseWeight = CONFIG.stateWeights[personState] || 1.0;
  const dwellBonus = Math.min(dwell_duration_sec / 10, 2.0);  // Bonus up to 2x for dwell
  const heatIncrement = baseWeight * (1 + dwellBonus);

  // Update or create point
  const existing = state.points.get(track_id);
  if (existing) {
    // Smooth position update
    existing.x = existing.x * 0.7 + x * 0.3;
    existing.y = existing.y * 0.7 + y * 0.3;
    existing.heat = Math.min(existing.heat + heatIncrement, CONFIG.maxHeatValue);
    existing.state = personState;
    existing.dwell = dwell_duration_sec;
  } else {
    state.points.set(track_id, {
      x, y,
      heat: heatIncrement * 2,  // Initial boost
      state: personState,
      dwell: dwell_duration_sec,
    });
  }
}

// ========== Render Heatmap ==========
ctx.clearRect(0, 0, canvas.width, canvas.height);

if (state.heat && state.points.size > 0) {
  // Convert Map to simpleheat data format: [[x, y, value], ...]
  const heatData = Array.from(state.points.values())
    .map(p => [p.x, p.y, p.heat]);

  state.heat.data(heatData);
  state.heat.draw(0.05);  // minOpacity
}

// ========== Render Person Bounding Boxes ==========
for (const person of persons) {
  const { bbox, track_id, state: personState, dwell_duration_sec = 0, confidence = 0 } = person;
  if (!bbox) continue;

  const color = CONFIG.stateColors[personState] || '#FFFFFF';

  // Calculate box coordinates (bbox is center-based)
  const bx = (bbox.x - bbox.w / 2) * canvas.width;
  const by = (bbox.y - bbox.h / 2) * canvas.height;
  const bw = bbox.w * canvas.width;
  const bh = bbox.h * canvas.height;

  // Draw bounding box
  ctx.strokeStyle = color;
  ctx.lineWidth = CONFIG.boxLineWidth;
  ctx.strokeRect(bx, by, bw, bh);

  // Draw semi-transparent fill
  ctx.fillStyle = color;
  ctx.globalAlpha = 0.1;
  ctx.fillRect(bx, by, bw, bh);
  ctx.globalAlpha = 1.0;

  // Draw label background
  const labelText = dwell_duration_sec > 1
    ? `#${track_id} ${dwell_duration_sec.toFixed(1)}s`
    : `#${track_id}`;

  ctx.font = CONFIG.labelFont;
  const textWidth = ctx.measureText(labelText).width;

  ctx.fillStyle = color;
  ctx.fillRect(bx, by - 20, textWidth + 8, 18);

  // Draw label text
  ctx.fillStyle = '#FFFFFF';
  ctx.fillText(labelText, bx + 4, by - 6);
}

// ========== Render Stats Panel ==========
const panelWidth = 180;
const panelHeight = 130;
const panelX = 10;
const panelY = 10;

// Panel background
ctx.fillStyle = 'rgba(0, 0, 0, 0.75)';
ctx.beginPath();
ctx.roundRect(panelX, panelY, panelWidth, panelHeight, 8);
ctx.fill();

// Panel border
ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)';
ctx.lineWidth = 1;
ctx.stroke();

// Title
ctx.fillStyle = '#FFFFFF';
ctx.font = CONFIG.statsHeaderFont;
ctx.fillText('People Flow Stats', panelX + 12, panelY + 24);

// Stats
ctx.font = CONFIG.statsFont;
let statY = panelY + 48;

// Total count
ctx.fillStyle = '#FFFFFF';
ctx.fillText(`Total: ${zoneOccupancy.total || 0}`, panelX + 12, statY);
statY += 20;

// Browsing
ctx.fillStyle = CONFIG.stateColors.browsing;
ctx.fillText(`Browsing: ${zoneOccupancy.browsing || 0}`, panelX + 12, statY);
statY += 20;

// Engaged
ctx.fillStyle = CONFIG.stateColors.engaged;
ctx.fillText(`Engaged: ${zoneOccupancy.engaged || 0}`, panelX + 12, statY);
statY += 20;

// Assistance
ctx.fillStyle = CONFIG.stateColors.assistance;
ctx.fillText(`Need Help: ${zoneOccupancy.assistance || 0}`, panelX + 12, statY);

// Inference time (bottom right of panel)
if (inferenceTime > 0) {
  ctx.fillStyle = '#9CA3AF';
  ctx.font = '10px Inter, sans-serif';
  ctx.fillText(`${inferenceTime.toFixed(0)}ms`, panelX + panelWidth - 40, panelY + panelHeight - 8);
}

// ========== Legend (Bottom Right) ==========
const legendX = canvas.width - 140;
const legendY = canvas.height - 90;
const legendItems = [
  { label: 'Moving', color: CONFIG.stateColors.transient },
  { label: 'Browsing', color: CONFIG.stateColors.browsing },
  { label: 'Engaged', color: CONFIG.stateColors.engaged },
  { label: 'Need Help', color: CONFIG.stateColors.assistance },
];

// Legend background
ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
ctx.beginPath();
ctx.roundRect(legendX - 8, legendY - 8, 138, legendItems.length * 18 + 16, 6);
ctx.fill();

ctx.font = '11px Inter, sans-serif';
legendItems.forEach((item, i) => {
  const y = legendY + i * 18 + 6;

  // Color box
  ctx.fillStyle = item.color;
  ctx.fillRect(legendX, y - 8, 12, 12);

  // Label
  ctx.fillStyle = '#FFFFFF';
  ctx.fillText(item.label, legendX + 20, y);
});
