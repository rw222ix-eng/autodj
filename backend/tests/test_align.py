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
    a_outro_samples = p.a_end_sample - p.a_start_sample
    ratio = len(p.stretched_outro) / a_outro_samples
    # 128/120 ≈ 1.0667 → stretched is ~6.7% shorter; ±trim slack
    assert 0.85 < ratio < 1.05


def test_far_bpm_skips_stretch(click_90_wav, click_174_wav):
    buf_a = load(click_90_wav)
    a = analyze(buf_a)
    b = analyze(load(click_174_wav))
    p = plan(a, b, bars=4, a_buffer=buf_a.samples)
    assert p.beat_match is False
    assert p.stretched_outro is None
