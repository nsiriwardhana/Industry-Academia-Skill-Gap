/**
 * Local AI Explainer API Service
 * Handles AI explanation generation using fine-tuned Qwen model
 * running on Agent Runtime (Port 8003)
 */

import { ENDPOINTS, REQUEST_HEADERS, DEFAULT_OPTIONS } from '@/config/api';

export interface ExplainerRequest {
  id?: string;
  mode: 'role_gap' | 'job_gap';
  input: ExplainerInput;
  metadata?: {
    generated_at: string;
    synthetic: boolean;
    version: string;
  };
}

export interface ExplainerInput {
  target_name: string;
  target_key: string;
  readiness: number;
  skill_gap_index: number;
  matched_skills: string[];
  num_matched: number;
  missing_skills: MissingSkillDetail[];
  num_missing: number;
  total_role_skills: number;
  project_relevance_score: number;
  relevant_projects: RelevantProject[];
  total_projects: number;
}

export interface MissingSkillDetail {
  skill: string;
  importance: number;
  deficit: number;
}

export interface RelevantProject {
  name: string;
  relevance: number;
  matched_skills: string[];
  total_skills: number;
  complexity: string;
}

export interface ExplainerResponse {
  explanation_text: string;
  generation_time: number;
  model: string;
}

/**
 * Generate AI explanation for skill gap analysis
 */
export async function generateExplanation(
  payload: ExplainerRequest
): Promise<ExplainerResponse> {
  console.log('🔍 AI Explainer Request:', {
    url: ENDPOINTS.EXPLAINER.EXPLAIN,
    payload,
  });

  const response = await fetch(ENDPOINTS.EXPLAINER.EXPLAIN, {
    method: 'POST',
    headers: REQUEST_HEADERS.JSON, // Use standard JSON headers (no ngrok)
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorText = await response.text();
    console.error('❌ AI Explainer Error Response:', errorText);
    throw new Error(`AI explanation failed: ${errorText}`);
  }

  const data = await response.json();
  console.log('✅ AI Explainer Response:', data);
  
  return data;
}

/**
 * Build explainer payload from gap analysis results
 */
export function buildExplainerPayload(
  gapResult: any,
  mode: 'role' | 'job',
  roleKey?: string,
  roleName?: string
): ExplainerRequest {
  let targetName: string;
  let targetKey: string;
  
  if (mode === 'role') {
    targetName = roleName || roleKey || gapResult.role_key || 'Unknown Role';
    targetKey = gapResult.role_key || roleKey || 'unknown';
  } else {
    targetName = gapResult.job_title || 'Uploaded Job';
    targetKey = gapResult.job_id || 'custom_job';
  }

  // Extract matched skills
  const matchedSkills = mode === 'role'
    ? (gapResult.skill_confidence_top || []).slice(0, 8).map((s: any) => s.skill_name)
    : (gapResult.matched_skills || []).slice(0, 8).map((s: any) => 
        typeof s === 'string' ? s : s.skill
      );

  // Extract missing skills with details
  const missingSkills: MissingSkillDetail[] = mode === 'role'
    ? (gapResult.skill_gap_top || [])
        .filter((s: any) => (s.match_strength || s.p_has || 0) < 0.5)
        .slice(0, 8)
        .map((s: any) => ({
          skill: s.skill_name,
          importance: s.importance || 0.5,
          deficit: s.deficit || 1.0,
        }))
    : (gapResult.missing_skills_ranked || [])
        .slice(0, 8)
        .map((s: any) => ({
          skill: s.skill,
          importance: s.importance || 0.5,
          deficit: s.deficit || 1.0,
        }));

  // Extract relevant projects
  const relevantProjects: RelevantProject[] = (gapResult.relevant_projects || [])
    .slice(0, 3)
    .map((proj: any) => ({
      name: proj.project_name || proj.name || 'Unknown Project',
      relevance: proj.relevance_score || proj.relevance || 0,
      matched_skills: (proj.matched_role_skills || proj.matched_skills || []).slice(0, 4),
      total_skills: proj.num_project_skills || proj.total_skills || 0,
      complexity: proj.complexity || 'Medium',
    }));

  return {
    id: `EXP_${Date.now()}`,
    mode: mode === 'role' ? 'role_gap' : 'job_gap',
    input: {
      target_name: targetName,
      target_key: targetKey,
      readiness: gapResult.readiness_score || gapResult.readiness || 0,
      skill_gap_index: gapResult.skill_gap_index || 0,
      matched_skills: matchedSkills,
      num_matched: matchedSkills.length,
      missing_skills: missingSkills,
      num_missing: missingSkills.length,
      total_role_skills:
        gapResult.total_role_skills ||
        gapResult.total_job_skills ||
        matchedSkills.length + missingSkills.length,
      project_relevance_score: gapResult.project_relevance_score || 0,
      relevant_projects: relevantProjects,
      total_projects: relevantProjects.length,
    },
    metadata: {
      generated_at: new Date().toISOString(),
      synthetic: false,
      version: '1.0',
    },
  };
}

/**
 * Health check for AI explainer
 */
export async function checkExplainerHealth(): Promise<any> {
  const response = await fetch(ENDPOINTS.EXPLAINER.HEALTH, {
    headers: REQUEST_HEADERS.JSON,
  });
  
  if (!response.ok) {
    throw new Error(`Health check failed: ${response.status}`);
  }
  
  return response.json();
}

/**
 * Get explainer service info
 */
export async function getExplainerInfo(): Promise<any> {
  const response = await fetch(ENDPOINTS.EXPLAINER.INFO, {
    headers: REQUEST_HEADERS.JSON,
  });
  
  if (!response.ok) {
    throw new Error(`Failed to get info: ${response.status}`);
  }
  
  return response.json();
}
