"""Step 3: how much does a UAV want a task? (the bid)
Higher bid = the UAV wants the task more. CBBA (Step 4) uses these bids to decide who gets what."""
import math

from packages.allocation.world import LANDMARKS, travel_time

# How much a task is worth, by priority (3 = most urgent).  <-- a research choice, we fix it now
PRIORITY_VALUE = {1: 1.0, 2: 2.0, 3: 3.0}

# How fast a task loses value while it waits (per second). 0.01 -> after 100 s the value is 37%.
TIME_DISCOUNT = 0.01


def can_bid(uav, task):
    """A UAV may bid only if it carries the camera the task asks for. ANY = every UAV may bid."""
    if task["sensor"] == "ANY":
        return True
    return task["sensor"] in uav.sensors


def arrival_time(uav, task, position, now):
    """When this UAV would arrive, if it flies straight from `position` starting at time `now`."""
    return now + travel_time(uav, position, LANDMARKS[task["landmark"]])


def bid(uav, task, position, now):
    """The bid, or None if the UAV cannot bid. Value = priority value x exp(-discount x arrival time)."""
    if not can_bid(uav, task):
        return None
    t = arrival_time(uav, task, position, now)
    return PRIORITY_VALUE[task["priority"]] * math.exp(-TIME_DISCOUNT * t)