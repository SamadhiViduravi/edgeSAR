from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.api.app.allocation_routes import router


def test_allocation_demo_payload():
    app = FastAPI()
    app.include_router(router)
    data = TestClient(app).get("/api/allocation/demo").json()
    assert [c["id"] for c in data["cases"]] == ["c0618", "c0119", "c1189", "c0093", "c0047"]
    for c in data["cases"]:
        assert set(c["arms"]) == {"gold", "FP16", "Q4"}
    # c0093: FP16 ignores the report, Q4 creates the task (the pilot's clearest difference)
    c = next(c for c in data["cases"] if c["id"] == "c0093")
    assert c["arms"]["FP16"]["result"]["missed"] == 1
    assert c["arms"]["Q4"]["result"]["missed"] == 0
    assert round(c["arms"]["Q4"]["result"]["rmivt"], 1) == 75.3
