import time
from fastapi.testclient import TestClient
from apps.api.app.main import app


def test_api_controls_websocket_and_export():
    with TestClient(app) as client:
        assert client.get('/api/health').status_code==200
        assert client.get('/api/scenario/schema').json()['title']=='Scenario'
        initial=client.get('/api/state').json()
        assert initial['state']['tick']==0
        with client.websocket_connect('/ws') as socket:
            assert socket.receive_json()['type']=='world_state'
        assert client.post('/api/control/run').json()['state']['mission_status']=='RUNNING'
        time.sleep(.6)
        paused=client.post('/api/control/pause').json()['state']
        assert paused['tick']>=1
        time.sleep(.4)
        assert client.get('/api/state').json()['state']==paused
        assert client.post('/api/control/step').json()['state']['tick']==paused['tick']+1
        exported=client.get('/api/export').json()
        assert len(exported['scenario_sha256'])==64
        assert exported['snapshot']['state']['tick']==paused['tick']+1
        reset=client.post('/api/control/reset').json()
        assert reset['state']==initial['state']
        assert reset['revision']>initial['revision']
        assert client.post('/api/control/invalid').status_code==422


def test_websocket_origin_restriction():
    from starlette.websockets import WebSocketDisconnect
    import pytest
    with TestClient(app) as client:
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect('/ws',headers={'origin':'https://untrusted.example'}):
                pass
