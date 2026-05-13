import numpy as np

from app.audio_io import load
from app.analysis import analyze, TrackFeatures
from app.align import plan


def test_same_bpm_alignment(click_120_wav):
    a = analyze(load(click_120_wav))
    b = analyze(load(click_120_wav))
    p = plan(a, b, bars=4)
    assert p.beat_match is True
    assert p.effective_bars == 4
    assert p.a_end_sample > p.a_start_sample
    assert p.b_end_sample > p.b_start_sample
    bar_samples = int(44_100 * 60 / a.bpm * 4 * 4)
    beat_samples = int(44_100 * 60 / a.bpm)
    assert abs((p.a_end_sample - p.a_start_sample) - bar_samples) <= beat_samples


def test_close_bpm_stretches_outro(click_120_wav, click_128_wav):
    buf_a = load(click_120_wav)
    a = analyze(buf_a)
    b = analyze(load(click_128_wav))
    p = plan(a, b, bars=4, a_buffer=buf_a.samples)
    assert p.beat_match is True
    assert p.stretched_outro is not None
    # Pre-stretch expected outro: effective_bars * bar_seconds(a.bpm) * sr.
    # Comparing against (a_end_sample - a_start_sample) is trivially ~1.0 because
    # the implementation updates a_end_sample to match stretched_outro length.
    expected_pre_stretch_samples = int(p.effective_bars * (60 / a.bpm * 4) * 44_100)
    ratio = len(p.stretched_outro) / expected_pre_stretch_samples
    # 128/120 ≈ 1.067 → stretched should be ~0.937 × pre-stretch length, ± trim slack
    assert 0.85 < ratio < 1.00, f"stretch ratio {ratio:.3f} outside expected range"


def test_far_bpm_skips_stretch(click_90_wav, click_174_wav):
    buf_a = load(click_90_wav)
    a = analyze(buf_a)
    b = analyze(load(click_174_wav))
    p = plan(a, b, bars=4, a_buffer=buf_a.samples)
    assert p.beat_match is False
    assert p.stretched_outro is None


def test_short_outro_shrinks_bars():
    bpm = 120
    duration = 5.0
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
