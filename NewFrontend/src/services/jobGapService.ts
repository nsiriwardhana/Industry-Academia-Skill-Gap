/**
 * Job Gap Analysis API Service
 * Handles job description-based gap analysis (Port 8003)
 */

import { ENDPOINTS, REQUEST_HEADERS, DEFAULT_OPTIONS } from '@/config/api';

export interface JobGapRequest {
  candidate_json: string;
  jd_file: File;
  store_job?: boolean;
  top_k?: number;
}

export interface JobGapResponse {
  candidate_id: string;
  job_id: string;
  job_title: string;
  readiness: number;
  skill_gap_index: number;
  ranking_method?: string;
  matched_skills: MatchedSkill[];
  missing_skills_ranked: MissingSkill[];
  candidate_upsert: any;
  explanation_text?: string;
  xai?: any;
}

export interface MatchedSkill {
  skill: string;
  match_strength: number;
}

export interface MissingSkill {
  skill: string;
  importance: number;
  deficit: number;
  match_strength: number;
  P_gnn?: number;
  final_score?: number;
  reason?: string;
  ranking_method?: string;
}

/**
 * Analyze job gap between candidate and job description
 */
export async function analyzeJobGap(
  candidateJson: string,
  jdFile: File,
  storeJob: boolean = false,
  topK: number = DEFAULT_OPTIONS.TOP_K,
  rankingMethod: 'symbolic' | 'hybrid' | 'additive_gnn' = 'hybrid'
): Promise<JobGapResponse> {
  const formData = new FormData();
  formData.append('candidate_json', candidateJson);
  formData.append('jd_file', jdFile);
  formData.append('store_job', storeJob.toString());
  formData.append('top_k', topK.toString());
  formData.append('ranking_method', rankingMethod);

  const response = await fetch(ENDPOINTS.JOB_GAP.ANALYZE, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Health check for Job Gap service
 */
export async function checkJobGapHealth(): Promise<any> {
  const response = await fetch(ENDPOINTS.JOB_GAP.HEALTH);
  
  if (!response.ok) {
    throw new Error(`Health check failed: ${response.status}`);
  }
  
  return response.json();
}
