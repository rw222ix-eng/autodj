from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_ROOT.parent


def _samples_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "samples"
    return PROJECT_ROOT / "samples"


def _workdir() -> Path:
    if getattr(sys, "frozen", False):
        # Use a stable user-writable location for jobs in bundled mode.
        return Path.home() / ".autodj" / "workdir"
    return PROJECT_ROOT / "workdir"


WORKDIR = _workdir()
SAMPLES_DIR = _samples_dir()
WORKDIR.mkdir(parents=True, exist_ok=True)

TARGET_SAMPLE_RATE = 44_100
TARGET_CHANNELS = 2
INPUT_PEAK_DBFS = -1.0
OUTPUT_PEAK_DBFS = -0.5
MAX_INPUT_DURATION_S = 15 * 60
MIN_BPM_CONFIDENCE = 0.5
BPM_BEAT_MATCH_TOLERANCE = 0.08
MIN_TRACK_DURATION_S = 60
SILENCE_GAP_LIMIT_S = 30
