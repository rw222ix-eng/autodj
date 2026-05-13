# AutoDJ Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build AutoDJ — a local Windows tool that mixes two audio files in any common format into a single output with a natural-sounding, beat-matched transition (crossfade or cut), optional effect (filter sweep / echo / reverb / backspin) and optional bridge sample.

**Architecture:** FastAPI backend (Python 3.11+) with five sequential audio modules (`audio_io` → `analysis` → `align` → `transition` → `render`) exposed over three HTTP endpoints, plus a single-screen Vite+React frontend on `localhost:5173`. Everything runs locally; no auth, no persistence between sessions. All decisions are driven by the spec at [docs/specs/2026-05-13-autodj-design.md](../specs/2026-05-13-autodj-design.md).

**Tech Stack:** Python 3.11+, FastAPI, Uvicorn, librosa, numpy, scipy, soundfile, python-multipart, ffmpeg (binary). Frontend: Vite, React, TypeScript, plain CSS, wavesurfer.js (optional). Tooling: pytest, ruff, mypy.

**File Structure:**
```
E:\AutoDJ\
├── backend\app\           # audio_io.py analysis.py align.py transition.py render.py api.py config.py
├── backend\tests\         # one test file per module + test_e2e.py + fixtures/
├── frontend\src\          # App.tsx, components/{UploadTile,OptionsPanel,OutputPanel}.tsx, api.ts, types.ts
├── samples\               # drumroll.wav sweep_up.wav vinyl_stop.wav airhorn.wav dj_tag.wav
├── workdir\               # gitignored per-job scratch
├── scripts\               # setup.ps1, run.ps1
└── docs\specs\, docs\plans\
```

**Conventions used throughout this plan:**
- Every command block that runs `pytest`, `ruff`, `mypy`, `pip`, `python`, `uvicorn` begins with `Set-Location E:\AutoDJ\backend` (or is already there from the previous step). Every command block that runs `npm` begins with `Set-Location E:\AutoDJ\frontend`. Never rely on implicit cwd between tasks — a fresh agent may pick up at any step.
- Every task ends with a commit. Use Conventional Commits prefixes (`feat:`, `test:`, `chore:`, `fix:`, `docs:`).
- Apply @superpowers:test-driven-development for every code change: failing test first, then implementation.
- Apply @superpowers:verification-before-completion before claiming a task done — show the passing test output.

---

## Chunk 1: Project scaffolding, tooling, and `audio_io`

### Task 1.1: Initialize repository and directory skeleton

**Files:**
- Create: `E:\AutoDJ\.gitignore`
- Create: `E:\AutoDJ\README.md`
- Create empty directories: `backend\app\`, `backend\tests\fixtures\`, `frontend\`, `samples\`, `workdir\`, `scripts\`.

- [ ] **Step 1: Initialize git and create the directory tree**

Run (PowerShell, from `E:\AutoDJ\`):
```powershell
git init
New-Item -ItemType Directory -Force -Path backend\app, backend\tests\fixtures, frontend, samples, workdir, scripts | Out-Null
```
Expected: `Initialized empty Git repository in E:/AutoDJ/.git/`

- [ ] **Step 2: Write `.gitignore`**

Create `E:\AutoDJ\.gitignore`:
```
# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
.pytest_cache/
.mypy_cache/
.ruff_cache/

# Node
node_modules/
dist/
.vite/

# AutoDJ runtime
workdir/
*.log

# OS / editor
.DS_Store
Thumbs.db
.idea/
.vscode/
```

- [ ] **Step 3: Write a minimal `README.md`**

Create `E:\AutoDJ\README.md`:
```markdown
# AutoDJ

Local tool that mixes two audio files into one with a natural-sounding transition.

See `docs/specs/2026-05-13-autodj-design.md` for the design and `docs/plans/2026-05-13-autodj-implementation.md` for the build plan.

## Quick start
```powershell
.\scripts\setup.ps1
.\scripts\run.ps1
```
Then open <http://localhost:5173>.
```

- [ ] **Step 4: Commit**
```powershell
git add .gitignore README.md
git commit -m "chore: initial repo scaffold"
```

---

### Task 1.2: Backend project setup (pyproject, venv, dependencies)

**Files:**
- Create: `E:\AutoDJ\backend\pyproject.toml`
- Create: `E:\AutoDJ\backend\app\__init__.py`
- Create: `E:\AutoDJ\backend\tests\__init__.py`
- Create: `E:\AutoDJ\backend\app\config.py`

- [ ] **Step 1: Create `pyproject.toml`**

Create `E:\AutoDJ\backend\pyproject.toml`:
```toml
[project]
name = "autodj-backend"
version = "0.1.0"
description = "AutoDJ backend — beat-matched two-track mixer."
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.110",
    "uvicorn[standard]>=0.27",
    "librosa>=0.10.1",
    "numpy>=1.26",
    "scipy>=1.11",
    "soundfile>=0.12",
    "python-multipart>=0.0.9",
    "pydantic>=2.6",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "httpx>=0.27",
    "ruff>=0.3",
    "mypy>=1.8",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra -q"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.mypy]
python_version = "3.11"
strict = false
ignore_missing_imports = true
```

- [ ] **Step 2: Create venv and install dependencies**

Run:
```powershell
Set-Location E:\AutoDJ\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```
Expected: `Successfully installed fastapi-... librosa-... pytest-... ...`

- [ ] **Step 3: Verify ffmpeg is on PATH**

Run:
```powershell
ffmpeg -version
```
Expected: `ffmpeg version N.x ...`. If not present, install via `winget install ffmpeg` and re-open the shell.

- [ ] **Step 4: Create empty package and config files**

Create `E:\AutoDJ\backend\app\__init__.py` (empty).
Create `E:\AutoDJ\backend\tests\__init__.py` (empty).
Create `E:\AutoDJ\backend\app\config.py`:
```python
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_ROOT.parent
WORKDIR = PROJECT_ROOT / "workdir"
SAMPLES_DIR = PROJECT_ROOT / "samples"

TARGET_SAMPLE_RATE = 44_100
TARGET_CHANNELS = 2
INPUT_PEAK_DBFS = -1.0
OUTPUT_PEAK_DBFS = -0.5
MAX_INPUT_DURATION_S = 15 * 60
MIN_BPM_CONFIDENCE = 0.5
BPM_BEAT_MATCH_TOLERANCE = 0.08
MIN_TRACK_DURATION_S = 60
SILENCE_GAP_LIMIT_S = 30
```

- [ ] **Step 5: Smoke-test pytest discovery**

Run:
```powershell
Set-Location E:\AutoDJ\backend
pytest -q
```
Expected: `no tests ran` (no failures).

- [ ] **Step 6: Commit**
```powershell
git add backend/
git commit -m "chore: backend python project scaffold"
```

---

### Task 1.3: `audio_io.load` — TDD on WAV first

**Files:**
- Create: `E:\AutoDJ\backend\app\audio_io.py`
- Create: `E:\AutoDJ\backend\tests\test_audio_io.py`
- Create: `E:\AutoDJ\backend\tests\conftest.py`

- [ ] **Step 1: Add a fixture generator for synthetic click tracks**

Create `E:\AutoDJ\backend\tests\conftest.py`:
```python
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
```

- [ ] **Step 2: Write the failing test**

Create `E:\AutoDJ\backend\tests\test_audio_io.py`:
```python
import numpy as np
from app.audio_io import load


def test_load_wav_returns_normalized_stereo_44k(click_120_wav):
    buf = load(click_120_wav)
    assert buf.sr == 44_100
    assert buf.channels == 2
    assert buf.samples.dtype == np.float32
    assert buf.samples.ndim == 2
    assert buf.samples.shape[1] == 2
    peak = float(np.max(np.abs(buf.samples)))
    # peak-normalized to -1 dBFS = 10**(-1/20) ≈ 0.8913
    assert 0.88 < peak <= 0.90
```

- [ ] **Step 3: Run the test to verify it fails**

Run:
```powershell
pytest tests/test_audio_io.py::test_load_wav_returns_normalized_stereo_44k -v
```
Expected: `ImportError: cannot import name 'load' from 'app.audio_io'` (or `ModuleNotFoundError`).

- [ ] **Step 4: Implement `audio_io.load` for WAV via soundfile**

Create `E:\AutoDJ\backend\app\audio_io.py`:
```python
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
    samples: np.ndarray  # float32 (n_samples, 2)
    sr: int
    channels: int
    scale_applied: float  # the factor used for peak-normalization


def _peak_normalize(samples: np.ndarray, target_dbfs: float) -> tuple[np.ndarray, float]:
    peak = float(np.max(np.abs(samples))) or 1.0
    target_peak = 10 ** (target_dbfs / 20)
    scale = target_peak / peak
    return samples * scale, scale


def load(path: Path) -> AudioBuffer:
    path = Path(path)
    try:
        data, sr = sf.read(str(path), dtype="float32", always_2d=True)
    except Exception as exc:  # soundfile can't decode it — fall through to ffmpeg
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
            [
                "ffmpeg", "-y", "-i", str(path),
                "-ac", "2", "-ar", str(TARGET_SAMPLE_RATE),
                "-f", "wav", str(tmp_path),
            ],
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
```

- [ ] **Step 5: Run the test to verify it passes**

Run:
```powershell
pytest tests/test_audio_io.py::test_load_wav_returns_normalized_stereo_44k -v
```
Expected: `1 passed`.

- [ ] **Step 6: Commit**
```powershell
git add backend/app/audio_io.py backend/app/config.py backend/tests/
git commit -m "feat(audio_io): load WAV files as normalized stereo float32"
```

---

### Task 1.4: `audio_io.load` — MP3 and FLAC via ffmpeg fallback

**Files:**
- Modify: `E:\AutoDJ\backend\tests\conftest.py` (add MP3 and FLAC fixtures via ffmpeg conversion).
- Modify: `E:\AutoDJ\backend\tests\test_audio_io.py`.

- [ ] **Step 1: Add MP3/FLAC fixture generation to `conftest.py`**

Append to `E:\AutoDJ\backend\tests\conftest.py`:
```python
import subprocess


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
```

- [ ] **Step 2: Write the failing test**

Append to `E:\AutoDJ\backend\tests\test_audio_io.py`:
```python
import pytest
from app.audio_io import load, UnsupportedFormat


@pytest.mark.parametrize("fixture_name", ["click_120_mp3", "click_120_flac", "click_120_m4a"])
def test_load_handles_compressed_formats(request, fixture_name):
    path = request.getfixturevalue(fixture_name)
    buf = load(path)
    assert buf.sr == 44_100
    assert buf.channels == 2
    assert buf.samples.shape[1] == 2
    assert buf.samples.dtype.kind == "f"


def test_load_raises_on_unsupported_format(tmp_path):
    bad = tmp_path / "garbage.bin"
    bad.write_bytes(b"this is not audio")
    with pytest.raises(UnsupportedFormat):
        load(bad)
```

- [ ] **Step 3: Run the tests to verify the MP3/FLAC pass and the bad-file fails as expected**

Run:
```powershell
pytest tests/test_audio_io.py -v
```
Expected: 5 passed (1 WAV + 3 compressed + 1 unsupported).

- [ ] **Step 4: Commit**
```powershell
git add backend/tests/
git commit -m "test(audio_io): cover MP3/FLAC/M4A and unsupported-format error"
```

---

### Task 1.5: `audio_io.save_wav` and `audio_io.save_mp3`

**Files:**
- Modify: `E:\AutoDJ\backend\app\audio_io.py`.
- Modify: `E:\AutoDJ\backend\tests\test_audio_io.py`.

- [ ] **Step 1: Write the failing tests**

Append to `E:\AutoDJ\backend\tests\test_audio_io.py`:
```python
import numpy as np
from app.audio_io import save_wav, save_mp3, load


def test_save_wav_roundtrip(tmp_path, click_120_wav):
    buf = load(click_120_wav)
    out = tmp_path / "out.wav"
    save_wav(buf, out)
    reloaded = load(out)
    # After two normalization passes the absolute values won't match, but shape and sr must.
    assert reloaded.sr == buf.sr
    assert reloaded.samples.shape == buf.samples.shape


def test_save_mp3_produces_decodable_file(tmp_path, click_120_wav):
    buf = load(click_120_wav)
    out = tmp_path / "out.mp3"
    save_mp3(buf, out)
    assert out.exists()
    reloaded = load(out)
    # MP3 encoding adds short padding; allow ±50 ms (~2205 samples).
    diff = abs(reloaded.samples.shape[0] - buf.samples.shape[0])
    assert diff < 2205, f"length differs by {diff} samples"
```

- [ ] **Step 2: Run the tests to verify they fail (functions don't exist yet)**

Run:
```powershell
pytest tests/test_audio_io.py::test_save_wav_roundtrip -v
```
Expected: `ImportError: cannot import name 'save_wav'`.

- [ ] **Step 3: Implement the save functions**

Append to `E:\AutoDJ\backend\app\audio_io.py`:
```python
def save_wav(buf: "AudioBuffer", path: Path) -> None:
    path = Path(path)
    sf.write(str(path), buf.samples, buf.sr, subtype="PCM_16")


def save_mp3(buf: "AudioBuffer", path: Path, bitrate: str = "320k") -> None:
    path = Path(path)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        sf.write(str(tmp_path), buf.samples, buf.sr, subtype="PCM_16")
        proc = subprocess.run(
            ["ffmpeg", "-y", "-i", str(tmp_path), "-b:a", bitrate, str(path)],
            capture_output=True, text=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip().splitlines()[-1])
    finally:
        if tmp_path.exists():
            tmp_path.unlink()
```

- [ ] **Step 4: Run all `audio_io` tests**

Run:
```powershell
pytest tests/test_audio_io.py -v
```
Expected: 7 passed.

- [ ] **Step 5: Commit**
```powershell
git add backend/app/audio_io.py backend/tests/test_audio_io.py
git commit -m "feat(audio_io): save_wav and save_mp3 with ffmpeg encoding"
```

---

## Chunk 2: `analysis` module

### Task 2.1: BPM and beat detection

**Files:**
- Create: `E:\AutoDJ\backend\app\analysis.py`
- Create: `E:\AutoDJ\backend\tests\test_analysis.py`

- [ ] **Step 1: Write the failing test**

Create `E:\AutoDJ\backend\tests\test_analysis.py`:
```python
import pytest
from app.audio_io import load
from app.analysis import analyze


@pytest.mark.parametrize("fixture, expected_bpm", [
    ("click_90_wav", 90),
    ("click_120_wav", 120),
    ("click_128_wav", 128),
    ("click_174_wav", 174),
])
def test_bpm_detection_within_half_bpm(request, fixture, expected_bpm):
    path = request.getfixturevalue(fixture)
    buf = load(path)
    features = analyze(buf)
    assert abs(features.bpm - expected_bpm) < 0.5, (
        f"detected {features.bpm}, expected {expected_bpm}"
    )
    assert features.bpm_confidence >= 0.7
    # At least one beat per second on a 30-second click track is the floor.
    assert len(features.beat_times) >= 25
```

- [ ] **Step 2: Run the test to verify it fails**

Run:
```powershell
pytest tests/test_analysis.py -v
```
Expected: `ModuleNotFoundError: No module named 'app.analysis'`.

- [ ] **Step 3: Implement BPM + beats + confidence**

Create `E:\AutoDJ\backend\app\analysis.py`:
```python
from dataclasses import dataclass, field
import numpy as np
import librosa

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


def _bpm_confidence(mono: np.ndarray, sr: int, bpm: float) -> float:
    onset_env = librosa.onset.onset_strength(y=mono, sr=sr)
    ac = librosa.autocorrelate(onset_env, max_size=len(onset_env))
    if ac[0] == 0:
        return 0.0
    # hop default in onset_strength is 512 samples
    hop = 512
    lag = int(round(sr * 60 / bpm / hop))
    if lag <= 0 or lag >= len(ac):
        return 0.0
    return float(np.clip(ac[lag] / ac[0], 0.0, 1.0))


def analyze(buf: AudioBuffer) -> TrackFeatures:
    mono = _mono(buf.samples)
    sr = buf.sr
    duration_s = len(mono) / sr
    if duration_s < 1.0:
        raise InsufficientContent("audio too short to analyze")
    bpm, beat_frames = librosa.beat.beat_track(y=mono, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    if len(beat_times) < 4:
        raise InsufficientContent("not enough beats detected")
    confidence = _bpm_confidence(mono, sr, float(bpm))
    downbeats = _pick_downbeats(mono, sr, beat_times)
    return TrackFeatures(
        bpm=float(bpm),
        bpm_confidence=confidence,
        beat_times=beat_times,
        downbeats=downbeats,
        duration_s=duration_s,
    )


def _pick_downbeats(mono: np.ndarray, sr: int, beat_times: np.ndarray) -> np.ndarray:
    onset_env = librosa.onset.onset_strength(y=mono, sr=sr)
    strengths = []
    for t in beat_times[:4]:
        idx = int(librosa.time_to_frames(t, sr=sr))
        idx = max(0, min(idx, len(onset_env) - 1))
        strengths.append(onset_env[idx])
    first = int(np.argmax(strengths))
    return beat_times[first::4]
```

- [ ] **Step 4: Run the test to verify it passes**

Run:
```powershell
pytest tests/test_analysis.py -v
```
Expected: 4 passed.

- [ ] **Step 5: Commit**
```powershell
git add backend/app/analysis.py backend/tests/test_analysis.py
git commit -m "feat(analysis): BPM detection, beats, downbeats, confidence proxy"
```

---

### Task 2.2: RMS envelope + intro/outro windows

**Files:**
- Modify: `E:\AutoDJ\backend\app\analysis.py`.
- Modify: `E:\AutoDJ\backend\tests\test_analysis.py`.

- [ ] **Step 1: Write the failing test**

Append to `E:\AutoDJ\backend\tests\test_analysis.py`:
```python
def test_rms_envelope_and_windows(click_120_wav):
    buf = load(click_120_wav)
    f = analyze(buf)
    assert f.rms_envelope.ndim == 1
    # 100 ms windows over 30 s → ~300 samples
    assert 270 <= len(f.rms_envelope) <= 330
    intro_start, intro_end = f.intro_window
    outro_start, outro_end = f.outro_window
    assert 0 <= intro_start < intro_end <= f.duration_s
    assert 0 <= outro_start < outro_end <= f.duration_s
    assert intro_end <= outro_start  # they don't overlap on a 30 s track
```

- [ ] **Step 2: Verify the test fails**

Run:
```powershell
pytest tests/test_analysis.py::test_rms_envelope_and_windows -v
```
Expected: `AttributeError` on `rms_envelope` empty or windows still default.

- [ ] **Step 3: Implement RMS + window helpers**

Append helpers and wire them into `analyze` in `E:\AutoDJ\backend\app\analysis.py`. Replace the `return TrackFeatures(...)` block in `analyze` with:
```python
    rms_env = _rms_envelope(mono, sr)
    intro_w, outro_w = _intro_outro_windows(downbeats, bpm=float(bpm), duration_s=duration_s)
    return TrackFeatures(
        bpm=float(bpm),
        bpm_confidence=confidence,
        beat_times=beat_times,
        downbeats=downbeats,
        rms_envelope=rms_env,
        intro_window=intro_w,
        outro_window=outro_w,
        duration_s=duration_s,
    )
```
Add helpers at the bottom of the file:
```python
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
    intro_end = min(intro_start + bars * bar_s, duration_s)
    outro_end = float(downbeats[-1])
    outro_start = max(outro_end - bars * bar_s, intro_end)
    return (intro_start, intro_end), (outro_start, outro_end)
```

- [ ] **Step 4: Run the test**

Run:
```powershell
pytest tests/test_analysis.py -v
```
Expected: 5 passed.

- [ ] **Step 5: Commit**
```powershell
git add backend/app/analysis.py backend/tests/test_analysis.py
git commit -m "feat(analysis): RMS envelope and intro/outro window selection"
```

---

### Task 2.3: Key detection (Krumhansl-Schmuckler)

**Files:**
- Modify: `E:\AutoDJ\backend\app\analysis.py`
- Modify: `E:\AutoDJ\backend\tests\test_analysis.py`
- Modify: `E:\AutoDJ\backend\tests\conftest.py`

- [ ] **Step 1: Add an A-minor fixture for testing**

Append to `conftest.py`:
```python
@pytest.fixture(scope="session")
def a_minor_chord_wav() -> Path:
    """30 s sustained A minor chord (A3, C4, E4) — unambiguous key for testing."""
    path = FIXTURES / "a_minor_chord.wav"
    if not path.exists():
        n = SR * 30
        t = np.arange(n) / SR
        freqs = [220.0, 261.63, 329.63]
        sig = sum(np.sin(2 * np.pi * f * t) for f in freqs) / len(freqs)
        sig = (sig * 0.3).astype(np.float32)
        sf.write(path, np.stack([sig, sig], 1), SR)
    return path
```

- [ ] **Step 2: Write the failing test**

Append to `test_analysis.py`:
```python
def test_key_detection_a_minor(a_minor_chord_wav):
    f = analyze(load(a_minor_chord_wav))
    assert f.key.lower() in {"a minor", "c major"}  # relative-key ambiguity is acceptable
```

- [ ] **Step 3: Run test, expect failure**

Run:
```powershell
pytest tests/test_analysis.py::test_key_detection_a_minor -v
```
Expected: `assert '' in {'a minor', 'c major'}` failure.

- [ ] **Step 4: Implement Krumhansl-Schmuckler in `analysis.py`**

Add to `E:\AutoDJ\backend\app\analysis.py`:
```python
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
            best_score = maj; best_label = f"{_PITCH_NAMES[shift]} major"
        if minr > best_score:
            best_score = minr; best_label = f"{_PITCH_NAMES[shift]} minor"
    return best_label
```

In `analyze()`, after computing `rms_env`, before the return, set:
```python
    key = _detect_key(mono, sr)
```
And pass `key=key` into `TrackFeatures(...)`.

- [ ] **Step 5: Run test, expect pass**

```powershell
pytest tests/test_analysis.py -v
```
Expected: 7 passed (6 pre-existing + key test).

- [ ] **Step 6: Commit**
```powershell
git add backend/app/analysis.py backend/tests/
git commit -m "feat(analysis): Krumhansl-Schmuckler key detection"
```

---

### Task 2.4: `InsufficientContent` on long silence

**Files:**
- Modify: `E:\AutoDJ\backend\app\analysis.py`.
- Modify: `E:\AutoDJ\backend\tests\test_analysis.py`.
- Modify: `E:\AutoDJ\backend\tests\conftest.py`.

- [ ] **Step 1: Add a silent fixture and the failing test**

Append to `E:\AutoDJ\backend\tests\conftest.py`:
```python
@pytest.fixture(scope="session")
def silent_40s_wav() -> Path:
    path = FIXTURES / "silent_40s.wav"
    if not path.exists():
        sf.write(path, np.zeros((SR * 40, 2), dtype=np.float32), SR)
    return path
```

Append to `E:\AutoDJ\backend\tests\test_analysis.py`:
```python
from app.analysis import InsufficientContent


def test_long_silence_raises(silent_40s_wav):
    buf = load(silent_40s_wav)
    with pytest.raises(InsufficientContent):
        analyze(buf)
```

- [ ] **Step 2: Implement silence detection in `analyze`**

In `E:\AutoDJ\backend\app\analysis.py`, after computing `rms_env` and before the `return`, add:
```python
    if _max_silent_gap_s(rms_env, window_s=0.1) > 30:
        raise InsufficientContent("silence gap longer than 30 s")
```
Add helper:
```python
def _max_silent_gap_s(rms_env: np.ndarray, window_s: float, threshold: float = 1e-4) -> float:
    longest = current = 0
    for v in rms_env:
        if v < threshold:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest * window_s
```

- [ ] **Step 3: Run tests**

Run:
```powershell
pytest tests/test_analysis.py -v
```
Expected: 6 passed.

- [ ] **Step 4: Commit**
```powershell
git add backend/app/analysis.py backend/tests/
git commit -m "feat(analysis): raise InsufficientContent on >30s silence"
```

---

## Chunk 3: `align` module

### Task 3.1: Choose transition points on same-BPM tracks

**Files:**
- Create: `E:\AutoDJ\backend\app\align.py`
- Create: `E:\AutoDJ\backend\tests\test_align.py`

- [ ] **Step 1: Write the failing test**

Create `E:\AutoDJ\backend\tests\test_align.py`:
```python
from app.audio_io import load
from app.analysis import analyze
from app.align import plan


def test_same_bpm_alignment(click_120_wav):
    a = analyze(load(click_120_wav))
    b = analyze(load(click_120_wav))
    p = plan(a, b, bars=4)
    assert p.beat_match is True
    assert p.effective_bars == 4
    assert p.a_end_sample > p.a_start_sample
    assert p.b_end_sample > p.b_start_sample
    bar_samples = int(44_100 * 60 / a.bpm * 4 * 4)  # 4 bars at 120 BPM
    # Allow ±1 beat of slack
    beat_samples = int(44_100 * 60 / a.bpm)
    assert abs((p.a_end_sample - p.a_start_sample) - bar_samples) <= beat_samples
```

- [ ] **Step 2: Run the test (expect failure)**

Run:
```powershell
pytest tests/test_align.py -v
```
Expected: `ModuleNotFoundError: No module named 'app.align'`.

- [ ] **Step 3: Implement `plan` for the same-BPM case**

Create `E:\AutoDJ\backend\app\align.py`:
```python
from dataclasses import dataclass
from typing import Optional
import numpy as np
import librosa

from .analysis import TrackFeatures
from .config import TARGET_SAMPLE_RATE, BPM_BEAT_MATCH_TOLERANCE


@dataclass
class AlignmentPlan:
    a_start_sample: int
    a_end_sample: int
    b_start_sample: int
    b_end_sample: int
    beat_match: bool
    effective_bars: int
    stretched_outro: Optional[np.ndarray] = None
    warning: Optional[str] = None  # e.g. "bars_reduced"


def _samples(t: float) -> int:
    return int(round(t * TARGET_SAMPLE_RATE))


def _bar_seconds(bpm: float) -> float:
    return 60 / bpm * 4


def plan(a: TrackFeatures, b: TrackFeatures, bars: int) -> AlignmentPlan:
    # Effective length and warning may be mutated by 3.2/3.3 logic below.
    effective_bars = bars
    warning: Optional[str] = None

    bar_s_a = _bar_seconds(a.bpm)
    bar_s_b = _bar_seconds(b.bpm)
    needed_a = effective_bars * bar_s_a
    needed_b = effective_bars * bar_s_b

    outro_start, outro_end = a.outro_window
    intro_start, intro_end = b.intro_window

    # A: latest downbeat in outro window with `needed_a` seconds remaining
    a_downbeats_in_outro = [d for d in a.downbeats if outro_start <= d <= outro_end - needed_a]
    if not a_downbeats_in_outro:
        a_downbeats_in_outro = [outro_start]
    a_start_s = max(a_downbeats_in_outro)

    # B: earliest downbeat in intro window with `needed_b` seconds forward
    b_downbeats_in_intro = [d for d in b.downbeats if intro_start <= d <= intro_end - needed_b]
    if not b_downbeats_in_intro:
        b_downbeats_in_intro = [intro_start]
    b_start_s = min(b_downbeats_in_intro)

    a_end_s = a_start_s + needed_a
    b_end_s = b_start_s + needed_b

    diff = abs(a.bpm - b.bpm) / b.bpm
    beat_match = diff <= BPM_BEAT_MATCH_TOLERANCE

    return AlignmentPlan(
        a_start_sample=_samples(a_start_s),
        a_end_sample=_samples(a_end_s),
        b_start_sample=_samples(b_start_s),
        b_end_sample=_samples(b_end_s),
        beat_match=beat_match,
        effective_bars=effective_bars,
        warning=warning,
    )
```

- [ ] **Step 4: Run the test (expect pass)**

Run:
```powershell
pytest tests/test_align.py -v
```
Expected: 1 passed.

- [ ] **Step 5: Commit**
```powershell
git add backend/app/align.py backend/tests/test_align.py
git commit -m "feat(align): basic transition-point selection for same-BPM tracks"
```

---

### Task 3.2: Time-stretch A's outro when BPMs are close

**Files:**
- Modify: `E:\AutoDJ\backend\app\align.py`.
- Modify: `E:\AutoDJ\backend\tests\test_align.py`.

- [ ] **Step 1: Write the failing test**

Append to `E:\AutoDJ\backend\tests\test_align.py`:
```python
def test_close_bpm_stretches_outro(click_120_wav, click_128_wav):
    a = analyze(load(click_120_wav))
    b = analyze(load(click_128_wav))
    p = plan(a, b, bars=4)
    assert p.beat_match is True
    assert p.stretched_outro is not None
    # 128 / 120 ≈ 1.0667 → stretched outro is ~6.7% shorter than the 4-bar window at A's BPM
    a_outro_samples = p.a_end_sample - p.a_start_sample
    ratio = len(p.stretched_outro) / a_outro_samples
    assert 0.90 < ratio < 0.99


def test_far_bpm_skips_stretch(click_90_wav, click_174_wav):
    a = analyze(load(click_90_wav))
    b = analyze(load(click_174_wav))
    p = plan(a, b, bars=4)
    assert p.beat_match is False
    assert p.stretched_outro is None
```

These tests don't yet provide the source audio to `plan`. To stretch we need access to A's samples for the outro region — update the API to take the source buffer.

- [ ] **Step 2: Refactor `plan` to accept the source buffer for A**

Change the `plan` signature in `E:\AutoDJ\backend\app\align.py` to:
```python
def plan(
    a: TrackFeatures, b: TrackFeatures, bars: int,
    a_buffer: Optional[np.ndarray] = None,
) -> AlignmentPlan:
    ...
```
`effective_bars` and `warning` are already initialized at the top of `plan()` from Task 3.1. After computing `beat_match`, if `beat_match` and `a.bpm != b.bpm` and `a_buffer is not None`:
```python
    stretched = None
    if beat_match and not np.isclose(a.bpm, b.bpm) and a_buffer is not None:
        outro_slice = a_buffer[_samples(a_start_s):_samples(a_end_s)]
        ratio = b.bpm / a.bpm  # >1 speeds up
        mono = outro_slice.mean(axis=1) if outro_slice.ndim == 2 else outro_slice
        stretched_mono = librosa.effects.time_stretch(mono.astype(np.float32), rate=ratio)
        # Per spec §4.3 step 3: re-detect beats in the stretched outro and trim/pad to
        # exactly effective_bars * 4 beats so the grid lines up with B at B's BPM.
        expected_beats = effective_bars * 4
        try:
            _, new_beat_frames = librosa.beat.beat_track(y=stretched_mono, sr=TARGET_SAMPLE_RATE)
            new_beats = librosa.frames_to_time(new_beat_frames, sr=TARGET_SAMPLE_RATE)
        except Exception:
            new_beats = np.array([])
        if len(new_beats) >= expected_beats:
            trim_end_s = float(new_beats[expected_beats - 1]) + 60 / b.bpm  # include the final beat's bar
            stretched_mono = stretched_mono[:_samples(trim_end_s)]
        elif len(new_beats) > 0:
            # Fewer beats than expected — shrink effective_bars to what's actually present.
            new_effective_bars = max(1, len(new_beats) // 4)
            if new_effective_bars < effective_bars:
                effective_bars = new_effective_bars
                warning = "bars_reduced"
                trim_end_s = float(new_beats[effective_bars * 4 - 1]) + 60 / b.bpm
                stretched_mono = stretched_mono[:_samples(trim_end_s)]
        # restore stereo by duplicating; v1 accepts the simplification (mono outro is acceptable for a short transition)
        stretched = np.stack([stretched_mono, stretched_mono], axis=1).astype(np.float32)
        # Update a_end_sample to match the trimmed stretched length so the transition region length is consistent.
        a_end_s = a_start_s + len(stretched_mono) / TARGET_SAMPLE_RATE
```
Pass `stretched` into the returned dataclass. Update existing same-BPM test if needed (no source buffer → `stretched_outro` stays None for the same-BPM case, which the existing test already asserts implicitly by not checking it).

- [ ] **Step 3: Update the new tests to pass the source buffer**

Change the new tests to:
```python
def test_close_bpm_stretches_outro(click_120_wav, click_128_wav):
    buf_a = load(click_120_wav)
    a = analyze(buf_a)
    b = analyze(load(click_128_wav))
    p = plan(a, b, bars=4, a_buffer=buf_a.samples)
    ...

def test_far_bpm_skips_stretch(click_90_wav, click_174_wav):
    buf_a = load(click_90_wav)
    a = analyze(buf_a)
    b = analyze(load(click_174_wav))
    p = plan(a, b, bars=4, a_buffer=buf_a.samples)
    ...
```

- [ ] **Step 4: Run all align tests**

Run:
```powershell
pytest tests/test_align.py -v
```
Expected: 3 passed.

- [ ] **Step 5: Commit**
```powershell
git add backend/app/align.py backend/tests/test_align.py
git commit -m "feat(align): time-stretch A's outro when BPMs are within 8%"
```

---

### Task 3.3: Shrink `effective_bars` when outro is too short

**Files:**
- Modify: `E:\AutoDJ\backend\app\align.py`.
- Modify: `E:\AutoDJ\backend\tests\test_align.py`.

- [ ] **Step 1: Write the failing test**

Append to `E:\AutoDJ\backend\tests\test_align.py`:
```python
import numpy as np
from app.analysis import TrackFeatures
from app.align import plan


def test_short_outro_shrinks_bars():
    bpm = 120
    sr = 44_100
    duration = 5.0  # only ~2.5 bars at 120 BPM
    beats = np.arange(0, duration, 60 / bpm)
    downbeats = beats[::4]
    a = TrackFeatures(
        bpm=bpm, bpm_confidence=0.9,
        beat_times=beats, downbeats=downbeats,
        rms_envelope=np.ones(50, dtype=np.float32),
        intro_window=(0.0, 1.0), outro_window=(0.0, duration),
        duration_s=duration,
    )
    b = a
    p = plan(a, b, bars=4)
    assert p.effective_bars < 4
    assert p.warning == "bars_reduced"
```

- [ ] **Step 2: Implement the shrink logic in `plan`**

In `E:\AutoDJ\backend\app\align.py`, reorder `plan()` so `outro_start/end` and `intro_start/end` are extracted **before** `needed_a`/`needed_b` are computed (currently the opposite — swap those two blocks). Then add the room-check between those two now-reordered blocks, after `bar_s_a`/`bar_s_b` and `outro_*`/`intro_*` are available but before `needed_*`:
```python
    outro_available_s = outro_end - outro_start
    intro_available_s = intro_end - intro_start
    max_bars_a = int(outro_available_s // bar_s_a)
    max_bars_b = int(intro_available_s // bar_s_b)
    cap = max(1, min(max_bars_a, max_bars_b))
    if cap < bars:
        effective_bars = cap
        warning = "bars_reduced"
    needed_a = effective_bars * bar_s_a
    needed_b = effective_bars * bar_s_b
```
`AlignmentPlan(...)` already receives `effective_bars` and `warning` from Task 3.1 — no return-shape change needed.

- [ ] **Step 3: Run tests**

Run:
```powershell
pytest tests/test_align.py -v
```
Expected: 4 passed.

- [ ] **Step 4: Commit**
```powershell
git add backend/app/align.py backend/tests/test_align.py
git commit -m "feat(align): shrink effective_bars when outro/intro too short"
```

---

## Chunk 4: `transition` module

### Task 4.1: Equal-power crossfade

**Files:**
- Create: `E:\AutoDJ\backend\app\transition.py`
- Create: `E:\AutoDJ\backend\tests\test_transition.py`

- [ ] **Step 1: Write the failing test**

Create `E:\AutoDJ\backend\tests\test_transition.py`:
```python
import numpy as np
from app.audio_io import load
from app.analysis import analyze
from app.align import plan
from app.transition import build, TransitionOptions
from app.config import OUTPUT_PEAK_DBFS


def _peak_dbfs(x: np.ndarray) -> float:
    peak = float(np.max(np.abs(x))) or 1e-9
    return 20 * np.log10(peak)


def test_crossfade_default(click_120_wav):
    buf_a = load(click_120_wav)
    buf_b = load(click_120_wav)
    a = analyze(buf_a)
    b = analyze(buf_b)
    p = plan(a, b, bars=4, a_buffer=buf_a.samples)
    options = TransitionOptions(type="crossfade", bars=4, effect="none", bridge="none")
    mixed = build(buf_a.samples, buf_b.samples, p, options)
    assert mixed.ndim == 2
    assert mixed.shape[1] == 2
    assert _peak_dbfs(mixed) <= OUTPUT_PEAK_DBFS + 0.05
    # expected duration ≈ a_end + (full B from b_start) - overlap
    overlap = p.a_end_sample - p.a_start_sample
    expected = p.a_end_sample + (buf_b.samples.shape[0] - p.b_start_sample) - overlap
    assert abs(mixed.shape[0] - expected) < 200  # ≤5 ms drift
```

- [ ] **Step 2: Run the test (expect failure)**

Run:
```powershell
pytest tests/test_transition.py -v
```
Expected: `ModuleNotFoundError`.

- [ ] **Step 3: Implement crossfade**

Create `E:\AutoDJ\backend\app\transition.py`:
```python
from dataclasses import dataclass
from typing import Literal
import numpy as np

from .align import AlignmentPlan
from .config import OUTPUT_PEAK_DBFS

TransitionType = Literal["crossfade", "cut"]
EffectType = Literal["none", "lowpass_sweep", "highpass_sweep", "echo_tail", "reverb_wash", "backspin"]
BridgeType = Literal["none", "drumroll", "sweep_up", "vinyl_stop", "airhorn", "dj_tag"]


@dataclass
class TransitionOptions:
    type: TransitionType = "crossfade"
    bars: int = 16
    effect: EffectType = "none"
    bridge: BridgeType = "none"


def _peak_normalize(x: np.ndarray, target_dbfs: float) -> np.ndarray:
    peak = float(np.max(np.abs(x))) or 1.0
    target = 10 ** (target_dbfs / 20)
    if peak <= target:
        return x
    return (x * (target / peak)).astype(np.float32)


def _equal_power(n: int) -> tuple[np.ndarray, np.ndarray]:
    t = np.linspace(0.0, np.pi / 2, n, dtype=np.float32)
    fade_out = np.cos(t) ** 2
    fade_in = np.sin(t) ** 2
    return fade_out, fade_in


def build(
    a_samples: np.ndarray,
    b_samples: np.ndarray,
    plan: AlignmentPlan,
    options: TransitionOptions,
) -> np.ndarray:
    pre_a = a_samples[:plan.a_start_sample]
    a_outro = a_samples[plan.a_start_sample:plan.a_end_sample]
    b_intro = b_samples[plan.b_start_sample:plan.b_end_sample]
    post_b = b_samples[plan.b_end_sample:]

    if plan.stretched_outro is not None:
        a_outro = plan.stretched_outro

    n = min(len(a_outro), len(b_intro))
    a_outro = a_outro[:n]
    b_intro = b_intro[:n]

    if options.type == "crossfade":
        fo, fi = _equal_power(n)
        mixed_region = a_outro * fo[:, None] + b_intro * fi[:, None]
    elif options.type == "cut":
        mixed_region = b_intro
    else:
        raise ValueError(f"unknown transition type: {options.type}")

    full = np.concatenate([pre_a, mixed_region, post_b], axis=0).astype(np.float32)
    return _peak_normalize(full, OUTPUT_PEAK_DBFS)
```

- [ ] **Step 4: Run the test (expect pass)**

Run:
```powershell
pytest tests/test_transition.py -v
```
Expected: 1 passed.

- [ ] **Step 5: Commit**
```powershell
git add backend/app/transition.py backend/tests/test_transition.py
git commit -m "feat(transition): equal-power crossfade and cut transitions"
```

---

### Task 4.2: Effects — filter sweeps and echo tail

**Files:**
- Modify: `E:\AutoDJ\backend\app\transition.py`.
- Modify: `E:\AutoDJ\backend\tests\test_transition.py`.

- [ ] **Step 1: Write the failing test**

Append to `E:\AutoDJ\backend\tests\test_transition.py`:
```python
def test_lowpass_sweep_attenuates_highs(click_120_wav):
    buf = load(click_120_wav)
    a = analyze(buf); b = analyze(buf)
    p = plan(a, b, bars=4, a_buffer=buf.samples)

    plain = build(buf.samples, buf.samples, p,
                  TransitionOptions(type="crossfade", bars=4, effect="none", bridge="none"))
    swept = build(buf.samples, buf.samples, p,
                  TransitionOptions(type="crossfade", bars=4, effect="lowpass_sweep", bridge="none"))

    # Compare high-frequency energy in the transition region
    region_start = p.a_start_sample
    region_end = p.a_end_sample
    plain_region = plain[region_start:region_end, 0]
    swept_region = swept[region_start:region_end, 0]

    plain_hf = np.abs(np.fft.rfft(plain_region))[len(plain_region)//4:].sum()
    swept_hf = np.abs(np.fft.rfft(swept_region))[len(swept_region)//4:].sum()
    assert swept_hf < plain_hf * 0.5
```

- [ ] **Step 2: Verify the test fails**

Run:
```powershell
pytest tests/test_transition.py::test_lowpass_sweep_attenuates_highs -v
```
Expected: assertion failure (effect not yet implemented — equal output).

- [ ] **Step 3: Implement sweep effects**

In `E:\AutoDJ\backend\app\transition.py`, add at module level:
```python
from scipy.signal import butter, sosfilt, sosfilt_zi


def _swept_filter(x: np.ndarray, sr: int, btype: str,
                   start_hz: float, end_hz: float) -> np.ndarray:
    """Apply a per-block Butterworth filter whose cutoff sweeps from start_hz → end_hz.
    Filter state (zi) is carried block-to-block per channel so block boundaries don't click."""
    block = max(1, int(sr * 0.05))
    n = len(x)
    out = np.empty_like(x)
    n_blocks = max(1, (n + block - 1) // block)
    # Initialize state from the first block's filter so the first sample isn't a transient.
    sos0 = butter(4, start_hz, btype=btype, fs=sr, output="sos")
    zi_per_ch = [sosfilt_zi(sos0) * x[0, ch] for ch in range(x.shape[1])]
    for i in range(n_blocks):
        start = i * block
        end = min(n, start + block)
        frac = i / max(1, n_blocks - 1)
        cutoff = start_hz * (1 - frac) + end_hz * frac
        sos = butter(4, cutoff, btype=btype, fs=sr, output="sos")
        for ch in range(x.shape[1]):
            filtered, zi_per_ch[ch] = sosfilt(sos, x[start:end, ch], zi=zi_per_ch[ch])
            out[start:end, ch] = filtered
    return out.astype(np.float32)


def _apply_lowpass_sweep(x: np.ndarray, sr: int = 44_100) -> np.ndarray:
    return _swept_filter(x, sr, "low", 20000.0, 200.0)


def _apply_highpass_sweep(x: np.ndarray, sr: int = 44_100) -> np.ndarray:
    return _swept_filter(x, sr, "high", 20.0, 4000.0)


def _apply_echo_tail(x: np.ndarray, bpm: float, sr: int = 44_100,
                     feedback: float = 0.35) -> np.ndarray:
    delay_samples = int(sr * 60 / bpm / 4)  # 1/4 note
    out = x.copy()
    buffer_signal = x.copy()
    ramp = np.linspace(0.0, 1.0, len(x), dtype=np.float32)[:, None]
    delayed = np.zeros_like(x)
    for offset in range(1, 5):
        gain = (feedback ** offset)
        shifted_start = delay_samples * offset
        if shifted_start >= len(x):
            break
        delayed[shifted_start:] += buffer_signal[:-shifted_start] * gain
    out = out + delayed * ramp
    return out.astype(np.float32)
```
Then change the crossfade branch in `build()`:
```python
    if options.type == "crossfade":
        fo, fi = _equal_power(n)
        effected_a = _apply_effect(a_outro, options.effect, plan_bpm_a=None)
        mixed_region = effected_a * fo[:, None] + b_intro * fi[:, None]
```
Add the dispatcher:
```python
def _apply_effect(x: np.ndarray, effect: EffectType, plan_bpm_a: float | None) -> np.ndarray:
    if effect == "none":
        return x
    if effect == "lowpass_sweep":
        return _apply_lowpass_sweep(x)
    if effect == "highpass_sweep":
        return _apply_highpass_sweep(x)
    if effect == "echo_tail":
        return _apply_echo_tail(x, bpm=plan_bpm_a or 120.0)
    return x  # remaining effects implemented in 4.3
```
Pass the BPM into `build` for echo:
```python
def build(
    a_samples: np.ndarray,
    b_samples: np.ndarray,
    plan: AlignmentPlan,
    options: TransitionOptions,
    bpm_a: float | None = None,
) -> np.ndarray:
    ...
    effected_a = _apply_effect(a_outro, options.effect, plan_bpm_a=bpm_a)
    ...
```
Update the test to pass `bpm_a=a.bpm`.

- [ ] **Step 4: Run all transition tests**

Run:
```powershell
pytest tests/test_transition.py -v
```
Expected: 2 passed.

- [ ] **Step 5: Add echo and highpass tests**

Append:
```python
def test_highpass_sweep_attenuates_lows(click_120_wav):
    buf = load(click_120_wav)
    a = analyze(buf); b = analyze(buf)
    p = plan(a, b, bars=4, a_buffer=buf.samples)
    plain = build(buf.samples, buf.samples, p,
                  TransitionOptions(type="crossfade", bars=4, effect="none"), bpm_a=a.bpm)
    swept = build(buf.samples, buf.samples, p,
                  TransitionOptions(type="crossfade", bars=4, effect="highpass_sweep"), bpm_a=a.bpm)
    region = slice(p.a_start_sample, p.a_end_sample)
    plain_lf = np.abs(np.fft.rfft(plain[region, 0]))[:50].sum()
    swept_lf = np.abs(np.fft.rfft(swept[region, 0]))[:50].sum()
    assert swept_lf < plain_lf * 0.6


def test_echo_tail_produces_repeats(click_120_wav):
    buf = load(click_120_wav)
    a = analyze(buf); b = analyze(buf)
    p = plan(a, b, bars=4, a_buffer=buf.samples)
    plain = build(buf.samples, buf.samples, p,
                  TransitionOptions(type="crossfade", bars=4, effect="none"), bpm_a=a.bpm)
    echoed = build(buf.samples, buf.samples, p,
                   TransitionOptions(type="crossfade", bars=4, effect="echo_tail"), bpm_a=a.bpm)
    # Echo adds energy in the second half of the transition region.
    region_len = p.a_end_sample - p.a_start_sample
    tail = slice(p.a_start_sample + region_len // 2, p.a_end_sample)
    assert np.sum(echoed[tail] ** 2) > np.sum(plain[tail] ** 2) * 1.05
```

Run:
```powershell
pytest tests/test_transition.py -v
```
Expected: 4 passed.

- [ ] **Step 6: Commit**
```powershell
git add backend/app/transition.py backend/tests/test_transition.py
git commit -m "feat(transition): lowpass/highpass sweep and echo tail effects"
```

---

### Task 4.3: Algorithmic reverb and backspin

**Files:**
- Modify: `E:\AutoDJ\backend\app\transition.py`.
- Modify: `E:\AutoDJ\backend\tests\test_transition.py`.

- [ ] **Step 1: Write tests for reverb and backspin**

Append to `E:\AutoDJ\backend\tests\test_transition.py`:
```python
def test_reverb_wash_adds_energy(click_120_wav):
    buf = load(click_120_wav)
    a = analyze(buf); b = analyze(buf)
    p = plan(a, b, bars=4, a_buffer=buf.samples)
    plain = build(buf.samples, buf.samples, p,
                  TransitionOptions(type="crossfade", bars=4, effect="none"), bpm_a=a.bpm)
    reverbed = build(buf.samples, buf.samples, p,
                     TransitionOptions(type="crossfade", bars=4, effect="reverb_wash"), bpm_a=a.bpm)
    region = slice(p.a_start_sample, p.a_end_sample)
    assert np.sum(reverbed[region] ** 2) > np.sum(plain[region] ** 2) * 1.05


def test_backspin_overrides_last_bar(click_120_wav):
    buf = load(click_120_wav)
    a = analyze(buf); b = analyze(buf)
    p = plan(a, b, bars=4, a_buffer=buf.samples)
    out = build(buf.samples, buf.samples, p,
                TransitionOptions(type="crossfade", bars=4, effect="backspin"), bpm_a=a.bpm)
    # The output should still be the right length and not clip
    assert out.shape[1] == 2
    assert float(np.max(np.abs(out))) <= 10 ** (-0.5 / 20) + 0.01
```

- [ ] **Step 2: Run the tests to confirm they fail**

Run:
```powershell
pytest tests/test_transition.py -v
```
Expected: 2 failures (the new tests).

- [ ] **Step 3: Implement reverb and backspin**

Append to `E:\AutoDJ\backend\app\transition.py`:
```python
from scipy.signal import lfilter


def _comb_filter(x_mono: np.ndarray, delay: int, feedback: float) -> np.ndarray:
    """Vectorized feedback comb: y[n] = x[n] + feedback * y[n-delay].
    Implemented as IIR via `lfilter` (single-pass C loop)."""
    b = np.zeros(delay + 1, dtype=np.float32); b[0] = 1.0
    a = np.zeros(delay + 1, dtype=np.float32); a[0] = 1.0; a[delay] = -feedback
    return lfilter(b, a, x_mono).astype(np.float32)


def _allpass_filter(x_mono: np.ndarray, delay: int, feedback: float = 0.5) -> np.ndarray:
    """Vectorized allpass: y[n] = -feedback*x[n] + x[n-delay] + feedback*y[n-delay]."""
    b = np.zeros(delay + 1, dtype=np.float32); b[0] = -feedback; b[delay] = 1.0
    a = np.zeros(delay + 1, dtype=np.float32); a[0] = 1.0; a[delay] = -feedback
    return lfilter(b, a, x_mono).astype(np.float32)


def _apply_reverb_wash(x: np.ndarray, sr: int = 44_100) -> np.ndarray:
    """Schroeder-style algorithmic reverb: 4 parallel combs → 2 series allpasses.
    Processes each channel independently with vectorized IIR filters (no Python sample loop)."""
    combs = [1116, 1188, 1277, 1356]    # Freeverb comb lengths
    allpasses = [556, 441]
    wet = np.zeros_like(x)
    for ch in range(x.shape[1]):
        signal = x[:, ch]
        ch_wet = np.zeros_like(signal)
        for d in combs:
            ch_wet += _comb_filter(signal, d, feedback=0.7)
        ch_wet /= len(combs)
        for d in allpasses:
            ch_wet = _allpass_filter(ch_wet, d, feedback=0.5)
        wet[:, ch] = ch_wet
    ramp = np.linspace(0.0, 0.6, len(x), dtype=np.float32)[:, None]
    return (x + wet * ramp).astype(np.float32)


def _apply_backspin(
    x: np.ndarray, fade_out: np.ndarray, bpm: float, bars: int, sr: int = 44_100
) -> tuple[np.ndarray, np.ndarray]:
    """Replace the last bar of A with a reversed copy of the preceding bar played back with a
    speed ramp from 1.0× → 0.5× (linear pitch-down). Returns (modified_signal, envelope_override).
    The envelope override holds A at -3 dB across the final bar in place of the equal-power curve."""
    bar_samples = int(sr * 60 / bpm * 4)
    n = len(x)
    if bar_samples >= n or bar_samples < 2:
        return x, fade_out
    cut = n - bar_samples
    # Source: the bar of A immediately preceding `cut`, time-reversed.
    source = x[cut - bar_samples:cut][::-1]                          # (bar_samples, 2)
    # Playhead position over `bar_samples` output samples: integrate speed ramp 1.0 → 0.5.
    speed_ramp = np.linspace(1.0, 0.5, bar_samples, dtype=np.float32)
    playhead = np.cumsum(speed_ramp) - speed_ramp[0]                 # starts at 0
    # Rescale so the playhead spans the full reversed source bar exactly once.
    playhead = playhead * ((bar_samples - 1) / playhead[-1])
    # Fractional-sample lookup via linear interpolation (preserves stereo).
    idx = np.arange(bar_samples, dtype=np.float32)
    played = np.empty_like(source)
    played[:, 0] = np.interp(playhead, idx, source[:, 0])
    played[:, 1] = np.interp(playhead, idx, source[:, 1])
    out = x.copy()
    out[cut:cut + bar_samples] = played
    env = fade_out.copy()
    env[cut:] = 10 ** (-3 / 20)  # fixed -3 dB across the final bar
    return out, env
```

Update the dispatcher and the `build()` function. Replace the crossfade branch with:
```python
    if options.type == "crossfade":
        fo, fi = _equal_power(n)
        effected_a = a_outro
        if options.effect == "lowpass_sweep":
            effected_a = _apply_lowpass_sweep(a_outro)
        elif options.effect == "highpass_sweep":
            effected_a = _apply_highpass_sweep(a_outro)
        elif options.effect == "echo_tail":
            effected_a = _apply_echo_tail(a_outro, bpm=bpm_a or 120.0)
        elif options.effect == "reverb_wash":
            effected_a = _apply_reverb_wash(a_outro)
        elif options.effect == "backspin":
            effected_a, fo = _apply_backspin(a_outro, fo, bpm=bpm_a or 120.0, bars=options.bars)
        mixed_region = effected_a * fo[:, None] + b_intro * fi[:, None]
```

- [ ] **Step 4: Run all tests**

Run:
```powershell
pytest tests/test_transition.py -v
```
Expected: 6 passed.

- [ ] **Step 5: Commit**
```powershell
git add backend/app/transition.py backend/tests/test_transition.py
git commit -m "feat(transition): algorithmic reverb wash and backspin effect"
```

---

### Task 4.4: Bridge insertion

**Files:**
- Modify: `E:\AutoDJ\backend\app\transition.py`.
- Modify: `E:\AutoDJ\backend\tests\test_transition.py`.
- Create: `E:\AutoDJ\samples\drumroll.wav` (placeholder; can be a short synthesized noise burst).

- [ ] **Step 1: Generate all 5 placeholder bridge WAVs**

Each bridge is a short stereo 44.1 kHz WAV. Quality is "placeholder" — fine for v1; the user can swap in real samples by overwriting these files later. Run all five from `E:\AutoDJ\backend\` with the venv activated:

```powershell
Set-Location E:\AutoDJ\backend
.\.venv\Scripts\Activate.ps1
python -c @"
import numpy as np, soundfile as sf
from pathlib import Path
sr = 44100
out_dir = Path('../samples'); out_dir.mkdir(exist_ok=True)
rng = np.random.RandomState(0)

# drumroll: 1 s of decaying noise burst
t = np.linspace(0, 1, sr, endpoint=False)
roll = (rng.randn(sr) * np.exp(-t * 2)).astype(np.float32) * 0.7
sf.write(str(out_dir / 'drumroll.wav'), np.stack([roll, roll], 1), sr)

# sweep_up: 1 s of upward chirp
chirp = np.sin(2 * np.pi * np.cumsum(np.linspace(80, 4000, sr) / sr)).astype(np.float32) * 0.5
sf.write(str(out_dir / 'sweep_up.wav'), np.stack([chirp, chirp], 1), sr)

# vinyl_stop: 0.5 s of pitch-down tone
n = sr // 2
freqs = np.linspace(440, 30, n)
stop = np.sin(2 * np.pi * np.cumsum(freqs) / sr).astype(np.float32) * np.linspace(0.7, 0, n)
sf.write(str(out_dir / 'vinyl_stop.wav'), np.stack([stop, stop], 1), sr)

# airhorn: 0.6 s of square-wave honk at ~250 Hz
n = int(sr * 0.6)
phase = np.cumsum(np.full(n, 250 / sr))
horn = (np.sign(np.sin(2 * np.pi * phase)) * 0.5).astype(np.float32)
horn[:int(sr * 0.02)] *= np.linspace(0, 1, int(sr * 0.02))      # fade-in
horn[-int(sr * 0.05):] *= np.linspace(1, 0, int(sr * 0.05))    # fade-out
sf.write(str(out_dir / 'airhorn.wav'), np.stack([horn, horn], 1), sr)

# dj_tag: 0.4 s of filtered noise + sine — placeholder for a vocal tag
n = int(sr * 0.4)
noise = (rng.randn(n) * 0.2).astype(np.float32)
tone = (np.sin(2 * np.pi * 600 * np.arange(n) / sr) * 0.3).astype(np.float32)
tag = (noise + tone) * np.linspace(1, 0, n).astype(np.float32)
sf.write(str(out_dir / 'dj_tag.wav'), np.stack([tag, tag], 1), sr)

print('5 bridge samples written to', out_dir.resolve())
"@
```
Verify with `Get-ChildItem ..\samples\*.wav` — expect 5 files.

- [ ] **Step 2: Write the failing tests (TDD: write all bridge tests before impl)**

Append to `E:\AutoDJ\backend\tests\test_transition.py`:
```python
from app.config import SAMPLES_DIR
import soundfile as sf


def test_bridge_inserted_before_crossfade(click_120_wav):
    buf = load(click_120_wav)
    a = analyze(buf); b = analyze(buf)
    p = plan(a, b, bars=4, a_buffer=buf.samples)
    out_no = build(buf.samples, buf.samples, p,
                   TransitionOptions(type="crossfade", bars=4, effect="none", bridge="none"),
                   bpm_a=a.bpm)
    out_br = build(buf.samples, buf.samples, p,
                   TransitionOptions(type="crossfade", bars=4, effect="none", bridge="drumroll"),
                   bpm_a=a.bpm)
    bridge, _ = sf.read(str(SAMPLES_DIR / "drumroll.wav"), dtype="float32", always_2d=True)
    # Bridge-inserted output is longer by approximately the bridge length
    diff = out_br.shape[0] - out_no.shape[0]
    assert abs(diff - len(bridge)) < 100  # ≤2 ms drift


def test_bridge_seamless_to_crossfade(click_120_wav):
    """Spec §7.1: silence between bridge end and crossfade start is 0 samples."""
    buf = load(click_120_wav)
    a = analyze(buf); b = analyze(buf)
    p = plan(a, b, bars=4, a_buffer=buf.samples)
    out = build(buf.samples, buf.samples, p,
                TransitionOptions(type="crossfade", bars=4, effect="none", bridge="drumroll"),
                bpm_a=a.bpm)
    bridge, _ = sf.read(str(SAMPLES_DIR / "drumroll.wav"), dtype="float32", always_2d=True)
    crossfade_start = p.a_start_sample + len(bridge)
    # The 50 samples immediately before crossfade_start are the tail of bridge_region;
    # the 50 samples after are the head of mixed_region. There must be no silent run
    # straddling the join.
    window = np.abs(out[crossfade_start - 50:crossfade_start + 50, 0])
    assert np.max(window) > 1e-3, "silence detected at bridge→crossfade join"


def test_missing_bridge_raises(tmp_path, click_120_wav, monkeypatch):
    from app import transition as t
    monkeypatch.setattr(t, "SAMPLES_DIR", tmp_path)
    buf = load(click_120_wav)
    a = analyze(buf); b = analyze(buf)
    p = plan(a, b, bars=4, a_buffer=buf.samples)
    from app.transition import BridgeSampleMissing
    with pytest.raises(BridgeSampleMissing):
        build(buf.samples, buf.samples, p,
              TransitionOptions(type="crossfade", bars=4, effect="none", bridge="drumroll"),
              bpm_a=a.bpm)
```

- [ ] **Step 3: Verify the test fails**

Run:
```powershell
pytest tests/test_transition.py::test_bridge_inserted_before_crossfade -v
```
Expected: failure (bridge ignored).

- [ ] **Step 4: Implement bridge insertion**

Append a loader and modify `build()` in `E:\AutoDJ\backend\app\transition.py`:
```python
from pathlib import Path
import soundfile as sf
from .config import SAMPLES_DIR


class BridgeSampleMissing(Exception):
    pass


def _load_bridge(name: BridgeType) -> np.ndarray:
    if name == "none":
        return np.zeros((0, 2), dtype=np.float32)
    path = SAMPLES_DIR / f"{name}.wav"
    if not path.exists():
        raise BridgeSampleMissing(str(path))
    data, _ = sf.read(str(path), dtype="float32", always_2d=True)
    if data.shape[1] == 1:
        data = np.repeat(data, 2, axis=1)
    return data.astype(np.float32)
```
Modify `build()` to insert the bridge **before** the crossfade region. While the bridge plays, A continues underneath at -6 dB (per spec §4.4). The bridge audio is taken from `samples/<name>.wav` and the underlying A audio is taken from the bar(s) immediately after `a_end_sample` so the underbed sounds natural. If A doesn't have that much remaining tail (e.g., a_end is at the very end of A), the underbed falls back to the last `len(bridge)` samples of A's outro.

Replace the construction of `full` with:
```python
    bridge = _load_bridge(options.bridge)
    if len(bridge) > 0:
        bridge_len = len(bridge)
        # Pick the A-continuation underbed: samples following a_end_sample if available.
        a_tail_start = plan.a_end_sample
        a_tail_end = min(a_tail_start + bridge_len, len(a_samples))
        underbed = a_samples[a_tail_start:a_tail_end]
        if len(underbed) < bridge_len:
            # Pad with the last available samples of A's outro to fill the bridge length.
            fill = a_outro[-(bridge_len - len(underbed)):] if len(a_outro) >= (bridge_len - len(underbed)) else np.zeros((bridge_len - len(underbed), 2), dtype=np.float32)
            underbed = np.concatenate([underbed, fill], axis=0)
        underbed = underbed[:bridge_len]
        underbed_gain = 10 ** (-6 / 20)  # -6 dB
        bridge_region = bridge + underbed * underbed_gain
        full = np.concatenate([pre_a, bridge_region, mixed_region, post_b], axis=0)
    else:
        full = np.concatenate([pre_a, mixed_region, post_b], axis=0)
    full = full.astype(np.float32)
```

- [ ] **Step 5: Run tests**

Run:
```powershell
pytest tests/test_transition.py -v
```
Expected: 9 passed (6 pre-existing + 3 new bridge tests including the missing-bridge error case).

- [ ] **Step 6: Commit**
```powershell
git add backend/app/transition.py backend/tests/test_transition.py samples/
git commit -m "feat(transition): bridge sample insertion with fail-fast on missing files"
```

---

### Task 4.5: Beat-grid alignment test

**Files:**
- Modify: `E:\AutoDJ\backend\tests\test_transition.py`.

- [ ] **Step 1: Write the alignment test**

Append:
```python
def test_beat_grid_alignment_within_15ms(click_120_wav):
    """Verifies §2.2 success criterion: rendered transition region has A and B beats
    within ±15 ms of a shared 120 BPM grid."""
    import librosa
    buf = load(click_120_wav)
    a = analyze(buf); b = analyze(buf)
    p = plan(a, b, bars=4, a_buffer=buf.samples)
    out = build(buf.samples, buf.samples, p,
                TransitionOptions(type="crossfade", bars=4, effect="none"), bpm_a=a.bpm)
    region = out[p.a_start_sample:p.a_end_sample, 0]
    _, frames = librosa.beat.beat_track(y=region, sr=44_100)
    times = librosa.frames_to_time(frames, sr=44_100)
    beat_period = 60 / a.bpm
    for t in times:
        nearest_grid = round(t / beat_period) * beat_period
        assert abs(t - nearest_grid) < 0.015, f"beat at {t}s is {abs(t-nearest_grid)*1000:.1f}ms off grid"
```

- [ ] **Step 2: Run it**

Run:
```powershell
pytest tests/test_transition.py::test_beat_grid_alignment_within_15ms -v
```
Expected: 1 passed. (If it fails on the click track, increase tolerance slightly or investigate the crossfade region's beat detection — but on synthetic clicks at the same BPM it should pass cleanly.)

- [ ] **Step 3: Commit**
```powershell
git add backend/tests/test_transition.py
git commit -m "test(transition): beat-grid alignment within ±15 ms"
```

---

## Chunk 5: `render` and FastAPI surface

### Task 5.1: `render.write`

**Files:**
- Create: `E:\AutoDJ\backend\app\render.py`
- Create: `E:\AutoDJ\backend\tests\test_render.py`

- [ ] **Step 1: Write the failing test**

Create `E:\AutoDJ\backend\tests\test_render.py`:
```python
import json
from app.audio_io import load
from app.render import write
from app.config import WORKDIR


def test_render_writes_all_three_outputs(tmp_path, click_120_wav):
    buf = load(click_120_wav)
    job_dir = tmp_path / "job123"
    job_dir.mkdir()
    metadata = {"bpm_a": 120.0, "bpm_b": 120.0, "transition_start_s": 5.0,
                "transition_end_s": 7.0, "bars": 4, "type": "crossfade",
                "effect": "none", "bridge": "none", "beat_match": True}
    write(buf.samples, job_dir, metadata)
    assert (job_dir / "mix.wav").exists()
    assert (job_dir / "mix.mp3").exists()
    meta = json.loads((job_dir / "mix.json").read_text())
    assert meta["bpm_a"] == 120.0
    assert meta["type"] == "crossfade"


def test_render_mp3_sample_count_matches_wav_within_10ms(tmp_path, click_120_wav):
    """Spec §7.1: WAV and MP3 decode back to the same number of samples (±10 ms)."""
    import soundfile as sf
    buf = load(click_120_wav)
    job_dir = tmp_path / "job_mp3_check"
    job_dir.mkdir()
    write(buf.samples, job_dir, {"bpm_a": 120, "bpm_b": 120, "type": "crossfade",
                                  "bars": 4, "effect": "none", "bridge": "none",
                                  "transition_start_s": 0, "transition_end_s": 0,
                                  "beat_match": True})
    wav_data, sr = sf.read(str(job_dir / "mix.wav"), always_2d=True)
    mp3_data, _ = sf.read(str(job_dir / "mix.mp3"), always_2d=True)
    diff_samples = abs(wav_data.shape[0] - mp3_data.shape[0])
    assert diff_samples < int(sr * 0.01), f"WAV/MP3 length differs by {diff_samples} samples"
```

- [ ] **Step 2: Implement `render.write`**

Create `E:\AutoDJ\backend\app\render.py`:
```python
import json
from pathlib import Path
import numpy as np

from .audio_io import AudioBuffer, save_wav, save_mp3
from .config import TARGET_SAMPLE_RATE


def write(samples: np.ndarray, job_dir: Path, metadata: dict) -> dict:
    job_dir = Path(job_dir)
    job_dir.mkdir(parents=True, exist_ok=True)
    buf = AudioBuffer(samples=samples.astype(np.float32), sr=TARGET_SAMPLE_RATE,
                     channels=2, scale_applied=1.0)
    save_wav(buf, job_dir / "mix.wav")
    save_mp3(buf, job_dir / "mix.mp3")
    (job_dir / "mix.json").write_text(json.dumps(metadata, indent=2))
    return {
        "wav": str(job_dir / "mix.wav"),
        "mp3": str(job_dir / "mix.mp3"),
        "json": str(job_dir / "mix.json"),
    }
```

- [ ] **Step 3: Run the test**

Run:
```powershell
pytest tests/test_render.py -v
```
Expected: 2 passed.

- [ ] **Step 4: Commit**
```powershell
git add backend/app/render.py backend/tests/test_render.py
git commit -m "feat(render): write WAV, MP3, and metadata JSON for a job"
```

---

### Task 5.2: FastAPI `POST /analyze`

**Files:**
- Create: `E:\AutoDJ\backend\app\api.py`
- Create: `E:\AutoDJ\backend\tests\test_api.py`

- [ ] **Step 1: Write the failing test**

Create `E:\AutoDJ\backend\tests\test_api.py`:
```python
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
    assert data["a"]["duration"] > 25  # ~30 s click track
```

- [ ] **Step 2: Implement the endpoint**

Create `E:\AutoDJ\backend\app\api.py`:
```python
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

    JOBS[job_id] = {
        "dir": job_dir,
        "buf_a": buf_a, "buf_b": buf_b,
        "feat_a": feat_a, "feat_b": feat_b,
    }
    return {
        "job_id": job_id,
        "a": _feature_summary(feat_a),
        "b": _feature_summary(feat_b),
    }
```

- [ ] **Step 3: Run the test**

Run:
```powershell
pytest tests/test_api.py -v
```
Expected: 1 passed.

- [ ] **Step 4: Commit**
```powershell
git add backend/app/api.py backend/tests/test_api.py
git commit -m "feat(api): POST /analyze with format and content validation"
```

---

### Task 5.3: FastAPI `POST /mix`, `GET /preview`, `GET /download`

**Files:**
- Modify: `E:\AutoDJ\backend\app\api.py`.
- Modify: `E:\AutoDJ\backend\tests\test_api.py`.

- [ ] **Step 1: Write the failing tests**

Append to `E:\AutoDJ\backend\tests\test_api.py`:
```python
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
```

- [ ] **Step 2: Implement the endpoints**

Append to `E:\AutoDJ\backend\app\api.py`:
```python
from pydantic import BaseModel
from fastapi.responses import FileResponse
from .align import plan as align_plan
from .transition import build, TransitionOptions, BridgeSampleMissing
from .render import write as render_write


class MixRequest(BaseModel):
    job_id: str
    type: str = "crossfade"
    bars: int = 16
    effect: str = "none"
    bridge: str = "none"
    manual_bpm_a: float | None = None
    manual_bpm_b: float | None = None


@app.post("/mix")
async def mix_endpoint(req: MixRequest):
    job = JOBS.get(req.job_id)
    if not job:
        raise HTTPException(404, detail="unknown job")
    feat_a = job["feat_a"]; feat_b = job["feat_b"]
    if req.manual_bpm_a is not None:
        feat_a.bpm = req.manual_bpm_a
    if req.manual_bpm_b is not None:
        feat_b.bpm = req.manual_bpm_b

    alignment = align_plan(feat_a, feat_b, bars=req.bars,
                           a_buffer=job["buf_a"].samples)
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
    # For v1 we just serve the full mix WAV as the preview; the frontend seeks.
    return FileResponse(job["paths"]["wav"], media_type="audio/wav")
```

- [ ] **Step 3: Run all API tests**

Run:
```powershell
pytest tests/test_api.py -v
```
Expected: 2 passed.

- [ ] **Step 4: Commit**
```powershell
git add backend/app/api.py backend/tests/test_api.py
git commit -m "feat(api): POST /mix, GET /preview, GET /download"
```

---

### Task 5.4: Full backend E2E test

**Files:**
- Create: `E:\AutoDJ\backend\tests\test_e2e.py`

- [ ] **Step 1: Write the E2E test**

Create `E:\AutoDJ\backend\tests\test_e2e.py`:
```python
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
    print(f"\nE2E wall-time: {elapsed:.2f}s")  # informational

    # Decode and check peak
    from io import BytesIO
    data, sr = sf.read(BytesIO(dl.content), dtype="float32", always_2d=True)
    peak_dbfs = 20 * np.log10(float(np.max(np.abs(data))))
    assert peak_dbfs <= -0.5 + 0.05
    assert sr == 44_100
```

- [ ] **Step 2: Run it**

Run:
```powershell
pytest tests/test_e2e.py -v -s
```
Expected: 1 passed, with an `E2E wall-time` line logged.

- [ ] **Step 3: Commit**
```powershell
git add backend/tests/test_e2e.py
git commit -m "test(e2e): full analyze→mix→download pipeline with timing log"
```

---

### Task 5.5: §6 error-handling tests + short_track warning + cut+beat_match guard

**Files:**
- Modify: `E:\AutoDJ\backend\app\api.py`
- Modify: `E:\AutoDJ\backend\tests\test_api.py`
- Modify: `E:\AutoDJ\backend\tests\conftest.py`

- [ ] **Step 1: Add short and oversized fixtures**

Append to `conftest.py`:
```python
@pytest.fixture(scope="session")
def click_120_short_wav() -> Path:
    """45 s click — below the 60 s threshold to trigger `short_track` warning."""
    path = FIXTURES / "click_120_short.wav"
    if not path.exists():
        sf.write(path, _click_track(120, 45), SR)
    return path
```

- [ ] **Step 2: Write failing tests for each error row**

Append to `test_api.py`:
```python
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
    """Tracks under 60 s should still analyze, but with a `short_track` warning surfaced."""
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
```

- [ ] **Step 3: Implement the missing behaviors**

In `E:\AutoDJ\backend\app\api.py`:

(a) Add a `warnings` array to the `/analyze` response. After computing features and before returning, build:
```python
    warnings = []
    if feat_a.duration_s < 60:
        warnings.append("short_track:a")
    if feat_b.duration_s < 60:
        warnings.append("short_track:b")
```
Include `"warnings": warnings` in the response dict.

(b) Reject `cut` with non-matching BPM in `/mix`. After computing `alignment`:
```python
    if req.type == "cut" and not alignment.beat_match:
        raise HTTPException(422, detail="cut_requires_beat_match")
```

- [ ] **Step 4: Run all API tests**

```powershell
pytest tests/test_api.py -v
```
Expected: 6 passed.

- [ ] **Step 5: Commit**
```powershell
git add backend/app/api.py backend/tests/
git commit -m "feat(api): §6 error coverage — 415/422/404 + short_track warnings"
```

---

## Chunk 6: Frontend (Vite + React + TypeScript)

### Task 6.1: Scaffold and API client

**Files:**
- Create: `E:\AutoDJ\frontend\` (via `npm create vite@latest`).
- Create: `E:\AutoDJ\frontend\src\api.ts`, `E:\AutoDJ\frontend\src\types.ts`.

- [ ] **Step 1: Scaffold Vite project**

Run from `E:\AutoDJ\`:
```powershell
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
```
Verify with `npm run dev` (should open <http://localhost:5173>). Ctrl+C to stop.

- [ ] **Step 2: Define types**

Create `E:\AutoDJ\frontend\src\types.ts`:
```typescript
export type TransitionType = "crossfade" | "cut";
export type EffectType = "none" | "lowpass_sweep" | "highpass_sweep" | "echo_tail" | "reverb_wash" | "backspin";
export type BridgeType = "none" | "drumroll" | "sweep_up" | "vinyl_stop" | "airhorn" | "dj_tag";

export interface TrackSummary {
  bpm: number;
  bpm_confidence: number;
  key: string;
  duration: number;
  suggested_start: number;
}

export interface AnalyzeResponse {
  job_id: string;
  a: TrackSummary;
  b: TrackSummary;
}

export interface MixRequest {
  job_id: string;
  type: TransitionType;
  bars: number;
  effect: EffectType;
  bridge: BridgeType;
  manual_bpm_a?: number;
  manual_bpm_b?: number;
}

export interface MixResponse {
  status: "ok";
  preview_url: string;
  download_wav_url: string;
  download_mp3_url: string;
  beat_match: boolean;
  effective_bars: number;
  warning?: string | null;
}
```

- [ ] **Step 3: Implement the API client**

Create `E:\AutoDJ\frontend\src\api.ts`:
```typescript
import type { AnalyzeResponse, MixRequest, MixResponse } from "./types";

const BASE = "http://localhost:8000";

export async function analyze(fileA: File, fileB: File): Promise<AnalyzeResponse> {
  const fd = new FormData();
  fd.append("file_a", fileA);
  fd.append("file_b", fileB);
  const res = await fetch(`${BASE}/analyze`, { method: "POST", body: fd });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function mix(req: MixRequest): Promise<MixResponse> {
  const res = await fetch(`${BASE}/mix`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export function downloadUrl(path: string): string {
  return `${BASE}${path}`;
}
```

- [ ] **Step 4: Commit**
```powershell
git add frontend/
git commit -m "chore(frontend): vite+react+ts scaffold and API client"
```

---

### Task 6.2: Single-screen UI components

**Files:**
- Create: `E:\AutoDJ\frontend\src\components\UploadTile.tsx`
- Create: `E:\AutoDJ\frontend\src\components\OptionsPanel.tsx`
- Create: `E:\AutoDJ\frontend\src\components\OutputPanel.tsx`
- Modify: `E:\AutoDJ\frontend\src\App.tsx`
- Modify: `E:\AutoDJ\frontend\src\App.css`

- [ ] **Step 1: `UploadTile.tsx`**

Create `E:\AutoDJ\frontend\src\components\UploadTile.tsx`:
```tsx
import { useState } from "react";
import type { TrackSummary } from "../types";

interface Props {
  label: string;
  onSelect: (file: File) => void;
  summary?: TrackSummary;
  manualBpm: number | "";
  onManualBpm: (v: number | "") => void;
}

export default function UploadTile({ label, onSelect, summary, manualBpm, onManualBpm }: Props) {
  const [name, setName] = useState<string>("");
  return (
    <div className="tile">
      <h3>{label}</h3>
      <input
        type="file"
        accept="audio/*"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) { setName(f.name); onSelect(f); }
        }}
      />
      {name && <p className="filename">{name}</p>}
      {summary && (
        <div className="summary">
          <p>BPM: <strong>{summary.bpm.toFixed(1)}</strong>
             {summary.bpm_confidence < 0.5 && <span className="warning"> (low confidence)</span>}
          </p>
          <p>Duration: {summary.duration.toFixed(1)}s</p>
          {summary.bpm_confidence < 0.5 && (
            <label>Manual BPM:
              <input
                type="number"
                value={manualBpm}
                onChange={(e) => onManualBpm(e.target.value === "" ? "" : Number(e.target.value))}
              />
            </label>
          )}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: `OptionsPanel.tsx`**

Create `E:\AutoDJ\frontend\src\components\OptionsPanel.tsx`:
```tsx
import type { TransitionType, EffectType, BridgeType } from "../types";

interface Props {
  type: TransitionType;
  bars: number;
  effect: EffectType;
  bridge: BridgeType;
  onChange: (patch: Partial<{ type: TransitionType; bars: number; effect: EffectType; bridge: BridgeType }>) => void;
  beatMatch: boolean;
}

export default function OptionsPanel({ type, bars, effect, bridge, onChange, beatMatch }: Props) {
  return (
    <div className="options">
      <fieldset>
        <legend>Transition</legend>
        <label><input type="radio" name="type" checked={type === "crossfade"}
          onChange={() => onChange({ type: "crossfade" })} /> Crossfade</label>
        <label><input type="radio" name="type" checked={type === "cut"} disabled={!beatMatch}
          onChange={() => onChange({ type: "cut" })} /> Cut {!beatMatch && "(needs beat-match)"}</label>
      </fieldset>
      <fieldset>
        <legend>Length (bars)</legend>
        {[4, 8, 16, 32].map((n) => (
          <label key={n}>
            <input type="radio" name="bars" checked={bars === n} onChange={() => onChange({ bars: n })} />
            {n}
          </label>
        ))}
      </fieldset>
      <label>Effect:
        <select value={effect} onChange={(e) => onChange({ effect: e.target.value as EffectType })}>
          <option value="none">None</option>
          <option value="lowpass_sweep">Low-pass sweep</option>
          <option value="highpass_sweep">High-pass sweep</option>
          <option value="echo_tail">Echo tail</option>
          <option value="reverb_wash">Reverb wash</option>
          <option value="backspin">Backspin</option>
        </select>
      </label>
      <label>Bridge:
        <select value={bridge} onChange={(e) => onChange({ bridge: e.target.value as BridgeType })}>
          <option value="none">None</option>
          <option value="drumroll">Drumroll</option>
          <option value="sweep_up">Sweep up</option>
          <option value="vinyl_stop">Vinyl stop</option>
          <option value="airhorn">Airhorn</option>
          <option value="dj_tag">DJ tag</option>
        </select>
      </label>
    </div>
  );
}
```

- [ ] **Step 3: `OutputPanel.tsx`**

Create `E:\AutoDJ\frontend\src\components\OutputPanel.tsx`:
```tsx
import type { MixResponse } from "../types";
import { downloadUrl } from "../api";

interface Props {
  result?: MixResponse;
  rendering: boolean;
  error?: string;
  onRender: () => void;
}

export default function OutputPanel({ result, rendering, error, onRender }: Props) {
  return (
    <div className="output">
      <button disabled={rendering} onClick={onRender}>
        {rendering ? "Rendering…" : "Render mix"}
      </button>
      {error && <p className="error">{error}</p>}
      {result && (
        <>
          {result.warning === "bars_reduced" &&
            <p className="warning">Transition shortened to {result.effective_bars} bars to stay beat-aligned.</p>}
          {!result.beat_match &&
            <p className="warning">BPMs too different to beat-match — using crossfade only.</p>}
          <audio controls src={downloadUrl(result.preview_url)} />
          <p>
            <a href={downloadUrl(result.download_wav_url)} download>Download WAV</a>
            {" · "}
            <a href={downloadUrl(result.download_mp3_url)} download>Download MP3</a>
          </p>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 4: `App.tsx`**

Replace `E:\AutoDJ\frontend\src\App.tsx`:
```tsx
import { useState } from "react";
import UploadTile from "./components/UploadTile";
import OptionsPanel from "./components/OptionsPanel";
import OutputPanel from "./components/OutputPanel";
import { analyze, mix } from "./api";
import type {
  AnalyzeResponse, MixResponse, TransitionType, EffectType, BridgeType,
} from "./types";
import "./App.css";

export default function App() {
  const [analyzeRes, setAnalyzeRes] = useState<AnalyzeResponse>();
  const [fileA, setFileA] = useState<File>();
  const [fileB, setFileB] = useState<File>();
  const [manualA, setManualA] = useState<number | "">("");
  const [manualB, setManualB] = useState<number | "">("");
  const [type, setType] = useState<TransitionType>("crossfade");
  const [bars, setBars] = useState<number>(16);
  const [effect, setEffect] = useState<EffectType>("none");
  const [bridge, setBridge] = useState<BridgeType>("none");
  const [result, setResult] = useState<MixResponse>();
  const [rendering, setRendering] = useState(false);
  const [error, setError] = useState<string>();

  async function handleAnalyze(a?: File, b?: File) {
    const fa = a ?? fileA, fb = b ?? fileB;
    if (!fa || !fb) return;
    try {
      setError(undefined);
      const res = await analyze(fa, fb);
      setAnalyzeRes(res);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function handleMix() {
    if (!analyzeRes) return;
    setRendering(true); setError(undefined);
    try {
      const res = await mix({
        job_id: analyzeRes.job_id, type, bars, effect, bridge,
        manual_bpm_a: manualA === "" ? undefined : manualA,
        manual_bpm_b: manualB === "" ? undefined : manualB,
      });
      setResult(res);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setRendering(false);
    }
  }

  const beatMatch = result?.beat_match ?? true;

  return (
    <main>
      <h1>AutoDJ</h1>
      <section className="tiles">
        <UploadTile label="Track A"
          onSelect={(f) => { setFileA(f); handleAnalyze(f, fileB); }}
          summary={analyzeRes?.a} manualBpm={manualA} onManualBpm={setManualA} />
        <UploadTile label="Track B"
          onSelect={(f) => { setFileB(f); handleAnalyze(fileA, f); }}
          summary={analyzeRes?.b} manualBpm={manualB} onManualBpm={setManualB} />
      </section>
      <OptionsPanel type={type} bars={bars} effect={effect} bridge={bridge}
        beatMatch={beatMatch}
        onChange={(p) => {
          if (p.type !== undefined) setType(p.type);
          if (p.bars !== undefined) setBars(p.bars);
          if (p.effect !== undefined) setEffect(p.effect);
          if (p.bridge !== undefined) setBridge(p.bridge);
        }} />
      <OutputPanel result={result} rendering={rendering} error={error} onRender={handleMix} />
    </main>
  );
}
```

- [ ] **Step 5: Minimal CSS**

Replace `E:\AutoDJ\frontend\src\App.css`:
```css
main { max-width: 900px; margin: 2rem auto; font-family: system-ui, sans-serif; padding: 0 1rem; }
.tiles { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
.tile { border: 1px solid #ccc; border-radius: 8px; padding: 1rem; }
.options { display: flex; flex-wrap: wrap; gap: 1rem; margin: 1.5rem 0; align-items: flex-start; }
.options fieldset { border: 1px solid #ccc; border-radius: 6px; }
.output { margin-top: 1.5rem; }
.warning { color: #b86200; }
.error { color: #b00020; }
.filename { color: #555; font-size: 0.9rem; }
audio { width: 100%; margin: 0.75rem 0; }
button { padding: 0.6rem 1.2rem; font-size: 1rem; cursor: pointer; }
button:disabled { opacity: 0.5; cursor: progress; }
```

- [ ] **Step 6: Manual smoke test**

Run backend in one terminal:
```powershell
cd E:\AutoDJ\backend
.\.venv\Scripts\Activate.ps1
uvicorn app.api:app --reload
```
Run frontend in another:
```powershell
cd E:\AutoDJ\frontend
npm run dev
```
Open <http://localhost:5173>, upload two click-track fixtures from `backend/tests/fixtures/`, click Render. Verify the audio player appears and downloads work.

- [ ] **Step 7: Commit**
```powershell
git add frontend/
git commit -m "feat(frontend): single-screen UI with upload, options, output"
```

---

## Chunk 7: Setup scripts and final polish

### Task 7.1: `scripts/setup.ps1`

**Files:**
- Create: `E:\AutoDJ\scripts\setup.ps1`

- [ ] **Step 1: Write the script**

Create `E:\AutoDJ\scripts\setup.ps1`:
```powershell
#requires -version 5.1
$ErrorActionPreference = "Stop"
Push-Location $PSScriptRoot\..

Write-Host "Checking ffmpeg..."
$ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue
if (-not $ffmpeg) {
    Write-Host "ffmpeg not found. Install with: winget install ffmpeg" -ForegroundColor Yellow
    exit 1
}

Write-Host "Setting up backend venv..."
Push-Location backend
if (-not (Test-Path .venv)) { python -m venv .venv }
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]" --quiet
Pop-Location

Write-Host "Installing frontend deps..."
Push-Location frontend
npm install --silent
Pop-Location

Pop-Location
Write-Host "Done. Run scripts\run.ps1 to start both servers." -ForegroundColor Green
```

- [ ] **Step 2: Test it on a fresh shell**

Open a new PowerShell, run `E:\AutoDJ\scripts\setup.ps1`. Expected: ends with the green "Done" line.

- [ ] **Step 3: Commit**
```powershell
git add scripts/setup.ps1
git commit -m "chore: setup script for venv, deps, ffmpeg check"
```

---

### Task 7.2: `scripts/run.ps1`

**Files:**
- Create: `E:\AutoDJ\scripts\run.ps1`

- [ ] **Step 1: Write the script**

Create `E:\AutoDJ\scripts\run.ps1`:
```powershell
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Write-Host "Starting backend on http://localhost:8000 ..."
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "Set-Location '$root\backend'; .\.venv\Scripts\Activate.ps1; uvicorn app.api:app --reload"
)
Start-Sleep -Seconds 2
Write-Host "Starting frontend on http://localhost:5173 ..."
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "Set-Location '$root\frontend'; npm run dev"
)
Write-Host "Two new terminal windows have opened. Close them to stop." -ForegroundColor Green
```

- [ ] **Step 2: Commit**
```powershell
git add scripts/run.ps1
git commit -m "chore: run script to launch backend + frontend together"
```

---

### Task 7.3: Workdir cleanup on startup

**Files:**
- Modify: `E:\AutoDJ\backend\app\api.py`

- [ ] **Step 1: Add a startup hook**

In `E:\AutoDJ\backend\app\api.py`, after `app = FastAPI(...)`:
```python
from datetime import datetime, timedelta


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
```

- [ ] **Step 2: Manual verification**

Restart uvicorn. Workdir items older than 24 h should be removed.

- [ ] **Step 3: Commit**
```powershell
git add backend/app/api.py
git commit -m "chore(api): 24h rolling cleanup of workdir on startup"
```

---

### Task 7.4: Full-suite verification

- [ ] **Step 1: Run all backend tests**

```powershell
cd E:\AutoDJ\backend
.\.venv\Scripts\Activate.ps1
pytest -v
```
Expected: every test in `tests/` passes. Apply @superpowers:verification-before-completion — paste the test summary into your commit message or notes before claiming done.

- [ ] **Step 2: Run ruff and mypy**

```powershell
ruff check .
mypy app
```
Expected: no errors. Fix any that appear.

- [ ] **Step 3: Manual end-to-end with real audio**

Pick two MP3s from your music library (≤ 8 min each), upload, render, listen. Confirm: the transition is audible, the file plays, neither side clips.

- [ ] **Step 4: Final commit**
```powershell
git commit --allow-empty -m "chore: v1 verification complete — all tests green, manual e2e pass"
```

---

## Done criteria for v1

- All success criteria in §2 of the spec hold.
- All tests in `backend/tests/` pass under `pytest -v`.
- `scripts\setup.ps1` succeeds on a clean machine.
- A real-world MP3-pair mix renders in ≤ 15 s on the user's laptop (informational, logged in the E2E test).
- The UI lets the user pick all four option dimensions and produces working download links.

Anything beyond this is v2.
