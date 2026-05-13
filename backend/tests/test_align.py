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
