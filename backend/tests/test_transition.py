import numpy as np
import pytest
import soundfile as sf

from app.audio_io import load
from app.analysis import analyze
from app.align import plan
from app.transition import build, TransitionOptions, BridgeSampleMissing
from app.config import OUTPUT_PEAK_DBFS, SAMPLES_DIR


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
    a = analyze(buf)
    b = analyze(buf)
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
    a = analyze(buf)
    b = analyze(buf)
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
    a = analyze(buf)
    b = analyze(buf)
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
    a = analyze(buf)
    b = analyze(buf)
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
    a = analyze(buf)
    b = analyze(buf)
    p = plan(a, b, bars=4, a_buffer=buf.samples)
    out = build(buf.samples, buf.samples, p,
                TransitionOptions(type="crossfade", bars=4, effect="backspin"), bpm_a=a.bpm)
    assert out.shape[1] == 2
    assert float(np.max(np.abs(out))) <= 10 ** (-0.5 / 20) + 0.01


def test_bridge_inserted_before_crossfade(click_120_wav):
    buf = load(click_120_wav)
    a = analyze(buf)
    b = analyze(buf)
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
    a = analyze(buf)
    b = analyze(buf)
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
    a = analyze(buf)
    b = analyze(buf)
    p = plan(a, b, bars=4, a_buffer=buf.samples)
    with pytest.raises(BridgeSampleMissing):
        build(buf.samples, buf.samples, p,
              TransitionOptions(type="crossfade", bars=4, effect="none", bridge="drumroll"),
              bpm_a=a.bpm)


def test_beat_grid_alignment_within_15ms(click_120_wav, tone_120_wav):
    """Verifies §2.2 success criterion: in the rendered transition region, beats
    contributed by A (click track) AND beats contributed by B (tone burst track)
    both fall within ±15 ms of a shared 120 BPM grid.

    Uses two DIFFERENT timbres at the same BPM so A-beats and B-beats can be
    distinguished by cross-correlation against each source's onset-strength signal.
    """
    import librosa
    buf_a = load(click_120_wav)
    buf_b = load(tone_120_wav)
    a = analyze(buf_a)
    b = analyze(buf_b)
    p = plan(a, b, bars=4, a_buffer=buf_a.samples)
    out = build(buf_a.samples, buf_b.samples, p,
                TransitionOptions(type="crossfade", bars=4, effect="none"),
                bpm_a=a.bpm)
    sr = 44_100
    region = out[p.a_start_sample:p.a_end_sample, 0]
    region_mono = region.astype(np.float32)
    # Source onset-strength signals (mono) of the same length as the region:
    a_outro_mono = buf_a.samples[p.a_start_sample:p.a_end_sample, 0].astype(np.float32)
    b_intro_mono = buf_b.samples[p.b_start_sample:p.b_end_sample, 0].astype(np.float32)
    n = min(len(region_mono), len(a_outro_mono), len(b_intro_mono))
    region_mono = region_mono[:n]
    a_outro_mono = a_outro_mono[:n]
    b_intro_mono = b_intro_mono[:n]

    # Detect beats in the region and label each by whether it correlates more strongly
    # with A's onset or B's onset in a small window around it.
    onset_region = librosa.onset.onset_strength(y=region_mono, sr=sr)
    _, frames = librosa.beat.beat_track(onset_envelope=onset_region, sr=sr)
    times = librosa.frames_to_time(frames, sr=sr)

    onset_a = librosa.onset.onset_strength(y=a_outro_mono, sr=sr)
    onset_b = librosa.onset.onset_strength(y=b_intro_mono, sr=sr)
    hop = 512  # librosa default for onset_strength

    a_beats = []
    b_beats = []
    for t in times:
        frame = int(t * sr / hop)
        if frame >= len(onset_a) or frame >= len(onset_b):
            continue
        # Compare which source had a stronger onset at this beat time
        # (look at a small ±2-frame window for robustness).
        lo = max(0, frame - 2)
        hi = min(len(onset_a), frame + 3)
        sa = float(onset_a[lo:hi].max())
        sb = float(onset_b[lo:hi].max())
        if sa > sb:
            a_beats.append(t)
        else:
            b_beats.append(t)

    # Both A and B should contribute at least one identifiable beat in a 4-bar region.
    assert len(a_beats) >= 1, f"no A-beats identified; times={times}"
    assert len(b_beats) >= 1, f"no B-beats identified; times={times}"

    # Every beat (regardless of source) must fall within ±15 ms of the shared grid.
    beat_period = 60 / a.bpm
    for label, beats in (("A", a_beats), ("B", b_beats)):
        for t in beats:
            nearest = round(t / beat_period) * beat_period
            offset_ms = abs(t - nearest) * 1000
            assert offset_ms < 15, (
                f"{label}-beat at {t:.3f}s is {offset_ms:.1f} ms off grid"
            )
