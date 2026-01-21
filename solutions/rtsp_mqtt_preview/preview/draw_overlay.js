// Custom Overlay Renderer for RTSP+MQTT Preview
// This script is executed for each MQTT message to draw overlays on the canvas
//
// Parameters:
// - ctx: CanvasRenderingContext2D
// - data: Parsed MQTT message payload
// - canvas: HTMLCanvasElement
// - video: HTMLVideoElement

// Calculate scale factors
const scaleX = canvas.width / (data.frame_width || 640);
const scaleY = canvas.height / (data.frame_height || 480);

// Style configuration
const boxColor = '#8CC63F';
const boxLineWidth = 2;
const labelFont = '14px Inter, sans-serif';
const labelColor = '#ffffff';

// Draw bounding boxes for detections
const detections = data.detections || data.boxes || [];

for (const det of detections) {
  // Parse bounding box
  let x, y, w, h;
  if (det.bbox) {
    [x, y, w, h] = det.bbox;
  } else if (det.x !== undefined) {
    x = det.x;
    y = det.y;
    w = det.width || det.w;
    h = det.height || det.h;
  }

  if (x === undefined) continue;

  // Scale to canvas
  const sx = x * scaleX;
  const sy = y * scaleY;
  const sw = w * scaleX;
  const sh = h * scaleY;

  // Draw box with semi-transparent fill
  ctx.fillStyle = boxColor;
  ctx.globalAlpha = 0.1;
  ctx.fillRect(sx, sy, sw, sh);
  ctx.globalAlpha = 1;

  // Draw border
  ctx.strokeStyle = boxColor;
  ctx.lineWidth = boxLineWidth;
  ctx.strokeRect(sx, sy, sw, sh);

  // Draw label
  const className = det.class || det.label || 'Object';
  const confidence = det.confidence || det.score;
  const label = confidence !== undefined
    ? `${className} ${Math.round(confidence * 100)}%`
    : className;

  ctx.font = labelFont;
  const metrics = ctx.measureText(label);
  const padding = 4;

  // Label background
  ctx.fillStyle = boxColor;
  ctx.fillRect(
    sx - padding,
    sy - metrics.actualBoundingBoxAscent - padding * 2,
    metrics.width + padding * 2,
    metrics.actualBoundingBoxAscent + metrics.actualBoundingBoxDescent + padding * 2
  );

  // Label text
  ctx.fillStyle = labelColor;
  ctx.fillText(label, sx, sy - padding);
}

// Draw frame info
if (data.frame_id !== undefined || data.timestamp !== undefined) {
  ctx.font = '12px monospace';
  ctx.fillStyle = 'rgba(255, 255, 255, 0.6)';
  const info = [];
  if (data.frame_id !== undefined) info.push(`Frame: ${data.frame_id}`);
  if (data.timestamp !== undefined) info.push(`Time: ${new Date(data.timestamp).toLocaleTimeString()}`);
  ctx.fillText(info.join(' | '), 10, canvas.height - 10);
}
