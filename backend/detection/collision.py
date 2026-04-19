# detection/collision.py
"""
Collision detection module.
Checks all pairs of objects each time step and flags near-misses or impacts.
"""

import numpy as np
from backend.physics.constants import COLLISION_THRESHOLD


def check_collisions(objects: list, threshold: float = COLLISION_THRESHOLD) -> list:
    """
    Checks every unique pair of active objects for dangerous proximity.

    Uses an O(n²) pairwise check — fine for small object counts (<100).
    For large simulations, this should be replaced with a spatial index (e.g. k-d tree).

    Parameters
    ----------
    objects   : list of SpaceObject
    threshold : float — distance in meters below which a collision is flagged

    Returns
    -------
    list of dicts, one per collision event:
        {
            "ids"      : (str, str),       — IDs of the two objects
            "distance" : float,            — distance in meters
            "midpoint" : np.ndarray        — [x, y, z] midpoint between them
        }
    """
    events = []

    for i in range(len(objects)):
        for j in range(i + 1, len(objects)):   # j > i → never check same pair twice
            a = objects[i]
            b = objects[j]

            if not a.is_active or not b.is_active:
                continue

            distance = np.linalg.norm(a.position - b.position)

            if distance < threshold:
                midpoint = (a.position + b.position) / 2
                event = {
                    "ids"      : (a.obj_id, b.obj_id),
                    "distance" : distance,
                    "midpoint" : midpoint,
                }
                events.append(event)

                # Visual flag
                a.mark_collision()
                b.mark_collision()

                _log_collision(event)

    return events


def _log_collision(event: dict):
    """Prints a formatted collision warning to the console."""
    id_a, id_b = event["ids"]
    dist_km    = event["distance"] / 1000
    pos_mm     = np.round(event["midpoint"] / 1e6, 3)
    print(f"⚠️  COLLISION ALERT | {id_a} ↔ {id_b} | "
          f"Distance: {dist_km:.2f} km | Midpoint: {pos_mm} Mm")