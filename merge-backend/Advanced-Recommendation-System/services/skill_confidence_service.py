"""
Skill Confidence Engine - Multi-Evidence Aggregation.

Computes evidence-weighted confidence scores using formula:
P(has(skill)) = 1 - Π(1 - evidence_i)
"""
import logging
from typing import Dict, List
from config import EVIDENCE_WEIGHTS

logger = logging.getLogger(__name__)


class SkillConfidenceService:
    """
    Computes skill confidence from multiple evidence sources.
    
    Evidence Sources:
    - HAS_SKILL: Direct CV claims
    - USED_SKILL: Work experience (capped at 3 instances)
    - USES_TECHNOLOGY: Project usage (capped at 3 instances)
    - CERTIFICATION: Certification keywords
    """
    
    @staticmethod
    def compute_confidence(session, candidate_id: str) -> Dict[str, Dict]:
        """
        Compute evidence-weighted skill confidence for a candidate.
        
        Args:
            session: Neo4j session
            candidate_id: Candidate identifier
            
        Returns:
            Dict mapping skill_name to {confidence, evidence_sources, evidence_count}
        """
        logger.info(f"Computing skill confidence for candidate: {candidate_id}")
        
        skill_evidence = {}
        
        # Query 1: HAS_SKILL (CV direct claims)
        query_has_skill = """
        MATCH (p:Person {candidate_id: $candidate_id})-[:HAS_SKILL]->(s:Skill)
        RETURN DISTINCT s.name AS skill_name
        LIMIT 1000
        """
        result = session.run(query_has_skill, candidate_id=candidate_id)
        for record in result:
            skill_name = record["skill_name"]
            if skill_name not in skill_evidence:
                skill_evidence[skill_name] = []
            skill_evidence[skill_name].append(("HAS_SKILL", 1))
        
        # Query 2: USED_SKILL (work experience)
        query_used_skill = """
        MATCH (p:Person {candidate_id: $candidate_id})-[:WORKED_AT]->(w:WorkExperience)
              -[:USED_SKILL]->(s:Skill)
        WITH s.name AS skill_name, count(DISTINCT w) AS work_count
        RETURN skill_name, work_count
        LIMIT 1000
        """
        result = session.run(query_used_skill, candidate_id=candidate_id)
        for record in result:
            skill_name = record["skill_name"]
            work_count = min(record["work_count"], 3)  # Cap at 3
            if skill_name not in skill_evidence:
                skill_evidence[skill_name] = []
            skill_evidence[skill_name].append(("USED_SKILL", work_count))
        
        # Query 3: USES_TECHNOLOGY (projects)
        query_uses_tech = """
        MATCH (p:Person {candidate_id: $candidate_id})-[:WORKED_ON]->(pr:Project)
              -[:USES_TECHNOLOGY]->(s:Skill)
        WITH s.name AS skill_name, count(DISTINCT pr) AS project_count
        RETURN skill_name, project_count
        LIMIT 1000
        """
        result = session.run(query_uses_tech, candidate_id=candidate_id)
        for record in result:
            skill_name = record["skill_name"]
            project_count = min(record["project_count"], 3)  # Cap at 3
            if skill_name not in skill_evidence:
                skill_evidence[skill_name] = []
            skill_evidence[skill_name].append(("USES_TECHNOLOGY", project_count))
        
        # Query 4: CERTIFICATION (keyword matching)
        query_cert = """
        MATCH (p:Person {candidate_id: $candidate_id})-[:HAS_CERTIFICATION]->(cert:Certification)
        RETURN cert.name AS cert_name, cert.issuer AS cert_issuer
        LIMIT 100
        """
        result = session.run(query_cert, candidate_id=candidate_id)
        certifications = [(r["cert_name"], r.get("cert_issuer", "")) for r in result]
        
        # Simple keyword matching for certifications
        # In production, use more sophisticated NLP matching
        for cert_name, cert_issuer in certifications:
            cert_text = f"{cert_name} {cert_issuer}".lower()
            # Example keywords - expand based on your data
            skill_keywords = {
                "python": ["python"],
                "java": ["java"],
                "aws": ["aws", "amazon web services"],
                "azure": ["azure", "microsoft azure"],
                "machine learning": ["machine learning", "ml"],
                "data science": ["data science"],
            }
            for skill_name, keywords in skill_keywords.items():
                if any(kw in cert_text for kw in keywords):
                    if skill_name not in skill_evidence:
                        skill_evidence[skill_name] = []
                    skill_evidence[skill_name].append(("CERTIFICATION", 1))
        
        # Combine evidence using probability formula
        skill_confidence = {}
        for skill_name, evidence_list in skill_evidence.items():
            prob_not_has = 1.0
            evidence_sources = set()
            evidence_count = 0
            
            for evidence_type, count in evidence_list:
                weight = EVIDENCE_WEIGHTS.get(evidence_type, 0.5)
                # Apply evidence multiple times (for USED_SKILL, USES_TECHNOLOGY)
                for _ in range(count):
                    prob_not_has *= (1 - weight)
                    evidence_count += 1
                evidence_sources.add(evidence_type)
            
            confidence = 1 - prob_not_has
            skill_confidence[skill_name] = {
                "confidence": confidence,
                "evidence_sources": sorted(list(evidence_sources)),
                "evidence_count": evidence_count,
            }
        
        logger.info(f"Computed confidence for {len(skill_confidence)} skills")
        return skill_confidence
