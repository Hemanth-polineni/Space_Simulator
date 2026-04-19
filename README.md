# Space_Simulator

**ORBITAL TRACKER** — A Real-Time 3D Space Physics Simulation & Mission Control System

![Language Composition](https://img.shields.io/badge/Python-44.4%25-blue) ![Language Composition](https://img.shields.io/badge/JavaScript-32.1%25-yellow) ![Language Composition](https://img.shields.io/badge/CSS-16.5%25-pink) ![Language Composition](https://img.shields.io/badge/HTML-7%25-orange)

## 📋 Overview

**Space Simulator** is a full-stack web application that simulates realistic orbital mechanics and space object interactions in real-time. It features a **FastAPI backend** with physics-based propagation, collision detection, and telemetry calculations, paired with a **Three.js 3D visualization** frontend for immersive mission control.

The system tracks multiple space objects (satellites, debris) in orbit around Earth, computes orbital parameters, detects collision alerts, and broadcasts live state updates via WebSocket at 20 fps.

---

## ✨ Features

- **Real-Time Orbital Physics**  
  - Accurate Keplerian orbit propagation (RK4 integrator)  
  - Gravitational force calculations  
  - Support for multiple orbital altitudes (LEO, MEO)  
  
- **3D Visualization**  
  - Interactive Three.js scene with Earth and space objects  
  - Orbit trail visualization  
  - Real-time position updates via WebSocket  
  - Smooth camera controls (OrbitControls)

- **Telemetry & Tracking**  
  - Compute altitude, velocity, orbital period, eccentricity  
  - Real-time state broadcasting  
  - Frame-by-frame state snapshots

- **Collision Detection**  
  - Proximity-based collision alerts  
  - 5 km threshold detection  
  - Alert log with historical data

- **Mission Control Dashboard**  
  - Live mission time, frame counter  
  - Alert management system  
  - Pause/Reset simulation controls  
  - Object-specific telemetry cards

---

## 🏗️ Architecture

```
Space_Simulator/
├── backend/                     # FastAPI server & physics engine
│   ├── main.py                 # API endpoints and WebSocket management
│   ├── simulation.py           # Core simulation engine
│   ├── models/                 # Data models (SpaceObject)
│   ├── physics/                # Physics calculations
│   │   ├── constants.py        # Earth radius, orbital parameters
│   │   ├── propagator.py       # Orbit propagation (RK4)
│   │   └── ...
│   ├── detection/              # Collision detection
│   ├── telemetry/              # Orbital telemetry calculations
│   └── utils/                  # Orbital math helpers
│
├── frontend/                    # Web UI (HTML/CSS/JavaScript)
│   ├── index.html              # Main page structure
│   ├── style.css               # Styling & layouts
│   └── js/
│       ├── scene.js            # Three.js scene management
│       ├── dashboard.js        # UI updates & state management
│       └── main.js             # WebSocket connection & app logic
│
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

### Tech Stack

**Backend:**
- FastAPI (async web framework)
- NumPy & SciPy (numerical computing)
- Python 3.7+

**Frontend:**
- Three.js (3D graphics)
- WebSocket (real-time communication)
- Vanilla JavaScript/CSS
- Responsive design

---

## 🚀 Quick Start

### Prerequisites
- Python 3.7 or higher
- pip or conda
- Modern web browser (Chrome, Firefox, Safari, Edge)

### Installation

1. **Clone the repository**  
   ```bash
   git clone https://github.com/Hemanth-polineni/Space_Simulator.git
   cd Space_Simulator
   ```

2. **Install dependencies**  
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the server**  
   ```bash
   uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   ```

4. **Open in browser**  
   ```
   http://localhost:8000
   ```

---

## 📖 Usage

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Serves the main dashboard |
| GET | `/config` | Returns initial object configuration (IDs, colors) |
| POST | `/pause` | Toggle pause/resume simulation |
| POST | `/reset` | Restart simulation from initial state |
| WS | `/ws` | WebSocket stream of simulation state (20 fps) |
| GET | `/static/*` | Serves frontend assets (CSS, JS, etc.) |

### WebSocket Data Format

The server broadcasts JSON state snapshots every 50ms:

```json
{
  "frame": 1234,
  "elapsed_s": 12340,
  "paused": false,
  "alert_count": 3,
  "new_alerts": [
    {
      "ids": ["SAT-1", "DEBRIS-1"],
      "distance": 4.532
    }
  ],
  "objects": [
    {
      "id": "SAT-1",
      "position": [6731000, 0, 0],
      "velocity": [0, 7850, 0],
      "color": "cyan",
      "base_color": "cyan",
      "is_active": true,
      "telemetry": {
        "altitude": 352000,
        "speed": 7850,
        "period": 5400,
        "eccentricity": 0.0001
      }
    }
  ]
}
```

### Dashboard Controls

- **⏸ PAUSE** — Toggles simulation pause state
- **↺ RESET** — Restarts the simulation
- **3D View** — Drag to rotate, scroll to zoom, right-click to pan
- **Telemetry Cards** — Click to highlight objects in the 3D scene

---

## 🔬 Simulation Details

### Default Objects

1. **SAT-1** (Cyan)
   - Mass: 500 kg
   - Altitude: 352 km (LEO)
   - Inclination: 0°

2. **SAT-2** (Lime)
   - Mass: 300 kg
   - Altitude: 352 km (LEO)
   - Inclination: 15°

3. **DEBRIS-1** (Orange)
   - Mass: 10 kg
   - Altitude: 600 km (MEO)
   - High velocity debris object

### Physics Engine

- **Integrator:** Runge-Kutta 4th Order (RK4)
- **Time Step:** 10 seconds per frame
- **Propagation:** Full N-body Keplerian mechanics
- **Collision Threshold:** 5 km minimum separation distance

### Performance

- Frame rate: ~20 fps (50 ms per step)
- WebSocket broadcast: Every frame to all connected clients
- Real-time telemetry computation per object

---

## 📊 System Status Indicators

- **LIVE ORBITAL VIEW** — 3D visualization status
- **Connection Pill** — WebSocket connection state (green = connected)
- **FPS Counter** — Real-time rendering frame rate
- **Alert Bar** — System status ("ALL SYSTEMS NOMINAL" or collision warnings)

---

## 🛠️ Development

### Local Development
- Backend runs on `http://localhost:8000`
- Frontend auto-updates via WebSocket
- Use `--reload` flag for hot-reloading backend changes

### Debugging

- Check browser console for JavaScript errors
- Monitor server logs for Python exceptions
- WebSocket messages are logged in browser DevTools

### Adding New Objects

Edit `backend/simulation.py::_build_default_objects()` to add more space objects:

```python
SpaceObject(
    "MY-SAT",
    mass=1000,
    radius=2.5,
    position=[x, y, z],
    velocity=[vx, vy, vz],
    color='magenta'
)
```

---

## 📦 Dependencies

See `requirements.txt`:
- **fastapi** — Web framework
- **uvicorn[standard]** — ASGI server
- **numpy** — Numerical computing
- **scipy** — Scientific algorithms

---

## 🎓 Physics Background

This simulator implements:
- **Orbital Mechanics:** Keplerian equations, circular orbits
- **Numerical Integration:** RK4 method for trajectory computation
- **Collision Detection:** Euclidean distance-based proximity checks
- **Telemetry:** Real-time orbital element calculations

---

## 📝 License

This project is open-source. Feel free to use, modify, and distribute.

---

## 🤝 Contributing

Contributions are welcome! To contribute:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit changes (`git commit -m 'Add my feature'`)
4. Push to branch (`git push origin feature/my-feature`)
5. Open a Pull Request

---

## 📧 Contact & Support

For questions or issues:
- Open an issue on GitHub
- Check existing documentation and examples

---

**Built with ❤️ by Hemanth Polineni**