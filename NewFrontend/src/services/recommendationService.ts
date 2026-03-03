/**
 * Recommendation System API Service
 * Handles Advanced Recommendation System API calls (Port 8001)
 */

import { ENDPOINTS, REQUEST_HEADERS, DEFAULT_OPTIONS } from '@/config/api';

export interface ProjectRelevanceResponse {
  candidate_id: string;
  role_key: string;
  role_name: string;
  top_projects: ProjectRelevance[];
  candidate_project_score: number;
  total_projects: number;
}

export interface ProjectRelevance {
  project_name: string;
  relevance_score: number;
  matched_role_skills: string[];
  project_skills: string[];
  num_matched: number;
  num_project_skills: number;
  complexity?: string;
}

export interface SkillConfidenceResponse {
  candidate_id: string;
  role_key: string;
  top_skills: Array<{
    skill_name: string;
    confidence: number;
    evidence_count: number;
  }>;
}

export interface SkillGapResponse {
  candidate_id: string;
  role_key: string;
  readiness_score: number;
  skill_gap_index: number;
  top_deficits: Array<{
    skill_name: string;
    deficit: number;
    importance: number;
    p_has: number;
  }>;
}

/**
 * Get project relevance for candidate-role pair
 */
export async function getProjectRelevance(
  candidateId: string,
  roleKey: string,
  topN: number = DEFAULT_OPTIONS.TOP_N,
  topKRole: number = DEFAULT_OPTIONS.TOP_K
): Promise<ProjectRelevanceResponse> {
  const url = `${ENDPOINTS.RECOMMENDATION.PROJECT_RELEVANCE(candidateId, roleKey)}?top_n=${topN}&top_k_role=${topKRole}`;
  
  const response = await fetch(url, {
    method: 'GET',
    headers: REQUEST_HEADERS.JSON,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Get skill confidence for candidate-role pair
 */
export async function getSkillConfidence(
  candidateId: string,
  roleKey: string,
  topK: number = DEFAULT_OPTIONS.TOP_K
): Promise<SkillConfidenceResponse> {
  const url = `${ENDPOINTS.RECOMMENDATION.SKILL_CONFIDENCE(candidateId, roleKey)}?top_k=${topK}`;
  
  const response = await fetch(url, {
    method: 'GET',
    headers: REQUEST_HEADERS.JSON,
  });

  if (!response.ok) {
    throw new Error(`Skill confidence failed: ${response.status}`);
  }

  return response.json();
}

/**
 * Get skill gap analysis for candidate-role pair
 */
export async function getSkillGap(
  candidateId: string,
  roleKey: string,
  topK: number = DEFAULT_OPTIONS.TOP_K
): Promise<SkillGapResponse> {
  const url = `${ENDPOINTS.RECOMMENDATION.SKILL_GAP(candidateId, roleKey)}?top_k=${topK}`;
  
  const response = await fetch(url, {
    method: 'GET',
    headers: REQUEST_HEADERS.JSON,
  });

  if (!response.ok) {
    throw new Error(`Skill gap analysis failed: ${response.status}`);
  }

  return response.json();
}

/**
 * Get all available roles
 */
export async function getRoles(): Promise<any[]> {
  const response = await fetch(ENDPOINTS.RECOMMENDATION.ROLES, {
    method: 'GET',
    headers: REQUEST_HEADERS.JSON,
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch roles: ${response.status}`);
  }

  return response.json();
}

/**
 * Clear cache (admin endpoint)
 */
export async function clearCache(): Promise<any> {
  const response = await fetch(ENDPOINTS.RECOMMENDATION.CACHE_CLEAR, {
    method: 'GET',
    headers: REQUEST_HEADERS.JSON,
  });

  if (!response.ok) {
    throw new Error(`Failed to clear cache: ${response.status}`);
  }

  return response.json();
}
