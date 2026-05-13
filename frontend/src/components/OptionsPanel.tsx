import type { TransitionType, EffectType, BridgeType } from "../types";

interface Props {
  type: TransitionType;
  bars: number;
  effect: EffectType;
  bridge: BridgeType;
  onChange: (patch: Partial<{ type: TransitionType; bars: number; effect: EffectType; bridge: BridgeType }>) => void;
  beatMatch: boolean;
}

export default function OptionsPanel({ type, bars, effect, bridge, onChange, beatMatch }: Props) {
  return (
    <div className="options">
      <fieldset>
        <legend>Transition</legend>
        <label><input type="radio" name="type" checked={type === "crossfade"}
          onChange={() => onChange({ type: "crossfade" })} /> Crossfade</label>
        <label><input type="radio" name="type" checked={type === "cut"} disabled={!beatMatch}
          onChange={() => onChange({ type: "cut" })} /> Cut {!beatMatch && "(needs beat-match)"}</label>
      </fieldset>
      <fieldset>
        <legend>Length (bars)</legend>
        {[4, 8, 16, 32].map((n) => (
          <label key={n}>
            <input type="radio" name="bars" checked={bars === n} onChange={() => onChange({ bars: n })} />
            {n}
          </label>
        ))}
      </fieldset>
      <label>Effect:
        <select value={effect} onChange={(e) => onChange({ effect: e.target.value as EffectType })}>
          <option value="none">None</option>
          <option value="lowpass_sweep">Low-pass sweep</option>
          <option value="highpass_sweep">High-pass sweep</option>
          <option value="echo_tail">Echo tail</option>
          <option value="reverb_wash">Reverb wash</option>
          <option value="backspin">Backspin</option>
        </select>
      </label>
      <label>Bridge:
        <select value={bridge} onChange={(e) => onChange({ bridge: e.target.value as BridgeType })}>
          <option value="none">None</option>
          <option value="drumroll">Drumroll</option>
          <option value="sweep_up">Sweep up</option>
          <option value="vinyl_stop">Vinyl stop</option>
          <option value="airhorn">Airhorn</option>
          <option value="dj_tag">DJ tag</option>
        </select>
      </label>
    </div>
  );
}
