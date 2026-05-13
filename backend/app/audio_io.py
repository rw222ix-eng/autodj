from dataclasses import dataclass
from pathlib import Path
import subprocess
import tempfile
import numpy as np
import soundfile as sf

from .config import TARGET_SAMPLE_RATE, TARGET_CHANNELS, INPUT_PEAK_DBFS


class UnsupportedFormat(Exception):
    pass


@dataclass
class AudioBuffer:
    samples: np.ndarray
    sr: int
    channels: int
    scale_applied: float


def _peak_normalize(samples: np.ndarray, target_dbfs: float) -> tuple[np.ndarray, float]:
    peak = float(np.max(np.abs(samples))) or 1.0
    target_peak = 10 ** (target_dbfs / 20)
    scale = target_peak / peak
    return samples * scale, scale


def load(path: Path) -> AudioBuffer:
    path = Path(path)
    try:
        data, sr = sf.read(str(path), dtype="float32", always_2d=True)
    except Exception:
        data, sr = _ffmpeg_decode(path)
    data = _ensure_stereo(data)
    data = _resample_if_needed(data, sr, TARGET_SAMPLE_RATE)
    normalized, scale = _peak_normalize(data, INPUT_PEAK_DBFS)
    return AudioBuffer(
        samples=normalized.astype(np.float32),
        sr=TARGET_SAMPLE_RATE,
        channels=TARGET_CHANNELS,
        scale_applied=scale,
    )


def _ensure_stereo(data: np.ndarray) -> np.ndarray:
    if data.ndim == 1:
        data = np.stack([data, data], axis=1)
    elif data.shape[1] == 1:
        data = np.repeat(data, 2, axis=1)
    elif data.shape[1] > 2:
        data = data[:, :2]
    return data


def _resample_if_needed(data: np.ndarray, sr: int, target_sr: int) -> np.ndarray:
    if sr == target_sr:
        return data
    import librosa
    left = librosa.resample(data[:, 0], orig_sr=sr, target_sr=target_sr)
    right = librosa.resample(data[:, 1], orig_sr=sr, target_sr=target_sr)
    return np.stack([left, right], axis=1)


def _ffmpeg_decode(path: Path) -> tuple[np.ndarray, int]:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        proc = subprocess.run(
            ["ffmpeg", "-y", "-i", str(path),
             "-ac", "2", "-ar", str(TARGET_SAMPLE_RATE),
             "-f", "wav", str(tmp_path)],
            capture_output=True, text=True,
        )
        if proc.returncode != 0:
            last = proc.stderr.strip().splitlines()[-1] if proc.stderr else "ffmpeg failed"
            raise UnsupportedFormat(last)
        data, sr = sf.read(str(tmp_path), dtype="float32", always_2d=True)
        return data, sr
    finally:
        if tmp_path.exists():
            tmp_path.unlink()
