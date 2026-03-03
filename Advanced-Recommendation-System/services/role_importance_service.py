"""
Role Importance Engine - TF-IDF Computation.

Computes importance(role, skill) = TF × IDF where:
- TF = count(jobs in role requiring skill)
- IDF = log(total_roles / df)
- df = count(roles where skill appears)
"""
import logging
import math
from typing import Dict, Tuple
from utils import cache

logger = logging.getLogger(__name__)


class RoleImportanceService:
    """
    Computes TF-IDF importance scores for role-skill pairs.
    
    Results are cached for 1 hour since role data changes infrequently.
    """
    
    @staticmethod
    def compute_role_importance(session, role_key: str) -> Tuple[Dict[str, Dict], int, str]:
        """
        Compute TF-IDF importance for all skills in a role.
        
        Args:
            session: Neo4j session
            role_key: Role identifier
            
        Returns:
            Tuple of (skill_importance_dict, total_jobs, role_name)
            where skill_importance_dict maps skill_name to {tf, df, idf, importance, percentage}
        """
        logger.info(f"Computing TF-IDF importance for role: {role_key}")
        
        # Check cache first
        cache_key = f"role_importance:{role_key}"
        cached = cache.get(cache_key)
        if cached is not None:
            logger.info(f"Cache hit for role: {role_key}")
            return cached
        
        # Query 1: Get TF from Job->Role->Skill OR direct Role->Skill
        # Supports both Desktop (with Jobs) and Aura (direct) schemas
        query_tf = """
        MATCH (r:Role {role_key: $role_key})
        OPTIONAL MATCH (r)<-[:BELONGS_TO_ROLE]-(j:Job)-[:REQUIRES_SKILL]->(s:Skill)
        OPTIONAL MATCH (r)-[:REQUIRES_SKILL]->(s2:Skill)
        WITH r, COALESCE(s, s2) as skill
        WHERE skill IS NOT NULL
        OPTIONAL MATCH (skill)-[:BELONGS_TO_CATEGORY]->(cat:SkillCategory)
        WITH r, skill, cat, count(DISTINCT skill) AS tf, 1 AS total_jobs
        RETURN r.name AS role_name, skill.name AS skill_name, 
               COALESCE(cat.name, 'Uncategorized') AS category, tf, total_jobs
        LIMIT 1000
        """
        result_tf = session.run(query_tf, role_key=role_key)
        
        skill_tf = {}
        role_name = None
        total_jobs = 0
        
        for record in result_tf:
            role_name = record["role_name"]
            skill_name = record["skill_name"]
            category = record["category"]
            tf = record["tf"]
            total_jobs = record["total_jobs"]
            
            skill_tf[skill_name] = {
                "tf": tf,
                "category": category,
                "percentage": (tf / total_jobs * 100) if total_jobs > 0 else 0.0
            }
        
        if not skill_tf:
            logger.warning(f"No skills found for role: {role_key}")
            return {}, 0, role_key
        
        # Query 2: Compute DF (document frequency) for each skill
        # Supports both Job-based and direct Role-based schemas
        query_df = """
        MATCH (r:Role)-[:REQUIRES_SKILL]->(s:Skill)
        WITH s.name AS skill_name, count(DISTINCT r) AS df
        RETURN skill_name, df
        """
        result_df = session.run(query_df)
        
        skill_df = {}
        for record in result_df:
            skill_name = record["skill_name"]
            df = record["df"]
            skill_df[skill_name] = df
        
        # Query 3: Get total number of roles for IDF calculation
        query_total_roles = """
        MATCH (r:Role)
        RETURN count(DISTINCT r) AS total_roles
        """
        result_total = session.run(query_total_roles)
        total_roles = result_total.single()["total_roles"]
        
        # Compute IDF and final importance scores
        skill_importance = {}
        for skill_name, tf_data in skill_tf.items():
            tf = tf_data["tf"]
            df = skill_df.get(skill_name, 1)  # Default to 1 to avoid division by zero
            
            # IDF = log(total_roles / df)
            idf = math.log(total_roles / df) if df > 0 else 0.0
            
            # Importance = TF × IDF
            importance = tf * idf
            
            skill_importance[skill_name] = {
                "tf": tf,
                "df": df,
                "idf": idf,
                "importance": importance,
                "percentage": tf_data["percentage"],
                "category": tf_data["category"],  # Include category
            }
        
        # Cache the result
        result = (skill_importance, total_jobs, role_name)
        cache.set(cache_key, result)
        
        logger.info(f"Computed importance for {len(skill_importance)} skills in role {role_key}")
        return result
