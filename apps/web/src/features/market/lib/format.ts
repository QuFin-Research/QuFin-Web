export function formatPrice(value: number, precision: number) {
  return value.toLocaleString('en-US', {
    minimumFractionDigits: precision,
    maximumFractionDigits: precision
  });
}

export function formatPct(value: number, digits = 1, signed = true) {
  const pct = (value * 100).toFixed(digits);
  return signed && value > 0 ? `+${pct}%` : `${pct}%`;
}

/** Converts a CSS colour (including oklch and var()) to rgb() for canvas-based charts */
export function resolveCssColor(value: string, fallback = '#888888') {
  if (typeof document === 'undefined') return fallback;
  const probe = document.createElement('span');
  probe.style.color = value;
  probe.style.display = 'none';
  document.body.appendChild(probe);
  const computed = getComputedStyle(probe).color;
  probe.remove();
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = 1;
  const ctx = canvas.getContext('2d');
  if (!ctx || !computed) return fallback;
  ctx.fillStyle = computed;
  ctx.fillRect(0, 0, 1, 1);
  const [r, g, b, a] = ctx.getImageData(0, 0, 1, 1).data;
  return a === 0 ? fallback : `rgb(${r}, ${g}, ${b})`;
}
