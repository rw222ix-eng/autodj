from dataclasses import dataclass
from typing import Optional
import numpy as np
import librosa

from .analysis import TrackFeatures
from .config import TARGET_SAMPLE_RATE, BPM_BEAT_MATCH_TOLERANCE


@dataclass
class AlignmentPlan:
    a_start_sample: int
    a_end_sample: int
    b_start_sample: int
    b_end_sample: int
    beat_match: bool
    effective_bars: int
    stretched_outro: Optional[np.ndarray] = None
    warning: Optional[str] = None


def _samples(t: float) -> int:
    return int(round(t * TARGET_SAMPLE_RATE))


def _bar_seconds(bpm: float) -> float:
    return 60 / bpm * 4


def plan(
    a: TrackFeatures, b: TrackFeatures, bars: int,
    a_buffer: Optional[np.ndarray] = None,
) -> AlignmentPlan:
    effective_bars = bars
    warning: Optional[str] = None

    bar_s_a = _bar_seconds(a.bpm)
    bar_s_b = _bar_seconds(b.bpm)

    outro_start, outro_end = a.outro_window
    intro_start, intro_end = b.intro_window

    # Room check (Task 3.3 contribution): cap effective_bars to what intro/outro can fit.
    outro_available_s = outro_end - outro_start
    intro_available_s = intro_end - intro_start
    max_bars_a = int(outro_available_s // bar_s_a)
    max_bars_b = int(intro_available_s // bar_s_b)
    cap = max(1, min(max_bars_a, max_bars_b))
    if cap < bars:
        effective_bars = cap
        warning = "bars_reduced"

    needed_a = effective_bars * bar_s_a
    needed_b = effective_bars * bar_s_b

    a_downbeats_in_outro = [d for d in a.downbeats if outro_start <= d <= outro_end - needed_a]
    if not a_downbeats_in_outro:
        a_downbeats_in_outro = [outro_start]
    a_start_s = max(a_downbeats_in_outro)

    b_downbeats_in_intro = [d for d in b.downbeats if intro_start <= d <= intro_end - needed_b]
    if not b_downbeats_in_intro:
        b_downbeats_in_intro = [intro_start]
    b_start_s = min(b_downbeats_in_intro)

    a_end_s = a_start_s + needed_a
    b_end_s = b_start_s + needed_b

    diff = abs(a.bpm - b.bpm) / b.bpm
    beat_match = diff <= BPM_BEAT_MATCH_TOLERANCE

    return AlignmentPlan(
        a_start_sample=_samples(a_start_s),
        a_end_sample=_samples(a_end_s),
        b_start_sample=_samples(b_start_s),
        b_end_sample=_samples(b_end_s),
        beat_match=beat_match,
        effective_bars=effective_bars,
        warning=warning,
    )
