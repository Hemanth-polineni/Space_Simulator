// frontend/js/scene.js
/**
 * OrbitalScene — Three.js 3D renderer
 * Photorealistic Earth with NASA textures, cloud layer,
 * city night lights, bump mapping, and specular ocean sheen.
 *
 * Texture sources (unpkg CDN — NASA Blue Marble derivatives):
 *   earth-day.jpg      → Surface color (Blue Marble)
 *   earth-topology.png → Bump map (elevation data)
 *   earth-water.png    → Specular map (ocean vs land reflectivity)
 *   earth-clouds.png   → Cloud alpha map (animated layer)
 *   earth-night.jpg    → City lights (visible on dark side)
 *
 * Coordinate mapping (physics → Three.js):
 *   physics [x, y, z]  →  Three.js [x, z, y] × SCALE
 *   Physics Z = north pole → Three.js Y = up axis
 *
 * Scale: 1 meter = 1e-6 Three.js units
 *   Earth radius ≈ 6.371 units, LEO ≈ 6.771 units
 */

const SCALE     = 1e-6;
const MAX_TRAIL = 350;
const EARTH_R   = 6.371;

// Base URLs for all Earth textures
const TEX = {
  day      : 'https://unpkg.com/three-globe@2.27.2/example/img/earth-day.jpg',
  bump     : 'https://unpkg.com/three-globe@2.27.2/example/img/earth-topology.png',
  specular : 'https://unpkg.com/three-globe@2.27.2/example/img/earth-water.png',
  clouds   : 'https://unpkg.com/three-globe@2.27.2/example/img/earth-clouds.png',
  night    : 'https://unpkg.com/three-globe@2.27.2/example/img/earth-night.jpg',
};

const COLOR_MAP = {
  cyan    : 0x00e5ff,
  lime    : 0x00e676,
  orange  : 0xff6d00,
  red     : 0xff1744,
  magenta : 0xea00ff,
  yellow  : 0xffea00,
  white   : 0xffffff,
};

function cssColorToHex(name) {
  return COLOR_MAP[name] ?? 0x00e5ff;
}

function physToThree(pos) {
  return new THREE.Vector3(
    pos[0] * SCALE,
    pos[2] * SCALE,
    pos[1] * SCALE
  );
}

// ─────────────────────────────────────────────────────────────────────
// Trail — rolling buffer orbital trail
// ─────────────────────────────────────────────────────────────────────

class Trail {
  constructor(color) {
    this._buffer = [];

    const positions = new Float32Array(MAX_TRAIL * 3);
    this.geometry   = new THREE.BufferGeometry();
    this.geometry.setAttribute(
      'position',
      new THREE.BufferAttribute(positions, 3)
    );
    this.geometry.setDrawRange(0, 0);

    this.material = new THREE.LineBasicMaterial({
      color, opacity: 0.75, transparent: true
    });
    this.line = new THREE.Line(this.geometry, this.material);
  }

  push(x, y, z) {
    this._buffer.push(x, y, z);
    if (this._buffer.length > MAX_TRAIL * 3) {
      this._buffer.splice(0, 3);
    }
    const arr   = this.geometry.attributes.position.array;
    const count = this._buffer.length / 3;
    for (let i = 0; i < this._buffer.length; i++) {
      arr[i] = this._buffer[i];
    }
    this.geometry.setDrawRange(0, count);
    this.geometry.attributes.position.needsUpdate = true;
  }

  setColor(hex) {
    this.material.color.set(hex);
  }
}

// ─────────────────────────────────────────────────────────────────────
// TextureLoadManager — shows a loading overlay while textures fetch
// ─────────────────────────────────────────────────────────────────────

class TextureLoadManager {
  constructor() {
    this.loader  = new THREE.TextureLoader();
    this._total  = 0;
    this._loaded = 0;
    this._overlay = this._buildOverlay();
  }

  _buildOverlay() {
    const el = document.createElement('div');
    el.id = 'tex-loading-overlay';
    Object.assign(el.style, {
      position        : 'absolute',
      inset           : '0',
      display         : 'flex',
      flexDirection   : 'column',
      alignItems      : 'center',
      justifyContent  : 'center',
      gap             : '14px',
      background      : 'rgba(2,6,9,0.92)',
      zIndex          : '20',
      fontFamily      : "'Share Tech Mono', monospace",
      color           : '#5a8090',
      fontSize        : '11px',
      letterSpacing   : '2px',
      pointerEvents   : 'none',
    });

    el.innerHTML = `
      <div class="spinner" style="
        width:28px; height:28px;
        border:2px solid rgba(0,229,255,0.15);
        border-top-color:#00e5ff;
        border-radius:50%;
        animation:spin 1s linear infinite;
      "></div>
      <div id="tex-load-label">LOADING EARTH TEXTURES</div>
      <div id="tex-load-bar-wrap" style="
        width:180px; height:3px;
        background:rgba(0,229,255,0.1);
        border-radius:2px; overflow:hidden;
      ">
        <div id="tex-load-bar" style="
          height:100%; width:0%;
          background:#00e5ff;
          border-radius:2px;
          transition:width 0.3s ease;
        "></div>
      </div>
    `;
    document.getElementById('canvas-wrap').appendChild(el);
    return el;
  }

  load(url) {
    this._total++;
    return new Promise((resolve) => {
      this.loader.load(
        url,
        (tex) => {
          this._loaded++;
          this._updateBar();
          resolve(tex);
        },
        undefined,
        () => {
          // On error, resolve with null — Earth still renders, just missing one map
          console.warn(`Texture failed to load: ${url}`);
          this._loaded++;
          this._updateBar();
          resolve(null);
        }
      );
    });
  }

  _updateBar() {
    const pct = Math.round((this._loaded / this._total) * 100);
    const bar = document.getElementById('tex-load-bar');
    const lbl = document.getElementById('tex-load-label');
    if (bar) bar.style.width = pct + '%';
    if (lbl) lbl.textContent = `LOADING EARTH TEXTURES  ${pct}%`;

    if (this._loaded >= this._total) {
      // Fade out overlay once all textures are loaded
      this._overlay.style.transition = 'opacity 0.8s ease';
      this._overlay.style.opacity    = '0';
      setTimeout(() => this._overlay.remove(), 900);
    }
  }
}

// ─────────────────────────────────────────────────────────────────────
// OrbitalScene — main Three.js scene
// ─────────────────────────────────────────────────────────────────────

class OrbitalScene {
  constructor(container) {
    this.container  = container;
    this.satellites = {};
    this.cloudMesh  = null;
    this.earthMesh  = null;

    this._initRenderer();
    this._initCamera();
    this._initControls();
    this._initLights();
    this._buildStarfield();
    this._buildAtmosphere();

    // Load all textures in parallel, then build Earth
    this._loadEarthTextures();

    this._animate();
  }

  // ── Renderer / Camera / Controls / Lights ───────────────────────

  _initRenderer() {
    this.scene    = new THREE.Scene();
    this.renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha    : true,
    });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.setClearColor(0x020609, 1);
    this.container.appendChild(this.renderer.domElement);
    this._resize();
    window.addEventListener('resize', () => this._resize());
  }

  _resize() {
    const w = this.container.clientWidth;
    const h = this.container.clientHeight;
    this.renderer.setSize(w, h, false);
    if (this.camera) {
      this.camera.aspect = w / h;
      this.camera.updateProjectionMatrix();
    }
  }

  _initCamera() {
    const w = this.container.clientWidth;
    const h = this.container.clientHeight;
    this.camera = new THREE.PerspectiveCamera(45, w / h, 0.01, 1000);
    this.camera.position.set(12, 6, 12);
    this.camera.lookAt(0, 0, 0);
  }

  _initControls() {
    this.controls                 = new THREE.OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping   = true;
    this.controls.dampingFactor   = 0.06;
    this.controls.minDistance     = 7.5;
    this.controls.maxDistance     = 60;
    this.controls.autoRotate      = true;
    this.controls.autoRotateSpeed = 0.15;
  }

  _initLights() {
    // Deep space ambient — very dim, slightly blue-tinted
    this.scene.add(new THREE.AmbientLight(0x0d1f2d, 3.0));

    // Main sun — warm directional light from upper right
    const sun = new THREE.DirectionalLight(0xfff4e0, 3.5);
    sun.position.set(20, 8, 14);
    this.scene.add(sun);

    // Subtle fill from opposite side — prevents pure black on dark side
    const fill = new THREE.DirectionalLight(0x0a0a2a, 0.4);
    fill.position.set(-15, -5, -10);
    this.scene.add(fill);
  }

  // ── Starfield ───────────────────────────────────────────────────

  _buildStarfield() {
    const count  = 4000;
    const pos    = new Float32Array(count * 3);
    const colors = new Float32Array(count * 3);

    // Varied star colors: mostly white/blue, occasional warm yellow
    const starPalette = [
      [0.9, 0.95, 1.0],   // Cool white
      [0.8, 0.88, 1.0],   // Blue-white
      [1.0, 0.98, 0.85],  // Warm yellow-white
      [0.7, 0.82, 1.0],   // Blue
      [1.0, 1.0,  1.0],   // Pure white
    ];

    for (let i = 0; i < count; i++) {
      const theta = Math.random() * Math.PI * 2;
      const phi   = Math.acos(2 * Math.random() - 1);
      const r     = 380 + Math.random() * 80;

      pos[i*3]     = r * Math.sin(phi) * Math.cos(theta);
      pos[i*3 + 1] = r * Math.cos(phi);
      pos[i*3 + 2] = r * Math.sin(phi) * Math.sin(theta);

      const c = starPalette[Math.floor(Math.random() * starPalette.length)];
      const brightness = 0.5 + Math.random() * 0.5;
      colors[i*3]     = c[0] * brightness;
      colors[i*3 + 1] = c[1] * brightness;
      colors[i*3 + 2] = c[2] * brightness;
    }

    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    geo.setAttribute('color',    new THREE.BufferAttribute(colors, 3));

    const mat = new THREE.PointsMaterial({
      size            : 0.18,
      sizeAttenuation : true,
      vertexColors    : true,
    });
    this.scene.add(new THREE.Points(geo, mat));
  }

  // ── Atmosphere glow ─────────────────────────────────────────────

  _buildAtmosphere() {
    // Inner glow — tight blue ring around Earth's limb
    const innerGeo = new THREE.SphereGeometry(EARTH_R * 1.02, 40, 40);
    const innerMat = new THREE.MeshBasicMaterial({
      color       : 0x1a6fb5,
      side        : THREE.BackSide,
      transparent : true,
      opacity     : 0.22,
      blending    : THREE.AdditiveBlending,
      depthWrite  : false,
    });
    this.scene.add(new THREE.Mesh(innerGeo, innerMat));

    // Outer haze — wide soft glow
    const outerGeo = new THREE.SphereGeometry(EARTH_R * 1.09, 40, 40);
    const outerMat = new THREE.MeshBasicMaterial({
      color       : 0x0a3a6a,
      side        : THREE.BackSide,
      transparent : true,
      opacity     : 0.10,
      blending    : THREE.AdditiveBlending,
      depthWrite  : false,
    });
    this.scene.add(new THREE.Mesh(outerGeo, outerMat));
  }

  // ── Earth texture loading & construction ────────────────────────

  async _loadEarthTextures() {
    const mgr = new TextureLoadManager();

    // Kick off all 5 texture downloads in parallel
    const [dayTex, bumpTex, specTex, cloudTex, nightTex] = await Promise.all([
      mgr.load(TEX.day),
      mgr.load(TEX.bump),
      mgr.load(TEX.specular),
      mgr.load(TEX.clouds),
      mgr.load(TEX.night),
    ]);

    this._buildEarth(dayTex, bumpTex, specTex, nightTex);
    this._buildClouds(cloudTex);
    this._buildGridLines();   // Lat/lon grid on top of texture
  }

  _buildEarth(dayTex, bumpTex, specTex, nightTex) {
    const geo = new THREE.SphereGeometry(EARTH_R, 64, 64);

    // ── Primary surface: Blue Marble day texture ──────────────────
    const mat = new THREE.MeshPhongMaterial({
      map         : dayTex,        // Full-color NASA surface
      bumpMap     : bumpTex,       // Elevation data → bumpy mountains
      bumpScale   : 0.035,         // Subtle — real Earth isn't that bumpy at this scale
      specularMap : specTex,       // White = ocean (shiny), black = land (matte)
      specular    : new THREE.Color(0x2266aa),
      shininess   : 28,
    });

    this.earthMesh = new THREE.Mesh(geo, mat);
    this.scene.add(this.earthMesh);

    // ── Night lights: city glow on the dark side ──────────────────
    // A second Earth sphere, slightly larger, additive blending.
    // Additive blend: on the bright (day) side it's washed out by sunlight.
    // On the dark side it becomes visible — city lights glow through.
    if (nightTex) {
      const nightMat = new THREE.MeshBasicMaterial({
        map        : nightTex,
        blending   : THREE.AdditiveBlending,
        transparent: true,
        opacity    : 0.65,
        depthWrite : false,
      });

      const nightMesh = new THREE.Mesh(
        new THREE.SphereGeometry(EARTH_R * 1.001, 64, 64),
        nightMat
      );
      this.scene.add(nightMesh);

      // Store reference so it co-rotates with Earth
      this.nightMesh = nightMesh;
    }
  }

  _buildClouds(cloudTex) {
    if (!cloudTex) return;

    // Cloud layer sits 0.5% above the surface
    const geo = new THREE.SphereGeometry(EARTH_R * 1.005, 48, 48);
    const mat = new THREE.MeshPhongMaterial({
      map         : cloudTex,
      transparent : true,
      opacity     : 0.38,
      depthWrite  : false,
      blending    : THREE.NormalBlending,
    });

    this.cloudMesh = new THREE.Mesh(geo, mat);
    this.scene.add(this.cloudMesh);
  }

  _buildGridLines() {
    // Faint lat/lon grid over the textured Earth
    const geo = new THREE.SphereGeometry(EARTH_R * 1.003, 18, 12);
    const mat = new THREE.MeshBasicMaterial({
      color       : 0x224466,
      wireframe   : true,
      transparent : true,
      opacity     : 0.06,
      depthWrite  : false,
    });
    this.scene.add(new THREE.Mesh(geo, mat));
  }

  // ── Satellite management ────────────────────────────────────────

  addSatellite(id, colorName) {
    const hex = cssColorToHex(colorName);

    // Core dot
    const mesh = new THREE.Mesh(
      new THREE.SphereGeometry(0.07, 12, 12),
      new THREE.MeshBasicMaterial({ color: hex })
    );

    // Glow shell
    const glow = new THREE.Mesh(
      new THREE.SphereGeometry(0.18, 12, 12),
      new THREE.MeshBasicMaterial({
        color       : hex,
        transparent : true,
        opacity     : 0.28,
        depthWrite  : false,
        blending    : THREE.AdditiveBlending,
      })
    );
    mesh.add(glow);

    // Trail
    const trail = new Trail(hex);
    this.scene.add(trail.line);
    this.scene.add(mesh);

    this.satellites[id] = { mesh, glow, trail };
  }

  // ── Per-frame satellite update ───────────────────────────────────

  updateSatellites(objects) {
    objects.forEach(obj => {
      const sat = this.satellites[obj.id];
      if (!sat) return;

      const p = physToThree(obj.position);
      sat.mesh.position.copy(p);
      sat.trail.push(p.x, p.y, p.z);

      const hex = obj.color === 'red'
        ? 0xff1744
        : cssColorToHex(obj.base_color);

      sat.mesh.material.color.set(hex);
      sat.glow.material.color.set(hex);
      sat.trail.setColor(hex);
    });
  }

  // ── Render loop ──────────────────────────────────────────────────

  _animate() {
    requestAnimationFrame(() => this._animate());

    // Earth rotation — 1 full rotation ≈ 24 min sim time at real speed
    // At this rate it looks alive without being distracting
    if (this.earthMesh) {
      this.earthMesh.rotation.y += 0.0004;
    }

    // Night mesh co-rotates with Earth
    if (this.nightMesh) {
      this.nightMesh.rotation.y = this.earthMesh.rotation.y;
    }

    // Clouds rotate slightly faster than the surface (they drift)
    if (this.cloudMesh) {
      this.cloudMesh.rotation.y += 0.00055;
    }

    this.controls.update();
    this.renderer.render(this.scene, this.camera);
  }
}