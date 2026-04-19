# physics/gravity.py
"""
Computes gravitational acceleration vectors.
Isolated here so the physics logic is completely separate from everything else.
"""

import numpy as np
from backend.physics.constants import MU


def gravitational_acceleration(position: np.ndarray) -> np.ndarray:
    """
    Computes the gravitational acceleration vector at a given 3D position.

    Formula: a = -(μ / |r|³) * r

    Parameters
    ----------
    position : np.ndarray
        3D position vector [x, y, z] in meters from Earth's center.

    Returns
    -------
    np.ndarray
        Acceleration vector [ax, ay, az] in m/s².
        Always points toward Earth's center (hence the negative sign).

    Raises
    ------
    ValueError
        If the object is inside Earth (|r| < Earth's radius).
    """
    r_magnitude = np.linalg.norm(position)

    if r_magnitude < 6_371_000:
        raise ValueError(
            f"Object is inside Earth! |r| = {r_magnitude:.0f} m. "
            "Check your initial conditions."
        )

    return -(MU / r_magnitude ** 3) * position