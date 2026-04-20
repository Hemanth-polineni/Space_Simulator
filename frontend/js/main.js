// frontend/js/main.js
/**
 * Application entry point.
 *
 * The original FastAPI backend (WebSocket + /config, /pause, /reset) is
 * not available on the static Netlify deployment, so the simulation is
 * driven entirely in the browser via SimulationEngine (see simulation.js).
 */

let scene, dashboard, engine;
let simTimer    = null;
let isPaused    = false;
let frameCount  = 0;
let lastFpsTime = performance.now();

const SIM_INTERVAL_MS = 50;   // 20 fps — matches the old server cadence

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
    connecting: { cls: '',     text: 'CONNECTING', color: '' },
    live:       { cls: 'live', text: 'LIVE',       color: 'var(--clr-ok)' },
    paused:     { cls: 'live', text: 'PAUSED',     color: 'var(--clr-warn)' },
    dead:       { cls: 'dead', text: 'OFFLINE',    color: 'var(--clr-danger)' },
  };
  const s = styles[state] || styles.connecting;

  dot.className     = 'conn-dot ' + s.cls;
  label.textContent = s.text;
  if (s.color) pill.style.color = s.color;
}

// ── Simulation tick ──────────────────────────────────────────────────
function simTick() {
  if (!engine) return;
  engine.step();
  const state = engine.getState();

  if (dashboard && !dashboard._initialized) {
    dashboard.init(state.objects);
  }

  if (scene)     scene.updateSatellites(state.objects);
  if (dashboard) dashboard.update(state);

  tickFps();
}

// ── Control functions (bound to HTML buttons) ────────────────────────
function appTogglePause() {
  if (!engine) return;
  isPaused = engine.togglePause();

  const btn = document.getElementById('btn-pause');
  if (btn) btn.textContent = isPaused ? '▶ RESUME' : '⏸ PAUSE';

  setConnStatus(isPaused ? 'paused' : 'live');
}

function appReset() {
  if (!engine) return;
  engine.reset();
  isPaused = false;

  const btn = document.getElementById('btn-pause');
  if (btn) btn.textContent = '⏸ PAUSE';

  // Clear existing trails
  if (scene) {
    Object.values(scene.satellites).forEach(sat => {
      sat.trail._buffer = [];
      sat.trail.geometry.setDrawRange(0, 0);
      sat.trail.geometry.attributes.position.needsUpdate = true;
    });
  }

  setConnStatus('live');
}

// ── App initialization ───────────────────────────────────────────────
function init() {
  setConnStatus('connecting');

  engine = new SimulationEngine(10);
  const config = engine.getConfig();

  // Initialize Three.js scene
  const canvasWrap = document.getElementById('canvas-wrap');
  scene = new OrbitalScene(canvasWrap);
  config.objects.forEach(o => scene.addSatellite(o.id, o.color));

  // Initialize telemetry dashboard
  const telemList = document.getElementById('telem-list');
  dashboard = new Dashboard(telemList);

  // Kick off the simulation loop
  setConnStatus('live');
  simTimer = setInterval(simTick, SIM_INTERVAL_MS);
}

// Expose button handlers to the inline onclick attributes in index.html
window.appTogglePause = appTogglePause;
window.appReset       = appReset;

window.addEventListener('DOMContentLoaded', init);
