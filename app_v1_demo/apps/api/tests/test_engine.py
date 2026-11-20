import copy
import math
import pytest
from pydantic import ValidationError
from shapely.geometry import LineString, Polygon
from apps.api.app.models import Scenario
from apps.api.app.repository import load_scenario
from packages.simulation.engine import DT, Engine


def complete(engine):
    engine.command('run')
    for _ in range(3000):
        engine.advance()
        if engine.state.mission_status == 'COMPLETED':
            return engine.state.model_dump()
    pytest.fail('Mission did not complete within 750 simulated seconds')


def test_fixture_counts_and_schema_roundtrip():
    s = load_scenario()
    assert (s.width_m,s.height_m)==(2000,2000)
    assert (len(s.uavs),len(s.tasks),len(s.sectors))==(3,5,6)
    assert sum(r.kind=='building' for r in s.regions)==12
    assert Scenario.model_validate_json(s.model_dump_json()) == s


def test_determinism_completion_and_reset():
    engine=Engine(load_scenario())
    initial=engine.state.model_dump()
    first=complete(engine)
    assert all(t['status']=='COMPLETED' for t in first['tasks'])
    assert sum(e['type']=='TASK_COMPLETED' for e in first['events'])==5
    engine.command('reset')
    assert engine.state.model_dump()==initial
    assert complete(engine)==first
    assert complete(Engine(load_scenario()))==first


def test_step_and_pause_commands():
    engine=Engine(load_scenario())
    engine.command('step')
    assert engine.state.simulation_time==DT
    assert engine.state.mission_status=='PAUSED'
    engine.command('run')
    engine.advance()
    engine.command('pause')
    assert engine.state.simulation_time==2*DT
    previous=copy.deepcopy(engine.state)
    engine.command('pause')
    assert engine.state==previous


def test_movement_distance_battery_and_obstacle_safety():
    s=load_scenario()
    engine=Engine(s)
    engine.command('run')
    obstacles=[Polygon([p.xy() for p in r.polygon]).buffer(12) for r in s.regions if r.kind!='water']
    for _ in range(2200):
        before={u.id:u.position.xy() for u in engine.state.uavs}
        engine.advance()
        for u in engine.state.uavs:
            segment=LineString([before[u.id],u.position.xy()])
            assert not any(segment.intersects(o) for o in obstacles)
            assert math.dist(before[u.id],u.position.xy())<=u.speed_mps*DT+1e-7
    for u in engine.state.uavs:
        original=next(v for v in s.uavs if v.id==u.id)
        assert u.battery_percent==pytest.approx(original.battery_percent-u.distance_m*0.002)


def test_service_duration_and_task_sequence():
    engine=Engine(load_scenario())
    complete(engine)
    for task in engine.state.tasks:
        started=next(e for e in engine.state.events if e.type=='TASK_STARTED' and task.id in e.entity_ids)
        done=next(e for e in engine.state.events if e.type=='TASK_COMPLETED' and task.id in e.entity_ids)
        assert done.simulation_time-started.simulation_time>=task.service_seconds
    events=engine.state.events
    t1=next(e for e in events if e.type=='TASK_COMPLETED' and 'TASK-01' in e.entity_ids)
    t4=next(e for e in events if e.type=='TASK_DISPATCHED' and 'TASK-04' in e.entity_ids)
    assert t4.sequence>t1.sequence


@pytest.mark.parametrize('mutation',['collision','duplicate','unknown_uav','invalid_polygon','out_of_bounds'])
def test_rejects_invalid_scenario(mutation):
    data=load_scenario().model_dump()
    if mutation=='collision': data['tasks'][0]['route']=[data['tasks'][0]['route'][0],{'x':350,'y':280},data['tasks'][0]['route'][-1]]
    if mutation=='duplicate': data['uavs'][1]['id']=data['uavs'][0]['id']
    if mutation=='unknown_uav': data['tasks'][0]['assigned_uav_id']='MISSING'
    if mutation=='invalid_polygon': data['regions'][0]['polygon'][-1]={'x':10,'y':10}
    if mutation=='out_of_bounds': data['tasks'][0]['route'][1]={'x':-1,'y':300}
    with pytest.raises(ValidationError): Scenario.model_validate(data)
