"""
All physical constants used across the simulation.
Centralizing them here means you only ever change a value in ONE place.
"""

# Earth's standard gravitational parameter (G * M_earth)
MU = 3.986004418e14          # m³/s²

# Earth's mean radius
EARTH_RADIUS = 6_371_000     # meters (6,371 km)

# Collision danger zone
COLLISION_THRESHOLD = 5_000  # meters (5 km)

# Common orbit altitudes above surface (meters)
LEO_ALTITUDE = 400_000       # Low Earth Orbit   (~400 km)
MEO_ALTITUDE = 20_200_000    # Medium Earth Orbit (~20,200 km — GPS satellites)
GEO_ALTITUDE = 35_786_000    # Geostationary Orbit (~35,786 km)