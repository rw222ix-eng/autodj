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
    elif options.type == "cut":
        mixed_region = b_intro
    else:
        raise ValueError(f"unknown transition type: {options.type}")

    full = np.concatenate([pre_a, mixed_region, post_b], axis=0).astype(np.float32)
    return _peak_normalize(full, OUTPUT_PEAK_DBFS)
