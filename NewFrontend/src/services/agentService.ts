/**
 * Agent Runtime API Service
 * Handles all Agent Runtime backend API calls (Port 8003)
 */

import { API_CONFIG, ENDPOINTS, REQUEST_HEADERS, DEFAULT_OPTIONS } from '@/config/api';

export interface ExtractedData {
  candidate_id: string;
  candidate_name?: string;
  skills?: Array<{ name: string; proficiency?: string }>;
  experience?: any[];
  education?: any[];
  projects?: any[];
  [key: string]: any;
}

export interface AgentRunResponse {
  candidate_id: string;
  role_key: string;
  status: string;
  message: string;
  normalized_skills_count: number;
  nodes_created: number;
  relationships_created: number;
  skill_confidence_top: SkillConfidence[];
  skill_gap_top: SkillGap[];
  readiness_score: number;
  skill_gap_index?: number;
  total_role_skills?: number;
  project_relevance_score?: number;
  relevant_projects?: Array<{
    project_name: string;
    relevance_score: number;
    matched_role_skills: string[];
    num_project_skills: number;
    complexity?: string;
  }>;
  xai?: XAIResponse;
}

export interface SkillConfidence {
  skill_name: string;
  confidence: number;
  evidence_count: number;
}

export interface SkillGap {
  skill_name: string;
  deficit: number;
  importance: number;
  match_strength: number;
  // GNN Hybrid fields (present when using hybrid ranking)
  P_gnn?: number;  // Learning potential from GNN (0-1)
  final_score?: number;  // Hybrid score: gap × importance × P_gnn
  gap?: number;  // Skill gap magnitude (1 - P_has)
  importance_norm?: number;  // Normalized importance
  reason?: string;  // Human-readable explanation (e.g., "high learning potential (avg baseline)")
  category?: string;  // Skill category
  ranking_method?: string;  // "hybrid", "symbolic", or "additive_gnn"
  // Legacy fields for backward compatibility
  p_has?: number;
  tf?: number;
  df?: number;
  idf?: number;
}

export interface XAIResponse {
  skill_level?: SkillLevelXAI;
  shap_level?: ShapLevelXAI;
}

export interface SkillLevelXAI {
  candidate_id: string;
  role_key: string;
  top_contributors: Array<{
    skill_name: string;
    deficit: number;
    importance: number;
    contribution_percent: number;
  }>;
  total_deficit: number;
}

export interface ShapLevelXAI {
  enabled: boolean;
  predicted_skill_gap_index?: number;
  predicted_readiness?: number;
  top_increasing_factors?: Array<{
    feature: string;
    value?: any;
    impact: number;
    message: string;
  }>;
  top_reducing_factors?: Array<{
    feature: string;
    value?: any;
    impact: number;
    message: string;
  }>;
  summary_text?: string;
  base_value?: number;
  notes?: string[];
  reason?: string;
}

/**
 * Run complete agent pipeline: Extract → Normalize → Write → Analyze
 */
export async function runAgentPipeline(
  cvData: ExtractedData,
  roleKey: string,
  topK: number = DEFAULT_OPTIONS.TOP_K,
  includeXai: boolean = DEFAULT_OPTIONS.INCLUDE_XAI
): Promise<AgentRunResponse> {
  const url = `${ENDPOINTS.AGENT.RUN}?role_key=${roleKey}&top_k=${topK}&include_xai=${includeXai}`;
  
  const response = await fetch(url, {
    method: 'POST',
    headers: REQUEST_HEADERS.JSON,
    body: JSON.stringify(cvData),
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
  }

  return response.json();
}

/**
 * Run complete agent pipeline from PDF file: Parse → Extract → Normalize → Write → Analyze
 */
export async function runAgentPipelineFromPDF(
  cvFile: File,
  roleKey: string,
  topK: number = DEFAULT_OPTIONS.TOP_K,
  includeXai: boolean = DEFAULT_OPTIONS.INCLUDE_XAI
): Promise<AgentRunResponse> {
  const formData = new FormData();
  formData.append('cv_file', cvFile);
  
  const params = new URLSearchParams({
    role_key: roleKey,
    top_k: topK.toString(),
    include_xai: includeXai.toString(),
  });

  const url = `${ENDPOINTS.AGENT.RUN_FROM_PDF}?${params.toString()}`;
  
  const response = await fetch(url, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(errorData.detail || `Pipeline failed with status ${response.status}`);
  }

  return response.json();
}

/**
 * Health check for Agent Runtime
 */
export async function checkAgentHealth(): Promise<any> {
  const response = await fetch(ENDPOINTS.AGENT.HEALTH);
  
  if (!response.ok) {
    throw new Error(`Health check failed: ${response.status}`);
  }
  
  return response.json();
}

/**
 * Get skill-level explanation
 */
export async function getSkillExplanation(
  candidateId: string,
  roleKey: string,
  topN: number = DEFAULT_OPTIONS.TOP_N
): Promise<any> {
  const url = `${ENDPOINTS.AGENT.SKILL_EXPLAIN}?candidate_id=${candidateId}&role_key=${roleKey}&top_n=${topN}`;
  
  const response = await fetch(url);
  
  if (!response.ok) {
    throw new Error(`Skill explanation failed: ${response.status}`);
  }
  
  return response.json();
}

/**
 * Get model-level (SHAP) explanation
 */
export async function getPredictExplanation(
  candidateId: string,
  roleKey: string,
  topK: number = 5
): Promise<any> {
  const url = `${ENDPOINTS.AGENT.PREDICT_EXPLAIN}?candidate_id=${candidateId}&role_key=${roleKey}&top_k=${topK}`;
  
  const response = await fetch(url);
  
  if (!response.ok) {
    throw new Error(`Predict explanation failed: ${response.status}`);
  }
  
  return response.json();
}
