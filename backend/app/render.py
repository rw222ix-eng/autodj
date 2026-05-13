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
