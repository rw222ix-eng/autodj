import uuid
import shutil
import sys
import os
import threading
import webbrowser
from datetime import datetime, timedelta
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .audio_io import load, UnsupportedFormat
from .analysis import analyze, InsufficientContent
from .config import WORKDIR, MAX_INPUT_DURATION_S
from .align import plan as align_plan
from .transition import (
    build,
    TransitionOptions,
    BridgeSampleMissing,
    TransitionType,
    EffectType,
    BridgeType,
)
from .render import write as render_write

app = FastAPI(title="AutoDJ")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _open_browser_when_ready():
    # Only auto-open when running as a packaged exe, not during dev/tests.
    if not getattr(sys, "frozen", False):
        return
    if os.environ.get("AUTODJ_NO_BROWSER"):
        return

    def _open():
        import time
        time.sleep(1.0)  # let uvicorn bind the port
        webbrowser.open("http://localhost:8000")

    threading.Thread(target=_open, daemon=True).start()


_open_browser_when_ready()


@app.on_event("startup")
def _cleanup_workdir():
    if not WORKDIR.exists():
        return
    cutoff = datetime.now() - timedelta(hours=24)
    for child in WORKDIR.iterdir():
        if not child.is_dir():
            continue
        if datetime.fromtimestamp(child.stat().st_mtime) < cutoff:
            shutil.rmtree(child, ignore_errors=True)


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
        buf_a = load(a_path)
        buf_b = load(b_path)
    except UnsupportedFormat as e:
        raise HTTPException(415, detail=str(e))

    if buf_a.samples.shape[0] / buf_a.sr > MAX_INPUT_DURATION_S:
        raise HTTPException(413, detail="file_too_long: a")
    if buf_b.samples.shape[0] / buf_b.sr > MAX_INPUT_DURATION_S:
        raise HTTPException(413, detail="file_too_long: b")

    try:
        feat_a = analyze(buf_a)
        feat_b = analyze(buf_b)
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


class MixRequest(BaseModel):
    job_id: str
    type: TransitionType = "crossfade"
    bars: int = 16
    effect: EffectType = "none"
    bridge: BridgeType = "none"
    manual_bpm_a: float | None = None
    manual_bpm_b: float | None = None


@app.post("/mix")
async def mix_endpoint(req: MixRequest):
    job = JOBS.get(req.job_id)
    if not job:
        raise HTTPException(404, detail="unknown job")
    from dataclasses import replace
    feat_a = job["feat_a"]
    feat_b = job["feat_b"]
    if req.manual_bpm_a is not None:
        feat_a = replace(feat_a, bpm=req.manual_bpm_a)
    if req.manual_bpm_b is not None:
        feat_b = replace(feat_b, bpm=req.manual_bpm_b)

    alignment = align_plan(feat_a, feat_b, bars=req.bars,
                           a_buffer=job["buf_a"].samples)

    if req.type == "cut" and not alignment.beat_match:
        raise HTTPException(422, detail="cut_requires_beat_match")

    options = TransitionOptions(type=req.type, bars=alignment.effective_bars,
                                effect=req.effect, bridge=req.bridge)
    try:
        mixed = build(job["buf_a"].samples, job["buf_b"].samples,
                      alignment, options, bpm_a=feat_a.bpm)
    except BridgeSampleMissing as e:
        raise HTTPException(500, detail=f"bridge_sample_missing: {e}")

    metadata = {
        "bpm_a": feat_a.bpm, "bpm_b": feat_b.bpm,
        "key_a": feat_a.key, "key_b": feat_b.key,
        "transition_start_s": alignment.a_start_sample / 44_100,
        "transition_end_s": alignment.a_end_sample / 44_100,
        "bars": alignment.effective_bars,
        "type": req.type, "effect": req.effect, "bridge": req.bridge,
        "beat_match": alignment.beat_match,
        "scale_a": job["buf_a"].scale_applied,
        "scale_b": job["buf_b"].scale_applied,
    }
    paths = render_write(mixed, job["dir"], metadata)
    job["paths"] = paths

    return {
        "status": "ok",
        "preview_url": f"/preview/{req.job_id}",
        "download_wav_url": f"/download/{req.job_id}.wav",
        "download_mp3_url": f"/download/{req.job_id}.mp3",
        "beat_match": alignment.beat_match,
        "effective_bars": alignment.effective_bars,
        "warning": alignment.warning,
    }


@app.get("/download/{job_id}.{ext}")
async def download_endpoint(job_id: str, ext: str):
    job = JOBS.get(job_id)
    if not job or "paths" not in job:
        raise HTTPException(404)
    if ext not in {"wav", "mp3"}:
        raise HTTPException(404)
    media = "audio/wav" if ext == "wav" else "audio/mpeg"
    return FileResponse(job["paths"][ext], media_type=media, filename=f"mix.{ext}")


@app.get("/preview/{job_id}")
async def preview_endpoint(job_id: str):
    job = JOBS.get(job_id)
    if not job or "paths" not in job:
        raise HTTPException(404)
    return FileResponse(job["paths"]["wav"], media_type="audio/wav")


def _frontend_dist_path() -> Path | None:
    # When packaged by PyInstaller, _MEIPASS is the extraction dir.
    if getattr(sys, "frozen", False):
        meipass = Path(sys._MEIPASS)  # type: ignore[attr-defined]
        candidate = meipass / "frontend_dist"
        if candidate.exists():
            return candidate
    # Dev: frontend/dist relative to project root
    dev = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
    return dev if dev.exists() else None


_frontend_path = _frontend_dist_path()
if _frontend_path:
    app.mount("/", StaticFiles(directory=str(_frontend_path), html=True), name="frontend")
