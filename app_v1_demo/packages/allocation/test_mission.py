import pytest

from packages.allocation.mission import DWELL, run_mission
from packages.allocation.world import LANDMARKS, UAVS, travel_time

UAV1, UAV2, UAV3 = UAVS


def task(task_id, landmark, sensor="ANY", priority=2):
    return {"id": task_id, "landmark": landmark, "sensor": sensor, "priority": priority}


def test_one_uav_one_task_time_is_distance_over_speed_plus_dwell():
    out = run_mission([UAV1], [task("A", "Clinic Gate")], {"Clinic Gate": "ANY"})
    expected = travel_time(UAV1, UAV1.start, LANDMARKS["Clinic Gate"]) + DWELL
    assert out["verify_time"]["Clinic Gate"] == pytest.approx(expected)
    assert out["missed"] == 0 and out["wasted"] == 0


def test_same_input_same_result():
    table = [task("A", "Clinic Gate"), task("B", "Boat Jetty", "THERMAL", 3)]
    truth = {"Clinic Gate": "ANY", "Boat Jetty": "THERMAL"}
    assert run_mission(UAVS, table, truth) == run_mission(UAVS, table, truth)


def test_two_uavs_one_task_only_one_flies():
    out = run_mission([UAV1, UAV3], [task("A", "Clinic Gate")], {"Clinic Gate": "ANY"})
    assert [v["uav"] for v in out["visits"]] == ["UAV-03"]            # UAV-03 is faster


def test_wrong_camera_costs_time():
    # the label says ANY, but the victim really needs THERMAL. UAV-01 is faster, flies there, sees nothing.
    out = run_mission([UAV1, UAV2], [task("A", "Clinic Gate", "ANY")], {"Clinic Gate": "THERMAL"})
    results = [(v["uav"], v["result"]) for v in out["visits"]]
    assert results == [("UAV-01", "failed"), ("UAV-02", "verified")]
    direct = travel_time(UAV2, UAV2.start, LANDMARKS["Clinic Gate"]) + DWELL
    assert out["verify_time"]["Clinic Gate"] > direct + 20             # clearly later than a direct flight
    assert out["wasted"] == 1


def test_false_alarm_is_a_wasted_visit_and_nobody_is_missed():
    out = run_mission([UAV1], [task("A", "Clinic Gate")], truth={})
    assert out["wasted"] == 1 and out["missed"] == 0


def test_victim_without_a_task_is_missed():
    out = run_mission(UAVS, [], {"North Bridge": "THERMAL"})
    assert out["missed"] == 1
    assert out["rmivt"] == 600.0


def test_more_tasks_than_uavs_everyone_is_found_later():
    names = ["Clinic Gate", "Market Square", "School Ground", "Fuel Station"]
    table = [task(f"T{i}", n) for i, n in enumerate(names)]
    out = run_mission(UAVS, table, {n: "ANY" for n in names})
    assert out["missed"] == 0 and len(out["visits"]) == 4