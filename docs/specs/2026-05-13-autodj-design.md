# AutoDJ — Design Specification

**Date:** 2026-05-13
**Status:** Approved (pending spec review)
**Owner:** rw222ix@student.lnu.se

---

## 1. Purpose

AutoDJ is a local desktop tool that takes two audio files in arbitrary formats and produces a single mixed audio file with a natural-sounding transition between them. The user controls transition type, length, optional effect, and optional bridge sample. The system uses beat- and energy-aware audio analysis so the join feels like a human DJ made it rather than a hard cut or naive fade.

**Primary user:** a single user on Windows running the tool locally via a browser UI. No multi-user/auth/cloud requirements.

**Out of scope for v1:**
- More than two tracks per mix.
- Real-time DJing / live playback control.
- Stem separation (vocal/drums) — the transition operates on the full mix.
- Key-shifting / pitch correction of one track to match the other's key (only tempo bending is supported).
- Publishing or sharing of mixes.

---

## 2. Success Criteria

1. User uploads two audio files in any of: MP3, WAV, FLAC, M4A/AAC, OGG. Both are decoded without manual format conversion.
2. With default settings ("crossfade, 16 bars, no effect, no bridge"), the produced mix is beat-aligned during the transition — when BPMs are within 8% of each other, detected beats from A and B in the rendered transition region fall within ±15 ms of a shared beat grid (verified by §7's beat-grid test).
3. The user can change transition type, transition length, effect, and bridge from a single screen and re-render. Performance target: under 15 seconds for songs ≤ 8 minutes each on a modern laptop (aspirational — not gated by tests in v1, but the E2E test logs render time for tracking).
4. The mix is downloadable as both WAV (lossless) and MP3 (320 kbps).
5. The system never produces a mix that clips: the **sample-peak** of the final mix stays ≤ -0.5 dBFS (verified by §7).
6. Unit + E2E tests pass on four fixture pairs covering: same BPM, close BPM (within 8%), far BPM (>8%), variable BPM.

---

## 3. Architecture Overview

```
┌────────────────────────────────────────────────────────────────┐
│  Browser (localhost:5173)                                       │
│  React + Vite UI: upload, options, preview, download            │
└──────────────────────────┬─────────────────────────────────────┘
                           │ HTTP (JSON + multipart)
┌──────────────────────────▼─────────────────────────────────────┐
│  FastAPI (localhost:8000)                                       │
│                                                                 │
│   audio_io ── analysis ── align ── transition ── render         │
│       │          │          │          │            │           │
│       ▼          ▼          ▼          ▼            ▼           │
│   ffmpeg     librosa    numpy      numpy        soundfile       │
│                                                  + ffmpeg       │
└────────────────────────────────────────────────────────────────┘
```

All processing is synchronous within a single request; no background worker queue is needed at this scale (single user, ~15 s jobs).

Files are stored under `E:\AutoDJ\workdir\<job-id>\` and cleaned up on a 24 h rolling basis by a small startup job.

---

## 4. Components

### 4.1 `audio_io` — format-agnostic load/save
- **Purpose:** Convert any supported input file into a normalized in-memory representation, and write final output in WAV and MP3.
- **Interface:**
  - `load(path: Path) -> AudioBuffer` where `AudioBuffer = { samples: np.ndarray[float32], sr: int = 44100, channels: int = 2 }`. Decoding goes through `ffmpeg` (resamples to 44.1 kHz stereo). **Peak-normalization to -1 dBFS is applied to the full buffer to give the transition headroom — this means non-transition regions of the final mix are also scaled by the same factor and are not bit-exact relative to the source.** The applied scaling factor per track is recorded in `mix.json`.
  - `save_wav(buf, path)` and `save_mp3(buf, path, bitrate="320k")`.
- **Dependencies:** `ffmpeg` binary in PATH, `soundfile` Python package.
- **Failure modes:** unknown codec → raise `UnsupportedFormat` with the ffmpeg stderr line attached.

### 4.2 `analysis` — per-track features
- **Purpose:** Extract everything downstream needs to pick a good transition point.
- **Outputs (per track):**
  - `bpm: float` — via `librosa.beat.beat_track`.
  - `bpm_confidence: float` (0–1) — defined concretely as the **normalized peak of the onset-strength autocorrelation** at the lag corresponding to the detected BPM, divided by the autocorrelation value at lag 0. Computed from `librosa.onset.onset_strength` + `librosa.autocorrelate`. Values ≥ 0.5 indicate a confident detection.
  - `beat_times: np.ndarray` — seconds of every detected beat.
  - `downbeats: np.ndarray` — every 4th beat starting from a chosen phase. **First-downbeat selection: among the first 4 detected beats, pick the one with the highest `librosa.onset.onset_strength` value as beat-1; downbeats are then every 4th beat from that index.** (v1 assumes 4/4 time signature; non-4/4 tracks will be analyzed but may produce off-grid downbeats — the user can manually nudge the start beat in the UI via the manual override.)
  - `key: str` — Krumhansl-Schmuckler estimate, e.g., `"A minor"`. Informational only in v1.
  - `rms_envelope: np.ndarray` — RMS energy in 100 ms windows for the full track.
  - `intro_window: (start_s, end_s)` — first 32 bars after the first downbeat where RMS rises monotonically.
  - `outro_window: (start_s, end_s)` — last 32 bars before the final downbeat where RMS declines or plateaus.
- **Performance target:** ≤ 2 s per 6-minute song on the user's machine (aspirational — logged but not test-gated).
- **Failure modes:** silence longer than 30 s contiguous → raise `InsufficientContent`. BPM confidence < 0.5 → still return the value but the UI surfaces a manual override.

### 4.3 `align` — choose the join
- **Purpose:** Given features for A and B, pick the exact sample indices where the transition starts/ends in each track, and decide whether to tempo-bend A's outro to lock its grid to B.
- **Algorithm:**
  1. Default transition point for A: latest downbeat inside `outro_window` such that there are at least `N` bars remaining (N = user-selected transition length).
  2. Default transition point for B: earliest downbeat inside `intro_window` with at least N bars of forward content.
  3. If `|bpm_A - bpm_B| / bpm_B ≤ 0.08`, compute time-stretch ratio `r = bpm_B / bpm_A` and apply `librosa.effects.time_stretch` to A's outro region only (not the whole track). Re-detect beats in the stretched region. **If the re-detected beat count in the stretched outro differs from the expected `N * 4` beats: trim the stretched buffer to end exactly at the (N×4)-th detected beat, then update `a_end_sample` to that trimmed length. If fewer than N×4 beats are detected, shrink N to the available bar count and surface a warning to the UI.**
  4. If outside 8%: skip tempo bend, return a flag `beat_match=False` that the UI can show as a warning.
- **Output:** `AlignmentPlan = { a_start_sample, a_end_sample, b_start_sample, b_end_sample, beat_match: bool, stretched_outro: Optional[np.ndarray], effective_bars: int }`.

### 4.4 `transition` — build the joined region
- **Purpose:** Produce the audio for the overlap region given a plan + user options.
- **Transition types:**
  - `crossfade(bars)`: equal-power curves (`cos²` / `sin²`) over `bars` × beats. Default.
  - `cut`: instant switch on the chosen downbeat (only sensible when `beat_match=True`).
- **Effects (applied to A's signal *before* the crossfade gain is multiplied in — i.e., the crossfade envelope shapes the effected signal, not the dry one — unless an individual effect explicitly overrides the envelope):**
  - `none` (default)
  - `lowpass_sweep`: Butterworth low-pass with cutoff sweeping from 20 kHz → 200 Hz across the transition. Applied to A's signal *before* the crossfade gain is applied.
  - `highpass_sweep`: high-pass 20 Hz → 4 kHz. Same insertion point as `lowpass_sweep`.
  - `echo_tail`: feedback delay synced to A's beat (1/4 note, 35% feedback) ramping in over the last 4 bars of A. Applied to A *before* the crossfade gain.
  - `reverb_wash`: **algorithmic reverb (scipy-based Schroeder-style: 4 parallel comb filters + 2 series allpass filters, room size ≈ 0.7, damping ≈ 0.5).** Wet mix ramps 0→0.6 across the transition. Applied to A *before* the crossfade gain. (No external IR file required; chosen over convolution to keep the dependency footprint small.)
  - `backspin`: **overrides the A channel's crossfade envelope for the final 1 bar of the transition.** The last bar of A's contribution is replaced by a time-reversed copy of the preceding bar with a linear pitch-down ramp (1.0 → 0.5×). During this final bar, A is mixed at a fixed -3 dB (not the equal-power curve) and B continues on its normal curve. The remainder of the crossfade (everything before the final bar) follows the standard envelope.
- **Bridges (optional, inserted *before* the crossfade starts, beat-aligned to A's outgoing beat grid):**
  - `none` (default)
  - `drumroll`, `sweep_up`, `vinyl_stop`, `airhorn`, `dj_tag` — each shipped as a 44.1 kHz stereo WAV in `E:\AutoDJ\samples\`. Bridge length is preserved; A continues underneath at -6 dB during the bridge.
- **Output:** `np.ndarray` representing the full mix (A pre-transition + transition region + B post-transition), peak-normalized to -0.5 dBFS.

### 4.5 `render` — write outputs
- **Purpose:** Persist the mix and a metadata sidecar.
- **Outputs per job:**
  - `mix.wav`
  - `mix.mp3`
  - `mix.json` — `{ bpm_a, bpm_b, key_a, key_b, transition_start_s, transition_end_s, bars, type, effect, bridge, beat_match }` for transparency and debugging.

### 4.6 `api` — FastAPI surface
- `POST /analyze` (multipart: `file_a`, `file_b`) → `{ job_id, a: {bpm, key, duration, suggested_start}, b: {...} }`.
- `POST /mix` (JSON: `{ job_id, type, bars, effect, bridge, manual_bpm_a?, manual_bpm_b? }`) → `{ status: "ok", preview_url, download_wav_url, download_mp3_url, beat_match: bool, effective_bars: int, warning?: "bars_reduced" | "short_track" | ... }`.
- `GET /preview/{job_id}` → 20 s WAV centered on the transition.
- `GET /download/{job_id}.{wav|mp3}` → final file.
- CORS: only `http://localhost:5173`.

### 4.7 `ui` — React frontend
- **Single screen, three sections:**
  1. **Upload** — two drag-and-drop zones; on drop the file is sent to `/analyze` immediately and BPM/key/duration appear.
  2. **Options** — `transition type` (radio), `length in bars` (4/8/16/32 segmented), `effect` (dropdown), `bridge` (dropdown), manual BPM override fields (shown only when confidence is low).
  3. **Output** — "Preview transition" button (plays the 20 s preview inline), "Render full mix" button (then shows WAV + MP3 download links and the `mix.json` summary).
- **No routing, no persistence between sessions in v1.** State lives in memory; refreshing the page loses the job.

---

## 5. Data Flow

1. User drops `a.flac` and `b.m4a` → frontend POSTs both to `/analyze`.
2. Backend runs `audio_io.load` → `analysis.extract` for each, returns features + `job_id`.
3. User picks `crossfade / 16 bars / lowpass_sweep / drumroll`, clicks "Preview transition".
4. Frontend POSTs to `/mix`. Backend: `align.plan` → `transition.build` → `render.write` → returns URLs.
5. User listens to preview, adjusts options, re-renders (same `job_id`, new options — analysis cached).
6. User clicks download.

---

## 6. Error Handling

| Condition | System behavior |
|---|---|
| Unsupported codec | 415 with ffmpeg stderr; UI shows red error under the upload tile. |
| Track < 60 s | 200 with `warning: "short_track"`; UI shows yellow warning but allows continue. |
| BPM confidence < 0.5 | Feature returned; UI marks BPM field yellow and exposes manual override. |
| `analysis.InsufficientContent` (silence > 30 s) | 422 with `error: "insufficient_content"`; UI shows red error under the offending upload tile asking for a different file. |
| `|bpm_a - bpm_b| / bpm_b > 0.08` | Mix succeeds but `beat_match=False` in the response; UI shows yellow banner: "BPMs too different to beat-match — using crossfade only." |
| User selects `cut` with `beat_match=False` | 422; UI disables the `cut` radio when the BPMs are too far apart. |
| `align` shrinks N due to too few beats in stretched outro | 200 with `warning: "bars_reduced"` and `effective_bars` in response; UI shows yellow banner: "Transition shortened to X bars to stay beat-aligned." |
| Bridge sample WAV missing from `samples/` | 500 with `error: "bridge_sample_missing"` naming the file; UI shows red toast with the path. Mix is not produced rather than silently dropping the bridge. |
| File > 15 min duration | 413 with `error: "file_too_long"`; UI shows red error under the upload tile. |
| Disk full / write error | 500 with the OS error; UI shows red toast. |
| Job ID unknown | 404. |

The pipeline never silently degrades — every fallback is surfaced to the UI.

---

## 7. Testing Strategy

### 7.1 Unit tests (`pytest`)
- `audio_io`: load each supported format, assert sample rate, channels, and that round-trip WAV→load matches within 1e-6 (modulo the documented peak-normalization scaling).
- `analysis`: on fixtures with known BPM (click tracks at 90, 120, 128, 174), assert detected BPM within ±0.5; assert `bpm_confidence ≥ 0.7` on those clean fixtures.
- `align`: synthetic case with identical BPM → assert downbeat indices match; mismatched BPM within 8% → assert stretched outro length differs by expected ratio and `effective_bars == N`; **fixture where A's outro is shorter than requested N bars → assert `effective_bars < N` and warning surfaced.**
- `transition`: assert output buffer length = expected, assert sample-peak ≤ -0.5 dBFS, assert silence between bridge end and crossfade start is 0 samples. **Beat-grid alignment test:** on a same-BPM fixture pair, run analysis on the rendered transition region and assert that the nearest detected beats from A and from B (identified by cross-correlating against each source's onset-strength signal in that region) fall within ±15 ms of a shared grid derived from the chosen BPM.
- `render`: assert WAV and MP3 files exist and decode back to the same number of samples (±10 ms for MP3 padding).

### 7.2 Fixtures in `tests/fixtures/`
- `click_120.wav`, `click_128.wav` — synthetic, generated by a helper in `conftest.py`.
- Four real-music pairs (royalty-free, ~30 s each) sourced from a CC0 library, covering: same BPM, close BPM (124 vs 128), far BPM (90 vs 170), variable BPM.

### 7.3 End-to-end test
A single `pytest` test boots the FastAPI app via `TestClient`, POSTs two fixtures to `/analyze`, then `/mix` with default options, then `GET /download/{id}.wav`, and asserts the resulting file:
- decodes successfully,
- has duration within ±100 ms of `len(a) + len(b) - transition_length`,
- has sample-peak ≤ -0.5 dBFS,
- includes the bridge sample's first 100 ms (detected by cross-correlation against the bridge WAV) when a bridge was requested.

The E2E test also **logs total render wall-time** (analyze + mix) to stdout. This is informational only — not asserted — so a slow CI machine does not fail the build, but regressions are visible.

### 7.4 What is *not* automated
Subjective "does it sound natural" — that is judged by the user during interactive use. The tests guarantee the pipeline produces *correct* audio; the design guarantees it produces *good-sounding* audio.

---

## 8. File Structure

```
E:\AutoDJ\
├── backend\
│   ├── app\
│   │   ├── __init__.py
│   │   ├── audio_io.py
│   │   ├── analysis.py
│   │   ├── align.py
│   │   ├── transition.py
│   │   ├── render.py
│   │   ├── api.py
│   │   └── config.py
│   ├── tests\
│   │   ├── conftest.py
│   │   ├── fixtures\
│   │   ├── test_audio_io.py
│   │   ├── test_analysis.py
│   │   ├── test_align.py
│   │   ├── test_transition.py
│   │   ├── test_render.py
│   │   └── test_e2e.py
│   ├── pyproject.toml
│   └── README.md
├── frontend\
│   ├── src\
│   │   ├── App.tsx
│   │   ├── components\
│   │   │   ├── UploadTile.tsx
│   │   │   ├── OptionsPanel.tsx
│   │   │   └── OutputPanel.tsx
│   │   ├── api.ts
│   │   └── types.ts
│   ├── index.html
│   ├── package.json
│   └── vite.config.ts
├── samples\
│   ├── drumroll.wav
│   ├── sweep_up.wav
│   ├── vinyl_stop.wav
│   ├── airhorn.wav
│   └── dj_tag.wav
├── workdir\           (gitignored; per-job scratch)
├── scripts\
│   ├── setup.ps1      (creates venv, installs deps, checks ffmpeg)
│   └── run.ps1        (starts backend + frontend dev servers)
├── docs\
│   └── specs\
│       └── 2026-05-13-autodj-design.md   ← this file
└── README.md
```

---

## 9. Tech Stack

**Backend (Python 3.11+):**
- FastAPI, Uvicorn — HTTP server.
- librosa — beat/BPM/key/onset analysis, time-stretching.
- numpy, scipy — DSP primitives (Butterworth filters for the sweeps, comb/allpass for the algorithmic reverb, delay line for echo, autocorrelation for BPM confidence).
- soundfile — WAV read/write.
- python-multipart — file uploads.
- `ffmpeg` binary (required in PATH) — format conversion + MP3 export.

**Frontend:**
- Vite + React + TypeScript.
- Plain CSS (no UI framework needed for one screen).
- `wavesurfer.js` (optional, nice-to-have) — to render a small waveform under each upload tile.

**Dev tooling:**
- `ruff` + `mypy` for backend.
- `eslint` + `tsc --noEmit` for frontend.
- `pytest` for backend tests.

---

## 10. Non-Goals / Explicit YAGNI

- No auth, no user accounts.
- No persistent job history — refresh = lose state.
- No cloud deploy story; runs locally only.
- No mobile / tablet UI.
- No support for time signatures other than 4/4.
- No live MIDI control.
- No real-time monitoring during render.
- No batch mode (one pair at a time).

These are all reasonable v2 candidates but explicitly excluded from v1 to keep the surface small enough to ship in one focused effort.

---

## 11. Risks & Open Questions

| Risk | Mitigation |
|---|---|
| `librosa` BPM detection wrong on EDM with heavy sub-bass | Confidence threshold + manual override in UI. |
| Time-stretching A's outro audibly distorts vocals | Stretch limited to ≤ 8% ratio; effect is short (transition region only); informally validated by user during dev. |
| ffmpeg not installed | `scripts/setup.ps1` checks and prints install instructions. |
| Large files (> 15 min) blow memory | Document 15 min / file limit in README; reject larger uploads at the API layer with a clear error. |

No open questions for v1.
