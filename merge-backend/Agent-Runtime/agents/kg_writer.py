"""
KG Writer Tool - Creates/updates candidate graph in Neo4j.

Responsibilities:
- MERGE Person by candidate_id
- MERGE/CREATE Skills, Companies, Projects, Certifications, Education
- Create relationships with proper deduplication
- Use UNWIND for batch performance
- Return write statistics
"""
import logging
from typing import List, Dict, Any, Optional
from neo4j import Session
from models import ExtractedData, GraphWriteResult

logger = logging.getLogger(__name__)


class KGWriterTool:
    """
    Knowledge Graph Writer Tool.
    
    Writes candidate data to Neo4j with proper deduplication
    and batch performance optimization using UNWIND.
    """
    
    @staticmethod
    def write_candidate(session: Session, extracted_data: ExtractedData) -> GraphWriteResult:
        """
        Write complete candidate profile to Neo4j.
        
        Strategy:
        1. MERGE Person node
        2. Batch MERGE all Skills
        3. Create HAS_SKILL relationships
        4. Create work experiences with USED_SKILL
        5. Create projects with USES_TECHNOLOGY
        6. Create certifications
        7. Create education
        
        Args:
            session: Neo4j session
            extracted_data: Normalized candidate data
            
        Returns:
            GraphWriteResult with statistics
        """
        logger.info(f"Writing candidate {extracted_data.candidate_id} to Neo4j")
        
        candidate_id = extracted_data.candidate_id
        nodes_created = 0
        relationships_created = 0
        
        try:
            # Step 1: MERGE Person node
            person_result = KGWriterTool._merge_person(session, extracted_data)
            nodes_created += person_result["nodes_created"]
            
            # Step 2: MERGE Skills (batch)
            skills_result = KGWriterTool._merge_skills(session, extracted_data)
            nodes_created += skills_result["nodes_created"]
            
            # Step 3: Create HAS_SKILL relationships
            has_skill_result = KGWriterTool._create_has_skill_relationships(
                session, candidate_id, extracted_data.skills
            )
            relationships_created += has_skill_result["relationships_created"]
            
            # Step 4: Create work experiences with USED_SKILL
            work_exp_result = KGWriterTool._create_work_experiences(
                session, candidate_id, extracted_data.work_experiences
            )
            nodes_created += work_exp_result["nodes_created"]
            relationships_created += work_exp_result["relationships_created"]
            
            # Step 5: Create projects
            project_result = KGWriterTool._create_projects(
                session, candidate_id, extracted_data.projects_and_technologies_involved
            )
            nodes_created += project_result["nodes_created"]
            relationships_created += project_result["relationships_created"]
            
            # Step 6: Create certifications
            cert_result = KGWriterTool._create_certifications(
                session, candidate_id, extracted_data.certificates_or_qualifications
            )
            nodes_created += cert_result["nodes_created"]
            relationships_created += cert_result["relationships_created"]
            
            # Step 7: Create education
            edu_result = KGWriterTool._create_education(
                session, candidate_id, extracted_data.education
            )
            nodes_created += edu_result["nodes_created"]
            relationships_created += edu_result["relationships_created"]
            
            logger.info(
                f"✓ Wrote candidate {candidate_id}: "
                f"{nodes_created} nodes, {relationships_created} relationships"
            )
            
            return GraphWriteResult(
                success=True,
                nodes_created=nodes_created,
                relationships_created=relationships_created,
                candidate_id=candidate_id,
                message=f"Successfully wrote candidate {candidate_id}"
            )
            
        except Exception as e:
            logger.error(f"Failed to write candidate {candidate_id}: {e}")
            return GraphWriteResult(
                success=False,
                nodes_created=0,
                relationships_created=0,
                candidate_id=candidate_id,
                message=f"Error: {str(e)}"
            )
    
    # ========================================================================
    # Internal Helper Methods
    # ========================================================================
    
    @staticmethod
    def _merge_person(session: Session, data: ExtractedData) -> Dict[str, int]:
        """MERGE Person node with properties."""
        query = """
        MERGE (p:Person {candidate_id: $candidate_id})
        ON CREATE SET
            p.name = $name,
            p.email = $email,
            p.phone = $phone,
            p.current_role = $current_role,
            p.target_role = $target_role,
            p.current_employment = $current_employment,
            p.experience_level = $experience_level,
            p.experience_months = $experience_months,
            p.num_skills = $num_skills,
            p.num_projects = $num_projects,
            p.created_at = datetime()
        ON MATCH SET
            p.name = $name,
            p.email = $email,
            p.phone = $phone,
            p.current_role = $current_role,
            p.target_role = $target_role,
            p.current_employment = $current_employment,
            p.experience_level = $experience_level,
            p.experience_months = $experience_months,
            p.num_skills = $num_skills,
            p.num_projects = $num_projects,
            p.updated_at = datetime()
        RETURN p, 
               CASE WHEN p.created_at IS NOT NULL AND p.updated_at IS NULL THEN 1 ELSE 0 END AS created
        """
        
        result = session.run(
            query,
            candidate_id=data.candidate_id,
            name=data.candidate_name,
            email=data.email,
            phone=data.mobile_number,
            current_role=data.current_role,
            target_role=data.target_role,
            current_employment=data.current_employment,
            experience_level=data.experience_level,
            experience_months=data.experience_months,
            num_skills=data.num_skills,
            num_projects=data.num_projects
        )
        
        record = result.single()
        nodes_created = record["created"] if record else 0
        
        return {"nodes_created": nodes_created}
    
    @staticmethod
    def _merge_skills(session: Session, data: ExtractedData) -> Dict[str, int]:
        """
        Batch MERGE all unique skills using UNWIND.
        Uses all_skills field which contains normalized unique skills.
        """
        # Use all_skills if available, otherwise collect from categories
        skill_names = set()
        
        if data.all_skills:
            skill_names = set(data.all_skills)
        elif data.skills and len(data.skills) > 0:
            skills_obj = data.skills[0]
            skill_names.update(skills_obj.programming_languages)
            skill_names.update(skills_obj.frameworks)
            skill_names.update(skills_obj.technologies)
            skill_names.update(skills_obj.technical_skills)
            skill_names.update(skills_obj.database)
            skill_names.update(skills_obj.soft_skills)
        
        if not skill_names:
            return {"nodes_created": 0}
        
        query = """
        UNWIND $skill_names AS skill_name
        MERGE (s:Skill {name: skill_name})
        ON CREATE SET
            s.category = 'unknown',
            s.created_at = datetime()
        RETURN count(*) AS total
        """
        
        result = session.run(query, skill_names=list(skill_names))
        
        return {"nodes_created": len(skill_names)}
    
    @staticmethod
    def _create_has_skill_relationships(
        session: Session,
        candidate_id: str,
        skills: List[Any]
    ) -> Dict[str, int]:
        """
        Create HAS_SKILL relationships from categorized skills.
        """
        if not skills or len(skills) == 0:
            return {"relationships_created": 0}
        
        # First, delete existing HAS_SKILL relationships to avoid duplicates
        delete_query = """
        MATCH (p:Person {candidate_id: $candidate_id})-[r:HAS_SKILL]->()
        DELETE r
        """
        session.run(delete_query, candidate_id=candidate_id)
        
        skills_obj = skills[0]  # First element has categorized skills
        
        # Create skill data with category info
        skill_data = []
        
        for skill in skills_obj.programming_languages:
            skill_data.append({"name": skill, "category": "programming_language"})
        for skill in skills_obj.frameworks:
            skill_data.append({"name": skill, "category": "framework"})
        for skill in skills_obj.technologies:
            skill_data.append({"name": skill, "category": "technology"})
        for skill in skills_obj.technical_skills:
            skill_data.append({"name": skill, "category": "technical_skill"})
        for skill in skills_obj.database:
            skill_data.append({"name": skill, "category": "database"})
        for skill in skills_obj.soft_skills:
            skill_data.append({"name": skill, "category": "soft_skill"})
        
        if not skill_data:
            return {"relationships_created": 0}
        
        query = """
        MATCH (p:Person {candidate_id: $candidate_id})
        UNWIND $skills AS skill_info
        MATCH (s:Skill {name: skill_info.name})
        MERGE (p)-[r:HAS_SKILL]->(s)
        SET r.category = skill_info.category,
            r.created_at = datetime()
        RETURN count(*) AS count
        """
        
        result = session.run(
            query,
            candidate_id=candidate_id,
            skills=skill_data
        )
        
        count = result.single()["count"]
        return {"relationships_created": count}
    
    @staticmethod
    @staticmethod
    def _create_projects(
        session: Session,
        candidate_id: str,
        projects: List[Any]
    ) -> Dict[str, int]:
        """
        Create projects with USES_TECHNOLOGY relationships.
        """
        if not projects:
            return {"nodes_created": 0, "relationships_created": 0}
        
        # Delete existing projects
        delete_query = """
        MATCH (p:Person {candidate_id: $candidate_id})-[r:WORKED_ON]->(pr:Project)
        DETACH DELETE pr
        """
        session.run(delete_query, candidate_id=candidate_id)
        
        nodes_created = 0
        relationships_created = 0
        
        for project in projects:
            query = """
            MATCH (p:Person {candidate_id: $candidate_id})
            CREATE (pr:Project {
                name: $name,
                description: $description,
                duration: $duration,
                complexity: $complexity,
                created_at: datetime()
            })
            CREATE (p)-[:WORKED_ON]->(pr)
            
            WITH pr
            UNWIND $technologies AS tech_name
            MATCH (s:Skill {name: tech_name})
            CREATE (pr)-[:USES_TECHNOLOGY]->(s)
            
            RETURN pr
            """
            
            result = session.run(
                query,
                candidate_id=candidate_id,
                name=project.project_name,
                description=project.project_description,
                duration=project.duration,
                complexity=project.complexity,
                technologies=project.technologies_used
            )
            
            if result.single():
                nodes_created += 1  # Project
                relationships_created += 1 + len(project.technologies_used)  # WORKED_ON + USES_TECHNOLOGY
        
        return {
            "nodes_created": nodes_created,
            "relationships_created": relationships_created
        }
    
    @staticmethod
    def _create_certifications(
        session: Session,
        candidate_id: str,
        certifications: List[str]
    ) -> Dict[str, int]:
        """
        Create certifications from string array format.
        Format: "Cert Name: Issuer" or just "Cert Name"
        """
        if not certifications:
            return {"nodes_created": 0, "relationships_created": 0}
        
        # Delete existing certifications
        delete_query = """
        MATCH (p:Person {candidate_id: $candidate_id})-[r:HAS_CERTIFICATION]->(cert:Certification)
        DETACH DELETE cert
        """
        session.run(delete_query, candidate_id=candidate_id)
        
        # Parse certification strings
        cert_data = []
        for cert_str in certifications:
            if ":" in cert_str:
                parts = cert_str.split(":", 1)
                cert_data.append({
                    "name": parts[0].strip(),
                    "issuer": parts[1].strip()
                })
            else:
                cert_data.append({
                    "name": cert_str.strip(),
                    "issuer": "Unknown"
                })
        
        query = """
        MATCH (p:Person {candidate_id: $candidate_id})
        UNWIND $certs AS cert_data
        CREATE (cert:Certification {
            name: cert_data.name,
            issuer: cert_data.issuer,
            created_at: datetime()
        })
        CREATE (p)-[:HAS_CERTIFICATION]->(cert)
        RETURN count(*) AS count
        """
        
        result = session.run(
            query,
            candidate_id=candidate_id,
            certs=cert_data
        )
        
        count = result.single()["count"]
        
        return {
            "nodes_created": count,
            "relationships_created": count
        }
    
    @staticmethod
    def _create_education(
        session: Session,
        candidate_id: str,
        education: Optional[Any]
    ) -> Dict[str, int]:
        """
        Create education record from single education object.
        """
        if not education:
            return {"nodes_created": 0, "relationships_created": 0}
        
        # Delete existing education
        delete_query = """
        MATCH (p:Person {candidate_id: $candidate_id})-[r:STUDIED_AT]->(edu:Education)
        DETACH DELETE edu
        """
        session.run(delete_query, candidate_id=candidate_id)
        
        query = """
        MATCH (p:Person {candidate_id: $candidate_id})
        CREATE (edu:Education {
            university: $university,
            degree: $degree,
            created_at: datetime()
        })
        CREATE (p)-[:STUDIED_AT]->(edu)
        RETURN count(*) AS count
        """
        
        result = session.run(
            query,
            candidate_id=candidate_id,
            university=education.university,
            degree=education.degree
        )
        
        count = result.single()["count"]
        
        return {
            "nodes_created": count,
            "relationships_created": count
        }

    @staticmethod
    def _create_work_experiences(
        session: Session,
        candidate_id: str,
        work_experiences: List[Any]
    ) -> Dict[str, int]:
        """
        Create work experience nodes with USED_SKILL relationships.
        
        This creates:
        - WorkExperience nodes
        - (Person)-[:WORKED_AT]->(WorkExperience) relationships
        - (WorkExperience)-[:USED_SKILL]->(Skill) relationships
        
        Args:
            session: Neo4j session
            candidate_id: Candidate identifier
            work_experiences: List of WorkExperienceData objects
            
        Returns:
            Dict with nodes_created and relationships_created counts
        """
        if not work_experiences:
            return {"nodes_created": 0, "relationships_created": 0}
        
        # Delete existing work experiences
        delete_query = """
        MATCH (p:Person {candidate_id: $candidate_id})-[r:WORKED_AT]->(w:WorkExperience)
        DETACH DELETE w
        """
        session.run(delete_query, candidate_id=candidate_id)
        
        nodes_created = 0
        relationships_created = 0
        
        for exp in work_experiences:
            # Create WorkExperience node and WORKED_AT relationship
            query = """
            MATCH (p:Person {candidate_id: $candidate_id})
            CREATE (w:WorkExperience {
                role: $role,
                company: $company,
                duration: $duration,
                duration_months: $duration_months,
                created_at: datetime()
            })
            CREATE (p)-[:WORKED_AT]->(w)
            
            WITH w
            UNWIND $used_skills AS skill_name
            MATCH (s:Skill {name: skill_name})
            CREATE (w)-[:USED_SKILL]->(s)
            
            RETURN w
            """
            
            result = session.run(
                query,
                candidate_id=candidate_id,
                role=exp.role,
                company=exp.company,
                duration=exp.duration if hasattr(exp, 'duration') else '',
                duration_months=exp.duration_months if hasattr(exp, 'duration_months') else 0,
                used_skills=exp.used_skills
            )
            
            if result.single():
                nodes_created += 1  # WorkExperience node
                relationships_created += 1  # WORKED_AT
                relationships_created += len(exp.used_skills)  # USED_SKILL
        
        return {
            "nodes_created": nodes_created,
            "relationships_created": relationships_created
        }
