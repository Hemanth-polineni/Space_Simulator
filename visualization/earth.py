# visualization/earth.py
"""
Draws a 3D Earth sphere on a Matplotlib Axes3D object.
Kept separate so the visual style is easy to tweak without touching the animator.
"""

import numpy as np
from physics.constants import EARTH_RADIUS


def draw_earth(ax, resolution: int = 30):
    """
    Renders Earth as a shaded blue sphere with a subtle wireframe overlay.

    Parameters
    ----------
    ax         : Axes3D — the 3D matplotlib axes to draw on
    resolution : int    — grid density (higher = smoother sphere, slower render)
    """
    u = np.linspace(0, 2 * np.pi, resolution)
    v = np.linspace(0, np.pi, resolution // 2)

    x = EARTH_RADIUS * np.outer(np.cos(u), np.sin(v))
    y = EARTH_RADIUS * np.outer(np.sin(u), np.sin(v))
    z = EARTH_RADIUS * np.outer(np.ones_like(u), np.cos(v))

    # Solid fill — semi-transparent blue
    ax.plot_surface(x, y, z,
                    color='royalblue',
                    alpha=0.45,
                    linewidth=0,
                    antialiased=True)

    # Wireframe grid — gives the "globe" feel
    ax.plot_wireframe(x, y, z,
                      color='deepskyblue',
                      alpha=0.12,
                      linewidth=0.3)