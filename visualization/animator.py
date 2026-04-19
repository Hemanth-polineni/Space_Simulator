
"""
Real-time continuous animation engine.

Physics is computed live inside each animation frame — no pre-computation,
no frame limit. The simulation runs until you close the window.

Key tools:
  - collections.deque(maxlen=N)  : rolling trail buffer, fixed memory
  - itertools.count()            : infinite frame counter
  - FuncAnimation                : drives the per-frame update loop
"""

import itertools
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from collections import deque
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401

from visualization.earth import draw_earth
from physics.propagator import propagate_all
from detection.collision import check_collisions
from physics.constants import EARTH_RADIUS

OBJECT_COLORS = ['cyan', 'lime', 'orange', 'magenta',
                 'yellow', 'white', 'coral', 'aquamarine']


# ─────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────

def _setup_axes(fig):
    """Creates and styles the 3D axes."""
    ax = fig.add_subplot(111, projection='3d')
    ax.set_facecolor('black')

    for pane in [ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane]:
        pane.fill = False
        pane.set_edgecolor('gray')

    ax.tick_params(colors='gray', labelsize=6)
    for axis in [ax.xaxis, ax.yaxis, ax.zaxis]:
        axis.label.set_color('white')

    ax.set_xlabel('X (m)')
    ax.set_ylabel('Y (m)')
    ax.set_zlabel('Z (m)')
    ax.grid(True, color='gray', alpha=0.15)

    limit = 8.5e6
    ax.set_xlim([-limit, limit])
    ax.set_ylim([-limit, limit])
    ax.set_zlim([-limit, limit])
    ax.set_title('🛰️  Space Object Tracking  —  Real-Time',
                 color='white', fontsize=14, pad=15)
    return ax


def _build_hud(ax):
    """Creates the HUD text elements overlaid on the plot."""
    kwargs = dict(transform=ax.transAxes, fontsize=9)
    time_label   = ax.text2D(0.02, 0.97, '',  color='white',  **kwargs)
    status_label = ax.text2D(0.02, 0.93, '',  color='#aaaaaa', fontsize=7,
                              transform=ax.transAxes)
    return time_label, status_label


# ─────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────

def run_simulation(objects: list,
                   dt: int = 10,
                   trail_length: int = 200):
    """
    Launches the real-time continuous orbital simulation.

    No pre-computation. No frame limit.
    Opens the window immediately and runs until closed.

    Parameters
    ----------
    objects      : list of SpaceObject — the objects to simulate
    dt           : int  — physics time step in seconds per animation frame
    trail_length : int  — number of past positions to show as orbital trail
                          (kept in a fixed-size rolling buffer — constant RAM)
    """

    # ── Assign colors ──────────────────────────────────────────────────────
    for idx, obj in enumerate(objects):
        obj.base_color = OBJECT_COLORS[idx % len(OBJECT_COLORS)]
        obj.color      = obj.base_color

    # ── Rolling trail buffers (one deque per object) ────────────────────────
    # deque(maxlen=N) auto-drops the oldest entry on every append.
    # Memory stays fixed no matter how long the simulation runs.
    trail_buffers = {
        obj.obj_id: deque([obj.position.copy()], maxlen=trail_length)
        for obj in objects
    }

    # ── Simulation state ────────────────────────────────────────────────────
    state = {
        "frame"            : 0,          # Total frames rendered
        "elapsed_seconds"  : 0,          # Simulated time in seconds
        "collision_count"  : 0,          # Total collision events logged
    }

    # ── Figure & axes ───────────────────────────────────────────────────────
    print("🚀 Opening simulation window — computing in real time...")
    fig = plt.figure(figsize=(13, 10), facecolor='black')
    ax  = _setup_axes(fig)
    draw_earth(ax)

    time_label, status_label = _build_hud(ax)

    # ── Plot elements (one scatter + one trail line + one label per object) ─
    scatter_plots, trail_lines, id_labels = [], [], []

    for obj in objects:
        sc = ax.scatter([], [], [], s=55, color=obj.base_color,
                        depthshade=True, zorder=5)
        ln, = ax.plot([], [], [], '-', lw=1.0, alpha=0.6, color=obj.base_color)
        lbl = ax.text(0, 0, 0, obj.obj_id, color=obj.base_color,
                      fontsize=8, fontweight='bold')
        scatter_plots.append(sc)
        trail_lines.append(ln)
        id_labels.append(lbl)

    # ── Per-frame update ─────────────────────────────────────────────────────
    def update(_):
        """
        Called once per animation frame by FuncAnimation.

        Steps:
          1. Reset collision colors from last frame
          2. Run one RK4 physics step for every object
          3. Check all object pairs for collisions
          4. Append new positions to rolling trail buffers
          5. Redraw all plot elements
          6. Update HUD
        """
        # 1 — Reset colors
        for obj in objects:
            obj.reset_color()

        # 2 — Physics: one RK4 step per object
        propagate_all(objects, dt)

        # 3 — Collision detection
        events = check_collisions(objects)
        state["collision_count"] += len(events)

        # 4 — Push new positions into rolling buffers
        for obj in objects:
            trail_buffers[obj.obj_id].append(obj.position.copy())

        # 5 — Redraw each object
        for idx, obj in enumerate(objects):
            pos   = obj.position
            trail = np.array(trail_buffers[obj.obj_id])  # Shape: (≤trail_length, 3)

            # Current position dot
            scatter_plots[idx]._offsets3d = ([pos[0]], [pos[1]], [pos[2]])
            scatter_plots[idx].set_color(obj.color)      # Red if collision this frame

            # Orbital trail
            trail_lines[idx].set_data(trail[:, 0], trail[:, 1])
            trail_lines[idx].set_3d_properties(trail[:, 2])
            trail_lines[idx].set_color(obj.color)

            # Floating ID label
            id_labels[idx].set_position((pos[0], pos[1]))
            id_labels[idx].set_3d_properties(pos[2], zdir='z')

        # 6 — HUD update
        state["elapsed_seconds"] += dt
        state["frame"]           += 1

        elapsed        = state["elapsed_seconds"]
        hours, rem     = divmod(int(elapsed), 3600)
        minutes, secs  = divmod(rem, 60)

        time_label.set_text(
            f'⏱  T+ {hours:02d}h {minutes:02d}m {secs:02d}s'
        )
        status_label.set_text(
            f'Frame: {state["frame"]:,}  |  '
            f'Δt: {dt}s/frame  |  '
            f'Alerts: {state["collision_count"]}'
        )

        return scatter_plots + trail_lines + id_labels + [time_label, status_label]

    # ── Launch animation ─────────────────────────────────────────────────────
    # itertools.count() produces 0, 1, 2, 3, ... forever.
    # FuncAnimation will keep calling update() indefinitely.
    # interval=20 → targets ~50 fps (actual fps depends on your machine's speed)
    ani = animation.FuncAnimation(
        fig,
        update,
        frames=itertools.count(),   # ← The key: infinite counter, no end frame
        interval=20,                # ms between frames (20ms ≈ 50 fps target)
        blit=False                  # blit=True can conflict with 3D axes
    )

    plt.tight_layout()
    plt.show()