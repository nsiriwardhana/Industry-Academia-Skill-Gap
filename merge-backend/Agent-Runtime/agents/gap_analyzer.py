"""
Gap Analyzer Tool - Runs skill confidence & gap analysis.

Orchestrates calls to existing recommendation API endpoints:
- GET /candidates/{candidate_id}/skill-confidence
- GET /candidates/{candidate_id}/roles/{role_key}/skill-gap-advanced

Can use either:
1. Internal function calls (if services are importable)
2. HTTP requests to the recommendation API
"""
import logging
import requests
from typing import List, Dict, Optional
from config import RECOMMENDATION_API_BASE_URL
from models import SkillConfidenceResult, SkillDeficitResult

logger = logging.getLogger(__name__)


class GapAnalyzerTool:
    """
    Gap Analyzer Tool orchestrates skill analysis.
    
    Calls existing recommendation system endpoints to:
    1. Get candidate skill confidence
    2. Get skill gap analysis for target role (symbolic OR hybrid with GNN)
    3. Compute readiness score
    
    Supports three ranking methods:
    - 'symbolic': Traditional TF-IDF based (fast, interpretable)
    - 'hybrid': GNN learnability × importance × gap (personalized, ML-powered)
    - 'additive_gnn': Weighted sum formula (experimental)
    """
    
    def __init__(self, api_base_url: str = None, ranking_method: str = 'symbolic'):
        """
        Initialize gap analyzer.
        
        Args:
            api_base_url: Base URL for recommendation API
            ranking_method: 'symbolic', 'hybrid', or 'additive_gnn'
        """
        self.api_base_url = api_base_url or RECOMMENDATION_API_BASE_URL
        self.ranking_method = ranking_method
        logger.info(f"Gap Analyzer initialized with API: {self.api_base_url}, method: {ranking_method}")
    
    def analyze_gap(
        self,
        candidate_id: str,
        role_key: str,
        top_k: int = 20
    ) -> Dict:
        """
        Run complete gap analysis for candidate-role pair.
        
        Args:
            candidate_id: Candidate identifier
            role_key: Target role key
            top_k: Number of top skills/deficits to return
            
        Returns:
            Dictionary with skill_confidence_top, skill_gap_top, readiness_score
        """
        logger.info(f"Analyzing gap: candidate={candidate_id}, role={role_key}")
        
        result = {
            "skill_confidence_top": [],
            "skill_gap_top": [],
            "readiness_score": None
        }
        
        try:
            # Step 1: Get skill confidence
            confidence_results = self._get_skill_confidence(candidate_id, top_k)
            result["skill_confidence_top"] = confidence_results
            
            # Step 2: Get skill gap analysis
            gap_results = self._get_skill_gap(candidate_id, role_key, top_k)
            result["skill_gap_top"] = gap_results["deficits"]
            
            # Step 3: Compute readiness score
            result["readiness_score"] = self._compute_readiness(gap_results["deficits"])
            
            logger.info(
                f"[OK] Gap analysis complete: "
                f"{len(result['skill_confidence_top'])} confidence, "
                f"{len(result['skill_gap_top'])} deficits, "
                f"readiness={result['readiness_score']:.2f}"
            )
            
        except Exception as e:
            logger.error(f"Gap analysis failed: {e}")
            result["error"] = str(e)
        
        return result
    
    def _get_skill_confidence(
        self,
        candidate_id: str,
        top_n: int = 25
    ) -> List[SkillConfidenceResult]:
        """
        Get candidate skill confidence from recommendation API.
        
        Endpoint: GET /candidates/{candidate_id}/skill-confidence?top_n={top_n}
        """
        url = f"{self.api_base_url}/candidates/{candidate_id}/skill-confidence"
        params = {"top_n": top_n}
        
        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Parse response
            confidence_results = []
            for skill in data.get("skills", []):
                confidence_results.append(SkillConfidenceResult(
                    skill_name=skill["skill_name"],
                    confidence=skill["confidence"],
                    evidence_count=skill["evidence_count"],
                    evidence_sources=skill["evidence_sources"]
                ))
            
            logger.info(f"Retrieved {len(confidence_results)} skill confidence scores")
            return confidence_results
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get skill confidence: {e}")
            return []
    
    def _get_skill_gap(
        self,
        candidate_id: str,
        role_key: str,
        top_k: int = 25
    ) -> Dict:
        """
        Get skill gap analysis from recommendation API.
        
        Supports three endpoints based on ranking_method:
        - symbolic: /skill-gap-advanced (TF-IDF based)
        - hybrid: /skill-gap-hybrid (GNN × importance × gap)
        - additive_gnn: /missing-skills-gnn (weighted sum)
        """
        # Select endpoint based on ranking method
        if self.ranking_method == 'hybrid' or self.ranking_method == 'additive_gnn':
            # Both use GNN endpoint (missing-skills-gnn)
            endpoint = f"{self.api_base_url}/candidates/{candidate_id}/roles/{role_key}/missing-skills-gnn"
        else:  # default to 'symbolic'
            endpoint = f"{self.api_base_url}/candidates/{candidate_id}/roles/{role_key}/skill-gap-advanced"
        
        params = {"top_k": top_k}
        
        try:
            response = requests.get(endpoint, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Parse deficits based on response format
            deficit_results = []
            
            if self.ranking_method in ['hybrid', 'additive_gnn']:
                # GNN endpoint returns: top_missing_skills with all GNN fields
                for skill_data in data.get("top_missing_skills", []):
                    deficit_results.append(SkillDeficitResult(
                        skill_name=skill_data["skill"],
                        p_has=skill_data["P_has"],
                        importance=skill_data["importance"],
                        deficit=skill_data["gap_magnitude"],  # Use gap_magnitude as deficit
                        tf=0,  # Not provided in GNN response
                        df=0,
                        idf=0,
                        # GNN-specific fields
                        P_gnn=skill_data.get("P_gnn"),
                        final_score=skill_data.get("final_score"),
                        gap=skill_data.get("gap_magnitude"),
                        importance_norm=skill_data.get("importance"),  # Already normalized
                        reason=skill_data.get("reason"),
                        category=skill_data.get("category"),
                        ranking_method=self.ranking_method
                    ))
                
            else:
                # Symbolic endpoint returns: deficits with tf, df, idf
                for deficit in data.get("deficits", []):
                    deficit_results.append(SkillDeficitResult(
                        skill_name=deficit["skill_name"],
                        p_has=deficit["p_has"],
                        importance=deficit["importance"],
                        deficit=deficit["deficit"],
                        tf=deficit.get("tf", 0),
                        df=deficit.get("df", 0),
                        idf=deficit.get("idf", 0),
                        ranking_method="symbolic"
                    ))
            
            logger.info(f"Retrieved {len(deficit_results)} skill deficits using {self.ranking_method} method")
            
            return {
                "deficits": deficit_results,
                "role_name": data.get("role_name", role_key),
                "ranking_method": self.ranking_method
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get skill gap: {e}")
            return {"deficits": [], "role_name": role_key, "ranking_method": self.ranking_method}
    
    @staticmethod
    def _compute_readiness(deficits: List[SkillDeficitResult]) -> float:
        """
        Compute readiness score from deficits.
        
        Formula: readiness = 1 - (sum(deficits) / sum(importances))
        
        Args:
            deficits: List of skill deficits
            
        Returns:
            Readiness score [0, 1]
        """
        if not deficits:
            return 1.0
        
        total_deficit = sum(d.deficit for d in deficits)
        total_importance = sum(d.importance for d in deficits)
        
        if total_importance == 0:
            return 1.0
        
        skill_gap_index = total_deficit / total_importance
        readiness = 1 - skill_gap_index
        
        return max(0.0, min(1.0, readiness))  # Clamp to [0, 1]
    
    def check_api_health(self) -> bool:
        """
        Check if recommendation API is available.
        
        Returns:
            True if API is healthy, False otherwise
        """
        try:
            url = f"{self.api_base_url}/"
            response = requests.get(url, timeout=5)
            return response.status_code == 200
        except:
            return False
