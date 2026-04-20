// frontend/js/simulation.js
/**
 * Client-side port of the FastAPI orbital simulation engine.
 * Runs entirely in the browser so the static Netlify deployment no longer
 * needs the WebSocket/HTTP backend that used to drive the scene.
 */

// ── Physical constants ────────────────────────────────────────────────
const MU                  = 3.986004418e14;   // m^3 / s^2
const EARTH_RADIUS        = 6_371_000;        // meters
const COLLISION_THRESHOLD = 5_000;            // meters
const LEO_ALTITUDE        = 400_000;          // meters

// ── Minimal 3-vector helpers ──────────────────────────────────────────
function vAdd(a, b)          { return [a[0]+b[0], a[1]+b[1], a[2]+b[2]]; }
function vSub(a, b)          { return [a[0]-b[0], a[1]-b[1], a[2]-b[2]]; }
function vScale(a, s)        { return [a[0]*s, a[1]*s, a[2]*s]; }
function vDot(a, b)          { return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]; }
function vNorm(a)            { return Math.sqrt(a[0]*a[0] + a[1]*a[1] + a[2]*a[2]); }
function vCross(a, b) {
  return [
    a[1]*b[2] - a[2]*b[1],
    a[2]*b[0] - a[0]*b[2],
    a[0]*b[1] - a[1]*b[0],
  ];
}

// ── Gravity ───────────────────────────────────────────────────────────
function gravitationalAcceleration(pos) {
  const r = vNorm(pos);
  // Python raises ValueError; here we just clamp to avoid NaN when
  // numerical error briefly dips below the surface.
  if (r < EARTH_RADIUS) return [0, 0, 0];
  const k = -MU / (r * r * r);
  return vScale(pos, k);
}

// ── RK4 integrator ────────────────────────────────────────────────────
function rk4Step(position, velocity, dt) {
  const deriv = (p, v) => [v, gravitationalAcceleration(p)];

  const [k1v, k1a] = deriv(position, velocity);
  const [k2v, k2a] = deriv(vAdd(position, vScale(k1v, 0.5*dt)), vAdd(velocity, vScale(k1a, 0.5*dt)));
  const [k3v, k3a] = deriv(vAdd(position, vScale(k2v, 0.5*dt)), vAdd(velocity, vScale(k2a, 0.5*dt)));
  const [k4v, k4a] = deriv(vAdd(position, vScale(k3v, dt)),     vAdd(velocity, vScale(k3a, dt)));

  const newPos = vAdd(position, vScale(
    vAdd(vAdd(k1v, vScale(k2v, 2)), vAdd(vScale(k3v, 2), k4v)),
    dt / 6
  ));
  const newVel = vAdd(velocity, vScale(
    vAdd(vAdd(k1a, vScale(k2a, 2)), vAdd(vScale(k3a, 2), k4a)),
    dt / 6
  ));
  return [newPos, newVel];
}

// ── SpaceObject ───────────────────────────────────────────────────────
class SpaceObject {
  constructor(id, mass, radius, position, velocity, color = 'cyan') {
    this.obj_id     = id;
    this.mass       = mass;
    this.radius     = radius;
    this.position   = position.slice();
    this.velocity   = velocity.slice();
    this.color      = color;
    this.base_color = color;
    this.is_active  = true;
  }
  resetColor()     { this.color = this.base_color; }
  markCollision()  { this.color = 'red'; }
}

// ── Orbital telemetry ─────────────────────────────────────────────────
class OrbitalCalculator {
  constructor(id) {
    this.obj_id             = id;
    this._accumulatedAngle  = 0;
    this._prevAngle         = null;
    this.orbit_count        = 0;
  }

  compute(pos, vel) {
    this._updateOrbitCount(pos);
    return {
      altitude_km    : this._altitude(pos),
      speed_ms       : vNorm(vel),
      inclination_deg: this._inclination(pos, vel),
      apoapsis_km    : this._apoapsis(pos, vel),
      periapsis_km   : this._periapsis(pos, vel),
      period_min     : this._period(pos, vel),
      orbit_count    : this.orbit_count,
      eccentricity   : this._eccentricity(pos, vel),
    };
  }

  _altitude(pos) { return (vNorm(pos) - EARTH_RADIUS) / 1000; }

  _inclination(pos, vel) {
    const h    = vCross(pos, vel);
    const hMag = vNorm(h);
    if (hMag < 1e-10) return 0;
    const c = Math.max(-1, Math.min(1, h[2] / hMag));
    return (Math.acos(c) * 180) / Math.PI;
  }

  _specificEnergy(pos, vel) {
    const r = vNorm(pos);
    const v = vNorm(vel);
    return (v * v) / 2 - MU / r;
  }

  _semiMajorAxis(pos, vel) {
    const eps = this._specificEnergy(pos, vel);
    if (Math.abs(eps) < 1e-10) return Infinity;
    return -MU / (2 * eps);
  }

  _eccentricity(pos, vel) {
    const r     = vNorm(pos);
    const v     = vNorm(vel);
    const rDotV = vDot(pos, vel);
    const termA = vScale(pos, (v * v) / MU - 1 / r);
    const termB = vScale(vel, rDotV / MU);
    return vNorm(vSub(termA, termB));
  }

  _apoapsis(pos, vel) {
    const a = this._semiMajorAxis(pos, vel);
    const e = this._eccentricity(pos, vel);
    if (a <= 0 || e >= 1) return Infinity;
    return (a * (1 + e) - EARTH_RADIUS) / 1000;
  }

  _periapsis(pos, vel) {
    const a = this._semiMajorAxis(pos, vel);
    const e = this._eccentricity(pos, vel);
    if (a <= 0) return -Infinity;
    return (a * (1 - e) - EARTH_RADIUS) / 1000;
  }

  _period(pos, vel) {
    const a = this._semiMajorAxis(pos, vel);
    if (a <= 0) return NaN;
    return (2 * Math.PI * Math.sqrt((a * a * a) / MU)) / 60;
  }

  _updateOrbitCount(pos) {
    const current = Math.atan2(pos[1], pos[0]);
    if (this._prevAngle !== null) {
      let delta = current - this._prevAngle;
      if (delta >  Math.PI) delta -= 2 * Math.PI;
      if (delta < -Math.PI) delta += 2 * Math.PI;
      this._accumulatedAngle += delta;
      const full = Math.floor(Math.abs(this._accumulatedAngle) / (2 * Math.PI));
      if (full > this.orbit_count) this.orbit_count = full;
    }
    this._prevAngle = current;
  }
}

// ── Collision detection ───────────────────────────────────────────────
function checkCollisions(objects) {
  const events = [];
  for (let i = 0; i < objects.length; i++) {
    for (let j = i + 1; j < objects.length; j++) {
      const a = objects[i], b = objects[j];
      if (!a.is_active || !b.is_active) continue;
      const dist = vNorm(vSub(a.position, b.position));
      if (dist < COLLISION_THRESHOLD) {
        events.push({ ids: [a.obj_id, b.obj_id], distance: dist });
        a.markCollision();
        b.markCollision();
      }
    }
  }
  return events;
}

// ── Helper orbital math ───────────────────────────────────────────────
function circularVelocity(altitude_m) {
  return Math.sqrt(MU / (EARTH_RADIUS + altitude_m));
}
function inclinationVelocity(speed, incDeg) {
  const a = (incDeg * Math.PI) / 180;
  return [-speed * Math.cos(a), speed * Math.sin(a)];
}

// ── Simulation engine ─────────────────────────────────────────────────
class SimulationEngine {
  constructor(dt = 10) {
    this.dt           = dt;
    this.paused       = false;
    this.frame        = 0;
    this.elapsed_s    = 0;
    this.alert_count  = 0;
    this.recent_alerts = [];
    this.objects     = this._buildDefaultObjects();
    this.calculators = {};
    this.objects.forEach(o => { this.calculators[o.obj_id] = new OrbitalCalculator(o.obj_id); });
  }

  _buildDefaultObjects() {
    const rLeo       = EARTH_RADIUS + LEO_ALTITUDE;
    const vLeo       = circularVelocity(LEO_ALTITUDE);
    const [vyI, vzI] = inclinationVelocity(vLeo, 15);
    const vMeo       = circularVelocity(600_000);

    return [
      new SpaceObject('SAT-1',    500, 2,   [rLeo, 0, 0],                      [0, vLeo, 0],     'cyan'),
      new SpaceObject('SAT-2',    300, 1.5, [-rLeo, 0, 0],                     [0, vyI, vzI],    'lime'),
      new SpaceObject('DEBRIS-1', 10,  0.5, [0, EARTH_RADIUS + 600_000, 0],    [-vMeo, 0, 80],   'orange'),
    ];
  }

  step() {
    if (this.paused) return;
    this.objects.forEach(o => o.resetColor());
    this.objects.forEach(o => {
      if (o.is_active) {
        const [p, v] = rk4Step(o.position, o.velocity, this.dt);
        o.position = p;
        o.velocity = v;
      }
    });
    const events       = checkCollisions(this.objects);
    this.recent_alerts = events;
    this.alert_count  += events.length;
    this.frame        += 1;
    this.elapsed_s    += this.dt;
  }

  getState() {
    const objectsData = this.objects.map(o => {
      const raw   = this.calculators[o.obj_id].compute(o.position, o.velocity);
      const telem = {};
      for (const k in raw) {
        telem[k] = typeof raw[k] === 'number' && !Number.isInteger(raw[k])
          ? Math.round(raw[k] * 1e4) / 1e4
          : raw[k];
      }
      return {
        id        : o.obj_id,
        position  : o.position.slice(),
        velocity  : o.velocity.slice(),
        color     : o.color,
        base_color: o.base_color,
        is_active : o.is_active,
        telemetry : telem,
      };
    });

    return {
      frame      : this.frame,
      elapsed_s  : this.elapsed_s,
      paused     : this.paused,
      alert_count: this.alert_count,
      new_alerts : this.recent_alerts.map(e => ({
        ids     : e.ids.slice(),
        distance: Math.round((e.distance / 1000) * 1e3) / 1e3,
      })),
      objects    : objectsData,
    };
  }

  togglePause() { this.paused = !this.paused; return this.paused; }

  reset() {
    const dt = this.dt;
    this.paused        = false;
    this.frame         = 0;
    this.elapsed_s     = 0;
    this.alert_count   = 0;
    this.recent_alerts = [];
    this.objects       = this._buildDefaultObjects();
    this.calculators   = {};
    this.objects.forEach(o => { this.calculators[o.obj_id] = new OrbitalCalculator(o.obj_id); });
    this.dt = dt;
  }

  getConfig() {
    return {
      objects: this.objects.map(o => ({ id: o.obj_id, color: o.base_color })),
      dt     : this.dt,
    };
  }
}

window.SimulationEngine = SimulationEngine;
