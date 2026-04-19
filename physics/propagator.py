
"""
Numerical integration engine.
Propagates object positions and velocities forward in time using RK4.
"""

import numpy as np
from physics.gravity import gravitational_acceleration


def rk4_step(position: np.ndarray, velocity: np.ndarray, dt: float):
    """
    Advances a single object's state by one time step using Runge-Kutta 4.

    RK4 takes 4 derivative samples per step and combines them — this keeps
    orbital energy conserved and prevents the orbit from drifting over time.

    Parameters
    ----------
    position : np.ndarray — current [x, y, z] in meters
    velocity : np.ndarray — current [vx, vy, vz] in m/s
    dt       : float      — time step size in seconds

    Returns
    -------
    (new_position, new_velocity) : tuple of np.ndarray
    """

    def derivatives(pos, vel):
        """Rate of change: position changes at velocity, velocity changes at acceleration."""
        return vel, gravitational_acceleration(pos)

    # Sample 1 — at the start of the interval
    k1_v, k1_a = derivatives(position, velocity)

    # Sample 2 — at the midpoint, using k1 to estimate
    k2_v, k2_a = derivatives(position + 0.5 * dt * k1_v,
                              velocity + 0.5 * dt * k1_a)

    # Sample 3 — at the midpoint again, using k2's better estimate
    k3_v, k3_a = derivatives(position + 0.5 * dt * k2_v,
                              velocity + 0.5 * dt * k2_a)

    # Sample 4 — at the end of the interval
    k4_v, k4_a = derivatives(position + dt * k3_v,
                              velocity + dt * k3_a)

    # Weighted average (RK4 formula)
    new_position = position + (dt / 6) * (k1_v + 2*k2_v + 2*k3_v + k4_v)
    new_velocity = velocity + (dt / 6) * (k1_a + 2*k2_a + 2*k3_a + k4_a)

    return new_position, new_velocity


def propagate_all(objects: list, dt: float):
    """
    Steps every active object in the simulation forward by dt seconds.
    Appends the new position to each object's trajectory history.

    Parameters
    ----------
    objects : list of SpaceObject
    dt      : float — time step in seconds
    """
    for obj in objects:
        if obj.is_active:
            obj.position, obj.velocity = rk4_step(obj.position, obj.velocity, dt)
            obj.trajectory.append(obj.position.copy())