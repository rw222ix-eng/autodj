import time
from fastapi.testclient import TestClient
import soundfile as sf
import numpy as np
from app.api import app


def test_full_pipeline_default_options(click_120_wav):
    client = TestClient(app)
    t0 = time.perf_counter()
    with open(click_120_wav, "rb") as f_a, open(click_120_wav, "rb") as f_b:
        analyze_res = client.post(
            "/analyze",
            files={"file_a": ("a.wav", f_a, "audio/wav"),
                   "file_b": ("b.wav", f_b, "audio/wav")},
        )
    job_id = analyze_res.json()["job_id"]
    mix_res = client.post("/mix", json={
        "job_id": job_id, "type": "crossfade", "bars": 4,
        "effect": "none", "bridge": "none",
    })
    assert mix_res.status_code == 200
    dl = client.get(f"/download/{job_id}.wav")
    elapsed = time.perf_counter() - t0
    print(f"\nE2E wall-time: {elapsed:.2f}s")

    from io import BytesIO
    data, sr = sf.read(BytesIO(dl.content), dtype="float32", always_2d=True)
    peak_dbfs = 20 * np.log10(float(np.max(np.abs(data))))
    assert peak_dbfs <= -0.5 + 0.05
    assert sr == 44_100
