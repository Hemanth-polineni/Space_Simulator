
/**
 * OrbitalScene — Three.js 3D renderer
 *
 * Coordinate mapping (physics → Three.js):
 *   physics [x, y, z]  →  Three.js [x, z, y] × SCALE
 *   (physics Z = north pole → Three.js Y = up axis)
 *
 * Scale: 1 meter = 1e-6 Three.js units
 *   Earth radius = 6.371 units, LEO altitude ≈ 6.771 units
 */

const SCALE       = 1e-6;
const MAX_TRAIL   = 350;
const EARTH_R     = 6.371;   // Three.js units

// CSS color name → hex (Three.js needs hex)
const COLOR_MAP = {
  cyan:   0x00e5ff,
  lime:   0x00e676,
  orange: 0xff6d00,
  red:    0xff1744,
  magenta:0xea00ff,
  yellow: 0xffea00,
  white:  0xffffff,
};

function cssColorToHex(name) {
  return COLOR_MAP[name] ?? 0x00e5ff;
}

// Convert physics position array to THREE.Vector3
function physToThree(pos) {
  return new THREE.Vector3(
    pos[0] * SCALE,
    pos[2] * SCALE,   // physics Z → Three.js Y (north pole up)
    pos[1] * SCALE    // physics Y → Three.js Z
  );
}

// ─────────────────────────────────────────────────────────────────────
class Trail {
  /**
   * Manages an orbital trail as a rolling buffer of positions.
   * Uses BufferGeometry for efficient per-frame updates.
   */
  constructor(color) {
    this._buffer = [];          // flat [x,y,z, x,y,z, ...]

    const positions = new Float32Array(MAX_TRAIL * 3);
    this.geometry   = new THREE.BufferGeometry();
    this.geometry.setAttribute(
      'position',
      new THREE.BufferAttribute(positions, 3)
    );
    this.geometry.setDrawRange(0, 0);

    this.material = new THREE.LineBasicMaterial({
      color, opacity: 0.7, transparent: true
    });
    this.line = new THREE.Line(this.geometry, this.material);
  }

  push(x, y, z) {
    this._buffer.push(x, y, z);
    // Rolling window — drop oldest 3 floats when full
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

  setColor(hexColor) {
    this.material.color.set(hexColor);
  }
}

// ─────────────────────────────────────────────────────────────────────
class OrbitalScene {
  constructor(container) {
    this.container  = container;
    this.satellites = {};   // id → { mesh, glow, trail }

    this._initRenderer();
    this._initCamera();
    this._initControls();
    this._initLights();
    this._buildStarfield();
    this._buildEarth();
    this._buildGrid();
    this._buildAtmosphere();
    this._animate();
  }

  // ── Setup ───────────────────────────────────────────────────────

  _initRenderer() {
    this.scene    = new THREE.Scene();
    this.renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha:     true
    });
    this.renderer.setPixelRatio(window.devicePixelRatio);
    this.renderer.setClearColor(0x020609, 1);
    this.container.appendChild(this.renderer.domElement);
    this._resize();
    window.addEventListener('resize', () => this._resize());
  }

  _resize() {
    const w = this.container.clientWidth;
    const h = this.container.clientHeight;
    this.renderer.setSize(w, h);
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
    this.controls                = new THREE.OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping  = true;
    this.controls.dampingFactor  = 0.06;
    this.controls.minDistance    = 7.5;
    this.controls.maxDistance    = 60;
    this.controls.autoRotate     = true;
    this.controls.autoRotateSpeed = 0.18;
  }

  _initLights() {
    this.scene.add(new THREE.AmbientLight(0x112233, 1.2));
    const sun = new THREE.DirectionalLight(0xffeedd, 2.0);
    sun.position.set(20, 10, 15);
    this.scene.add(sun);
    // Rim light from behind (deep blue)
    const rim = new THREE.DirectionalLight(0x0044ff, 0.5);
    rim.position.set(-15, -5, -10);
    this.scene.add(rim);
  }

  _buildStarfield() {
    const count   = 3000;
    const geo     = new THREE.BufferGeometry();
    const pos     = new Float32Array(count * 3);
    const radius  = 400;

    for (let i = 0; i < count; i++) {
      // Random point on sphere surface
      const theta  = Math.random() * Math.PI * 2;
      const phi    = Math.acos(2 * Math.random() - 1);
      const r      = radius * (0.8 + Math.random() * 0.2);
      pos[i*3]     = r * Math.sin(phi) * Math.cos(theta);
      pos[i*3 + 1] = r * Math.cos(phi);
      pos[i*3 + 2] = r * Math.sin(phi) * Math.sin(theta);
    }

    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    const mat   = new THREE.PointsMaterial({ color: 0xaaccff, size: 0.15, sizeAttenuation: true });
    this.scene.add(new THREE.Points(geo, mat));
  }

  _buildEarth() {
    const geo = new THREE.SphereGeometry(EARTH_R, 48, 48);

    // Layered Earth look: deep ocean base + specular highlights
    const mat = new THREE.MeshPhongMaterial({
      color:     0x0d3b6e,
      emissive:  0x001020,
      specular:  0x4488cc,
      shininess: 30,
    });
    this.earthMesh = new THREE.Mesh(geo, mat);
    this.scene.add(this.earthMesh);
  }

  _buildGrid() {
    // Latitude/longitude wireframe overlay on Earth
    const geo = new THREE.SphereGeometry(EARTH_R * 1.002, 18, 12);
    const mat = new THREE.MeshBasicMaterial({
      color:       0x1a5a8a,
      wireframe:   true,
      transparent: true,
      opacity:     0.15,
    });
    this.scene.add(new THREE.Mesh(geo, mat));
  }

  _buildAtmosphere() {
    // Slightly larger sphere, additive blend → blue glow around Earth
    const geo = new THREE.SphereGeometry(EARTH_R * 1.04, 32, 32);
    const mat = new THREE.MeshBasicMaterial({
      color:     0x0066cc,
      side:      THREE.BackSide,
      transparent: true,
      opacity:   0.18,
      blending:  THREE.AdditiveBlending,
      depthWrite: false,
    });
    this.scene.add(new THREE.Mesh(geo, mat));
  }

  // ── Satellite management ────────────────────────────────────────

  addSatellite(id, colorName) {
    const hex = cssColorToHex(colorName);

    // Core sphere
    const mesh = new THREE.Mesh(
      new THREE.SphereGeometry(0.07, 10, 10),
      new THREE.MeshBasicMaterial({ color: hex })
    );

    // Glow shell — larger, transparent, additive blend
    const glow = new THREE.Mesh(
      new THREE.SphereGeometry(0.16, 10, 10),
      new THREE.MeshBasicMaterial({
        color:       hex,
        transparent: true,
        opacity:     0.25,
        depthWrite:  false,
        blending:    THREE.AdditiveBlending,
      })
    );
    mesh.add(glow);

    // Orbital trail
    const trail = new Trail(hex);
    this.scene.add(trail.line);
    this.scene.add(mesh);

    this.satellites[id] = { mesh, glow, trail };
  }

  // ── Per-frame update ────────────────────────────────────────────

  updateSatellites(objects) {
    objects.forEach(obj => {
      const sat = this.satellites[obj.id];
      if (!sat) return;

      // Move to new position
      const p = physToThree(obj.position);
      sat.mesh.position.copy(p);

      // Push into trail
      sat.trail.push(p.x, p.y, p.z);

      // Color: flash red on collision, otherwise base color
      const hexColor = obj.color === 'red'
        ? 0xff1744
        : cssColorToHex(obj.base_color);

      sat.mesh.material.color.set(hexColor);
      sat.glow.material.color.set(hexColor);
      sat.trail.setColor(hexColor);
    });
  }

  // ── Render loop ─────────────────────────────────────────────────

  _animate() {
    requestAnimationFrame(() => this._animate());

    // Slowly rotate Earth
    if (this.earthMesh) this.earthMesh.rotation.y += 0.0005;

    this.controls.update();
    this.renderer.render(this.scene, this.camera);
  }
}