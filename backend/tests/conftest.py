import subprocess
from pathlib import Path
import numpy as np
import soundfile as sf
import pytest

SR = 44_100
FIXTURES = Path(__file__).parent / "fixtures"
FIXTURES.mkdir(exist_ok=True)


def _click_track(bpm: float, duration_s: float, sr: int = SR) -> np.ndarray:
    n_samples = int(duration_s * sr)
    samples_per_beat = int(sr * 60 / bpm)
    audio = np.zeros((n_samples, 2), dtype=np.float32)
    click = np.hanning(int(sr * 0.02)).astype(np.float32) * 0.8
    for i in range(0, n_samples - len(click), samples_per_beat):
        audio[i:i + len(click), 0] += click
        audio[i:i + len(click), 1] += click
    return audio


@pytest.fixture(scope="session")
def click_120_wav() -> Path:
    path = FIXTURES / "click_120.wav"
    if not path.exists():
        sf.write(path, _click_track(120, 30), SR)
    return path


@pytest.fixture(scope="session")
def click_128_wav() -> Path:
    path = FIXTURES / "click_128.wav"
    if not path.exists():
        sf.write(path, _click_track(128, 30), SR)
    return path


@pytest.fixture(scope="session")
def click_90_wav() -> Path:
    path = FIXTURES / "click_90.wav"
    if not path.exists():
        sf.write(path, _click_track(90, 30), SR)
    return path


@pytest.fixture(scope="session")
def click_174_wav() -> Path:
    path = FIXTURES / "click_174.wav"
    if not path.exists():
        sf.write(path, _click_track(174, 30), SR)
    return path


@pytest.fixture(scope="session")
def click_120_short_wav() -> Path:
    """45 s click - below the 60 s threshold to trigger `short_track` warning."""
    path = FIXTURES / "click_120_short.wav"
    if not path.exists():
        sf.write(path, _click_track(120, 45), SR)
    return path


def _convert(src: Path, dst: Path) -> Path:
    if dst.exists():
        return dst
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(src), str(dst)],
        check=True, capture_output=True,
    )
    return dst


@pytest.fixture(scope="session")
def click_120_mp3(click_120_wav) -> Path:
    return _convert(click_120_wav, FIXTURES / "click_120.mp3")


@pytest.fixture(scope="session")
def click_120_flac(click_120_wav) -> Path:
    return _convert(click_120_wav, FIXTURES / "click_120.flac")


@pytest.fixture(scope="session")
def click_120_m4a(click_120_wav) -> Path:
    return _convert(click_120_wav, FIXTURES / "click_120.m4a")


@pytest.fixture(scope="session")
def silent_40s_wav() -> Path:
    path = FIXTURES / "silent_40s.wav"
    if not path.exists():
        sf.write(path, np.zeros((SR * 40, 2), dtype=np.float32), SR)
    return path


@pytest.fixture(scope="session")
def a_minor_chord_wav() -> Path:
    """30 s sustained A minor chord (A3, C4, E4)."""
    path = FIXTURES / "a_minor_chord.wav"
    if not path.exists():
        n = SR * 30
        t = np.arange(n) / SR
        freqs = [220.0, 261.63, 329.63]
        sig = sum(np.sin(2 * np.pi * f * t) for f in freqs) / len(freqs)
        sig = (sig * 0.3).astype(np.float32)
        sf.write(path, np.stack([sig, sig], 1), SR)
    return path


@pytest.fixture(scope="session")
def tone_120_wav() -> Path:
    """30 s 120 BPM tone-burst track (440 Hz sine bursts) - different timbre from click_120,
    same BPM, for cross-source alignment tests."""
    path = FIXTURES / "tone_120.wav"
    if not path.exists():
        sr = SR
        bpm = 120
        duration_s = 30
        n_samples = int(duration_s * sr)
        samples_per_beat = int(sr * 60 / bpm)
        burst_len = int(sr * 0.05)  # 50 ms tone burst per beat
        t_burst = np.arange(burst_len) / sr
        burst = (np.sin(2 * np.pi * 440 * t_burst) * np.hanning(burst_len)).astype(np.float32) * 0.6
        audio = np.zeros((n_samples, 2), dtype=np.float32)
        for i in range(0, n_samples - burst_len, samples_per_beat):
            audio[i:i + burst_len, 0] += burst
            audio[i:i + burst_len, 1] += burst
        sf.write(path, audio, sr)
    return path
