import pytest
from app.audio_io import load
from app.analysis import analyze, InsufficientContent


@pytest.mark.parametrize("fixture, expected_bpm", [
    ("click_90_wav", 90),
    ("click_120_wav", 120),
    ("click_128_wav", 128),
    ("click_174_wav", 174),
])
def test_bpm_detection_within_half_bpm(request, fixture, expected_bpm):
    path = request.getfixturevalue(fixture)
    buf = load(path)
    features = analyze(buf)
    assert abs(features.bpm - expected_bpm) < 0.5, (
        f"detected {features.bpm}, expected {expected_bpm}"
    )
    assert features.bpm_confidence >= 0.7
    assert len(features.beat_times) >= 25


def test_rms_envelope_and_windows(click_120_wav):
    buf = load(click_120_wav)
    f = analyze(buf)
    assert f.rms_envelope.ndim == 1
    assert 270 <= len(f.rms_envelope) <= 330
    intro_start, intro_end = f.intro_window
    outro_start, outro_end = f.outro_window
    assert 0 <= intro_start < intro_end <= f.duration_s
    assert 0 <= outro_start < outro_end <= f.duration_s
    assert intro_end <= outro_start


def test_key_detection_a_minor(a_minor_chord_wav):
    f = analyze(load(a_minor_chord_wav))
    assert f.key.lower() in {"a minor", "c major"}


def test_long_silence_raises(silent_40s_wav):
    buf = load(silent_40s_wav)
    with pytest.raises(InsufficientContent):
        analyze(buf)
