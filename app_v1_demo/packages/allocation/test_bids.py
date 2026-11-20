from packages.allocation.bids import bid, can_bid
from packages.allocation.world import UAVS

UAV1, UAV2, UAV3 = UAVS
START = (220, 140)          # all three UAVs start close to here


def make_task(landmark="Clinic Gate", sensor="ANY", priority=2):
    return {"id": "T", "landmark": landmark, "sensor": sensor, "priority": priority}


def test_only_the_thermal_uav_can_take_a_thermal_task():
    task = make_task(sensor="THERMAL")
    assert not can_bid(UAV1, task)
    assert can_bid(UAV2, task)
    assert not can_bid(UAV3, task)


def test_a_uav_that_cannot_bid_gets_none():
    assert bid(UAV1, make_task(sensor="THERMAL"), START, 0) is None


def test_faster_uav_bids_higher_for_the_same_task():
    task = make_task("Clinic Gate")
    assert bid(UAV3, task, START, 0) > bid(UAV1, task, START, 0)    # UAV-03 is faster


def test_higher_priority_bids_higher_at_the_same_place():
    low = make_task(priority=1)
    high = make_task(priority=3)
    assert bid(UAV1, high, START, 0) > bid(UAV1, low, START, 0)


def test_the_same_input_gives_the_same_bid():
    task = make_task()
    assert bid(UAV1, task, START, 0) == bid(UAV1, task, START, 0)