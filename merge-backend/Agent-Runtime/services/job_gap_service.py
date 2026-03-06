"""
Job Gap Analysis Service - Complete pipeline for JD-based gap analysis.

Orchestrates:
1. OCR extraction (Chandra)
2. Skill extraction (rules + KG matching)
3. Skill normalization (Ollama LLM)
4. Job skill profile building
5. Optional KG write (JobPosting node)
6. Gap analysis (reuses existing graded matching)
7. Explanation generation (Ollama LLM)

This service provides the end-to-end pipeline for:
Job Description Image/PDF → Job Skill Profile → Candidate–Job Gap Analysis
"""
import os
import uuid
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import requests

from .chandra_ocr_service import get_ocr_service
from .skill_extract_service import get_skill_extract_service
from .skill_normalize_llm import get_skill_normalize_service

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
NORMALIZER_MODEL = os.getenv("NORMALIZER_MODEL", "qwen2.5:3b-instruct")

# Importance weights for skill categorization
REQUIRED_SKILL_BASE_WEIGHT = 1.0
OPTIONAL_SKILL_BASE_WEIGHT = 0.4

# Boost factors for emphasis keywords
EMPHASIS_KEYWORDS = ["must", "strong", "expert", "advanced", "senior", "lead"]
EMPHASIS_BOOST = 0.15


class JobGapService:
    """
    End-to-end service for JD-based skill gap analysis.
    
    Pipeline:
    1. OCR: Extract text from image/PDF
    2. Extract: Identify raw skills from text
    3. Normalize: Map to canonical skills via LLM
    4. Profile: Build job skill profile with importance
    5. KG Write: Optionally store JobPosting in Neo4j
    6. Gap Analysis: Compute candidate-job gap
    7. Explain: Generate plain English explanation
    """
    
    def __init__(self, neo4j_session=None, recommendation_api_url: str = None):
        """
        Initialize job gap service.
        
        Args:
            neo4j_session: Neo4j session for KG operations
            recommendation_api_url: URL for existing recommendation API
        """
        self.session = neo4j_session
        self.recommendation_api = recommendation_api_url or os.getenv(
            "RECOMMENDATION_API_BASE_URL",
            "http://localhost:8001"
        )
        
        # Initialize sub-services
        self.ocr_service = get_ocr_service()
        self.extract_service = get_skill_extract_service()
        self.normalize_service = get_skill_normalize_service(neo4j_session)
        
        logger.info("JobGapService initialized")
    
    def set_session(self, session) -> None:
        """Set Neo4j session."""
        self.session = session
        self.normalize_service.set_session(session)
        if session:
            self.extract_service.load_kg_skills(session)
    
    async def analyze_job_gap(
        self,
        candidate_id: str,
        file_content: bytes,
        content_type: str,
        store_job: bool = True,
        top_k: int = 25
    ) -> Dict:
        """
        Run complete job gap analysis pipeline.
        
        Args:
            candidate_id: Candidate identifier
            file_content: Raw file bytes (image or PDF)
            content_type: MIME type
            store_job: Whether to store JobPosting in KG
            top_k: Number of top skills to analyze
            
        Returns:
            Complete gap analysis response
        """
        logger.info(f"Starting job gap analysis for candidate: {candidate_id}")
        
        result = {
            "job_id": str(uuid.uuid4()),
            "job_title": "",
            "readiness": 0.0,
            "skill_gap_index": 1.0,
            "matched_skills": [],
            "missing_skills_ranked": [],
            "explanation_text": "",
            "pipeline_metadata": {}
        }
        
        try:
            # Step 1: OCR Extraction
            logger.info("Step 1: OCR Extraction")
            jd_text, ocr_metadata = await self.ocr_service.process_upload(
                file_content, content_type
            )
            result["pipeline_metadata"]["ocr"] = ocr_metadata
            
            if not jd_text:
                raise ValueError("OCR extraction failed - no text extracted")
            
            # Step 2: Skill Extraction
            logger.info("Step 2: Skill Extraction")
            extraction_result = self.extract_service.extract_skills(jd_text)
            result["job_title"] = extraction_result["job_title"]
            result["pipeline_metadata"]["extraction"] = extraction_result["extraction_metadata"]
            
            raw_required = extraction_result["raw_required_skills"]
            raw_optional = extraction_result["raw_optional_skills"]
            
            if not raw_required and not raw_optional:
                raise ValueError("No skills extracted from JD")
            
            # Step 3: Skill Normalization
            logger.info("Step 3: Skill Normalization")
            normalized_required = self.normalize_service.normalize_skills_batch(raw_required)
            normalized_optional = self.normalize_service.normalize_skills_batch(raw_optional)
            
            # Filter to matched skills only
            matched_required = [n for n in normalized_required if n["matched"]]
            matched_optional = [n for n in normalized_optional if n["matched"]]
            
            result["pipeline_metadata"]["normalization"] = {
                "required_input": len(raw_required),
                "required_matched": len(matched_required),
                "optional_input": len(raw_optional),
                "optional_matched": len(matched_optional)
            }
            
            # Step 4: Build Job Skill Profile
            logger.info("Step 4: Build Job Skill Profile")
            job_skills = self._build_job_skill_profile(
                matched_required,
                matched_optional,
                jd_text,
                top_k
            )
            
            if not job_skills:
                raise ValueError("No valid skills for job profile")
            
            # Step 5: Optional KG Write
            if store_job and self.session:
                logger.info("Step 5: Writing JobPosting to KG")
                self._write_job_to_kg(
                    result["job_id"],
                    result["job_title"],
                    job_skills
                )
            
            # Step 6: Gap Analysis
            logger.info("Step 6: Computing Gap Analysis")
            gap_result = self._compute_gap_analysis(
                candidate_id,
                job_skills,
                top_k
            )
            
            result["readiness"] = gap_result["readiness"]
            result["skill_gap_index"] = gap_result["skill_gap_index"]
            result["matched_skills"] = gap_result["matched_skills"]
            result["missing_skills_ranked"] = gap_result["missing_skills"]
            
            # Step 7: Generate Explanation
            logger.info("Step 7: Generating Explanation")
            result["explanation_text"] = self._generate_explanation(
                result["readiness"],
                result["matched_skills"][:5],
                result["missing_skills_ranked"][:5],
                result["job_title"]
            )
            
            logger.info(
                f"Job gap analysis complete: readiness={result['readiness']:.2f}, "
                f"gap_index={result['skill_gap_index']:.2f}"
            )
            
        except Exception as e:
            logger.error(f"Job gap analysis failed: {e}")
            result["error"] = str(e)
            result["explanation_text"] = f"Analysis could not be completed: {str(e)}"
        
        return result
    
    def _build_job_skill_profile(
        self,
        required_skills: List[Dict],
        optional_skills: List[Dict],
        jd_text: str,
        top_k: int
    ) -> List[Dict]:
        """
        Build job skill profile with importance scores.
        
        Args:
            required_skills: Normalized required skills
            optional_skills: Normalized optional skills
            jd_text: Original JD text for keyword boosting
            top_k: Max skills to include
            
        Returns:
            List of {"skill": "...", "importance": 0.0-1.0}
        """
        jd_lower = jd_text.lower()
        skill_scores = {}
        
        # Process required skills
        for norm in required_skills:
            skill = norm["canonical_skill"]
            if not skill:
                continue
            
            # Base weight
            score = REQUIRED_SKILL_BASE_WEIGHT
            
            # Boost for emphasis keywords near skill mention
            for keyword in EMPHASIS_KEYWORDS:
                # Check if keyword appears near skill in text
                skill_lower = skill.lower()
                if keyword in jd_lower and skill_lower in jd_lower:
                    score += EMPHASIS_BOOST
                    break
            
            # Boost for repetition
            count = jd_lower.count(skill_lower) if skill_lower in jd_lower else 1
            if count > 1:
                score += min(count * 0.05, 0.2)  # Cap repetition boost
            
            skill_scores[skill] = max(skill_scores.get(skill, 0), score)
        
        # Process optional skills
        for norm in optional_skills:
            skill = norm["canonical_skill"]
            if not skill:
                continue
            
            # Base weight (lower for optional)
            score = OPTIONAL_SKILL_BASE_WEIGHT
            
            # Don't override required skill score
            if skill not in skill_scores:
                skill_scores[skill] = score
        
        # Normalize to [0, 1]
        if skill_scores:
            max_score = max(skill_scores.values())
            if max_score > 0:
                skill_scores = {k: v / max_score for k, v in skill_scores.items()}
        
        # Sort by importance and take top-k
        sorted_skills = sorted(
            skill_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_k]
        
        return [{"skill": skill, "importance": imp} for skill, imp in sorted_skills]
    
    def _write_job_to_kg(
        self,
        job_id: str,
        job_title: str,
        job_skills: List[Dict]
    ) -> None:
        """
        Write JobPosting node and skill edges to Neo4j.
        
        Creates:
        - (:JobPosting {job_id, title, source, created_at})
        - (JobPosting)-[:REQUIRES_SKILL {importance}]->(Skill)
        """
        if not self.session:
            logger.warning("No Neo4j session - skipping KG write")
            return
        
        # Create JobPosting node
        create_job_query = """
        MERGE (j:JobPosting {job_id: $job_id})
        SET j.title = $title,
            j.source = 'image_upload',
            j.created_at = datetime()
        RETURN j
        """
        
        self.session.run(
            create_job_query,
            job_id=job_id,
            title=job_title or "Untitled Position"
        )
        
        # Create skill edges
        create_edge_query = """
        MATCH (j:JobPosting {job_id: $job_id})
        MATCH (s:Skill {name: $skill_name})
        MERGE (j)-[r:REQUIRES_SKILL]->(s)
        SET r.importance = $importance
        """
        
        for skill_data in job_skills:
            try:
                self.session.run(
                    create_edge_query,
                    job_id=job_id,
                    skill_name=skill_data["skill"],
                    importance=skill_data["importance"]
                )
            except Exception as e:
                logger.warning(f"Failed to create edge for skill {skill_data['skill']}: {e}")
        
        logger.info(f"JobPosting {job_id} written to KG with {len(job_skills)} skills")
    
    def _compute_gap_analysis(
        self,
        candidate_id: str,
        job_skills: List[Dict],
        top_k: int
    ) -> Dict:
        """
        Compute skill gap between candidate and job.
        
        Uses existing graded matching logic.
        
        Args:
            candidate_id: Candidate identifier
            job_skills: Job skill profile
            top_k: Number of skills to return
            
        Returns:
            {
                "readiness": 0.0-1.0,
                "skill_gap_index": 0.0-1.0,
                "matched_skills": [...],
                "missing_skills": [...]
            }
        """
        # Get candidate skill confidence
        candidate_skills = self._get_candidate_skills(candidate_id)
        
        if not candidate_skills:
            logger.warning(f"No skills found for candidate: {candidate_id}")
        
        matched_skills = []
        missing_skills = []
        total_importance = 0.0
        total_deficit = 0.0
        
        for job_skill in job_skills:
            skill_name = job_skill["skill"]
            importance = job_skill["importance"]
            total_importance += importance
            
            # Check if candidate has skill (with graded matching)
            match_strength = self._get_match_strength(
                skill_name,
                candidate_skills
            )
            
            deficit = importance * (1 - match_strength)
            total_deficit += deficit
            
            skill_data = {
                "skill": skill_name,
                "importance": round(importance, 3),
                "match_strength": round(match_strength, 3),
                "deficit": round(deficit, 3)
            }
            
            if match_strength >= 0.5:
                matched_skills.append(skill_data)
            else:
                missing_skills.append(skill_data)
        
        # Compute metrics
        skill_gap_index = total_deficit / total_importance if total_importance > 0 else 1.0
        readiness = 1.0 - skill_gap_index
        
        # Sort by deficit (highest first for missing)
        missing_skills.sort(key=lambda x: x["deficit"], reverse=True)
        matched_skills.sort(key=lambda x: x["match_strength"], reverse=True)
        
        return {
            "readiness": round(readiness, 3),
            "skill_gap_index": round(skill_gap_index, 3),
            "matched_skills": matched_skills[:top_k],
            "missing_skills": missing_skills[:top_k]
        }
    
    def _get_candidate_skills(self, candidate_id: str) -> Dict[str, float]:
        """
        Get candidate skills with confidence scores.
        
        Returns:
            Dict mapping skill_name to confidence
        """
        if not self.session:
            # Try recommendation API
            try:
                url = f"{self.recommendation_api}/candidates/{candidate_id}/skill-confidence"
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    return {
                        s["skill_name"]: s["confidence"]
                        for s in data.get("skills", [])
                    }
            except Exception as e:
                logger.error(f"Failed to get candidate skills from API: {e}")
            return {}
        
        # Query Neo4j directly
        query = """
        MATCH (p:Person {candidate_id: $candidate_id})
        
        // Get all skill sources
        OPTIONAL MATCH (p)-[:HAS_SKILL]->(s1:Skill)
        OPTIONAL MATCH (p)-[:WORKED_AT]->(w:WorkExperience)-[:USED_SKILL]->(s2:Skill)
        OPTIONAL MATCH (p)-[:WORKED_ON]->(pr:Project)-[:USES_TECHNOLOGY]->(s3:Skill)
        
        WITH collect(DISTINCT s1.name) + collect(DISTINCT s2.name) + collect(DISTINCT s3.name) AS all_skills
        UNWIND all_skills AS skill_name
        WITH skill_name WHERE skill_name IS NOT NULL
        RETURN DISTINCT skill_name, 0.8 AS confidence
        """
        
        result = self.session.run(query, candidate_id=candidate_id)
        return {record["skill_name"]: record["confidence"] for record in result}
    
    def _get_match_strength(
        self,
        target_skill: str,
        candidate_skills: Dict[str, float]
    ) -> float:
        """
        Get graded match strength for a skill.
        
        Uses:
        1. Exact match: 1.0
        2. Cluster match: 0.7
        3. Similarity: 0.4-0.6
        4. No match: 0.0
        """
        target_lower = target_skill.lower()
        
        # Check exact match
        for skill, conf in candidate_skills.items():
            if skill.lower() == target_lower:
                return min(conf, 1.0)
        
        # Check similar skills via KG
        if self.session:
            # Query for similar skills
            query = """
            MATCH (s1:Skill {name: $target_skill})-[r:SIMILAR_TO]->(s2:Skill)
            WHERE s2.name IN $candidate_skills
            RETURN s2.name AS skill, r.similarity AS similarity
            ORDER BY r.similarity DESC
            LIMIT 1
            """
            
            try:
                result = self.session.run(
                    query,
                    target_skill=target_skill,
                    candidate_skills=list(candidate_skills.keys())
                )
                record = result.single()
                if record:
                    return min(record["similarity"], 0.7)
            except Exception as e:
                logger.debug(f"Similarity query failed: {e}")
            
            # Check cluster match
            query = """
            MATCH (s1:Skill {name: $target_skill})
            MATCH (s2:Skill)
            WHERE s2.name IN $candidate_skills
              AND s1.cluster_id IS NOT NULL
              AND s1.cluster_id = s2.cluster_id
            RETURN s2.name AS skill
            LIMIT 1
            """
            
            try:
                result = self.session.run(
                    query,
                    target_skill=target_skill,
                    candidate_skills=list(candidate_skills.keys())
                )
                if result.single():
                    return 0.7
            except Exception as e:
                logger.debug(f"Cluster query failed: {e}")
        
        # Fuzzy text match
        for skill in candidate_skills:
            skill_lower = skill.lower()
            # Partial match
            if target_lower in skill_lower or skill_lower in target_lower:
                return 0.5
            # Word overlap
            target_words = set(target_lower.split())
            skill_words = set(skill_lower.split())
            if target_words & skill_words:
                return 0.4
        
        return 0.0
    
    def _generate_explanation(
        self,
        readiness: float,
        matched_skills: List[Dict],
        missing_skills: List[Dict],
        job_title: str
    ) -> str:
        """
        Generate plain English explanation using Ollama.
        
        Args:
            readiness: Readiness score 0-1
            matched_skills: Top matched skills
            missing_skills: Top missing skills
            job_title: Job title
            
        Returns:
            4-6 sentence explanation
        """
        matched_names = [s["skill"] for s in matched_skills[:5]]
        missing_names = [s["skill"] for s in missing_skills[:5]]
        
        prompt = f"""Generate a brief, friendly explanation of a job candidate's fit for a position.

Job Title: {job_title or 'this position'}
Readiness Score: {readiness:.0%}

Skills the candidate HAS that match the job:
{', '.join(matched_names) if matched_names else 'None identified'}

Skills the candidate is MISSING:
{', '.join(missing_names) if missing_names else 'None identified'}

Write 4-6 sentences in plain English explaining:
1. Overall fit assessment
2. Key strengths (matching skills)
3. Key gaps (missing skills)
4. Brief recommendation

Keep it professional but friendly. No technical jargon. No bullet points."""

        try:
            url = f"{OLLAMA_BASE_URL}/api/generate"
            response = requests.post(
                url,
                json={
                    "model": NORMALIZER_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.7, "num_predict": 300}
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                explanation = result.get("response", "").strip()
                if explanation:
                    return explanation
        
        except Exception as e:
            logger.error(f"Explanation generation failed: {e}")
        
        # Fallback explanation
        return self._fallback_explanation(readiness, matched_names, missing_names, job_title)
    
    def _fallback_explanation(
        self,
        readiness: float,
        matched_skills: List[str],
        missing_skills: List[str],
        job_title: str
    ) -> str:
        """Generate fallback explanation without LLM."""
        job = job_title or "this position"
        
        if readiness >= 0.8:
            fit = "excellent"
            rec = "highly recommended for consideration"
        elif readiness >= 0.6:
            fit = "good"
            rec = "a strong candidate with some areas for growth"
        elif readiness >= 0.4:
            fit = "moderate"
            rec = "could be considered with additional training"
        else:
            fit = "limited"
            rec = "may need significant skill development"
        
        explanation = f"The candidate shows {fit} alignment with {job}, with a readiness score of {readiness:.0%}. "
        
        if matched_skills:
            explanation += f"Key strengths include experience with {', '.join(matched_skills[:3])}. "
        
        if missing_skills:
            explanation += f"Areas for development include {', '.join(missing_skills[:3])}. "
        
        explanation += f"Overall, this candidate is {rec}."
        
        return explanation


# Module-level singleton
_job_gap_service = None

def get_job_gap_service(neo4j_session=None) -> JobGapService:
    """Get or create job gap service singleton."""
    global _job_gap_service
    if _job_gap_service is None:
        _job_gap_service = JobGapService(neo4j_session)
    elif neo4j_session:
        _job_gap_service.set_session(neo4j_session)
    return _job_gap_service
