
"""
Space Object Tracking Simulation — Entry Point
===============================================
Define your satellites and debris here, then launch.
Everything else is handled by the modules.
"""

from models.space_object import SpaceObject
from visualization.animator import run_simulation
from utils.orbital_math import circular_velocity, orbit_period, inclination_velocity
from physics.constants import EARTH_RADIUS, LEO_ALTITUDE

def main():
    # --- Orbital parameters ---
    r_leo  = EARTH_RADIUS + LEO_ALTITUDE        # Radius from Earth center
    v_leo  = circular_velocity(LEO_ALTITUDE)    # ≈ 7,670 m/s
    period = orbit_period(LEO_ALTITUDE)

    print("=" * 55)
    print("Space Object Tracking Simulation")
    print("=" * 55)
    print(f"   LEO radius   : {r_leo/1e6:.3f} Mm")
    print(f"   LEO velocity : {v_leo:.1f} m/s")
    print(f"   Orbit period : {period/60:.1f} min")
    print("=" * 55)

    # --- Define space objects ---
    vy_inclined, vz_inclined = inclination_velocity(v_leo, inclination_deg=15)

    objects = [
        # Standard equatorial orbit
        SpaceObject(
            obj_id   = "SAT-1",
            mass     = 500,
            radius   = 2,
            position = [r_leo, 0, 0],
            velocity = [0, v_leo, 0],
            color    = 'cyan'
        ),

        # 15° inclined orbit, opposite starting position
        SpaceObject(
            obj_id   = "SAT-2",
            mass     = 300,
            radius   = 1.5,
            position = [-r_leo, 0, 0],
            velocity = [0, vy_inclined, vz_inclined],
            color    = 'lime'
        ),

        # Debris at 600km — slightly higher, different plane
        SpaceObject(
            obj_id   = "DEBRIS-1",
            mass     = 10,
            radius   = 0.5,
            position = [0, EARTH_RADIUS + 600_000, 0],
            velocity = [-circular_velocity(600_000), 0, 80],
            color    = 'orange'
        ),
    ]

    print()
    for obj in objects:
        print(f"   Loaded → {obj}")
    print()

    # --- Launch ---
    run_simulation(
        objects      = objects,
        total_time   = 5400,   # 90 minutes
        dt           = 10,     # 10-second steps
        trail_length = 180
    )
if __name__ == "__main__":
    main()