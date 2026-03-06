"""
Skill Normalization Service using LLM (Ollama or HuggingFace).

Maps raw extracted skills to canonical skill names in the Knowledge Graph.

Strategy:
1. Query Neo4j for top-5 canonical skill candidates (exact + embedding similarity)
2. Send ONLY these candidates to LLM (Ollama/HuggingFace) for selection
3. Return normalized skill with confidence score

Environment Variables:
- OLLAMA_BASE_URL: Ollama API endpoint (default: http://localhost:11434)
- HF_TOKEN: HuggingFace API token (required if using huggingface provider)
- NORMALIZER_PROVIDER: "ollama" or "huggingface" (default: ollama)
- NORMALIZER_MODEL: Model name (default: qwen2.5:3b-instruct for Ollama, Qwen/Qwen2.5-3B-Instruct for HF)
"""
import os
import json
import logging
from typing import List, Dict, Optional, Tuple
import requests
from functools import lru_cache

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
HF_TOKEN = os.getenv("HF_TOKEN", "")
HF_API_BASE = "https://api-inference.huggingface.co/models"

NORMALIZER_PROVIDER = os.getenv("NORMALIZER_PROVIDER", "ollama")
NORMALIZER_MODEL = os.getenv("NORMALIZER_MODEL", "qwen2.5:3b-instruct")

# Minimum confidence to accept a mapping
MIN_CONFIDENCE_THRESHOLD = 0.6

# Cache settings
NORMALIZATION_CACHE_SIZE = 500


class SkillNormalizeLLMService:
    """
    LLM-based skill normalization service.
    
    Uses Ollama or HuggingFace (configurable provider) to map raw skills
    to canonical names from the Knowledge Graph.
    """
    
    def __init__(self, neo4j_session=None):
        """
        Initialize normalization service.
        
        Args:
            neo4j_session: Optional Neo4j session for skill lookups
        """
        self.provider = NORMALIZER_PROVIDER
        self.model = NORMALIZER_MODEL
        self.ollama_url = OLLAMA_BASE_URL
        self.session = neo4j_session
        
        # Cache for normalized mappings
        self._cache: Dict[str, Dict] = {}
        
        logger.info(
            f"SkillNormalizeLLMService initialized: "
            f"provider={self.provider}, model={self.model}"
        )
    
    def set_session(self, session) -> None:
        """Set Neo4j session for skill lookups."""
        self.session = session
    
    def normalize_skill(self, raw_skill: str) -> Dict:
        """
        Normalize a single raw skill to canonical form.
        
        Args:
            raw_skill: Raw skill name from extraction
            
        Returns:
            {
                "raw_skill": "...",
                "canonical_skill": "...",
                "confidence": 0.0-1.0,
                "matched": True/False,
                "method": "exact"|"llm"|"unmapped"
            }
        """
        raw_lower = raw_skill.lower().strip()
        
        # Check cache first
        if raw_lower in self._cache:
            logger.debug(f"Cache hit for: {raw_skill}")
            return self._cache[raw_lower]
        
        # Step 1: Try exact match in KG
        exact_match = self._exact_match(raw_skill)
        if exact_match:
            result = {
                "raw_skill": raw_skill,
                "canonical_skill": exact_match,
                "confidence": 1.0,
                "matched": True,
                "method": "exact"
            }
            self._cache[raw_lower] = result
            return result
        
        # Step 2: Get top-5 candidates from KG (exact + embedding similarity)
        candidates = self._get_skill_candidates(raw_skill, top_k=5)
        
        if not candidates:
            # No candidates found - mark as unmapped
            result = {
                "raw_skill": raw_skill,
                "canonical_skill": None,
                "confidence": 0.0,
                "matched": False,
                "method": "unmapped"
            }
            self._cache[raw_lower] = result
            logger.warning(f"No candidates found for: {raw_skill}")
            return result
        
        # Step 3: Send to LLM for selection
        llm_result = self._llm_select(raw_skill, candidates)
        
        # Cache and return
        self._cache[raw_lower] = llm_result
        return llm_result
    
    def normalize_skills_batch(self, raw_skills: List[str]) -> List[Dict]:
        """
        Normalize a batch of raw skills.
        
        Args:
            raw_skills: List of raw skill names
            
        Returns:
            List of normalization results
        """
        logger.info(f"Normalizing batch of {len(raw_skills)} skills")
        
        results = []
        for skill in raw_skills:
            result = self.normalize_skill(skill)
            results.append(result)
        
        matched = sum(1 for r in results if r["matched"])
        logger.info(f"Batch normalization complete: {matched}/{len(raw_skills)} matched")
        
        return results
    
    def _exact_match(self, raw_skill: str) -> Optional[str]:
        """
        Try exact match against KG skill names.
        
        Handles case-insensitive matching.
        """
        if not self.session:
            return None
        
        query = """
        MATCH (s:Skill)
        WHERE toLower(s.name) = toLower($skill_name)
        RETURN s.name AS name
        LIMIT 1
        """
        
        try:
            result = self.session.run(query, skill_name=raw_skill)
            record = result.single()
            if record:
                return record["name"]
        except Exception as e:
            logger.error(f"Exact match query failed: {e}")
        
        return None
    
    def _get_skill_candidates(self, raw_skill: str, top_k: int = 5) -> List[Dict]:
        """
        Get top-K canonical skill candidates from KG.
        
        Uses:
        1. Case-insensitive partial matching
        2. Embedding similarity (if available)
        
        Returns:
            List of {"name": "...", "score": 0.0-1.0}
        """
        if not self.session:
            logger.warning("No Neo4j session - returning empty candidates")
            return []
        
        # Query 1: Partial text match
        text_query = """
        MATCH (s:Skill)
        WHERE toLower(s.name) CONTAINS toLower($skill_name)
           OR toLower($skill_name) CONTAINS toLower(s.name)
        RETURN s.name AS name, 0.8 AS score
        LIMIT $limit
        """
        
        # Query 2: Embedding similarity (if embeddings exist)
        # This query finds skills similar via SIMILAR_TO edges
        similarity_query = """
        MATCH (s1:Skill)-[r:SIMILAR_TO]->(s2:Skill)
        WHERE toLower(s1.name) CONTAINS toLower($skill_name)
        RETURN s2.name AS name, r.similarity AS score
        ORDER BY r.similarity DESC
        LIMIT $limit
        """
        
        candidates = []
        seen = set()
        
        try:
            # Run text match query
            result = self.session.run(text_query, skill_name=raw_skill, limit=top_k)
            for record in result:
                name = record["name"]
                if name.lower() not in seen:
                    candidates.append({"name": name, "score": record["score"]})
                    seen.add(name.lower())
            
            # Run similarity query if we need more candidates
            if len(candidates) < top_k:
                result = self.session.run(
                    similarity_query, 
                    skill_name=raw_skill, 
                    limit=top_k - len(candidates)
                )
                for record in result:
                    name = record["name"]
                    if name.lower() not in seen:
                        candidates.append({"name": name, "score": record["score"]})
                        seen.add(name.lower())
            
            # If still no candidates, try fuzzy search
            if not candidates:
                fuzzy_query = """
                MATCH (s:Skill)
                RETURN s.name AS name
                LIMIT 100
                """
                result = self.session.run(fuzzy_query)
                all_skills = [record["name"] for record in result]
                
                # Simple fuzzy: skills that share words
                raw_words = set(raw_skill.lower().split())
                for skill_name in all_skills:
                    skill_words = set(skill_name.lower().split())
                    overlap = len(raw_words & skill_words)
                    if overlap > 0:
                        score = overlap / max(len(raw_words), len(skill_words))
                        candidates.append({"name": skill_name, "score": score})
                
                # Sort by score and take top-k
                candidates = sorted(candidates, key=lambda x: x["score"], reverse=True)[:top_k]
        
        except Exception as e:
            logger.error(f"Candidate query failed: {e}")
        
        return candidates
    
    def _llm_select(self, raw_skill: str, candidates: List[Dict]) -> Dict:
        """
        Use LLM to select best canonical skill from candidates.
        
        Args:
            raw_skill: Raw skill name
            candidates: List of {"name": "...", "score": ...}
            
        Returns:
            Normalization result dict
        """
        candidate_names = [c["name"] for c in candidates]
        
        # Build prompt
        prompt = self._build_selection_prompt(raw_skill, candidate_names)
        
        try:
            if self.provider == "ollama":
                response = self._call_ollama(prompt)
            elif self.provider == "huggingface":
                response = self._call_huggingface(prompt)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}. Use 'ollama' or 'huggingface'")
            
            # Parse JSON response
            result = self._parse_llm_response(response, raw_skill, candidate_names)
            return result
            
        except Exception as e:
            logger.error(f"LLM selection failed for '{raw_skill}': {e}")
            
            # Fallback: return highest-scoring candidate
            if candidates:
                best = max(candidates, key=lambda x: x["score"])
                return {
                    "raw_skill": raw_skill,
                    "canonical_skill": best["name"],
                    "confidence": best["score"] * 0.5,  # Reduce confidence for fallback
                    "matched": best["score"] >= MIN_CONFIDENCE_THRESHOLD,
                    "method": "fallback"
                }
            
            return {
                "raw_skill": raw_skill,
                "canonical_skill": None,
                "confidence": 0.0,
                "matched": False,
                "method": "error"
            }
    
    def _build_selection_prompt(self, raw_skill: str, candidates: List[str]) -> str:
        """Build prompt for LLM skill selection."""
        candidates_str = "\n".join(f"- {c}" for c in candidates)
        
        prompt = f"""You are a skill normalization assistant. Your task is to map a raw skill name to the most appropriate canonical skill from the given list.

Raw skill: "{raw_skill}"

Canonical skill candidates:
{candidates_str}

Instructions:
1. Select the canonical skill that best matches the raw skill's meaning
2. If none match well, select the closest one and give low confidence
3. Return ONLY valid JSON in this exact format:

{{"raw_skill": "{raw_skill}", "canonical_skill": "<selected_canonical>", "confidence": <0.0-1.0>}}

Return ONLY the JSON, no explanation."""

        return prompt
    
    def _call_ollama(self, prompt: str) -> str:
        """
        Call Ollama API for completion.
        
        Args:
            prompt: The prompt to send
            
        Returns:
            Generated text response
        """
        url = f"{self.ollama_url}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,  # Low temp for consistent output
                "num_predict": 100,  # Limit output length
            }
        }
        
        logger.debug(f"Calling Ollama: {url}")
        
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        return result.get("response", "")
    
    def _call_huggingface(self, prompt: str) -> str:
        """
        Call HuggingFace Inference API for completion.
        
        Args:
            prompt: The prompt to send
            
        Returns:
            Generated text response
        """
        if not HF_TOKEN:
            raise ValueError("HF_TOKEN environment variable is required for HuggingFace provider")
        
        url = f"{HF_API_BASE}/{self.model}"
        
        headers = {
            "Authorization": f"Bearer {HF_TOKEN}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 100,
                "temperature": 0.1,
                "return_full_text": False
            }
        }
        
        logger.debug(f"Calling HuggingFace: {url}")
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        # Handle different response formats
        if isinstance(result, list) and len(result) > 0:
            return result[0].get("generated_text", "")
        elif isinstance(result, dict):
            return result.get("generated_text", "")
        
        return str(result)
    
    def _parse_llm_response(
        self, 
        response: str, 
        raw_skill: str,
        candidates: List[str]
    ) -> Dict:
        """
        Parse LLM response to extract normalization result.
        
        Args:
            response: Raw LLM response
            raw_skill: Original raw skill
            candidates: List of candidate names
            
        Returns:
            Normalization result dict
        """
        # Try to extract JSON from response
        try:
            # Clean response
            response = response.strip()
            
            # Find JSON in response
            json_match = None
            if response.startswith("{"):
                json_match = response
            else:
                import re
                match = re.search(r'\{[^{}]+\}', response)
                if match:
                    json_match = match.group()
            
            if json_match:
                data = json.loads(json_match)
                
                canonical = data.get("canonical_skill", "")
                confidence = float(data.get("confidence", 0.0))
                
                # Validate canonical is in candidates
                if canonical and canonical not in candidates:
                    # Try case-insensitive match
                    for c in candidates:
                        if c.lower() == canonical.lower():
                            canonical = c
                            break
                
                return {
                    "raw_skill": raw_skill,
                    "canonical_skill": canonical if confidence >= MIN_CONFIDENCE_THRESHOLD else None,
                    "confidence": confidence,
                    "matched": confidence >= MIN_CONFIDENCE_THRESHOLD,
                    "method": "llm"
                }
        
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM JSON response: {e}")
        except Exception as e:
            logger.warning(f"Error parsing LLM response: {e}")
        
        # Fallback: try to extract skill name from text
        for candidate in candidates:
            if candidate.lower() in response.lower():
                return {
                    "raw_skill": raw_skill,
                    "canonical_skill": candidate,
                    "confidence": 0.5,
                    "matched": False,  # Low confidence
                    "method": "llm_partial"
                }
        
        return {
            "raw_skill": raw_skill,
            "canonical_skill": None,
            "confidence": 0.0,
            "matched": False,
            "method": "llm_failed"
        }
    
    def clear_cache(self) -> None:
        """Clear normalization cache."""
        self._cache.clear()
        logger.info("Normalization cache cleared")
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        return {
            "cache_size": len(self._cache),
            "max_size": NORMALIZATION_CACHE_SIZE
        }


# Module-level singleton
_normalize_service = None

def get_skill_normalize_service(neo4j_session=None) -> SkillNormalizeLLMService:
    """Get or create normalization service singleton."""
    global _normalize_service
    if _normalize_service is None:
        _normalize_service = SkillNormalizeLLMService(neo4j_session)
    elif neo4j_session:
        _normalize_service.set_session(neo4j_session)
    return _normalize_service
