
"""
Handy orbital mechanics helper functions.
These don't belong to any single module — they're general-purpose tools.
"""

import numpy as np
from physics.constants import MU, EARTH_RADIUS


def circular_velocity(altitude_m: float) -> float:
    """
    Returns the speed (m/s) needed for a circular orbit at a given altitude.

    Formula: v = sqrt(μ / r)   where r = Earth_radius + altitude

    Parameters
    ----------
    altitude_m : float — altitude above Earth's surface in meters

    Returns
    -------
    float — orbital speed in m/s
    """
    r = EARTH_RADIUS + altitude_m
    return np.sqrt(MU / r)


def orbit_period(altitude_m: float) -> float:
    """
    Returns the orbital period in seconds for a circular orbit.

    Formula: T = 2π * sqrt(r³ / μ)
    """
    r = EARTH_RADIUS + altitude_m
    return 2 * np.pi * np.sqrt(r ** 3 / MU)


def inclination_velocity(speed: float, inclination_deg: float):
    """
    Splits an orbital speed into velocity components for an inclined orbit.

    Parameters
    ----------
    speed           : float — orbital speed in m/s
    inclination_deg : float — orbit inclination in degrees (0 = equatorial)

    Returns
    -------
    (vy, vz) : tuple — velocity components in Y and Z directions
    """
    angle = np.radians(inclination_deg)
    vy = -speed * np.cos(angle)
    vz =  speed * np.sin(angle)
    return vy, vz