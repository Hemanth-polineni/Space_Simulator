
"""
Handles all Matplotlib 3D animation.
Completely decoupled from physics — it only reads trajectory data.
"""
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401 — required for 3D projection

from visualization.earth import draw_earth
from physics.propagator import propagate_all
from detection.collision import check_collisions
from physics.constants import EARTH_RADIUS

# Color palette for up to 8 distinct objects
OBJECT_COLORS = ['cyan', 'lime', 'orange', 'magenta', 'yellow',
                 'white', 'coral', 'aquamarine']


def _setup_axes(fig):
    """Creates and styles the 3D axes for a space-themed look."""
    ax = fig.add_subplot(111, projection='3d')
    ax.set_facecolor('black')

    for pane in [ax.xaxis.pane, ax.yaxis.pane, ax.zaxis.pane]:
        pane.fill = False
        pane.set_edgecolor('gray')

    ax.tick_params(colors='gray', labelsize=6)
    ax.xaxis.label.set_color('white')
    ax.yaxis.label.set_color('white')
    ax.zaxis.label.set_color('white')
    ax.set_xlabel('X (m)')
    ax.set_ylabel('Y (m)')
    ax.set_zlabel('Z (m)')
    ax.grid(True, color='gray', alpha=0.15)

    limit = 8.5e6
    ax.set_xlim([-limit, limit])
    ax.set_ylim([-limit, limit])
    ax.set_zlim([-limit, limit])
    ax.set_title('🛰️  Space Object Tracking Simulation',
                 color='white', fontsize=14, pad=15)
    return ax


def _precompute(objects, steps, dt):
    """
    Runs the full physics simulation upfront before animation starts.
    This way animation plays back smoothly — no physics computed per frame.
    """
    print(f"⚙️  Computing {steps} physics steps...")

    for step in range(steps):
        for obj in objects:
            obj.reset_color()         # Reset collision colors each step
        propagate_all(objects, dt)
        check_collisions(objects)

    # Lock trajectories as NumPy arrays for fast indexed access
    for obj in objects:
        obj.trajectory = np.array(obj.trajectory)  # Shape: (steps+1, 3)

    print(f"✅ Physics complete. {len(objects[0].trajectory)} frames ready.\n")


def run_simulation(objects: list,
                   total_time: int = 5400,
                   dt: int = 10,
                   trail_length: int = 200):
    """
    Main entry point for the full simulation + animation.

    Parameters
    ----------
    objects      : list of SpaceObject — the objects to simulate
    total_time   : int — duration in seconds (5400 = 90 min ≈ 1 LEO orbit)
    dt           : int — time step in seconds
    trail_length : int — how many past frames to show as an orbital trail
    """

    steps = int(total_time / dt)
    _precompute(objects, steps, dt)

    # --- Figure setup ---
    fig = plt.figure(figsize=(13, 10), facecolor='black')
    ax  = _setup_axes(fig)
    draw_earth(ax)

    # --- Assign colors and create plot elements per object ---
    scatter_plots, trail_lines, id_labels = [], [], []

    for idx, obj in enumerate(objects):
        color = OBJECT_COLORS[idx % len(OBJECT_COLORS)]
        obj.base_color = color

        sc = ax.scatter([], [], [], s=50, color=color,
                        depthshade=True, zorder=5)
        ln, = ax.plot([], [], [], '-', lw=0.9, alpha=0.65, color=color)
        lbl = ax.text(0, 0, 0, obj.obj_id, color=color, fontsize=7.5,
                      fontweight='bold')

        scatter_plots.append(sc)
        trail_lines.append(ln)
        id_labels.append(lbl)

    # HUD text elements
    time_label  = ax.text2D(0.02, 0.97, '', transform=ax.transAxes,
                             color='white', fontsize=10)
    frame_label = ax.text2D(0.02, 0.93, '', transform=ax.transAxes,
                             color='gray', fontsize=8)

    # --- Per-frame update ---
    def update(frame):
        for idx, obj in enumerate(objects):
            pos   = obj.trajectory[frame]
            start = max(0, frame - trail_length)
            trail = obj.trajectory[start : frame + 1]

            # Update scatter (current position dot)
            scatter_plots[idx]._offsets3d = ([pos[0]], [pos[1]], [pos[2]])
            scatter_plots[idx].set_color(obj.base_color)

            # Update trail line
            trail_lines[idx].set_data(trail[:, 0], trail[:, 1])
            trail_lines[idx].set_3d_properties(trail[:, 2])
            trail_lines[idx].set_color(obj.base_color)

            # Update label
            id_labels[idx].set_position((pos[0], pos[1]))
            id_labels[idx].set_3d_properties(pos[2], zdir='z')

        # Update HUD
        elapsed      = frame * dt
        minutes, sec = divmod(int(elapsed), 60)
        time_label.set_text(f'⏱  T+ {minutes:02d}:{sec:02d}')
        frame_label.set_text(f'Frame {frame}/{steps}')

        return scatter_plots + trail_lines + id_labels + [time_label, frame_label]

    ani = animation.FuncAnimation(
        fig,
        update,
        frames=steps + 1,
        interval=30,
        blit=False
    )

    plt.tight_layout()
    plt.show()