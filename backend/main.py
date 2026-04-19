# backend/main.py
"""
FastAPI Application
====================
  GET  /          → serves frontend index.html
  GET  /static/   → serves all frontend assets (CSS, JS)
  GET  /config    → returns initial object list (id + color)
  POST /pause     → toggle pause
  POST /reset     → restart simulation
  WS   /ws        → real-time physics broadcast at 20fps
"""

import asyncio
import json
from pathlib import Path
from typing import Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.simulation import SimulationEngine

# ── Paths ──────────────────────────────────────────────────────────────
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"

# ── App ────────────────────────────────────────────────────────────────
app    = FastAPI(title="Orbital Tracker")
engine = SimulationEngine(dt=10)

# Allow all origins during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve all of /frontend/ as static files under /static/
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

# ── Connected WebSocket clients ────────────────────────────────────────
clients: Set[WebSocket] = set()


# ── HTTP routes ────────────────────────────────────────────────────────

@app.get("/")
async def serve_index():
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/config")
async def get_config():
    """
    Called once by the frontend on startup.
    Returns the object list so Three.js can create meshes before
    the first WebSocket frame arrives.
    """
    return {
        "objects": [
            {"id": obj.obj_id, "color": obj.base_color}
            for obj in engine.objects
        ],
        "dt": engine.dt,
    }


@app.post("/pause")
async def toggle_pause():
    paused = engine.toggle_pause()
    return {"paused": paused}


@app.post("/reset")
async def reset_simulation():
    engine.reset()
    return {"status": "ok"}


# ── WebSocket endpoint ─────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    clients.add(ws)
    print(f"[WS] Client connected  — total: {len(clients)}")
    try:
        # Keep the connection open; the sim loop handles broadcasting
        while True:
            await ws.receive_text()     # Client can send 'ping' to keep alive
    except WebSocketDisconnect:
        pass
    finally:
        clients.discard(ws)
        print(f"[WS] Client disconnected — total: {len(clients)}")


async def _broadcast(payload: str):
    """Send JSON string to every connected client. Prune dead connections."""
    dead = set()
    for ws in clients:
        try:
            await ws.send_text(payload)
        except Exception:
            dead.add(ws)
    clients.difference_update(dead)


# ── Background simulation loop ─────────────────────────────────────────

async def _simulation_loop():
    """
    Runs forever as an asyncio background task.
    Computes one physics step then broadcasts state at ~20 fps (50 ms cadence).
    The asyncio.sleep yields control so FastAPI can handle HTTP/WS requests.
    """
    while True:
        engine.step()
        if clients:
            await _broadcast(json.dumps(engine.get_state()))
        await asyncio.sleep(0.05)   # 50 ms → 20 fps


@app.on_event("startup")
async def on_startup():
    asyncio.create_task(_simulation_loop())
    print("Orbital Tracker  — simulation loop started")
    print(f" Open http://localhost:8000 in your browser")