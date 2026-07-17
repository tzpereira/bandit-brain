from fastapi.testclient import TestClient

from banditbrain.api.main import app

client = TestClient(app)


def test_openapi_schema_is_served():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    for route in (
        "/signup",
        "/login",
        "/ingest",
        "/recommend",
        "/decide",
        "/reward",
        "/experiments",
        "/metrics",
        "/allocations",
    ):
        assert route in paths


def test_protected_routes_reject_missing_token():
    assert client.get("/experiments").status_code == 401
    assert client.post("/recommend", json={"experiment_name": "x"}).status_code == 401
    assert client.post("/decide", json={"experiment_name": "x"}).status_code == 401
    assert client.post("/reward", json={"decision_id": "x"}).status_code == 401
