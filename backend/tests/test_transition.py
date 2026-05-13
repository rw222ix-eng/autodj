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
    # Use silence as B so the mixed region IS A * fo (no B contamination).
    silent_b = np.zeros_like(buf.samples)
    plain = build(buf.samples, silent_b, p,
                  TransitionOptions(type="crossfade", bars=4, effect="none"), bpm_a=a.bpm)
    swept = build(buf.samples, silent_b, p,
                  TransitionOptions(type="crossfade", bars=4, effect="lowpass_sweep"), bpm_a=a.bpm)
    region = slice(p.a_start_sample, p.a_end_sample)
    plain_hf = np.abs(np.fft.rfft(plain[region, 0]))[len(plain[region, 0])//4:].sum()
    swept_hf = np.abs(np.fft.rfft(swept[region, 0]))[len(swept[region, 0])//4:].sum()
    assert swept_hf < plain_hf * 0.5


def test_highpass_sweep_attenuates_lows(click_120_wav):
    buf = load(click_120_wav)
    a = analyze(buf); b = analyze(buf)
    p = plan(a, b, bars=4, a_buffer=buf.samples)
    silent_b = np.zeros_like(buf.samples)
    plain = build(buf.samples, silent_b, p,
                  TransitionOptions(type="crossfade", bars=4, effect="none"), bpm_a=a.bpm)
    swept = build(buf.samples, silent_b, p,
                  TransitionOptions(type="crossfade", bars=4, effect="highpass_sweep"), bpm_a=a.bpm)
    region = slice(p.a_start_sample, p.a_end_sample)
    plain_lf = np.abs(np.fft.rfft(plain[region, 0]))[:50].sum()
    swept_lf = np.abs(np.fft.rfft(swept[region, 0]))[:50].sum()
    assert swept_lf < plain_lf * 0.6


def test_echo_tail_produces_repeats(click_120_wav):
    buf = load(click_120_wav)
    a = analyze(buf); b = analyze(buf)
    p = plan(a, b, bars=4, a_buffer=buf.samples)
    silent_b = np.zeros_like(buf.samples)
    plain = build(buf.samples, silent_b, p,
                  TransitionOptions(type="crossfade", bars=4, effect="none"), bpm_a=a.bpm)
    echoed = build(buf.samples, silent_b, p,
                   TransitionOptions(type="crossfade", bars=4, effect="echo_tail"), bpm_a=a.bpm)
    region_len = p.a_end_sample - p.a_start_sample
    tail = slice(p.a_start_sample + region_len // 2, p.a_end_sample)
    assert np.sum(echoed[tail] ** 2) > np.sum(plain[tail] ** 2) * 1.05


def test_reverb_wash_adds_energy(click_120_wav):
    buf = load(click_120_wav)
    a = analyze(buf); b = analyze(buf)
    p = plan(a, b, bars=4, a_buffer=buf.samples)
    silent_b = np.zeros_like(buf.samples)
    plain = build(buf.samples, silent_b, p,
                  TransitionOptions(type="crossfade", bars=4, effect="none"), bpm_a=a.bpm)
    reverbed = build(buf.samples, silent_b, p,
                     TransitionOptions(type="crossfade", bars=4, effect="reverb_wash"), bpm_a=a.bpm)
    region = slice(p.a_start_sample, p.a_end_sample)
    assert np.sum(reverbed[region] ** 2) > np.sum(plain[region] ** 2) * 1.05


def test_backspin_overrides_last_bar(click_120_wav):
    buf = load(click_120_wav)
    a = analyze(buf); b = analyze(buf)
    p = plan(a, b, bars=4, a_buffer=buf.samples)
    out = build(buf.samples, buf.samples, p,
                TransitionOptions(type="crossfade", bars=4, effect="backspin"), bpm_a=a.bpm)
    assert out.shape[1] == 2
    assert float(np.max(np.abs(out))) <= 10 ** (-0.5 / 20) + 0.01


from app.config import SAMPLES_DIR
import soundfile as sf
import pytest


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
    diff = out_br.shape[0] - out_no.shape[0]
    assert abs(diff - len(bridge)) < 100


def test_bridge_seamless_to_crossfade(click_120_wav):
    buf = load(click_120_wav)
    a = analyze(buf); b = analyze(buf)
    p = plan(a, b, bars=4, a_buffer=buf.samples)
    out = build(buf.samples, buf.samples, p,
                TransitionOptions(type="crossfade", bars=4, effect="none", bridge="drumroll"),
                bpm_a=a.bpm)
    bridge, _ = sf.read(str(SAMPLES_DIR / "drumroll.wav"), dtype="float32", always_2d=True)
    crossfade_start = p.a_start_sample + len(bridge)
    window = np.abs(out[crossfade_start - 50:crossfade_start + 50, 0])
    assert np.max(window) > 1e-3, "silence detected at bridge->crossfade join"


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


def test_beat_grid_alignment_within_15ms(click_120_wav):
    import librosa
    buf = load(click_120_wav)
    a = analyze(buf); b = analyze(buf)
    p = plan(a, b, bars=4, a_buffer=buf.samples)
    out = build(buf.samples, buf.samples, p,
                TransitionOptions(type="crossfade", bars=4, effect="none"), bpm_a=a.bpm)
    region = out[p.a_start_sample:p.a_end_sample, 0]
    onset_env = librosa.onset.onset_strength(y=region, sr=44_100)
    _, frames = librosa.beat.beat_track(onset_envelope=onset_env, sr=44_100)
    times = librosa.frames_to_time(frames, sr=44_100)
    beat_period = 60 / a.bpm
    for t in times:
        nearest_grid = round(t / beat_period) * beat_period
        assert abs(t - nearest_grid) < 0.015, f"beat at {t}s is {abs(t-nearest_grid)*1000:.1f}ms off grid"
