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
    assert 0.88 < peak <= 0.90
