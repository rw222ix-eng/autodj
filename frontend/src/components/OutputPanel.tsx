import { useMemo } from "react";
import type { MixResponse } from "../types";
import { downloadUrl } from "../api";

interface Props {
  result?: MixResponse;
  rendering: boolean;
  error?: string;
  onRender: () => void;
}

export default function OutputPanel({ result, rendering, error, onRender }: Props) {
  // Bust browser cache when re-rendering the same job — the mix.wav path is reused
  // by the backend, but its contents change. The nonce is rotated on every new result
  // and the key= prop forces React to fully remount the <audio> element.
  const nonce = useMemo(() => Date.now(), [result]);
  const bust = (path: string) => `${downloadUrl(path)}?t=${nonce}`;

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
          <audio key={nonce} controls src={bust(result.preview_url)} />
          <p>
            <a href={bust(result.download_wav_url)} download>Download WAV</a>
            {" · "}
            <a href={bust(result.download_mp3_url)} download>Download MP3</a>
          </p>
        </>
      )}
    </div>
  );
}
