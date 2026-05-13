import pytest
from app.audio_io import load
from app.analysis import analyze


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
