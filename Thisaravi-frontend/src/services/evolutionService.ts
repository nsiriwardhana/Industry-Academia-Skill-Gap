import { ENDPOINTS } from '@/config/api';
import type { PatternReport, PromptEvolution } from '@/types/api';

export type LLMProvider = 'ollama' | 'gemini';

export async function runAnalysis(provider: LLMProvider): Promise<PatternReport> {
  const res = await fetch(ENDPOINTS.EVOLUTION.RUN_ANALYSIS, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ provider }),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(detail.detail || `Analysis failed: ${res.status}`);
  }
  return res.json();
}

export async function fetchPatternReports(): Promise<PatternReport[]> {
  const res = await fetch(ENDPOINTS.EVOLUTION.PATTERN_REPORTS);
  if (!res.ok) throw new Error(`Failed to fetch pattern reports: ${res.status}`);
  return res.json();
}

export async function previewEvolution(
  reportId: string,
  provider: LLMProvider,
): Promise<{ diff: string }> {
  const res = await fetch(ENDPOINTS.EVOLUTION.PREVIEW, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ report_id: reportId, provider }),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(detail.detail || `Preview failed: ${res.status}`);
  }
  return res.json();
}

export async function applyEvolution(
  reportId: string,
  provider: LLMProvider,
): Promise<PromptEvolution> {
  const res = await fetch(ENDPOINTS.EVOLUTION.APPLY, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ report_id: reportId, provider }),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(detail.detail || `Evolution failed: ${res.status}`);
  }
  return res.json();
}

export async function fetchEvolutions(): Promise<PromptEvolution[]> {
  const res = await fetch(ENDPOINTS.EVOLUTION.EVOLUTIONS);
  if (!res.ok) throw new Error(`Failed to fetch evolutions: ${res.status}`);
  return res.json();
}

export async function fetchCurrentPrompt(): Promise<{ prompt: string; version: string }> {
  const res = await fetch(ENDPOINTS.EVOLUTION.CURRENT_PROMPT);
  if (!res.ok) throw new Error(`Failed to fetch current prompt: ${res.status}`);
  return res.json();
}

export async function runRegeneration(
  evolutionId: string,
  provider: LLMProvider,
  targetCount: number,
  generationMode: 'v1' | 'v2' = 'v2',
): Promise<{ output_path: string }> {
  const res = await fetch(ENDPOINTS.EVOLUTION.REGENERATE, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      evolution_id: evolutionId,
      provider,
      target_count: targetCount,
      generation_mode: generationMode,
    }),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(detail.detail || `Regeneration failed: ${res.status}`);
  }
  return res.json();
}

export interface DatasetFile {
  filename: string;
  entry_count: number;
}

export async function listDatasets(): Promise<{ datasets: DatasetFile[] }> {
  const res = await fetch(ENDPOINTS.EVOLUTION.LIST_DATASETS);
  if (!res.ok) throw new Error(`Failed to list datasets: ${res.status}`);
  return res.json();
}

export async function uploadToHF(
  filename: string,
  repoId?: string,
): Promise<{ status: string; filename: string }> {
  const res = await fetch(ENDPOINTS.EVOLUTION.UPLOAD_TO_HF, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filename, repo_id: repoId || null }),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(detail.detail || `Upload failed: ${res.status}`);
  }
  return res.json();
}
