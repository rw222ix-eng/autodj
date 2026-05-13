import numpy as np
import pytest

from app.audio_io import load, UnsupportedFormat, save_wav, save_mp3


def test_load_wav_returns_normalized_stereo_44k(click_120_wav):
    buf = load(click_120_wav)
    assert buf.sr == 44_100
    assert buf.channels == 2
    assert buf.samples.dtype == np.float32
    assert buf.samples.ndim == 2
    assert buf.samples.shape[1] == 2
    peak = float(np.max(np.abs(buf.samples)))
    assert 0.88 < peak <= 0.90


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


def test_save_wav_roundtrip(tmp_path, click_120_wav):
    buf = load(click_120_wav)
    out = tmp_path / "out.wav"
    save_wav(buf, out)
    reloaded = load(out)
    assert reloaded.sr == buf.sr
    assert reloaded.samples.shape == buf.samples.shape


def test_save_mp3_produces_decodable_file(tmp_path, click_120_wav):
    buf = load(click_120_wav)
    out = tmp_path / "out.mp3"
    save_mp3(buf, out)
    assert out.exists()
    reloaded = load(out)
    diff = abs(reloaded.samples.shape[0] - buf.samples.shape[0])
    assert diff < 2205, f"length differs by {diff} samples"
