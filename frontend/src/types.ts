export type TransitionType = "crossfade" | "cut";
export type EffectType = "none" | "lowpass_sweep" | "highpass_sweep" | "echo_tail" | "reverb_wash" | "backspin";
export type BridgeType = "none" | "drumroll" | "sweep_up" | "vinyl_stop" | "airhorn" | "dj_tag";

export interface TrackSummary {
  bpm: number;
  bpm_confidence: number;
  key: string;
  duration: number;
  suggested_start: number;
}

export interface AnalyzeResponse {
  job_id: string;
  a: TrackSummary;
  b: TrackSummary;
  warnings?: string[];
}

export interface MixRequest {
  job_id: string;
  type: TransitionType;
  bars: number;
  effect: EffectType;
  bridge: BridgeType;
  manual_bpm_a?: number;
  manual_bpm_b?: number;
}

export interface MixResponse {
  status: "ok";
  preview_url: string;
  download_wav_url: string;
  download_mp3_url: string;
  beat_match: boolean;
  effective_bars: number;
  warning?: string | null;
}
