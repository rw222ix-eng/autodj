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


def test_mix_and_download(client, click_120_wav):
    with open(click_120_wav, "rb") as f_a, open(click_120_wav, "rb") as f_b:
        res = client.post(
            "/analyze",
            files={"file_a": ("a.wav", f_a, "audio/wav"),
                   "file_b": ("b.wav", f_b, "audio/wav")},
        )
    job_id = res.json()["job_id"]
    res = client.post("/mix", json={
        "job_id": job_id, "type": "crossfade", "bars": 4,
        "effect": "none", "bridge": "none",
    })
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "ok"
    assert body["effective_bars"] == 4
    assert body["beat_match"] is True

    dl = client.get(f"/download/{job_id}.wav")
    assert dl.status_code == 200
    assert dl.headers["content-type"].startswith("audio/")
    assert len(dl.content) > 10_000
