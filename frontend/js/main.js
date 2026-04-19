// frontend/js/main.js
/**
 * Application entry point.
 *
 * Flow:
 *   1. Fetch /config  → get object list → initialize Scene + Dashboard
 *   2. Open WebSocket → receive state frames → update Scene + Dashboard
 *   3. Reconnect automatically on disconnect
 *   4. Wire pause / reset buttons
 */

const WS_URL  = `ws://${location.host}/ws`;
const API_URL = `http://${location.host}`;

let scene, dashboard, ws;
let isPaused    = false;
let frameCount  = 0;
let lastFpsTime = performance.now();

// ── FPS counter ──────────────────────────────────────────────────────
function tickFps() {
  frameCount++;
  const now  = performance.now();
  const diff = now - lastFpsTime;
  if (diff >= 1000) {
    const fps = (frameCount / diff * 1000).toFixed(0);
    const el  = document.getElementById('fps-display');
    if (el) el.textContent = `${fps} FPS`;
    frameCount  = 0;
    lastFpsTime = now;
  }
}

// ── Connection status helpers ────────────────────────────────────────
function setConnStatus(state) {
  const dot   = document.getElementById('conn-dot');
  const label = document.getElementById('conn-label');
  const pill  = document.getElementById('conn-pill');

  const styles = {
    connecting: { cls: '',     text: 'CONNECTING',  color: '' },
    live:       { cls: 'live', text: 'LIVE',         color: 'var(--clr-ok)' },
    dead:       { cls: 'dead', text: 'OFFLINE',      color: 'var(--clr-danger)' },
  };
  const s = styles[state] || styles.connecting;

  dot.className   = 'conn-dot ' + s.cls;
  label.textContent = s.text;
  if (s.color) pill.style.color = s.color;
}

// ── WebSocket management ─────────────────────────────────────────────
function connectWS() {
  setConnStatus('connecting');
  ws = new WebSocket(WS_URL);

  ws.onopen = () => {
    setConnStatus('live');
    console.log('[WS] Connected');
    // Send periodic ping to keep the connection alive
    ws._pingTimer = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) ws.send('ping');
    }, 20000);
  };

  ws.onmessage = (evt) => {
    const state = JSON.parse(evt.data);

    // Initialize scene objects on first frame
    if (dashboard && !dashboard._initialized) {
      dashboard.init(state.objects);
    }

    // Update 3D scene
    if (scene) scene.updateSatellites(state.objects);

    // Update dashboard
    if (dashboard) dashboard.update(state);

    // FPS
    tickFps();
  };

  ws.onclose = () => {
    setConnStatus('dead');
    clearInterval(ws._pingTimer);
    console.log('[WS] Disconnected — retrying in 2s');
    setTimeout(connectWS, 2000);    // Auto-reconnect
  };

  ws.onerror = (err) => {
    console.error('[WS] Error:', err);
    ws.close();
  };
}

// ── Control functions (bound to HTML buttons) ────────────────────────
async function appTogglePause() {
  const res  = await fetch(`${API_URL}/pause`, { method: 'POST' });
  const data = await res.json();
  isPaused   = data.paused;

  const btn = document.getElementById('btn-pause');
  if (btn) btn.textContent = isPaused ? '▶ RESUME' : '⏸ PAUSE';
}

async function appReset() {
  await fetch(`${API_URL}/reset`, { method: 'POST' });
  // Clear trails by rebuilding scene satellites
  if (scene) {
    const cfg = await fetch(`${API_URL}/config`).then(r => r.json());
    cfg.objects.forEach(o => {
      const sat = scene.satellites[o.id];
      if (sat) sat.trail._buffer = [];
    });
  }
}

// ── App initialization ───────────────────────────────────────────────
async function init() {
  // 1. Fetch config to know the objects before any WS data arrives
  let config;
  try {
    config = await fetch(`${API_URL}/config`).then(r => r.json());
  } catch (e) {
    console.error('Could not reach backend:', e);
    setTimeout(init, 2000);
    return;
  }

  // 2. Initialize Three.js scene
  const canvasWrap = document.getElementById('canvas-wrap');
  scene = new OrbitalScene(canvasWrap);

  // Add one satellite mesh per object (before WS data arrives)
  config.objects.forEach(o => scene.addSatellite(o.id, o.color));

  // 3. Initialize telemetry dashboard
  const telemList = document.getElementById('telem-list');
  dashboard = new Dashboard(telemList);

  // 4. Open WebSocket — state updates drive everything from here
  connectWS();
}

// Kick off once DOM is ready
window.addEventListener('DOMContentLoaded', init);