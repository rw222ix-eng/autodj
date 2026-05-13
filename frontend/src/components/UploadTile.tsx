import { useState } from "react";
import type { TrackSummary } from "../types";

interface Props {
  label: string;
  onSelect: (file: File) => void;
  summary?: TrackSummary;
  manualBpm: number | "";
  onManualBpm: (v: number | "") => void;
}

export default function UploadTile({ label, onSelect, summary, manualBpm, onManualBpm }: Props) {
  const [name, setName] = useState<string>("");
  return (
    <div className="tile">
      <h3>{label}</h3>
      <input
        type="file"
        accept="audio/*"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) { setName(f.name); onSelect(f); }
        }}
      />
      {name && <p className="filename">{name}</p>}
      {summary && (
        <div className="summary">
          <p>BPM: <strong>{summary.bpm.toFixed(1)}</strong>
             {summary.bpm_confidence < 0.5 && <span className="warning"> (low confidence)</span>}
          </p>
          <p>Duration: {summary.duration.toFixed(1)}s</p>
          {summary.key && <p>Key: {summary.key}</p>}
          {summary.bpm_confidence < 0.5 && (
            <label>Manual BPM:
              <input
                type="number"
                value={manualBpm}
                onChange={(e) => onManualBpm(e.target.value === "" ? "" : Number(e.target.value))}
              />
            </label>
          )}
        </div>
      )}
    </div>
  );
}
