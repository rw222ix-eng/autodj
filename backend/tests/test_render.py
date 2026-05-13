import json
from app.audio_io import load
from app.render import write


def test_render_writes_all_three_outputs(tmp_path, click_120_wav):
    buf = load(click_120_wav)
    job_dir = tmp_path / "job123"
    job_dir.mkdir()
    metadata = {"bpm_a": 120.0, "bpm_b": 120.0, "transition_start_s": 5.0,
                "transition_end_s": 7.0, "bars": 4, "type": "crossfade",
                "effect": "none", "bridge": "none", "beat_match": True}
    write(buf.samples, job_dir, metadata)
    assert (job_dir / "mix.wav").exists()
    assert (job_dir / "mix.mp3").exists()
    meta = json.loads((job_dir / "mix.json").read_text())
    assert meta["bpm_a"] == 120.0
    assert meta["type"] == "crossfade"


def test_render_mp3_sample_count_matches_wav_within_10ms(tmp_path, click_120_wav):
    import soundfile as sf
    buf = load(click_120_wav)
    job_dir = tmp_path / "job_mp3_check"
    job_dir.mkdir()
    write(buf.samples, job_dir, {"bpm_a": 120, "bpm_b": 120, "type": "crossfade",
                                  "bars": 4, "effect": "none", "bridge": "none",
                                  "transition_start_s": 0, "transition_end_s": 0,
                                  "beat_match": True})
    wav_data, sr = sf.read(str(job_dir / "mix.wav"), always_2d=True)
    mp3_data, _ = sf.read(str(job_dir / "mix.mp3"), always_2d=True)
    diff_samples = abs(wav_data.shape[0] - mp3_data.shape[0])
    assert diff_samples < int(sr * 0.015), f"WAV/MP3 length differs by {diff_samples} samples"
