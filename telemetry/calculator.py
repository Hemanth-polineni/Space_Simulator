# telemetry/calculator.py
"""
Orbital Telemetry Calculator
=============================
Computes real orbital parameters from raw position/velocity state vectors.
All formulas come from classical orbital mechanics (Keplerian orbits).
Each method explains the formula it uses.
"""
import numpy as np
from physics.constants import MU, EARTH_RADIUS


class OrbitalCalculator:
    """
    Stateful calculator for one space object.
    Stateful because orbit counting needs to remember
    the previous angle to detect when a full orbit completes.
    Parameters
    ----------
    obj_id : str — matches the SpaceObject it belongs to
    """

    def __init__(self, obj_id: str):
        self.obj_id = obj_id
        # Orbit counting state
        self._accumulated_angle = 0.0   # Total angle swept so far (radians)
        self._prev_angle        = None  # atan2(y, x) from last frame
        self.orbit_count        = 0     # Completed full orbits
    # ─────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────

    def compute(self, position: np.ndarray, velocity: np.ndarray) -> dict:
        """
        Computes all orbital parameters for the current state vector.
        Parameters
        ----------
        position : np.ndarray — [x, y, z] in meters
        velocity : np.ndarray — [vx, vy, vz] in m/s
        Returns
        -------
        dict with keys:
            altitude_km    : float — height above Earth's surface
            speed_ms       : float — current speed in m/s
            inclination_deg: float — orbital plane tilt vs equator
            apoapsis_km    : float — highest point altitude
            periapsis_km   : float — lowest point altitude
            period_min     : float — current orbital period
            orbit_count    : int   — completed full orbits
            eccentricity   : float — orbit shape (0=circle, 1=parabola)
        """
        self._update_orbit_count(position)
        return {
            "altitude_km"    : self._altitude(position),
            "speed_ms"       : self._speed(velocity),
            "inclination_deg": self._inclination(position, velocity),
            "apoapsis_km"    : self._apoapsis(position, velocity),
            "periapsis_km"   : self._periapsis(position, velocity),
            "period_min"     : self._period(position, velocity),
            "orbit_count"    : self.orbit_count,
            "eccentricity"   : self._eccentricity(position, velocity),
        }
    # ─────────────────────────────────────────────────────────────
    # Individual parameter calculations
    # ─────────────────────────────────────────────────────────────
    def _altitude(self, pos: np.ndarray) -> float:
        """
        Altitude above Earth's surface in km.
        altitude = |r| - R_earth
        |r| is the straight-line distance from Earth's center.
        """
        return (np.linalg.norm(pos) - EARTH_RADIUS) / 1000

    def _speed(self, vel: np.ndarray) -> float:
        """
        Current orbital speed in m/s.
        speed = |v| = sqrt(vx² + vy² + vz²)
        """
        return np.linalg.norm(vel)
    def _inclination(self, pos: np.ndarray, vel: np.ndarray) -> float:
        """
        Orbital inclination in degrees — angle between orbital plane
        and Earth's equatorial plane.

        Method:
          h = r * v          (specific angular momentum vector)
          i = arccos(hz / |h|)
        h points perpendicular to the orbital plane.
        If the orbit is equatorial, h points straight up (hz = |h|) → i = 0°.
        If the orbit is polar, hz = 0 → i = 90°.
        """
        h = np.cross(pos, vel)               # Angular momentum vector
        h_mag = np.linalg.norm(h)
        if h_mag < 1e-10:
            return 0.0
        return float(np.degrees(np.arccos(np.clip(h[2] / h_mag, -1.0, 1.0))))
    def _specific_energy(self, pos: np.ndarray, vel: np.ndarray) -> float:
        """
        Specific orbital energy (energy per unit mass) in J/kg.

        ε = v²/2 - μ/|r|

        Negative ε → bound orbit (ellipse).
        Zero ε      → escape trajectory (parabola).
        Positive ε  → hyperbolic escape.
        """
        r = np.linalg.norm(pos)
        v = np.linalg.norm(vel)
        return (v ** 2) / 2 - MU / r

    def _semi_major_axis(self, pos: np.ndarray, vel: np.ndarray) -> float:
        """
        Semi-major axis in meters — the 'average' radius of the ellipse.

        a = -μ / (2ε)

        For a circular orbit: a = r (the radius).
        """
        eps = self._specific_energy(pos, vel)
        if abs(eps) < 1e-10:
            return float('inf')
        return -MU / (2 * eps)

    def _eccentricity(self, pos: np.ndarray, vel: np.ndarray) -> float:
        """
        Orbital eccentricity — describes the shape of the orbit.
        e = |e_vec|
        e_vec = (v²/μ - 1/|r|)·r - (r·v/μ)·v

        e = 0    → perfect circle
        0 < e < 1 → ellipse
        e = 1    → parabola (escape)
        e > 1    → hyperbola
        """
        r     = np.linalg.norm(pos)
        v     = np.linalg.norm(vel)
        r_dot_v = np.dot(pos, vel)

        e_vec = ((v**2 / MU) - (1 / r)) * pos - (r_dot_v / MU) * vel
        return float(np.linalg.norm(e_vec))

    def _apoapsis(self, pos: np.ndarray, vel: np.ndarray) -> float:
        """
        Apoapsis altitude in km — the highest point of the orbit above surface.

        r_apoapsis  = a × (1 + e)
        altitude_km = (r_apoapsis - R_earth) / 1000
        """
        a = self._semi_major_axis(pos, vel)
        e = self._eccentricity(pos, vel)
        if a <= 0 or e >= 1:
            return float('inf')
        return (a * (1 + e) - EARTH_RADIUS) / 1000

    def _periapsis(self, pos: np.ndarray, vel: np.ndarray) -> float:
        """
        Periapsis altitude in km — the lowest point of the orbit above surface.

        r_periapsis = a * (1 - e)
        altitude_km = (r_periapsis - R_earth) / 1000
        """
        a = self._semi_major_axis(pos, vel)
        e = self._eccentricity(pos, vel)
        if a <= 0:
            return float('-inf')
        return (a * (1 - e) - EARTH_RADIUS) / 1000

    def _period(self, pos: np.ndarray, vel: np.ndarray) -> float:
        """
        Orbital period in minutes.

        T = 2π * sqrt(a³ / μ)

        Kepler's third law — larger orbits take longer.
        """
        a = self._semi_major_axis(pos, vel)
        if a <= 0:
            return float('nan')
        return (2 * np.pi * np.sqrt(a ** 3 / MU)) / 60  # Convert s → min

    def _update_orbit_count(self, pos: np.ndarray):
        """
        Tracks how many complete orbits the object has made.

        Method:
          - Project position onto equatorial plane (ignore Z).
          - Compute angle θ = atan2(y, x).
          - Accumulate angle changes frame by frame.
          - Every time accumulated angle crosses ±2π, increment orbit count.

        Handles wrapping correctly using the shortest-path angle delta.
        """
        # Angle in the equatorial plane
        current_angle = np.arctan2(pos[1], pos[0])

        if self._prev_angle is not None:
            # Shortest angular difference accounting for wrap-around
            delta = current_angle - self._prev_angle

            # Wrap delta into [-π, π] — handles the ±π discontinuity
            if delta > np.pi:
                delta -= 2 * np.pi
            elif delta < -np.pi:
                delta += 2 * np.pi

            self._accumulated_angle += delta

            # Every full revolution (±2π) → one orbit completed
            full_orbits = int(abs(self._accumulated_angle) / (2 * np.pi))
            if full_orbits > self.orbit_count:
                self.orbit_count = full_orbits

        self._prev_angle = current_angle