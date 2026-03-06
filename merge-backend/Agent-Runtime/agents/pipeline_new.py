"""
UPDATED AGENT PIPELINE IMPLEMENTATION
Matches your KG structure requirements exactly.
"""

# ==================================================
# 1. EXTRACTOR - Validate Schema
# ==================================================

from models.schemas_new import ExtractedData
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class Extractor:
    """Validates incoming CV data matches KG format."""
    
    def extract(self, data: ExtractedData) -> ExtractedData:
        """
        Validate extracted data schema.
        
        NOTE: Uses candidate_name and mobile_number (NOT 'name' or 'mobile').
        """
        # Required fields
        if not data.candidate_id:
            raise ValueError("candidate_id is required")
        if not data.candidate_name:
            raise ValueError("candidate_name is required")
        
        # Log what we got
        skills_count = len(data.all_skills) if data.all_skills else 0
        projects_count = len(data.projects_and_technologies_involved)
        certs_count = len(data.certificates_or_qualifications)
        
        logger.info(
            f"✓ Validated: {skills_count} skills, "
            f"{projects_count} projects, {certs_count} certifications"
        )
        
        return data


# ==================================================
# 2. NORMALIZER - Normalize Skills
# ==================================================

class Normalizer:
    """
    Normalize skill names from:
    1. all_skills (primary)
    2. projects_and_technologies_involved[].technologies_used (secondary)
    """
    
    def __init__(self, skill_aliases: Dict[str, str]):
        """
        Args:
            skill_aliases: Mapping from variant -> canonical name
                e.g., {"python3": "Python", "tf": "TensorFlow"}
        """
        self.aliases = {k.lower(): v for k, v in skill_aliases.items()}
        logger.info(f"Normalizer initialized with {len(self.aliases)} aliases")
    
    def normalize(self, data: ExtractedData) -> ExtractedData:
        """
        Normalize skills and update all_skills with canonical names.
        """
        all_skill_names = set()
        
        # Source 1: all_skills (PRIMARY)
        if data.all_skills:
            all_skill_names.update(data.all_skills)
        
        # Source 2: projects_and_technologies_involved (SECONDARY)
        for project in data.projects_and_technologies_involved:
            all_skill_names.update(project.technologies_used)
        
        # Normalize to canonical names
        normalized = set()
        for skill in all_skill_names:
            skill_lower = skill.lower().strip()
            canonical = self.aliases.get(skill_lower, skill)  # Use alias or original
            normalized.add(canonical)
        
        # Update data with normalized skills
        data.all_skills = sorted(normalized)
        data.num_skills = len(normalized)
        
        logger.info(f"✓ Normalized {len(all_skill_names)} → {len(normalized)} skills")
        
        return data


# ==================================================
# 3. KG WRITER - Write to Neo4j
# ==================================================

from neo4j import Session


class KGWriter:
    """Writes candidate data to Neo4j knowledge graph."""
    
    def write(self, session: Session, data: ExtractedData, role_key: str) -> Dict[str, int]:
        """
        Write candidate to Neo4j matching your KG structure.
        
        Creates:
        - Person node (MERGE by candidate_id)
        - Skill nodes
        - Project nodes
        - Certification nodes
        - Education node
        - TARGETS_ROLE relationship using role_key parameter
        
        Returns:
            Stats dict with nodes_created, relationships_created
        """
        stats = {"nodes_created": 0, "relationships_created": 0}
        
        # ==================================================
        # Step 1: MERGE Person Node
        # ==================================================
        person_query = """
        MERGE (p:Person {candidate_id: $candidate_id})
        SET p.candidate_name = $candidate_name,
            p.email = $email,
            p.mobile_number = $mobile_number,
            p.current_role = $current_role,
            p.target_role = $target_role,
            p.current_employment = $current_employment,
            p.experience_months = $experience_months,
            p.experience_level = $experience_level,
            p.num_skills = $num_skills,
            p.num_projects = $num_projects,
            p.evaluation_score = $evaluation_score,
            p.skill_score = $skill_score,
            p.date_uploaded = $date_uploaded,
            p.status = $status
        RETURN p
        """
        
        session.run(person_query, **{
            "candidate_id": data.candidate_id,
            "candidate_name": data.candidate_name,
            "email": data.email,
            "mobile_number": data.mobile_number,
            "current_role": data.current_role,
            "target_role": data.target_role,
            "current_employment": data.current_employment,
            "experience_months": data.experience_months,
            "experience_level": data.experience_level,
            "num_skills": data.num_skills,
            "num_projects": data.num_projects,
            "evaluation_score": data.evaluation_score,
            "skill_score": data.skill_score,
            "date_uploaded": data.date_uploaded,
            "status": data.status
        })
        stats["nodes_created"] += 1
        
        # ==================================================
        # Step 2: MERGE Skills & Create HAS_SKILL
        # ==================================================
        if data.all_skills:
            for skill_name in data.all_skills:
                skill_query = """
                MATCH (p:Person {candidate_id: $candidate_id})
                MERGE (s:Skill {name: $skill_name})
                MERGE (p)-[:HAS_SKILL]->(s)
                """
                session.run(skill_query, candidate_id=data.candidate_id, skill_name=skill_name)
                stats["nodes_created"] += 1
                stats["relationships_created"] += 1
        
        # ==================================================
        # Step 3: Create Projects & USES_TECHNOLOGY
        # ==================================================
        for project in data.projects_and_technologies_involved:
            project_query = """
            MATCH (p:Person {candidate_id: $candidate_id})
            CREATE (pr:Project {
                project_name: $project_name,
                project_description: $project_description,
                duration: $duration,
                complexity: $complexity
            })
            MERGE (p)-[:WORKED_ON]->(pr)
            """
            session.run(project_query, **{
                "candidate_id": data.candidate_id,
                "project_name": project.project_name,
                "project_description": project.project_description,
                "duration": project.duration,
                "complexity": project.complexity
            })
            stats["nodes_created"] += 1
            stats["relationships_created"] += 1
            
            # Connect project to technologies
            for tech in project.technologies_used:
                tech_query = """
                MATCH (pr:Project {project_name: $project_name})
                MERGE (s:Skill {name: $tech})
                MERGE (pr)-[:USES_TECHNOLOGY]->(s)
                """
                session.run(tech_query, project_name=project.project_name, tech=tech)
                stats["relationships_created"] += 1
        
        # ==================================================
        # Step 4: Create Certifications & HAS_CERTIFICATION
        # ==================================================
        for cert_string in data.certificates_or_qualifications:
            # Parse "Name: Issuer" format
            if ":" in cert_string:
                cert_name, cert_issuer = cert_string.split(":", 1)
                cert_name = cert_name.strip()
                cert_issuer = cert_issuer.strip()
            else:
                cert_name = cert_string.strip()
                cert_issuer = None
            
            cert_query = """
            MATCH (p:Person {candidate_id: $candidate_id})
            CREATE (c:Certification {
                name: $cert_name,
                issuer: $cert_issuer
            })
            MERGE (p)-[:HAS_CERTIFICATION]->(c)
            """
            session.run(cert_query, **{
                "candidate_id": data.candidate_id,
                "cert_name": cert_name,
                "cert_issuer": cert_issuer
            })
            stats["nodes_created"] += 1
            stats["relationships_created"] += 1
        
        # ==================================================
        # Step 5: Create Education & HAS_EDUCATION
        # ==================================================
        if data.education:
            edu_query = """
            MATCH (p:Person {candidate_id: $candidate_id})
            MERGE (inst:Institution {name: $university})
            CREATE (edu:Education {
                degree: $degree
            })
            MERGE (p)-[:HAS_EDUCATION]->(edu)
            MERGE (edu)-[:FROM_INSTITUTION]->(inst)
            """
            session.run(edu_query, **{
                "candidate_id": data.candidate_id,
                "degree": data.education.degree,
                "university": data.education.university
            })
            stats["nodes_created"] += 2  # Education + Institution
            stats["relationships_created"] += 2
        
        # ==================================================
        # Step 6: Create TARGETS_ROLE (using role_key parameter)
        # ==================================================
        role_query = """
        MATCH (p:Person {candidate_id: $candidate_id})
        MERGE (r:Role {role_key: $role_key})
        MERGE (p)-[:TARGETS_ROLE]->(r)
        """
        session.run(role_query, candidate_id=data.candidate_id, role_key=role_key)
        stats["relationships_created"] += 1
        
        logger.info(
            f"✓ KG Write: {stats['nodes_created']} nodes, "
            f"{stats['relationships_created']} relationships"
        )
        
        return stats


# ==================================================
# 4. GAP ANALYZER - Call Existing APIs
# ==================================================

import requests
from typing import Optional


class GapAnalyzer:
    """Calls existing skill confidence and gap analysis APIs."""
    
    def __init__(self, api_base_url: str):
        """
        Args:
            api_base_url: Base URL of Advanced-Recommendation-System (e.g., http://localhost:8001)
        """
        self.base_url = api_base_url.rstrip("/")
        logger.info(f"Gap Analyzer initialized with API: {self.base_url}")
    
    def analyze(
        self, 
        candidate_id: str, 
        role_key: str, 
        top_k: int = 25
    ) -> Dict[str, Any]:
        """
        Call skill confidence and gap analysis endpoints.
        
        Endpoints called:
        1. /candidates/{candidate_id}/skill-confidence
        2. /candidates/{candidate_id}/roles/{role_key}/skill-gap-advanced?top_k=...
        
        Returns:
            Combined result dict with top_skills, top_deficits, readiness_score
        """
        result = {}
        
        # ==================================================
        # Call 1: Skill Confidence
        # ==================================================
        try:
            url = f"{self.base_url}/candidates/{candidate_id}/skill-confidence"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            confidence_data = response.json()
            result["top_skills"] = confidence_data.get("top_skills", [])
            logger.info(f"✓ Skill confidence: {len(result['top_skills'])} skills")
        except Exception as e:
            logger.error(f"✗ Skill confidence failed: {e}")
            result["top_skills"] = []
        
        # ==================================================
        # Call 2: Skill Gap Advanced
        # ==================================================
        try:
            url = f"{self.base_url}/candidates/{candidate_id}/roles/{role_key}/skill-gap-advanced"
            response = requests.get(url, params={"top_k": top_k}, timeout=30)
            response.raise_for_status()
            gap_data = response.json()
            result["top_deficits"] = gap_data.get("skill_deficits", [])
            result["readiness_score"] = gap_data.get("readiness_score")
            logger.info(
                f"✓ Gap analysis: {len(result['top_deficits'])} deficits, "
                f"readiness={result['readiness_score']}"
            )
        except Exception as e:
            logger.error(f"✗ Gap analysis failed: {e}")
            result["top_deficits"] = []
            result["readiness_score"] = None
        
        return result
