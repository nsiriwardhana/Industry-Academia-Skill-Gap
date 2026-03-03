/**
 * Course Recommendation API Service
 * Handles course recommendation calls to Advanced-Recommendation-System (Port 8001)
 */

import { ENDPOINTS, REQUEST_HEADERS, DEFAULT_OPTIONS } from '@/config/api';

export interface CourseRecommendation {
  course_id: string;
  title: string;
  provider: string;
  url?: string;
  imageUrl?: string;
  avg_rating?: number;
  difficulty?: string;
  covered_deficit_skills: string[];
  gain_score: number;
}

export interface CourseRecommendationResponse {
  candidate_id: string;
  role_key: string;
  role_name: string;
  top_k_deficits_considered: number;
  recommendations: CourseRecommendation[];
}

/**
 * Get course recommendations for missing skills
 */
export async function getCourseRecommendations(
  candidateId: string,
  roleKey: string,
  topK: number = 25,
  topN: number = 10
): Promise<CourseRecommendationResponse> {
  console.log('📚 Fetching course recommendations:', {
    candidateId,
    roleKey,
    topK,
    topN,
  });

  const url = `${ENDPOINTS.RECOMMENDATION.BASE}/candidates/${candidateId}/roles/${roleKey}/recommendations?top_k=${topK}&top_n=${topN}`;

  const response = await fetch(url, {
    method: 'GET',
    headers: REQUEST_HEADERS.JSON,
    ...DEFAULT_OPTIONS,
  });

  if (!response.ok) {
    const errorText = await response.text();
    console.error('❌ Course recommendation error:', errorText);
    throw new Error(`Course recommendation failed: ${response.status} ${errorText}`);
  }

  const data = await response.json();
  console.log('✅ Course recommendations received:', data);

  return data;
}
