"""World for the EdgeSAR allocation core.
Distances are in metres, times in seconds (same units as V1)."""
import math
from dataclasses import dataclass

BASE = (220, 80)

# 12 landmarks used by the pilot reports. Positions are fixed for ALL runs.
LANDMARKS = {
    "Clinic Gate":      (520, 520),
    "Market Square":    (900, 260),
    "School Ground":    (1050, 560),
    "Temple Junction":  (240, 560),
    "Fuel Station":     (1500, 300),
    "Railway Crossing": (1700, 520),
    "Hill Road Bend":   (250, 1150),
    "Rice Field A":     (150, 1400),
    "Rice Field B":     (1100, 1120),
    "North Bridge":     (1150, 1450),
    "Boat Jetty":       (1750, 1550),
    "Canal Lock":       (800, 1550),
}


@dataclass(frozen=True)
class UAV:
    id: str
    speed: float      # metres per second
    sensors: tuple    # cameras it carries
    start: tuple      # (x, y)


# Same three aircraft as V1. Only UAV-02 has a thermal camera.
UAVS = [
    UAV("UAV-01", 18, ("RGB",), (160, 140)),
    UAV("UAV-02", 16, ("RGB", "THERMAL"), (220, 140)),
    UAV("UAV-03", 20, ("RGB",), (280, 140)),
]


def travel_time(uav, a, b):
    """Seconds for this UAV to fly in a straight line from a to b."""
    return math.dist(a, b) / uav.speed


if __name__ == "__main__":
    for name, pos in LANDMARKS.items():
        times = [f"{u.id} {travel_time(u, u.start, pos):5.1f}s" for u in UAVS]
        print(f"{name:17s}", "  ".join(times))