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
