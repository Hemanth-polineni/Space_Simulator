# main.py
from models.space_object import SpaceObject
from visualization.animator import run_simulation
from utils.orbital_math import circular_velocity, orbit_period, inclination_velocity
from physics.constants import EARTH_RADIUS, LEO_ALTITUDE


def main():
    r_leo  = EARTH_RADIUS + LEO_ALTITUDE
    v_leo  = circular_velocity(LEO_ALTITUDE)
    period = orbit_period(LEO_ALTITUDE)

    print("=" * 55)
    print("Space Object Tracking — Real-Time Mode")
    print("=" * 55)
    print(f"   LEO radius   : {r_leo/1e6:.3f} Mm")
    print(f"   LEO velocity : {v_leo:.1f} m/s")
    print(f"   Orbit period : {period/60:.1f} min")
    print(f"   Mode         : ♾️  Continuous (close window to stop)")
    print("=" * 55)

    vy_inc, vz_inc = inclination_velocity(v_leo, inclination_deg=15)

    objects = [
        SpaceObject(
            obj_id="SAT-1",  mass=500, radius=2,
            position=[r_leo, 0, 0],
            velocity=[0, v_leo, 0],
            color='cyan'
        ),
        SpaceObject(
            obj_id="SAT-2",  mass=300, radius=1.5,
            position=[-r_leo, 0, 0],
            velocity=[0, vy_inc, vz_inc],
            color='lime'
        ),
        SpaceObject(
            obj_id="DEBRIS-1", mass=10, radius=0.5,
            position=[0, EARTH_RADIUS + 600_000, 0],
            velocity=[-circular_velocity(600_000), 0, 80],
            color='orange'
        ),
    ]

    print()
    for obj in objects:
        print(f"   Loaded → {obj}")
    print()

    run_simulation(
        objects      = objects,
        dt           = 10,     # seconds of simulation per frame
        trail_length = 200     # rolling trail length (fixed RAM)
    )


if __name__ == "__main__":
    main()