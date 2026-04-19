
"""
Simulation Engine
==================
Self-contained wrapper around all physics modules.
Driven by FastAPI's async event loop — one .step() per broadcast cycle.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import numpy as np
from backend.models.space_object import SpaceObject
from backend.physics.propagator import propagate_all
from backend.physics.constants import EARTH_RADIUS, LEO_ALTITUDE
from backend.detection.collision import check_collisions
from backend.telemetry.calculator import OrbitalCalculator
from backend.utils.orbital_math import circular_velocity, inclination_velocity
class SimulationEngine:
    """
    Manages all space objects, runs physics, computes telemetry,
    and returns JSON-serializable state snapshots for WebSocket broadcast.
    """
    def __init__(self, dt: int = 10):
        self.dt             = dt
        self.paused         = False
        self.frame          = 0
        self.elapsed_s      = 0
        self.alert_count    = 0
        self.recent_alerts  = []
        self.objects        = self._build_default_objects()
        self.calculators    = {
            obj.obj_id: OrbitalCalculator(obj.obj_id)
            for obj in self.objects
        }
    # ── Object definitions ────────────────────────────────────────

    def _build_default_objects(self):
        r_leo      = EARTH_RADIUS + LEO_ALTITUDE
        v_leo      = circular_velocity(LEO_ALTITUDE)
        vy_i, vz_i = inclination_velocity(v_leo, 15)
        v_meo      = circular_velocity(600_000)

        return [
            SpaceObject(
                "SAT-1", 500, 2,
                position = [r_leo, 0, 0],
                velocity = [0, v_leo, 0],
                color    = 'cyan'
            ),
            SpaceObject(
                "SAT-2", 300, 1.5,
                position = [-r_leo, 0, 0],
                velocity = [0, vy_i, vz_i],
                color    = 'lime'
            ),
            SpaceObject(
                "DEBRIS-1", 10, 0.5,
                position = [0, EARTH_RADIUS + 600_000, 0],
                velocity = [-v_meo, 0, 80],
                color    = 'orange'
            ),
        ]

    # ── Core loop ─────────────────────────────────────────────────

    def step(self):
        """Advance simulation by one dt step. No-op when paused."""
        if self.paused:
            return

        for obj in self.objects:
            obj.reset_color()

        propagate_all(self.objects, self.dt)
        events = check_collisions(self.objects)

        self.recent_alerts  = events
        self.alert_count   += len(events)
        self.frame         += 1
        self.elapsed_s     += self.dt

    # ── State serialization ───────────────────────────────────────

    def get_state(self) -> dict:
        """
        Returns a fully JSON-serializable snapshot.
        Called after every step() and sent to all WebSocket clients.
        """
        objects_data = []
        for obj in self.objects:
            telem = self.calculators[obj.obj_id].compute(
                obj.position, obj.velocity
            )
            # Round floats to avoid unnecessary precision in JSON
            telem_clean = {
                k: (round(v, 4) if isinstance(v, float) else v)
                for k, v in telem.items()
            }
            objects_data.append({
                "id"        : obj.obj_id,
                "position"  : obj.position.tolist(),   # [x, y, z] meters
                "velocity"  : obj.velocity.tolist(),
                "color"     : obj.color,
                "base_color": obj.base_color,
                "is_active" : obj.is_active,
                "telemetry" : telem_clean,
            })

        return {
            "frame"      : self.frame,
            "elapsed_s"  : self.elapsed_s,
            "paused"     : self.paused,
            "alert_count": self.alert_count,
            "new_alerts" : [
                {
                    "ids"     : list(e["ids"]),
                    "distance": round(e["distance"] / 1000, 3),
                }
                for e in self.recent_alerts
            ],
            "objects"    : objects_data,
        }
    # ── Controls ──────────────────────────────────────────────────
    def toggle_pause(self):
        self.paused = not self.paused
        return self.paused

    def reset(self):
        self.__init__(self.dt)