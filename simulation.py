import numpy as np
class SpaceObject:
    """
    Represents a satellite or debris fragment in orbit.
    
    State vector = position [x, y, z] + velocity [vx, vy, vz]
    All units: meters (m) and meters/second (m/s)
    """
    def __init__(self,obj_id, mass, radius, position, velocity):
        """
        obj_id   : str   — a unique name e.g. "SAT-1", "DEBRIS-3"
        mass     : float — kg (not critical for gravity, but good practice)
        radius   : float — physical size in meters (used for collision detection)
        position : list  — [x, y, z] in meters from Earth's center
        velocity : list  — [vx, vy, vz] in m/s
        """
        self.obj_id   = obj_id
        self.mass     = mass
        self.radius   = radius
        self.position = np.array(position, dtype=float)  # Convert to NumPy arrays
        self.velocity = np.array(velocity, dtype=float)  # so we can do vector math

        self.trajectory = [self.position.copy()]  # Store history for trail rendering
        self.color      = 'cyan'                  # Default color; turns red on collision
        self.is_active  = True                    # False if it has "collided"
    def __repr__(self):
        return f"SpaceObject({self.obj_id}, pos={np.round(self.position/1e6, 2)} Mm)"

# Earth's gravitational parameter μ = G * M_earth
MU = 3.986004418e14  # m³/s²  (this is a well-known constant, very precise)
def gravitational_acceleration(position):
    """
    Computes the gravitational acceleration vector at a given position.

    Formula: a = -(μ / |r|³) * r
    
    - position : np.array [x, y, z]  — position vector from Earth's center
    - returns  : np.array [ax, ay, az] — acceleration in m/s²
    
    Intuition: The further you are (larger |r|), the weaker the pull.
               The direction is always TOWARD Earth (hence the minus sign).
    """
    r_magnitude = np.linalg.norm(position)          # |r| = sqrt(x²+y²+z²)
    acceleration = -(MU / r_magnitude**3) * position # Vector pointing to Earth center
    return acceleration
# Add this below the gravitational_acceleration function

def rk4_step(position, velocity, dt):
    """
    Advances position and velocity by one time step using RK4 integration.
    
    RK4 works by sampling the physics at 4 points within the time step
    and taking a weighted average — much more accurate than Euler.
    
    position : np.array [x, y, z]   — current position
    velocity : np.array [vx, vy, vz] — current velocity
    dt       : float                 — time step in seconds
    
    Returns: (new_position, new_velocity)
    """

    def derivatives(pos, vel):
        """Returns (velocity, acceleration) — the two rates of change."""
        acc = gravitational_acceleration(pos)
        return vel, acc  # d(position)/dt = velocity, d(velocity)/dt = acceleration
    # --- RK4 sampling ---
    # k1: derivatives at the START of the step
    k1_v, k1_a = derivatives(position, velocity)

    # k2: derivatives at the MIDPOINT, using k1 to estimate where we'll be
    k2_v, k2_a = derivatives(position + 0.5*dt*k1_v,
                              velocity + 0.5*dt*k1_a)

    # k3: derivatives at the MIDPOINT again, using k2's better estimate
    k3_v, k3_a = derivatives(position + 0.5*dt*k2_v,
                              velocity + 0.5*dt*k2_a)

    # k4: derivatives at the END of the step
    k4_v, k4_a = derivatives(position + dt*k3_v,
                              velocity + dt*k3_a)

    # Weighted average of all 4 samples (RK4 weights: 1, 2, 2, 1)
    new_position = position + (dt/6) * (k1_v + 2*k2_v + 2*k3_v + k4_v)
    new_velocity = velocity + (dt/6) * (k1_a + 2*k2_a + 2*k3_a + k4_a)

    return new_position, new_velocity


def propagate_all(objects, dt):
    """
    Moves every active object forward by one time step.
    Stores the new position in the object's trajectory history.
    """
    for obj in objects:
        if obj.is_active:
            obj.position, obj.velocity = rk4_step(obj.position, obj.velocity, dt)
            obj.trajectory.append(obj.position.copy())  # Save for trail rendering


COLLISION_THRESHOLD = 5000  # 5 km danger zone in meters

def check_collisions(objects):
    """
    Checks all pairs of objects for proximity.
    
    If two objects are within COLLISION_THRESHOLD meters of each other,
    logs a warning and marks them red.
    
    Uses itertools-style double loop to avoid checking (A,B) and (B,A) twice.
    """
    collision_events = []

    for i in range(len(objects)):
        for j in range(i + 1, len(objects)):  # j always > i, so no duplicates
            obj_a = objects[i]
            obj_b = objects[j]

            if not obj_a.is_active or not obj_b.is_active:
                continue  # Skip already-collided objects

            # Euclidean distance: d = sqrt((x2-x1)² + (y2-y1)² + (z2-z1)²)
            distance = np.linalg.norm(obj_a.position - obj_b.position)

            if distance < COLLISION_THRESHOLD:
                event = {
                    "objects" : (obj_a.obj_id, obj_b.obj_id),
                    "distance": distance,
                    "position": (obj_a.position + obj_b.position) / 2  # Midpoint
                }
                collision_events.append(event)

                # Visual alert: turn both objects red
                obj_a.color = 'red'
                obj_b.color = 'red'

                print(f"⚠️  COLLISION ALERT: {obj_a.obj_id} ↔ {obj_b.obj_id} | "
                      f"Distance: {distance/1000:.2f} km | "
                      f"Position: {np.round(obj_a.position/1e6, 2)} Mm")

    return collision_events

import matplotlib.pyplot as plt
import matplotlib.animation as animation
from mpl_toolkits.mplot3d import Axes3D  # Enables 3D projection

EARTH_RADIUS = 6_371_000  # 6,371 km in meters

def draw_earth(ax):
    """
    Draws a blue wireframe sphere representing Earth at the origin.
    Uses spherical coordinates converted to Cartesian (x,y,z).
    """
    u = np.linspace(0, 2 * np.pi, 30)   # Longitude angles
    v = np.linspace(0, np.pi, 20)        # Latitude angles

    x = EARTH_RADIUS * np.outer(np.cos(u), np.sin(v))
    y = EARTH_RADIUS * np.outer(np.sin(u), np.sin(v))
    z = EARTH_RADIUS * np.outer(np.ones(np.size(u)), np.cos(v))

    ax.plot_surface(x, y, z, color='royalblue', alpha=0.4, linewidth=0)
    ax.plot_wireframe(x, y, z, color='deepskyblue', alpha=0.15, linewidth=0.3)


def run_simulation(objects, total_time=5400, dt=10, trail_length=200):
    """
    Main simulation runner + animator.

    objects     : list of SpaceObject instances
    total_time  : total simulation duration in seconds (5400s = 1.5 orbits)
    dt          : time step in seconds (10s is a good balance of speed/accuracy)
    trail_length: how many past positions to show as a tail
    """

    # --- Pre-compute ALL physics upfront (fast, no lag during animation) ---
    print("🚀 Running physics simulation...")
    steps = int(total_time / dt)

    for step in range(steps):
        propagate_all(objects, dt)
        check_collisions(objects)
        # Reset colors to default each step (only stay red if collision this frame)
        for obj in objects:
            if obj.color != 'red':
                obj.color = 'cyan'

    print(f"✅ Simulation complete. {steps} steps computed.")

    # Convert trajectory lists to NumPy arrays for fast slicing
    for obj in objects:
        obj.trajectory = np.array(obj.trajectory)  # Shape: (steps+1, 3)

    # --- Set up the 3D plot ---
    fig = plt.figure(figsize=(12, 10), facecolor='black')
    ax  = fig.add_subplot(111, projection='3d')
    ax.set_facecolor('black')
    fig.patch.set_facecolor('black')

    # Style the axes for a space feel
    ax.set_xlabel('X (m)', color='white', fontsize=8)
    ax.set_ylabel('Y (m)', color='white', fontsize=8)
    ax.set_zlabel('Z (m)', color='white', fontsize=8)
    ax.tick_params(colors='gray', labelsize=6)
    ax.xaxis.pane.fill = False
    ax.yaxis.pane.fill = False
    ax.zaxis.pane.fill = False
    ax.grid(True, color='gray', alpha=0.2)

    draw_earth(ax)  # Draw Earth once (it doesn't move)

    # Set axis limits to slightly beyond LEO
    limit = 8e6  # 8,000 km
    ax.set_xlim([-limit, limit])
    ax.set_ylim([-limit, limit])
    ax.set_zlim([-limit, limit])
    ax.set_title('🛰️  Space Object Tracking Simulation', color='white',
                 fontsize=14, pad=15)

    # --- Create scatter plots and trail lines for each object ---
    scatter_plots = []
    trail_lines   = []
    labels        = []

    colors = ['cyan', 'lime', 'orange', 'magenta', 'yellow', 'white']

    for idx, obj in enumerate(objects):
        base_color = colors[idx % len(colors)]
        sc = ax.scatter([], [], [], s=40, color=base_color, zorder=5, depthshade=True)
        ln, = ax.plot([], [], [], '-', linewidth=0.8, alpha=0.6, color=base_color)
        lbl = ax.text(0, 0, 0, obj.obj_id, color=base_color, fontsize=7)
        scatter_plots.append(sc)
        trail_lines.append(ln)
        labels.append(lbl)
        obj.base_color = base_color  # Remember each object's original color

    # Time label
    time_text = ax.text2D(0.02, 0.95, '', transform=ax.transAxes,
                           color='white', fontsize=10)

    # --- Animation update function ---
    def update(frame):
        """Called once per animation frame. Updates positions + trails."""
        for idx, obj in enumerate(objects):
            traj = obj.trajectory

            # Current position
            pos = traj[frame]
            scatter_plots[idx]._offsets3d = ([pos[0]], [pos[1]], [pos[2]])

            # Trail: last N positions
            start = max(0, frame - trail_length)
            trail = traj[start:frame+1]
            trail_lines[idx].set_data(trail[:, 0], trail[:, 1])
            trail_lines[idx].set_3d_properties(trail[:, 2])

            # Label position
            labels[idx].set_position((pos[0], pos[1]))
            labels[idx].set_3d_properties(pos[2], zdir='z')

            # Color: red if recent collision, otherwise default
            # (Collision coloring was set during pre-computation; use base_color here)
            scatter_plots[idx].set_color(obj.base_color)
            trail_lines[idx].set_color(obj.base_color)

        elapsed = frame * dt
        time_text.set_text(f'T = {elapsed//60:.0f} min {elapsed%60:.0f} s')
        return scatter_plots + trail_lines + labels + [time_text]

    # Create animation — interval=30ms ≈ 33 fps
    ani = animation.FuncAnimation(
        fig,
        update,
        frames=len(objects[0].trajectory),
        interval=30,
        blit=False
    )

    plt.tight_layout()
    plt.show()

# ============================================================
# MAIN — Define objects and launch simulation
# ============================================================

if __name__ == "__main__":

    # --- Orbital velocity helper ---
    # For a circular orbit at radius r: v = sqrt(μ/r)
    # We orient each satellite differently using trig to spread them out

    def circular_velocity(r):
        """Speed needed to stay in a circular orbit at radius r."""
        return np.sqrt(MU / r)

    # --- Define 3 satellites in Low Earth Orbit (~400 km altitude) ---
    LEO = EARTH_RADIUS + 400_000   # 400 km above surface = 6,771,000 m from center
    v   = circular_velocity(LEO)   # ≈ 7,670 m/s

    objects = [
        # SAT-1: Equatorial orbit (orbits in XY plane)
        SpaceObject(
            obj_id   = "SAT-1",
            mass     = 500,
            radius   = 2,
            position = [LEO, 0, 0],        # Starts on the +X axis
            velocity = [0, v, 0]           # Moving in the +Y direction
        ),

        # SAT-2: Slightly inclined orbit (tilted 15°)
        SpaceObject(
            obj_id   = "SAT-2",
            mass     = 300,
            radius   = 1.5,
            position = [-LEO, 0, 0],       # Starts on the -X axis (opposite side)
            velocity = [0, -v * np.cos(np.radians(15)),
                            v * np.sin(np.radians(15))]  # 15° inclination
        ),

        # DEBRIS-1: Higher orbit (600 km), slightly different plane
        SpaceObject(
            obj_id   = "DEBRIS-1",
            mass     = 10,
            radius   = 0.5,
            position = [0, EARTH_RADIUS + 600_000, 0],
            velocity = [-circular_velocity(EARTH_RADIUS + 600_000), 0, 50]
        ),
    ]

    print("=" * 50)
    print("  🛰️  Space Object Tracking Simulation")
    print("=" * 50)
    for obj in objects:
        print(f"  Loaded: {obj}")
    print()

    # Launch the simulation!
    run_simulation(
        objects      = objects,
        total_time   = 5400,   # Simulate 90 minutes (≈ 1 full LEO orbit)
        dt           = 10,     # 10-second time steps
        trail_length = 150     # Show last 150 positions as a trail
    )