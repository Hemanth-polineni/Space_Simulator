# models/space_object.py
"""
Defines the SpaceObject class — the core data structure of the simulation.
Every satellite and debris fragment is one of these.
"""

import numpy as np


class SpaceObject:
    """
    Represents any object in orbit: satellite, debris, rocket body, etc.

    Attributes
    ----------
    obj_id     : str        — Unique identifier e.g. "SAT-1", "DEBRIS-3"
    mass       : float      — Mass in kg
    radius     : float      — Physical radius in meters (for collision sizing)
    position   : np.ndarray — [x, y, z] position vector in meters
    velocity   : np.ndarray — [vx, vy, vz] velocity vector in m/s
    trajectory : list       — History of all past positions (for trail rendering)
    color      : str        — Matplotlib color string; turns 'red' on collision
    is_active  : bool       — False if the object has been destroyed in a collision
    """
    def __init__(self, obj_id: str, mass: float, radius: float,
                 position: list, velocity: list, color: str = 'cyan'):
        self.obj_id     = obj_id
        self.mass       = mass
        self.radius     = radius
        self.position   = np.array(position, dtype=float)
        self.velocity   = np.array(velocity, dtype=float)
        self.color      = color
        self.base_color = color   # Preserved so we can reset after collision flash
        self.is_active  = True
        self.trajectory = [self.position.copy()]  # Seed with starting position

    def reset_color(self):
        """Restore the object's color to its original value."""
        self.color = self.base_color

    def mark_collision(self):
        """Flag this object as involved in a collision event."""
        self.color = 'red'

    def __repr__(self):
        pos_mm = np.round(self.position / 1e6, 3)  # Convert to megameters for readability
        return (f"SpaceObject(id='{self.obj_id}', mass={self.mass}kg, "
                f"pos={pos_mm} Mm, active={self.is_active})")