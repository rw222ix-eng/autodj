from dataclasses import dataclass, field
import numpy as np
import librosa
from scipy.signal import find_peaks

from .audio_io import AudioBuffer
from .config import TARGET_SAMPLE_RATE


class InsufficientContent(Exception):
    pass


@dataclass
class TrackFeatures:
    bpm: float
    bpm_confidence: float
    beat_times: np.ndarray
    downbeats: np.ndarray
    key: str = ""
    rms_envelope: np.ndarray = field(default_factory=lambda: np.zeros(0))
    intro_window: tuple[float, float] = (0.0, 0.0)
    outro_window: tuple[float, float] = (0.0, 0.0)
    duration_s: float = 0.0


def _mono(samples: np.ndarray) -> np.ndarray:
    return samples.mean(axis=1) if samples.ndim == 2 else samples


def _bpm_confidence(onset_env: np.ndarray, sr: int, bpm: float) -> float:
    ac = librosa.autocorrelate(onset_env, max_size=len(onset_env))
    if ac[0] == 0:
        return 0.0
    hop = 512
    lag = int(round(sr * 60 / bpm / hop))
    if lag <= 0 or lag >= len(ac):
        return 0.0
    return float(np.clip(ac[lag] / ac[0], 0.0, 1.0))


def _as_scalar(x) -> float:
    if isinstance(x, np.ndarray):
        return float(x.item() if x.size == 1 else x.flat[0])
    return float(x)


def analyze(buf: AudioBuffer) -> TrackFeatures:
    mono = _mono(buf.samples)
    sr = buf.sr
    duration_s = len(mono) / sr
    if duration_s < 1.0:
        raise InsufficientContent("audio too short to analyze")
    onset_env = librosa.onset.onset_strength(y=mono, sr=sr)
    bpm_raw, beat_frames = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)
    bpm = _as_scalar(bpm_raw)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    if len(beat_times) < 4 or bpm <= 0:
        raise InsufficientContent("not enough beats detected")
    bpm = _refine_bpm(mono, sr, bpm)
    confidence = _bpm_confidence(onset_env, sr, bpm)
    downbeats = _pick_downbeats(onset_env, sr, beat_times)
    rms_env = _rms_envelope(mono, sr)
    if _max_silent_gap_s(rms_env, window_s=0.1) > 30:
        raise InsufficientContent("silence gap longer than 30 s")
    intro_w, outro_w = _intro_outro_windows(downbeats, bpm=bpm, duration_s=duration_s)
    key = _detect_key(mono, sr)
    return TrackFeatures(
        bpm=bpm,
        bpm_confidence=confidence,
        beat_times=beat_times,
        downbeats=downbeats,
        key=key,
        rms_envelope=rms_env,
        intro_window=intro_w,
        outro_window=outro_w,
        duration_s=duration_s,
    )


def _refine_bpm(mono: np.ndarray, sr: int, coarse_bpm: float) -> float:
    """Refine the librosa BPM estimate using sample-level peak detection.

    librosa's frame-rate (~86 Hz at default hop=512) limits tempo resolution to
    roughly ~2 BPM near 170. We snap to a refined BPM only when it agrees with
    the coarse estimate within +/- 5%, otherwise we keep librosa's value.
    """
    abs_mono = np.abs(mono)
    if abs_mono.max() <= 0:
        return coarse_bpm
    min_period_s = 60.0 / 220.0  # cap at 220 BPM
    peaks, _ = find_peaks(
        abs_mono,
        height=0.3 * abs_mono.max(),
        distance=max(1, int(sr * min_period_s)),
    )
    if len(peaks) < 4:
        return coarse_bpm
    ibis = np.diff(peaks).astype(np.float64) / sr
    median_ibi = float(np.median(ibis))
    if median_ibi <= 0:
        return coarse_bpm
    # discard outliers
    mask = (ibis > 0.7 * median_ibi) & (ibis < 1.3 * median_ibi)
    if mask.sum() < 3:
        return coarse_bpm
    refined = 60.0 / float(np.median(ibis[mask]))
    if abs(refined - coarse_bpm) / coarse_bpm > 0.05:
        return coarse_bpm
    return refined


def _pick_downbeats(onset_env: np.ndarray, sr: int, beat_times: np.ndarray) -> np.ndarray:
    strengths = []
    for t in beat_times[:4]:
        idx = int(librosa.time_to_frames(t, sr=sr))
        idx = max(0, min(idx, len(onset_env) - 1))
        strengths.append(onset_env[idx])
    first = int(np.argmax(strengths))
    return beat_times[first::4]


def _rms_envelope(mono: np.ndarray, sr: int, window_s: float = 0.1) -> np.ndarray:
    hop = int(sr * window_s)
    if hop <= 0:
        return np.zeros(0)
    n = len(mono) // hop
    out = np.empty(n, dtype=np.float32)
    for i in range(n):
        chunk = mono[i * hop:(i + 1) * hop]
        out[i] = float(np.sqrt(np.mean(chunk ** 2)) if len(chunk) else 0.0)
    return out


def _intro_outro_windows(
    downbeats: np.ndarray, bpm: float, duration_s: float, bars: int = 32
) -> tuple[tuple[float, float], tuple[float, float]]:
    if len(downbeats) < 2:
        return (0.0, duration_s / 2), (duration_s / 2, duration_s)
    bar_s = 60 / bpm * 4
    intro_start = float(downbeats[0])
    outro_end = float(downbeats[-1])
    # Desired window length, capped so intro and outro do not overlap.
    span = outro_end - intro_start
    if span <= 0:
        return (0.0, duration_s / 2), (duration_s / 2, duration_s)
    window_s = min(bars * bar_s, span / 2)
    intro_end = intro_start + window_s
    outro_start = outro_end - window_s
    return (intro_start, intro_end), (outro_start, outro_end)


_KRUMHANSL_MAJOR = np.array([
    6.35, 2.23, 3.48, 2.33, 4.38, 4.09,
    2.52, 5.19, 2.39, 3.66, 2.29, 2.88,
])
_KRUMHANSL_MINOR = np.array([
    6.33, 2.68, 3.52, 5.38, 2.60, 3.53,
    2.54, 4.75, 3.98, 2.69, 3.34, 3.17,
])
_PITCH_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def _detect_key(mono: np.ndarray, sr: int) -> str:
    chroma = librosa.feature.chroma_stft(y=mono, sr=sr).mean(axis=1)
    if chroma.sum() == 0:
        return ""
    chroma = chroma / chroma.sum()
    best_score = -np.inf
    best_label = ""
    for shift in range(12):
        rotated = np.roll(chroma, -shift)
        maj = float(np.corrcoef(rotated, _KRUMHANSL_MAJOR)[0, 1])
        minr = float(np.corrcoef(rotated, _KRUMHANSL_MINOR)[0, 1])
        if maj > best_score:
            best_score = maj
            best_label = f"{_PITCH_NAMES[shift]} major"
        if minr > best_score:
            best_score = minr
            best_label = f"{_PITCH_NAMES[shift]} minor"
    return best_label


def _max_silent_gap_s(rms_env: np.ndarray, window_s: float, threshold: float = 1e-4) -> float:
    longest = current = 0
    for v in rms_env:
        if v < threshold:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest * window_s
