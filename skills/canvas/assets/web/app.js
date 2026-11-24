const canvas = document.getElementById('pad');
const ctx = canvas.getContext('2d', { willReadFrequently: true });
const toolbar = document.querySelector('[role="toolbar"]');
const status = document.getElementById('status');
const customColor = document.getElementById('custom-color');
const MARGIN = 20;

const state = { tool: 'pen', color: '#1d1d1f', size: 5 };

fetch('/prompt').then(r => r.json()).then(p => { document.getElementById('prompt').textContent = p; });

// ---------- Canvas sizing ----------

function paintWhite() {
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
}

// Grow the canvas to cover the window, keeping what's drawn. Never shrink, so a smaller window can't cut the drawing.
function fit() {
  const w = Math.max(canvas.width, innerWidth), h = Math.max(canvas.height, innerHeight);
  if (w === canvas.width && h === canvas.height) return;
  const old = ctx.getImageData(0, 0, canvas.width, canvas.height);
  canvas.width = w; canvas.height = h;  // resizing clears the canvas
  paintWhite();
  ctx.putImageData(old, 0, 0);
}
paintWhite();
fit();
addEventListener('resize', fit);

// ---------- Drawing ----------

let drawing = false;
const history = [];
const snapshot = () => { history.push(ctx.getImageData(0, 0, canvas.width, canvas.height)); if (history.length > 50) history.shift(); };

canvas.addEventListener('pointerdown', (e) => {
  snapshot();
  drawing = true;
  canvas.setPointerCapture(e.pointerId);
  ctx.beginPath();
  ctx.moveTo(e.offsetX, e.offsetY);
});
const eraserWidth = () => state.size * 4;

// Eraser preview: a circle the size of the area the eraser removes, following the pointer.
const eraserCursor = document.getElementById('eraser-cursor');
function moveEraserCursor(e) {
  // Touch has no hover, so only show the circle while the finger is down.
  const show = state.tool === 'eraser' && (e.pointerType !== 'touch' || drawing);
  eraserCursor.hidden = !show;
  if (!show) return;
  const d = eraserWidth();
  eraserCursor.style.width = eraserCursor.style.height = `${d}px`;
  eraserCursor.style.translate = `${e.clientX - d / 2}px ${e.clientY - d / 2}px`;
}
canvas.addEventListener('pointermove', moveEraserCursor);
canvas.addEventListener('pointerdown', moveEraserCursor);
canvas.addEventListener('pointerleave', () => { eraserCursor.hidden = true; });

canvas.addEventListener('pointermove', (e) => {
  if (!drawing) return;
  const erasing = state.tool === 'eraser';
  ctx.strokeStyle = erasing ? '#ffffff' : state.color;
  ctx.lineWidth = erasing ? eraserWidth() : state.size;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.lineTo(e.offsetX, e.offsetY);
  ctx.stroke();
});
const stop = (e) => {
  drawing = false;
  if (e.pointerType === 'touch') eraserCursor.hidden = true;
};
canvas.addEventListener('pointerup', stop);
canvas.addEventListener('pointercancel', stop);

// Fill first: a snapshot taken before a resize is smaller than the canvas.
function undo() {
  if (!history.length) return;
  paintWhite();
  ctx.putImageData(history.pop(), 0, 0);
}
document.getElementById('undo').addEventListener('click', undo);
addEventListener('keydown', (e) => {
  if ((e.metaKey || e.ctrlKey) && !e.shiftKey && e.key.toLowerCase() === 'z') { e.preventDefault(); undo(); }
});
document.getElementById('clear').addEventListener('click', () => { snapshot(); paintWhite(); });

// ---------- Toolbar state ----------

// Each group is mutually exclusive: exactly one button keeps aria-pressed="true".
function press(selector, button) {
  toolbar.querySelectorAll(selector).forEach(b => b.setAttribute('aria-pressed', b === button));
}

function setTool(button) {
  state.tool = button.dataset.tool;
  canvas.dataset.tool = state.tool;  // CSS hides the system cursor while the eraser circle is in use
  press('.tool', button);
  if (state.tool !== 'eraser') eraserCursor.hidden = true;
}
toolbar.querySelectorAll('.tool').forEach(b => b.addEventListener('click', () => setTool(b)));

const penButton = toolbar.querySelector('[data-tool="pen"]');
function useColor(color) {
  state.color = color;
  setTool(penButton);  // picking a color means you want to draw with it
}

toolbar.querySelectorAll('.swatch').forEach(b => b.addEventListener('click', () => {
  useColor(b.dataset.color);
  press('.swatch', b);
  customColor.classList.remove('active');
}));

// Clicking the well re-selects its current color; picking a new one updates it live.
const useCustom = () => {
  useColor(customColor.value);
  press('.swatch', null);
  customColor.classList.add('active');
};
customColor.addEventListener('click', useCustom);
customColor.addEventListener('input', useCustom);

toolbar.querySelectorAll('.size').forEach(b => b.addEventListener('click', () => {
  state.size = Number(b.dataset.size);
  press('.size', b);
}));

// ---------- Toolbar keyboard: one tab stop, arrow keys inside ----------

// Native focusgroup handles this where supported; otherwise a roving tabindex does the same job.
if (!('focusGroup' in HTMLElement.prototype)) {
  const items = [...toolbar.querySelectorAll('button, input')];
  items.forEach((b, i) => (b.tabIndex = i ? -1 : 0));
  toolbar.addEventListener('focusin', ({ target }) => {
    if (items.includes(target)) items.forEach(b => (b.tabIndex = b === target ? 0 : -1));
  });
  toolbar.addEventListener('keydown', (e) => {
    const rtl = getComputedStyle(toolbar).direction === 'rtl';
    const step = { ArrowRight: rtl ? -1 : 1, ArrowLeft: rtl ? 1 : -1 }[e.key];
    const i = items.indexOf(document.activeElement);
    let next;
    if (step) next = items[(i + step + items.length) % items.length];
    else if (e.key === 'Home') next = items[0];
    else if (e.key === 'End') next = items.at(-1);
    if (!next) return;
    e.preventDefault();
    next.focus();
  });
}

// ---------- Tooltips ----------

// Upgrade title tooltips to hint popovers only where interest invokers and anchor positioning both work.
if ('interestForElement' in HTMLButtonElement.prototype && CSS.supports('position-area', 'block-end')) {
  toolbar.querySelectorAll('button[title]').forEach((b, i) => {
    const tip = Object.assign(document.createElement('div'), { id: `tip-${i}`, textContent: b.title });
    tip.setAttribute('popover', 'hint');
    b.setAttribute('interestfor', tip.id);
    b.removeAttribute('title');  // avoid a second, native tooltip
    document.body.append(tip);
  });
}

// ---------- Export ----------

// Crop to the bounding box of everything that isn't white, plus MARGIN on every side.
// Scans pixels rather than tracking strokes, so eraser, undo and clear are all accounted for.
function cropped() {
  const w = canvas.width, h = canvas.height;
  const px = new Uint32Array(ctx.getImageData(0, 0, w, h).data.buffer);
  let x0 = w, y0 = h, x1 = -1, y1 = -1;
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      if (px[y * w + x] !== 0xffffffff) {  // canvas is opaque, so white is the only all-255 pixel
        if (x < x0) x0 = x;
        if (x > x1) x1 = x;
        if (y < y0) y0 = y;
        if (y > y1) y1 = y;
      }
    }
  }
  if (x1 < 0) return canvas;  // nothing drawn: send the blank canvas as is
  const cw = x1 - x0 + 1, ch = y1 - y0 + 1;
  const out = document.createElement('canvas');
  out.width = cw + 2 * MARGIN;
  out.height = ch + 2 * MARGIN;
  const o = out.getContext('2d');
  o.fillStyle = '#ffffff';
  o.fillRect(0, 0, out.width, out.height);
  o.drawImage(canvas, x0, y0, cw, ch, MARGIN, MARGIN, cw, ch);
  return out;
}

// ---------- Finish ----------

function finish(kind, icon, title) {
  document.body.classList.add('finished');
  status.className = `status ${kind}`;
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  const use = document.createElementNS('http://www.w3.org/2000/svg', 'use');
  svg.setAttribute('aria-hidden', 'true');
  use.setAttribute('href', `icons.svg#${icon}`);
  svg.append(use);
  status.replaceChildren(
    svg,
    Object.assign(document.createElement('strong'), { textContent: title }),
    Object.assign(document.createElement('span'), { textContent: 'You can close this tab.' }),
  );
  window.close();
}

async function post(path, body) {
  try {
    const r = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body });
    return r.ok;
  } catch {
    return false;
  }
}

document.getElementById('done').addEventListener('click', async () => {
  const image = cropped().toDataURL('image/png');
  if (await post('/save', JSON.stringify({ image }))) finish('sent', 'check', 'Sent to agent');
  else status.textContent = "Couldn't send the drawing. Is the agent still waiting?";
});

document.getElementById('cancel').addEventListener('click', async () => {
  await post('/cancel', '{}');
  finish('cancelled', 'xmark', 'Cancelled');
});
