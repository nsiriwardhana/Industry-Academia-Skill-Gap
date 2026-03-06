"""
Project Relevance Service

Computes how relevant a candidate's projects are to a target role
based on skill overlap and TF-IDF importance.
"""
import logging
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)


class ProjectRelevanceService:
    """
    Service for computing project-role relevance scores.
    
    Measures how well a candidate's projects align with a target role
    based on skill matches and importance weights.
    """
    
    @staticmethod
    def compute_project_relevance(
        session,
        candidate_id: str,
        role_key: str,
        top_n: int = 5,
        top_k_role: int = 100
    ) -> Dict:
        """
        Compute relevance of candidate's projects to target role.
        
        Args:
            session: Neo4j session
            candidate_id: Candidate identifier
            role_key: Target role key
            top_n: Number of top projects to return
            top_k_role: Number of top role skills to consider
            
        Returns:
            {
                "candidate_id": "...",
                "role_key": "...",
                "role_name": "...",
                "projects": [
                    {
                        "project_name": "...",
                        "relevance_score": 0.xx,
                        "matched_role_skills": ["skill1", "skill2"],
                        "project_skills": ["skill1", "skill2", "skill3"],
                        "num_matched": 2,
                        "num_project_skills": 3
                    }
                ],
                "candidate_project_score": 0.xx,
                "total_projects": 10
            }
        """
        logger.info(
            f"Computing project relevance: candidate={candidate_id}, "
            f"role={role_key}, top_n={top_n}, top_k={top_k_role}"
        )
        
        # Step 1: Get role skill importance profile
        role_importance = ProjectRelevanceService._get_role_importance(
            session, role_key, top_k_role
        )
        
        if not role_importance:
            return {
                "candidate_id": candidate_id,
                "role_key": role_key,
                "role_name": None,
                "projects": [],
                "candidate_project_score": 0.0,
                "total_projects": 0,
                "error": "Role not found or has no skills"
            }
        
        role_name = role_importance["role_name"]
        skill_importance = role_importance["skills"]
        total_role_importance = sum(s["importance"] for s in skill_importance)
        
        # Step 2: Get candidate projects with skills
        projects = ProjectRelevanceService._get_candidate_projects(
            session, candidate_id
        )
        
        if not projects:
            return {
                "candidate_id": candidate_id,
                "role_key": role_key,
                "role_name": role_name,
                "projects": [],
                "candidate_project_score": 0.0,
                "total_projects": 0
            }
        
        # Step 3: Compute relevance for each project
        project_relevance = []
        
        for project in projects:
            project_name = project["project_name"]
            project_skills = project["skills"]
            
            # Calculate matched importance with similarity support
            matched_importance = ProjectRelevanceService._compute_matched_importance(
                session, project_skills, skill_importance
            )
            
            # Relevance = matched_importance / total_role_importance
            relevance_score = (
                matched_importance / total_role_importance 
                if total_role_importance > 0 else 0.0
            )
            
            # Get matched skill names
            matched_skills = ProjectRelevanceService._get_matched_skill_names(
                session, project_skills, skill_importance
            )
            
            project_relevance.append({
                "project_name": project_name,
                "relevance_score": round(relevance_score, 4),
                "matched_role_skills": matched_skills,
                "project_skills": project_skills,
                "num_matched": len(matched_skills),
                "num_project_skills": len(project_skills)
            })
        
        # Step 4: Sort by relevance descending
        project_relevance.sort(key=lambda x: x["relevance_score"], reverse=True)
        
        # Step 5: Take top N
        top_projects = project_relevance[:top_n]
        
        # Step 6: Calculate candidate project score
        # Average of top 3 relevance scores (or max if fewer than 3)
        if len(project_relevance) == 0:
            candidate_score = 0.0
        elif len(project_relevance) <= 3:
            candidate_score = max(p["relevance_score"] for p in project_relevance)
        else:
            top_3_scores = [p["relevance_score"] for p in project_relevance[:3]]
            candidate_score = sum(top_3_scores) / len(top_3_scores)
        
        return {
            "candidate_id": candidate_id,
            "role_key": role_key,
            "role_name": role_name,
            "projects": top_projects,
            "candidate_project_score": round(candidate_score, 4),
            "total_projects": len(projects)
        }
    
    @staticmethod
    def _get_role_importance(
        session,
        role_key: str,
        top_k: int
    ) -> Optional[Dict]:
        """
        Get role skill importance profile using TF-IDF.
        
        Returns:
            {
                "role_name": "...",
                "skills": [
                    {"skill_name": "...", "importance": 42.5},
                    ...
                ]
            }
        """
        query = """
        // Get role
        MATCH (r:Role {role_key: $role_key})
        
        // Count total roles for IDF
        WITH r, count{(r2:Role)} AS total_roles
        
        // Get skills from jobs or directly from role (flexible schema)
        OPTIONAL MATCH (r)<-[:BELONGS_TO_ROLE]-(j:Job)-[:REQUIRES_SKILL]->(s:Skill)
        OPTIONAL MATCH (r)-[:REQUIRES_SKILL]->(s2:Skill)
        WITH r, COALESCE(s, s2) as skill, total_roles
        WHERE skill IS NOT NULL
        WITH r.name AS role_name, skill.name AS skill_name, 
             1 AS tf,
             total_roles
        
        // Compute DF (how many roles require this skill)
        MATCH (r2:Role)-[:REQUIRES_SKILL]->(s2:Skill {name: skill_name})
        WITH role_name, skill_name, tf, total_roles, count(DISTINCT r2) AS df
        
        // Compute TF-IDF importance
        WITH role_name, skill_name, tf, df, total_roles,
             log(toFloat(total_roles) / toFloat(df)) AS idf,
             toFloat(tf) * log(toFloat(total_roles) / toFloat(df)) AS importance
        
        ORDER BY importance DESC
        LIMIT $top_k
        
        RETURN role_name,
               collect({skill_name: skill_name, importance: importance}) AS skills
        """
        
        try:
            result = session.run(query, role_key=role_key, top_k=top_k)
            record = result.single()
            
            if not record:
                return None
            
            return {
                "role_name": record["role_name"],
                "skills": [
                    {
                        "skill_name": s["skill_name"],
                        "importance": s["importance"]
                    }
                    for s in record["skills"]
                ]
            }
        
        except Exception as e:
            logger.error(f"Failed to get role importance: {e}")
            return None
    
    @staticmethod
    def _get_candidate_projects(
        session,
        candidate_id: str
    ) -> List[Dict]:
        """
        Get candidate's projects with their skills.
        
        Returns:
            [
                {
                    "project_name": "...",
                    "skills": ["Python", "Django", ...]
                },
                ...
            ]
        """
        query = """
        MATCH (p:Person {candidate_id: $candidate_id})-[:WORKED_ON]->(proj:Project)
        OPTIONAL MATCH (proj)-[:USES_TECHNOLOGY]->(s:Skill)
        WITH proj.name AS project_name, 
             collect(DISTINCT s.name) AS skills
        RETURN project_name, skills
        ORDER BY project_name
        """
        
        try:
            result = session.run(query, candidate_id=candidate_id)
            
            projects = []
            for record in result:
                skills_list = [s for s in record["skills"] if s is not None]
                # Only include projects that have at least one skill
                if skills_list:
                    projects.append({
                        "project_name": record["project_name"],
                        "skills": skills_list
                    })
            
            return projects
        
        except Exception as e:
            logger.error(f"Failed to get candidate projects: {e}")
            return []
    
    @staticmethod
    def _compute_matched_importance(
        session,
        project_skills: List[str],
        role_skill_importance: List[Dict]
    ) -> float:
        """
        Compute total matched importance with similarity support.
        
        Handles:
        1. Exact matches: full importance
        2. Similar skills via SIMILAR_TO: importance × similarity
        
        Args:
            project_skills: List of skill names from project
            role_skill_importance: List of {skill_name, importance} from role
            
        Returns:
            Total matched importance score
        """
        # Build role skill lookup
        role_skills = {
            skill["skill_name"]: skill["importance"]
            for skill in role_skill_importance
        }
        
        total_matched = 0.0
        
        for project_skill in project_skills:
            # Check exact match
            if project_skill in role_skills:
                total_matched += role_skills[project_skill]
            else:
                # Check for similar skills
                similarity_score = ProjectRelevanceService._get_similarity_match(
                    session, project_skill, list(role_skills.keys())
                )
                
                if similarity_score and similarity_score["match_skill"] in role_skills:
                    # Partial match: importance × similarity
                    importance = role_skills[similarity_score["match_skill"]]
                    similarity = similarity_score["similarity"]
                    total_matched += importance * similarity
        
        return total_matched
    
    @staticmethod
    def _get_similarity_match(
        session,
        project_skill: str,
        role_skills: List[str]
    ) -> Optional[Dict]:
        """
        Find best similar skill match via SIMILAR_TO edge.
        
        Args:
            project_skill: Skill from project
            role_skills: List of role skill names
            
        Returns:
            {"match_skill": "...", "similarity": 0.xx} or None
        """
        query = """
        MATCH (s1:Skill {name: $project_skill})-[r:SIMILAR_TO]->(s2:Skill)
        WHERE s2.name IN $role_skills
        RETURN s2.name AS match_skill, r.similarity AS similarity
        ORDER BY r.similarity DESC
        LIMIT 1
        """
        
        try:
            result = session.run(
                query,
                project_skill=project_skill,
                role_skills=role_skills
            )
            record = result.single()
            
            if record:
                return {
                    "match_skill": record["match_skill"],
                    "similarity": record["similarity"]
                }
            
            return None
        
        except Exception as e:
            logger.debug(f"Similarity query failed: {e}")
            return None
    
    @staticmethod
    def _get_matched_skill_names(
        session,
        project_skills: List[str],
        role_skill_importance: List[Dict]
    ) -> List[str]:
        """
        Get list of matched skill names (exact + similar).
        
        Returns:
            List of skill names that matched
        """
        role_skills = {
            skill["skill_name"]: skill["importance"]
            for skill in role_skill_importance
        }
        
        matched = []
        
        for project_skill in project_skills:
            # Exact match
            if project_skill in role_skills:
                matched.append(project_skill)
            else:
                # Similar match
                similarity = ProjectRelevanceService._get_similarity_match(
                    session, project_skill, list(role_skills.keys())
                )
                if similarity:
                    matched.append(f"{project_skill} → {similarity['match_skill']}")
        
        return matched
