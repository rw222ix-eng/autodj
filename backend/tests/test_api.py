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


def test_unsupported_format_returns_415(client, tmp_path):
    bad = tmp_path / "garbage.bin"
    bad.write_bytes(b"not audio")
    with open(bad, "rb") as fa, open(bad, "rb") as fb:
        res = client.post("/analyze", files={
            "file_a": ("a.bin", fa, "application/octet-stream"),
            "file_b": ("b.bin", fb, "application/octet-stream"),
        })
    assert res.status_code == 415


def test_unknown_job_returns_404(client):
    res = client.post("/mix", json={"job_id": "does-not-exist", "type": "crossfade",
                                    "bars": 4, "effect": "none", "bridge": "none"})
    assert res.status_code == 404


def test_short_track_warning(client, click_120_short_wav, click_120_wav):
    with open(click_120_short_wav, "rb") as fa, open(click_120_wav, "rb") as fb:
        res = client.post("/analyze", files={
            "file_a": ("a.wav", fa, "audio/wav"),
            "file_b": ("b.wav", fb, "audio/wav"),
        })
    assert res.status_code == 200
    body = res.json()
    assert "warnings" in body
    assert "short_track:a" in body["warnings"]


def test_cut_with_far_bpm_returns_422(client, click_90_wav, click_174_wav):
    with open(click_90_wav, "rb") as fa, open(click_174_wav, "rb") as fb:
        res = client.post("/analyze", files={
            "file_a": ("a.wav", fa, "audio/wav"),
            "file_b": ("b.wav", fb, "audio/wav"),
        })
    job_id = res.json()["job_id"]
    res = client.post("/mix", json={"job_id": job_id, "type": "cut",
                                    "bars": 4, "effect": "none", "bridge": "none"})
    assert res.status_code == 422
