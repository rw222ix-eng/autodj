import pytest
from fastapi.testclient import TestClient
from app.api import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_analyze_returns_features(client, click_120_wav, click_128_wav):
    with open(click_120_wav, "rb") as f_a, open(click_128_wav, "rb") as f_b:
        res = client.post(
            "/analyze",
            files={"file_a": ("a.wav", f_a, "audio/wav"),
                   "file_b": ("b.wav", f_b, "audio/wav")},
        )
    assert res.status_code == 200
    data = res.json()
    assert "job_id" in data
    assert abs(data["a"]["bpm"] - 120) < 0.5
    assert abs(data["b"]["bpm"] - 128) < 0.5
    assert data["a"]["duration"] > 25
