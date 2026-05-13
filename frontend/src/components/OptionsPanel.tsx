import type { TransitionType, EffectType, BridgeType } from "../types";

interface Props {
  type: TransitionType;
  bars: number;
  effect: EffectType;
  bridge: BridgeType;
  onChange: (patch: Partial<{ type: TransitionType; bars: number; effect: EffectType; bridge: BridgeType }>) => void;
  beatMatch: boolean;
}

const TIP_TRANSITION =
  "How the two tracks are joined. Crossfade gradually fades A out while fading B in. " +
  "Cut switches instantly on a downbeat — only available when both tracks share a BPM.";

const TIP_LENGTH =
  "How long the transition takes, measured in musical bars (4 beats per bar). " +
  "4 = quick switch, 32 = long blend. 16 works well for most tracks.";

const TIP_EFFECT =
  "Optional effect applied to track A's signal during the transition. " +
  "Hover each option in the dropdown for details.";

const TIP_BRIDGE =
  "Optional short audio insert placed before the transition starts. " +
  "Track A continues underneath at -6 dB while the bridge plays. " +
  "Hover each option in the dropdown for details.";

const EFFECT_TIPS: Record<EffectType, string> = {
  none: "No effect — clean crossfade only.",
  lowpass_sweep: "Filters out treble across the transition (20 kHz → 200 Hz) — A fades into a muffled wash.",
  highpass_sweep: "Filters out bass across the transition (20 Hz → 4 kHz) — A thins out leaving only highs.",
  echo_tail: "Adds tempo-synced quarter-note echoes ramping in during A's outro.",
  reverb_wash: "Adds increasing reverb (0 → 60% wet) — A dissolves into space.",
  backspin: "Vinyl-rewind effect on the last bar of A — reversed and pitched down 1.0× → 0.5×.",
};

const BRIDGE_TIPS: Record<BridgeType, string> = {
  none: "No bridge — go straight from A into the transition.",
  drumroll: "1-second decaying noise burst — builds tension before the drop.",
  sweep_up: "1-second upward chirp (80 Hz → 4 kHz) — classic riser.",
  vinyl_stop: "0.5-second pitch-down whoosh — sounds like stopping a record.",
  airhorn: "0.6-second square-wave honk at 250 Hz — party shout.",
  dj_tag: "0.4-second noise + tone burst — placeholder for a vocal tag.",
};

export default function OptionsPanel({ type, bars, effect, bridge, onChange, beatMatch }: Props) {
  return (
    <div className="options">
      <fieldset>
        <legend className="tooltip" data-tooltip={TIP_TRANSITION}>Transition</legend>
        <label><input type="radio" name="type" checked={type === "crossfade"}
          onChange={() => onChange({ type: "crossfade" })} /> Crossfade</label>
        <label><input type="radio" name="type" checked={type === "cut"} disabled={!beatMatch}
          onChange={() => onChange({ type: "cut" })} /> Cut {!beatMatch && "(needs beat-match)"}</label>
      </fieldset>
      <fieldset>
        <legend className="tooltip" data-tooltip={TIP_LENGTH}>Length (bars)</legend>
        {[4, 8, 16, 32].map((n) => (
          <label key={n}>
            <input type="radio" name="bars" checked={bars === n} onChange={() => onChange({ bars: n })} />
            {n}
          </label>
        ))}
      </fieldset>
      <label>
        <span className="tooltip" data-tooltip={TIP_EFFECT}>Effect:</span>
        <select value={effect} onChange={(e) => onChange({ effect: e.target.value as EffectType })}>
          {(Object.keys(EFFECT_TIPS) as EffectType[]).map((key) => (
            <option key={key} value={key} title={EFFECT_TIPS[key]}>
              {key === "none" ? "None"
                : key === "lowpass_sweep" ? "Low-pass sweep"
                : key === "highpass_sweep" ? "High-pass sweep"
                : key === "echo_tail" ? "Echo tail"
                : key === "reverb_wash" ? "Reverb wash"
                : "Backspin"}
            </option>
          ))}
        </select>
      </label>
      <label>
        <span className="tooltip" data-tooltip={TIP_BRIDGE}>Bridge:</span>
        <select value={bridge} onChange={(e) => onChange({ bridge: e.target.value as BridgeType })}>
          {(Object.keys(BRIDGE_TIPS) as BridgeType[]).map((key) => (
            <option key={key} value={key} title={BRIDGE_TIPS[key]}>
              {key === "none" ? "None"
                : key === "drumroll" ? "Drumroll"
                : key === "sweep_up" ? "Sweep up"
                : key === "vinyl_stop" ? "Vinyl stop"
                : key === "airhorn" ? "Airhorn"
                : "DJ tag"}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}
