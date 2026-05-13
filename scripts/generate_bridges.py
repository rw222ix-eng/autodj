import numpy as np, soundfile as sf
from pathlib import Path

sr = 44100
out_dir = Path(__file__).resolve().parent.parent / "samples"
out_dir.mkdir(exist_ok=True)
rng = np.random.RandomState(0)

# drumroll
t = np.linspace(0, 1, sr, endpoint=False)
roll = (rng.randn(sr) * np.exp(-t * 2)).astype(np.float32) * 0.7
sf.write(str(out_dir / "drumroll.wav"), np.stack([roll, roll], 1), sr)

# sweep_up
chirp = np.sin(2 * np.pi * np.cumsum(np.linspace(80, 4000, sr) / sr)).astype(np.float32) * 0.5
sf.write(str(out_dir / "sweep_up.wav"), np.stack([chirp, chirp], 1), sr)

# vinyl_stop
n = sr // 2
freqs = np.linspace(440, 30, n)
stop = (np.sin(2 * np.pi * np.cumsum(freqs) / sr).astype(np.float32) * np.linspace(0.7, 0, n).astype(np.float32))
sf.write(str(out_dir / "vinyl_stop.wav"), np.stack([stop, stop], 1), sr)

# airhorn
n = int(sr * 0.6)
phase = np.cumsum(np.full(n, 250 / sr))
horn = (np.sign(np.sin(2 * np.pi * phase)) * 0.5).astype(np.float32)
horn[:int(sr * 0.02)] *= np.linspace(0, 1, int(sr * 0.02)).astype(np.float32)
horn[-int(sr * 0.05):] *= np.linspace(1, 0, int(sr * 0.05)).astype(np.float32)
sf.write(str(out_dir / "airhorn.wav"), np.stack([horn, horn], 1), sr)

# dj_tag
n = int(sr * 0.4)
noise = (rng.randn(n) * 0.2).astype(np.float32)
tone = (np.sin(2 * np.pi * 600 * np.arange(n) / sr) * 0.3).astype(np.float32)
tag = ((noise + tone) * np.linspace(1, 0, n).astype(np.float32))
sf.write(str(out_dir / "dj_tag.wav"), np.stack([tag, tag], 1), sr)

print(f"5 bridge samples written to {out_dir}")
