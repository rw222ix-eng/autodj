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
    overlap = p.a_end_sample - p.a_start_sample
    expected = p.a_end_sample + (buf_b.samples.shape[0] - p.b_start_sample) - overlap
    assert abs(mixed.shape[0] - expected) < 200
