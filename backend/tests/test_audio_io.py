import numpy as np
from app.audio_io import load


def test_load_wav_returns_normalized_stereo_44k(click_120_wav):
    buf = load(click_120_wav)
    assert buf.sr == 44_100
    assert buf.channels == 2
    assert buf.samples.dtype == np.float32
    assert buf.samples.ndim == 2
    assert buf.samples.shape[1] == 2
    peak = float(np.max(np.abs(buf.samples)))
    assert 0.88 < peak <= 0.90


import pytest
from app.audio_io import load, UnsupportedFormat


@pytest.mark.parametrize("fixture_name", ["click_120_mp3", "click_120_flac", "click_120_m4a"])
def test_load_handles_compressed_formats(request, fixture_name):
    path = request.getfixturevalue(fixture_name)
    buf = load(path)
    assert buf.sr == 44_100
    assert buf.channels == 2
    assert buf.samples.shape[1] == 2
    assert buf.samples.dtype.kind == "f"


def test_load_raises_on_unsupported_format(tmp_path):
    bad = tmp_path / "garbage.bin"
    bad.write_bytes(b"this is not audio")
    with pytest.raises(UnsupportedFormat):
        load(bad)
