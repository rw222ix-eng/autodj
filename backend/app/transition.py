from dataclasses import dataclass
from typing import Literal
import numpy as np
from pathlib import Path
import soundfile as sf
from scipy.signal import lfilter

from .align import AlignmentPlan
from .config import OUTPUT_PEAK_DBFS, SAMPLES_DIR


class BridgeSampleMissing(Exception):
    pass

TransitionType = Literal["crossfade", "cut"]
EffectType = Literal["none", "lowpass_sweep", "highpass_sweep", "echo_tail", "reverb_wash", "backspin"]
BridgeType = Literal["none", "drumroll", "sweep_up", "vinyl_stop", "airhorn", "dj_tag"]


@dataclass
class TransitionOptions:
    type: TransitionType = "crossfade"
    bars: int = 16
    effect: EffectType = "none"
    bridge: BridgeType = "none"


def _peak_normalize(x: np.ndarray, target_dbfs: float) -> np.ndarray:
    peak = float(np.max(np.abs(x))) or 1.0
    target = 10 ** (target_dbfs / 20)
    if peak <= target:
        return x
    return (x * (target / peak)).astype(np.float32)


def _equal_power(n: int) -> tuple[np.ndarray, np.ndarray]:
    t = np.linspace(0.0, np.pi / 2, n, dtype=np.float32)
    fade_out = np.cos(t) ** 2
    fade_in = np.sin(t) ** 2
    return fade_out, fade_in


def _swept_filter(x: np.ndarray, sr: int, btype: str,
                   start_hz: float, end_hz: float) -> np.ndarray:
    """Time-varying lowpass/highpass via cascaded one-pole IIR, sample-by-sample.

    Sweeps cutoff exponentially from start_hz to end_hz over len(x) samples.
    Four-pole cascade for ~24 dB/oct rolloff.
    """
    n = len(x)
    if n == 0:
        return x.astype(np.float32)
    out = np.empty_like(x, dtype=np.float32)
    cutoffs = np.exp(np.linspace(np.log(max(20.0, start_hz)),
                                  np.log(max(20.0, end_hz)), n))
    alphas = np.exp(-2 * np.pi * cutoffs / sr).astype(np.float32)
    poles = 4
    n_ch = x.shape[1]
    state = np.zeros((poles, n_ch), dtype=np.float32)
    if btype == "low":
        # cascaded one-pole lowpass: y[n] = (1-a)*x[n] + a*y[n-1]
        for i in range(n):
            a = alphas[i]
            b = np.float32(1.0) - a
            sig = x[i].astype(np.float32)
            for p in range(poles):
                state[p] = b * sig + a * state[p]
                sig = state[p]
            out[i] = sig
    elif btype == "high":
        # highpass = input - lowpass (single pole), cascaded
        for i in range(n):
            a = alphas[i]
            b = np.float32(1.0) - a
            sig = x[i].astype(np.float32)
            for p in range(poles):
                state[p] = b * sig + a * state[p]
                sig = sig - state[p]
            out[i] = sig
    else:
        raise ValueError(f"unknown filter btype: {btype}")
    return out


def _apply_lowpass_sweep(x: np.ndarray, sr: int = 44_100) -> np.ndarray:
    # Sweep lowpass from ~8 kHz down to ~80 Hz over the region (log scale)
    return _swept_filter(x, sr, "low", 8000.0, 80.0)


def _apply_highpass_sweep(x: np.ndarray, sr: int = 44_100) -> np.ndarray:
    # Sweep highpass from ~40 Hz up to ~4 kHz over the region (log scale)
    return _swept_filter(x, sr, "high", 40.0, 4000.0)


def _apply_echo_tail(x: np.ndarray, bpm: float, sr: int = 44_100,
                     feedback: float = 0.6) -> np.ndarray:
    """Add eighth-note delays with feedback, ramping in over the region."""
    delay_samples = int(sr * 60 / bpm / 2)  # eighth note
    if delay_samples <= 0 or delay_samples >= len(x):
        return x.astype(np.float32)
    out = x.astype(np.float32).copy()
    ramp = np.linspace(0.0, 1.0, len(x), dtype=np.float32)[:, None]
    delayed = np.zeros_like(out)
    for offset in range(1, 8):
        gain = feedback ** offset
        shifted = delay_samples * offset
        if shifted >= len(out):
            break
        delayed[shifted:] += x[:-shifted].astype(np.float32) * gain
    out = out + delayed * ramp
    return out.astype(np.float32)


def _load_bridge(name: str) -> np.ndarray:
    if name == "none":
        return np.zeros((0, 2), dtype=np.float32)
    path = Path(SAMPLES_DIR) / f"{name}.wav"
    if not path.exists():
        raise BridgeSampleMissing(str(path))
    data, _ = sf.read(str(path), dtype="float32", always_2d=True)
    if data.shape[1] == 1:
        data = np.repeat(data, 2, axis=1)
    return data.astype(np.float32)


def _comb_filter(x_mono: np.ndarray, delay: int, feedback: float) -> np.ndarray:
    b = np.zeros(delay + 1, dtype=np.float32)
    b[0] = 1.0
    a = np.zeros(delay + 1, dtype=np.float32)
    a[0] = 1.0
    a[delay] = -feedback
    return lfilter(b, a, x_mono).astype(np.float32)


def _allpass_filter(x_mono: np.ndarray, delay: int, feedback: float = 0.5) -> np.ndarray:
    b = np.zeros(delay + 1, dtype=np.float32)
    b[0] = -feedback
    b[delay] = 1.0
    a = np.zeros(delay + 1, dtype=np.float32)
    a[0] = 1.0
    a[delay] = -feedback
    return lfilter(b, a, x_mono).astype(np.float32)


def _apply_reverb_wash(x: np.ndarray, sr: int = 44_100) -> np.ndarray:
    combs = [1116, 1188, 1277, 1356]
    allpasses = [556, 441]
    wet = np.zeros_like(x)
    for ch in range(x.shape[1]):
        signal = x[:, ch]
        ch_wet = np.zeros_like(signal)
        for d in combs:
            ch_wet += _comb_filter(signal, d, feedback=0.7)
        ch_wet /= len(combs)
        for d in allpasses:
            ch_wet = _allpass_filter(ch_wet, d, feedback=0.5)
        wet[:, ch] = ch_wet
    ramp = np.linspace(0.0, 0.6, len(x), dtype=np.float32)[:, None]
    return (x + wet * ramp).astype(np.float32)


def _apply_backspin(
    x: np.ndarray, fade_out: np.ndarray, bpm: float, bars: int, sr: int = 44_100
) -> tuple[np.ndarray, np.ndarray]:
    bar_samples = int(sr * 60 / bpm * 4)
    n = len(x)
    if bar_samples >= n or bar_samples < 2:
        return x, fade_out
    cut = n - bar_samples
    source = x[cut - bar_samples:cut][::-1]
    speed_ramp = np.linspace(1.0, 0.5, bar_samples, dtype=np.float32)
    playhead = np.cumsum(speed_ramp) - speed_ramp[0]
    playhead = playhead * ((bar_samples - 1) / playhead[-1])
    idx = np.arange(bar_samples, dtype=np.float32)
    played = np.empty_like(source)
    played[:, 0] = np.interp(playhead, idx, source[:, 0])
    played[:, 1] = np.interp(playhead, idx, source[:, 1])
    out = x.copy()
    out[cut:cut + bar_samples] = played
    env = fade_out.copy()
    env[cut:] = 10 ** (-3 / 20)
    return out, env


def build(
    a_samples: np.ndarray,
    b_samples: np.ndarray,
    plan: AlignmentPlan,
    options: TransitionOptions,
    bpm_a: float | None = None,
) -> np.ndarray:
    pre_a = a_samples[:plan.a_start_sample]
    a_outro = a_samples[plan.a_start_sample:plan.a_end_sample]
    b_intro = b_samples[plan.b_start_sample:plan.b_end_sample]
    post_b = b_samples[plan.b_end_sample:]

    if plan.stretched_outro is not None:
        a_outro = plan.stretched_outro

    n = min(len(a_outro), len(b_intro))
    a_outro = a_outro[:n]
    b_intro = b_intro[:n]

    if options.type == "crossfade":
        fo, fi = _equal_power(n)
        effected_a = a_outro
        if options.effect == "lowpass_sweep":
            effected_a = _apply_lowpass_sweep(a_outro)
        elif options.effect == "highpass_sweep":
            effected_a = _apply_highpass_sweep(a_outro)
        elif options.effect == "echo_tail":
            effected_a = _apply_echo_tail(a_outro, bpm=bpm_a or 120.0)
        elif options.effect == "reverb_wash":
            effected_a = _apply_reverb_wash(a_outro)
        elif options.effect == "backspin":
            effected_a, fo = _apply_backspin(a_outro, fo, bpm=bpm_a or 120.0, bars=options.bars)
        mixed_region = effected_a * fo[:, None] + b_intro * fi[:, None]
    elif options.type == "cut":
        mixed_region = b_intro
    else:
        raise ValueError(f"unknown transition type: {options.type}")

    bridge = _load_bridge(options.bridge)
    if len(bridge) > 0:
        bridge_len = len(bridge)
        # Underbed = A's outro continuation, starting at a_start_sample.
        # The bridge plays as an overlay on top of the start of A's outro;
        # the crossfade then begins from a_start_sample as usual.
        underbed_end = min(plan.a_start_sample + bridge_len, len(a_samples))
        underbed = a_samples[plan.a_start_sample:underbed_end]
        if len(underbed) < bridge_len:
            pad = np.zeros((bridge_len - len(underbed), 2), dtype=np.float32)
            underbed = np.concatenate([underbed, pad], axis=0)
        underbed = underbed[:bridge_len]
        underbed_gain = 10 ** (-6 / 20)
        bridge_region = bridge + underbed * underbed_gain
        full = np.concatenate([pre_a, bridge_region, mixed_region, post_b], axis=0).astype(np.float32)
    else:
        full = np.concatenate([pre_a, mixed_region, post_b], axis=0).astype(np.float32)
    return _peak_normalize(full, OUTPUT_PEAK_DBFS)
