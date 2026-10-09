"""
Tests use a fake classifier (dependency override) so CI runs in seconds
and never downloads the real ~600MB CLIP weights.
"""

import io

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.model import get_classifier


class FakeClassifier:
    def classify(self, image_bytes: bytes, labels: list[str]) -> list[dict]:
        return [{"label": labels[0], "score": 0.99}]


app.dependency_overrides[get_classifier] = lambda: FakeClassifier()
client = TestClient(app)
client.__enter__()  # triggers lifespan startup (init_db) for the whole test session


def _sample_image_bytes() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), color=(128, 64, 32)).save(buf, format="PNG")
    return buf.getvalue()


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_frontend_is_served():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Defect Classifier" in resp.text


def test_predict_returns_predictions():
    files = {"image": ("test.png", _sample_image_bytes(), "image/png")}
    data = {"labels": "crack in hull plating,clean surface"}
    resp = client.post("/predict", files=files, data=data)
    assert resp.status_code == 200
    body = resp.json()
    assert body["cached"] is False
    assert body["predictions"][0]["label"] == "crack in hull plating"


def test_predict_cache_hit_on_second_call():
    files = {"image": ("test.png", _sample_image_bytes(), "image/png")}
    data = {"labels": "crack in hull plating,clean surface"}
    client.post("/predict", files=files, data=data)  # warm the cache
    resp = client.post("/predict", files=files, data=data)
    assert resp.json()["cached"] is True


def test_predict_rejects_empty_image():
    files = {"image": ("empty.png", b"", "image/png")}
    resp = client.post("/predict", files=files)
    assert resp.status_code == 400


def test_feedback_accepts_valid_rating():
    resp = client.post("/feedback", data={"request_id": "abc123", "rating": 1, "comment": "looks right"})
    assert resp.status_code == 200


def test_feedback_rejects_invalid_rating():
    resp = client.post("/feedback", data={"request_id": "abc123", "rating": 5})
    assert resp.status_code == 400


def test_metrics_endpoint_exposes_prometheus_format():
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert b"predict_requests_total" in resp.content
