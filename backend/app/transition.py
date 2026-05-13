from dataclasses import dataclass
from typing import Literal
import numpy as np

from .align import AlignmentPlan
from .config import OUTPUT_PEAK_DBFS

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
        mixed_region = a_outro * fo[:, None] + b_intro * fi[:, None]
        if options.effect == "lowpass_sweep":
            mixed_region = _apply_lowpass_sweep(mixed_region)
        elif options.effect == "highpass_sweep":
            mixed_region = _apply_highpass_sweep(mixed_region)
        elif options.effect == "echo_tail":
            mixed_region = _apply_echo_tail(mixed_region, bpm=bpm_a or 120.0)
    elif options.type == "cut":
        mixed_region = b_intro
    else:
        raise ValueError(f"unknown transition type: {options.type}")

    full = np.concatenate([pre_a, mixed_region, post_b], axis=0).astype(np.float32)
    return _peak_normalize(full, OUTPUT_PEAK_DBFS)
