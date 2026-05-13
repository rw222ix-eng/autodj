import type { MixResponse } from "../types";
import { downloadUrl } from "../api";

interface Props {
  result?: MixResponse;
  rendering: boolean;
  error?: string;
  onRender: () => void;
}

export default function OutputPanel({ result, rendering, error, onRender }: Props) {
  return (
    <div className="output">
      <button disabled={rendering} onClick={onRender}>
        {rendering ? "Rendering…" : "Render mix"}
      </button>
      {error && <p className="error">{error}</p>}
      {result && (
        <>
          {result.warning === "bars_reduced" &&
            <p className="warning">Transition shortened to {result.effective_bars} bars to stay beat-aligned.</p>}
          {!result.beat_match &&
            <p className="warning">BPMs too different to beat-match — using crossfade only.</p>}
          <audio controls src={downloadUrl(result.preview_url)} />
          <p>
            <a href={downloadUrl(result.download_wav_url)} download>Download WAV</a>
            {" · "}
            <a href={downloadUrl(result.download_mp3_url)} download>Download MP3</a>
          </p>
        </>
      )}
    </div>
  );
}
