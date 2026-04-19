// frontend/js/dashboard.js
/**
 * Dashboard — manages the right-hand telemetry sidebar.
 *
 * Creates one card per space object on init(), then updates
 * values in-place every frame (no DOM teardown/rebuild).
 */

class Dashboard {
  constructor(containerEl) {
    this.container = containerEl;
    this.cards     = {};    // id → { dom refs }
    this._initialized = false;
  }

  // ── Build cards (called once, on first data frame) ──────────────

  init(objects) {
    if (this._initialized) return;
    this._initialized = true;
    this.container.innerHTML = '';

    objects.forEach(obj => {
      const card = this._buildCard(obj);
      this.container.appendChild(card.root);
      this.cards[obj.id] = card;
    });

    // Update sidebar footer object count
    const sfCount = document.getElementById('sf-obj-count');
    if (sfCount) sfCount.textContent = objects.length;
  }

  _buildCard(obj) {
    // Determine accent color for the card ID label
    const accent = this._cssToVar(obj.color);

    const root = document.createElement('div');
    root.className = 'telem-card';

    root.innerHTML = `
      <div class="card-header">
        <span class="card-id" style="color:${accent}">${obj.id}</span>
        <span class="card-orbit-badge" id="orb-${obj.id}">ORBIT 0</span>
      </div>
      <div class="card-body">

        <div class="data-row">
          <div class="data-label">ALTITUDE</div>
          <div class="data-value highlight" id="alt-${obj.id}">—</div>
        </div>

        <div class="data-row">
          <div class="data-label">SPEED</div>
          <div class="data-value" id="spd-${obj.id}">—</div>
        </div>

        <div class="data-row">
          <div class="data-label">INCLINATION</div>
          <div class="data-value" id="inc-${obj.id}">—</div>
        </div>

        <div class="data-row">
          <div class="data-label">PERIOD</div>
          <div class="data-value" id="per-${obj.id}">—</div>
        </div>

        <div class="data-row">
          <div class="data-label">PERIAPSIS</div>
          <div class="data-value" id="peri-${obj.id}">—</div>
        </div>

        <div class="data-row">
          <div class="data-label">APOAPSIS</div>
          <div class="data-value" id="apo-${obj.id}">—</div>
        </div>

        <div class="data-row full">
          <div class="data-label">ECCENTRICITY</div>
          <div class="data-value" id="ecc-${obj.id}">—</div>
          <div class="progress-wrap">
            <div class="progress-bar" id="ecc-bar-${obj.id}" style="width:0%"></div>
          </div>
        </div>

      </div>
    `;

    return { root, id: obj.id };
  }

  _cssToVar(colorName) {
    const map = {
      cyan:    'var(--clr-cyan)',
      lime:    'var(--clr-ok)',
      orange:  'var(--clr-warn)',
      red:     'var(--clr-danger)',
      magenta: '#ea00ff',
      yellow:  '#ffea00',
      white:   '#ffffff',
    };
    return map[colorName] ?? 'var(--clr-cyan)';
  }

  // ── Per-frame update ─────────────────────────────────────────────

  update(state) {
    state.objects.forEach(obj => {
      const t = obj.telemetry;
      if (!t) return;

      this._set(`alt-${obj.id}`,   `${t.altitude_km.toFixed(1)} km`);
      this._set(`spd-${obj.id}`,   `${t.speed_ms.toFixed(0)} m/s`);
      this._set(`inc-${obj.id}`,   `${t.inclination_deg.toFixed(2)}°`);
      this._set(`per-${obj.id}`,   `${t.period_min.toFixed(2)} min`);
      this._set(`peri-${obj.id}`,  `${t.periapsis_km.toFixed(1)} km`);
      this._set(`apo-${obj.id}`,   `${t.apoapsis_km.toFixed(1)} km`);
      this._set(`ecc-${obj.id}`,   t.eccentricity.toFixed(6));
      this._set(`orb-${obj.id}`,   `ORBIT ${t.orbit_count}`);

      // Eccentricity bar: 0–0.05 mapped to 0–100%
      const eccPct = Math.min((t.eccentricity / 0.05) * 100, 100).toFixed(1);
      const bar    = document.getElementById(`ecc-bar-${obj.id}`);
      if (bar) bar.style.width = eccPct + '%';

      // Collision highlight
      const card = this.cards[obj.id];
      if (card) {
        card.root.classList.toggle('collision', obj.color === 'red');
      }
    });

    // Header stats
    this._set('frame-count', state.frame.toLocaleString());
    this._set('alert-total', state.alert_count.toString());

    // Elapsed time
    const h = Math.floor(state.elapsed_s / 3600);
    const m = Math.floor((state.elapsed_s % 3600) / 60);
    const s = state.elapsed_s % 60;
    this._set('elapsed-time',
      `${String(h).padStart(2,'0')}h ${String(m).padStart(2,'0')}m ${String(s).padStart(2,'0')}s`
    );

    // Alert bar
    const bar     = document.getElementById('alert-bar');
    const alertTxt = document.getElementById('alert-text');
    const alertTotal = document.getElementById('alert-total');

    if (state.new_alerts && state.new_alerts.length > 0) {
      const a = state.new_alerts[0];
      bar.classList.add('danger');
      alertTxt.textContent = `PROXIMITY: ${a.ids[0]} ↔ ${a.ids[1]} — ${a.distance.toFixed(2)} km`;
      alertTotal.style.color = 'var(--clr-danger)';
    } else {
      bar.classList.remove('danger');
      if (state.alert_count === 0) {
        alertTxt.textContent = 'ALL SYSTEMS NOMINAL';
        alertTotal.style.color = 'var(--clr-ok)';
      }
    }
  }

  _set(id, text) {
    const el = document.getElementById(id);
    if (el && el.textContent !== text) el.textContent = text;
  }
}