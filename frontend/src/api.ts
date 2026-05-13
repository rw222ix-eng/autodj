import type { AnalyzeResponse, MixRequest, MixResponse } from "./types";

const BASE = "http://localhost:8000";

export async function analyze(fileA: File, fileB: File): Promise<AnalyzeResponse> {
  const fd = new FormData();
  fd.append("file_a", fileA);
  fd.append("file_b", fileB);
  const res = await fetch(`${BASE}/analyze`, { method: "POST", body: fd });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function mix(req: MixRequest): Promise<MixResponse> {
  const res = await fetch(`${BASE}/mix`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export function downloadUrl(path: string): string {
  return `${BASE}${path}`;
}
