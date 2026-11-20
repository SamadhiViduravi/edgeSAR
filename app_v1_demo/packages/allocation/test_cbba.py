from packages.allocation.cbba import allocate
from packages.allocation.world import UAVS

UAV1, UAV2, UAV3 = UAVS
START = {u.id: u.start for u in UAVS}


def make_task(task_id, landmark, sensor="ANY", priority=2):
    return {"id": task_id, "landmark": landmark, "sensor": sensor, "priority": priority}


def test_same_input_same_result():
    tasks = [make_task("A", "Clinic Gate"), make_task("B", "Boat Jetty", "THERMAL", 3)]
    assert allocate(UAVS, tasks, START) == allocate(UAVS, tasks, START)


def test_one_uav_one_task():
    assignment, _ = allocate([UAV1], [make_task("A", "Clinic Gate")], START)
    assert assignment == {"UAV-01": "A"}


def test_two_uavs_one_task_only_the_best_bidder_gets_it():
    assignment, _ = allocate([UAV1, UAV3], [make_task("A", "Clinic Gate")], START)
    assert assignment == {"UAV-01": None, "UAV-03": "A"}      # UAV-03 is faster


def test_thermal_tasks_go_only_to_the_thermal_uav():
    tasks = [make_task("A", "Clinic Gate", "THERMAL"), make_task("B", "Market Square", "THERMAL")]
    assignment, _ = allocate(UAVS, tasks, START)
    assert sum(v is not None for v in assignment.values()) == 1    # only one thermal UAV
    assert assignment["UAV-01"] is None and assignment["UAV-03"] is None
    assert assignment["UAV-02"] in ("A", "B")


def test_more_tasks_than_uavs_no_task_is_given_twice():
    tasks = [make_task(f"T{i}", name) for i, name in
             enumerate(["Clinic Gate", "Market Square", "School Ground", "Fuel Station", "Boat Jetty"])]
    assignment, _ = allocate(UAVS, tasks, START)
    given = [v for v in assignment.values() if v is not None]
    assert len(given) == 3 and len(set(given)) == 3


def test_urgent_task_is_taken_before_a_lazy_one():
    tasks = [make_task("low", "Clinic Gate", priority=1), make_task("high", "Clinic Gate", priority=3)]
    assignment, _ = allocate([UAV1], tasks, START)
    assert assignment == {"UAV-01": "high"}