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


def test_lowpass_sweep_attenuates_highs(click_120_wav):
    buf = load(click_120_wav)
    a = analyze(buf); b = analyze(buf)
    p = plan(a, b, bars=4, a_buffer=buf.samples)
    plain = build(buf.samples, buf.samples, p,
                  TransitionOptions(type="crossfade", bars=4, effect="none"), bpm_a=a.bpm)
    swept = build(buf.samples, buf.samples, p,
                  TransitionOptions(type="crossfade", bars=4, effect="lowpass_sweep"), bpm_a=a.bpm)
    region_start = p.a_start_sample
    region_end = p.a_end_sample
    plain_hf = np.abs(np.fft.rfft(plain[region_start:region_end, 0]))[len(plain[region_start:region_end, 0])//4:].sum()
    swept_hf = np.abs(np.fft.rfft(swept[region_start:region_end, 0]))[len(swept[region_start:region_end, 0])//4:].sum()
    assert swept_hf < plain_hf * 0.5


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
    region_len = p.a_end_sample - p.a_start_sample
    tail = slice(p.a_start_sample + region_len // 2, p.a_end_sample)
    assert np.sum(echoed[tail] ** 2) > np.sum(plain[tail] ** 2) * 1.05
