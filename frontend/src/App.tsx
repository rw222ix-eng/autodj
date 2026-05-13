import { useState } from "react";
import UploadTile from "./components/UploadTile";
import OptionsPanel from "./components/OptionsPanel";
import OutputPanel from "./components/OutputPanel";
import { analyze, mix } from "./api";
import type {
  AnalyzeResponse, MixResponse, TransitionType, EffectType, BridgeType,
} from "./types";
import "./App.css";

export default function App() {
  const [analyzeRes, setAnalyzeRes] = useState<AnalyzeResponse>();
  const [fileA, setFileA] = useState<File>();
  const [fileB, setFileB] = useState<File>();
  const [manualA, setManualA] = useState<number | "">("");
  const [manualB, setManualB] = useState<number | "">("");
  const [type, setType] = useState<TransitionType>("crossfade");
  const [bars, setBars] = useState<number>(16);
  const [effect, setEffect] = useState<EffectType>("none");
  const [bridge, setBridge] = useState<BridgeType>("none");
  const [result, setResult] = useState<MixResponse>();
  const [rendering, setRendering] = useState(false);
  const [error, setError] = useState<string>();

  async function handleAnalyze(a?: File, b?: File) {
    const fa = a ?? fileA, fb = b ?? fileB;
    if (!fa || !fb) return;
    try {
      setError(undefined);
      const res = await analyze(fa, fb);
      setAnalyzeRes(res);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function handleMix() {
    if (!analyzeRes) return;
    setRendering(true); setError(undefined);
    try {
      const res = await mix({
        job_id: analyzeRes.job_id, type, bars, effect, bridge,
        manual_bpm_a: manualA === "" ? undefined : manualA,
        manual_bpm_b: manualB === "" ? undefined : manualB,
      });
      setResult(res);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setRendering(false);
    }
  }

  const beatMatch = result?.beat_match ?? true;

  return (
    <main>
      <h1>AutoDJ</h1>
      <section className="tiles">
        <UploadTile label="Track A"
          onSelect={(f) => { setFileA(f); handleAnalyze(f, fileB); }}
          summary={analyzeRes?.a} manualBpm={manualA} onManualBpm={setManualA} />
        <UploadTile label="Track B"
          onSelect={(f) => { setFileB(f); handleAnalyze(fileA, f); }}
          summary={analyzeRes?.b} manualBpm={manualB} onManualBpm={setManualB} />
      </section>
      <OptionsPanel type={type} bars={bars} effect={effect} bridge={bridge}
        beatMatch={beatMatch}
        onChange={(p) => {
          if (p.type !== undefined) setType(p.type);
          if (p.bars !== undefined) setBars(p.bars);
          if (p.effect !== undefined) setEffect(p.effect);
          if (p.bridge !== undefined) setBridge(p.bridge);
        }} />
      <OutputPanel result={result} rendering={rendering} error={error} onRender={handleMix} />
    </main>
  );
}
