
"""
Numerical integration engine.
Each call advances the simulation by exactly one time step — live.
"""

import numpy as np
from physics.gravity import gravitational_acceleration
def rk4_step(position: np.ndarray, velocity: np.ndarray, dt: float):
    """
    Advances a single object's state by one time step using Runge-Kutta 4.
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
        return vel, gravitational_acceleration(pos)
    k1_v, k1_a = derivatives(position, velocity)
    k2_v, k2_a = derivatives(position + 0.5*dt*k1_v, velocity + 0.5*dt*k1_a)
    k3_v, k3_a = derivatives(position + 0.5*dt*k2_v, velocity + 0.5*dt*k2_a)
    k4_v, k4_a = derivatives(position + dt*k3_v,     velocity + dt*k3_a)

    new_position = position + (dt / 6) * (k1_v + 2*k2_v + 2*k3_v + k4_v)
    new_velocity = velocity + (dt / 6) * (k1_a + 2*k2_a + 2*k3_a + k4_a)

    return new_position, new_velocity


def propagate_all(objects: list, dt: float):
    """
    Advances every active object forward by dt seconds.

     Real-time version — only updates position/velocity.
    ----------
    objects : list of SpaceObject
    dt      : float — time step in seconds
    """
    for obj in objects:
        if obj.is_active:
            obj.position, obj.velocity = rk4_step(obj.position, obj.velocity, dt)