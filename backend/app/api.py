import uuid
import shutil
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .audio_io import load, UnsupportedFormat
from .analysis import analyze, InsufficientContent
from .config import WORKDIR, MAX_INPUT_DURATION_S

app = FastAPI(title="AutoDJ")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

JOBS: dict[str, dict] = {}


def _save_upload(upload: UploadFile, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("wb") as f:
        shutil.copyfileobj(upload.file, f)
    return dest


def _feature_summary(features) -> dict:
    return {
        "bpm": float(features.bpm),
        "bpm_confidence": float(features.bpm_confidence),
        "key": features.key,
        "duration": float(features.duration_s),
        "suggested_start": float(features.outro_window[0]),
    }


@app.post("/analyze")
async def analyze_endpoint(file_a: UploadFile = File(...), file_b: UploadFile = File(...)):
    job_id = uuid.uuid4().hex[:12]
    job_dir = WORKDIR / job_id
    a_path = _save_upload(file_a, job_dir / f"a_{file_a.filename}")
    b_path = _save_upload(file_b, job_dir / f"b_{file_b.filename}")
    try:
        buf_a = load(a_path); buf_b = load(b_path)
    except UnsupportedFormat as e:
        raise HTTPException(415, detail=str(e))

    if buf_a.samples.shape[0] / buf_a.sr > MAX_INPUT_DURATION_S:
        raise HTTPException(413, detail="file_too_long: a")
    if buf_b.samples.shape[0] / buf_b.sr > MAX_INPUT_DURATION_S:
        raise HTTPException(413, detail="file_too_long: b")

    try:
        feat_a = analyze(buf_a); feat_b = analyze(buf_b)
    except InsufficientContent as e:
        raise HTTPException(422, detail=f"insufficient_content: {e}")

    warnings = []
    if feat_a.duration_s < 60:
        warnings.append("short_track:a")
    if feat_b.duration_s < 60:
        warnings.append("short_track:b")

    JOBS[job_id] = {
        "dir": job_dir,
        "buf_a": buf_a, "buf_b": buf_b,
        "feat_a": feat_a, "feat_b": feat_b,
    }
    return {
        "job_id": job_id,
        "a": _feature_summary(feat_a),
        "b": _feature_summary(feat_b),
        "warnings": warnings,
    }
