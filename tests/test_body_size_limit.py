from fastapi import FastAPI
from fastapi.testclient import TestClient

from banditbrain.api.body_size_limit import BodySizeLimitMiddleware

app = FastAPI()
app.add_middleware(BodySizeLimitMiddleware, max_body_bytes=1024)


@app.post("/echo")
def echo(payload: dict):
    return {"received": len(str(payload))}


client = TestClient(app)


def test_small_body_passes_through():
    response = client.post("/echo", json={"a": 1})
    assert response.status_code == 200


def test_oversized_body_is_rejected_with_413():
    response = client.post("/echo", json={"data": "x" * 2000})
    assert response.status_code == 413
