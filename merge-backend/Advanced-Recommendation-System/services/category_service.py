"""
Category Service for Skill Taxonomy Operations.

Provides helper functions for category-aware skill gap analysis and recommendations.
"""
import logging
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)


class CategoryService:
    """Service for skill category operations."""
    
    # Cache for skill -> category mappings
    _category_cache: Dict[str, Optional[str]] = {}
    
    @staticmethod
    def get_skill_category(session, skill_name: str) -> Optional[str]:
        """
        Get category for a skill using canonical name resolution.
        
        Args:
            session: Neo4j session
            skill_name: Name of the skill
            
        Returns:
            Category name or None if not mapped
        """
        # Check cache
        if skill_name in CategoryService._category_cache:
            return CategoryService._category_cache[skill_name]
        
        # Query Neo4j with canonical name fallback
        query = """
        MATCH (s:Skill {name: $skill_name})
        OPTIONAL MATCH (s)-[:BELONGS_TO_CATEGORY]->(c:SkillCategory)
        RETURN c.name AS category, s.canonical_name AS canonical_name
        """
        
        result = session.run(query, skill_name=skill_name)
        record = result.single()
        
        if not record:
            CategoryService._category_cache[skill_name] = None
            return None
        
        category = record["category"]
        canonical_name = record["canonical_name"]
        
        # If no direct category but has canonical name, try canonical
        if not category and canonical_name and canonical_name != skill_name:
            query_canonical = """
            MATCH (s:Skill {name: $canonical_name})
            OPTIONAL MATCH (s)-[:BELONGS_TO_CATEGORY]->(c:SkillCategory)
            RETURN c.name AS category
            """
            result_canonical = session.run(query_canonical, canonical_name=canonical_name)
            record_canonical = result_canonical.single()
            if record_canonical:
                category = record_canonical["category"]
        
        # Cache result
        CategoryService._category_cache[skill_name] = category
        return category
    
    @staticmethod
    def get_skill_categories_batch(session, skill_names: List[str]) -> Dict[str, Optional[str]]:
        """
        Get categories for multiple skills in a single query (efficient).
        
        Args:
            session: Neo4j session
            skill_names: List of skill names
            
        Returns:
            Dict mapping skill_name -> category (or None)
        """
        # Check what's already cached
        uncached_skills = [s for s in skill_names if s not in CategoryService._category_cache]
        
        if not uncached_skills:
            return {s: CategoryService._category_cache[s] for s in skill_names}
        
        # Batch query for uncached skills
        query = """
        UNWIND $skill_names AS skill_name
        MATCH (s:Skill {name: skill_name})
        OPTIONAL MATCH (s)-[:BELONGS_TO_CATEGORY]->(c:SkillCategory)
        RETURN s.name AS skill_name, c.name AS category, s.canonical_name AS canonical_name
        """
        
        result = session.run(query, skill_names=uncached_skills)
        
        # Process results
        skill_to_category = {}
        needs_canonical_lookup = []
        
        for record in result:
            skill_name = record["skill_name"]
            category = record["category"]
            canonical_name = record["canonical_name"]
            
            if category:
                skill_to_category[skill_name] = category
            elif canonical_name and canonical_name != skill_name:
                needs_canonical_lookup.append((skill_name, canonical_name))
            else:
                skill_to_category[skill_name] = None
        
        # Handle canonical name lookups
        if needs_canonical_lookup:
            canonical_names = [cn for _, cn in needs_canonical_lookup]
            query_canonical = """
            UNWIND $canonical_names AS canonical_name
            MATCH (s:Skill {name: canonical_name})
            OPTIONAL MATCH (s)-[:BELONGS_TO_CATEGORY]->(c:SkillCategory)
            RETURN s.name AS canonical_name, c.name AS category
            """
            result_canonical = session.run(query_canonical, canonical_names=canonical_names)
            
            canonical_to_category = {
                r["canonical_name"]: r["category"] 
                for r in result_canonical
            }
            
            for skill_name, canonical_name in needs_canonical_lookup:
                skill_to_category[skill_name] = canonical_to_category.get(canonical_name)
        
        # Update cache
        CategoryService._category_cache.update(skill_to_category)
        
        # Return all requested skills (including cached)
        return {s: CategoryService._category_cache.get(s) for s in skill_names}
    
    @staticmethod
    def compute_role_category_profile(
        session, 
        role_key: str, 
        role_importance: Dict[str, dict],
        top_skills_per_category: int = 5
    ) -> Tuple[List[dict], float]:
        """
        Compute aggregated category profile for a role.
        
        Args:
            session: Neo4j session
            role_key: Role identifier
            role_importance: Dict of {skill_name: {importance, tf, ...}}
            top_skills_per_category: Number of top skills to include per category
            
        Returns:
            Tuple of (category_profiles, category_coverage_percent)
        """
        logger.info(f"Computing category profile for role: {role_key}")
        
        # Get categories for all role skills
        skill_names = list(role_importance.keys())
        skill_to_category = CategoryService.get_skill_categories_batch(session, skill_names)
        
        # Aggregate by category
        category_data = defaultdict(lambda: {
            "importance_sum": 0.0,
            "skills": []
        })
        
        mapped_count = 0
        for skill_name, importance_data in role_importance.items():
            category = skill_to_category.get(skill_name)
            
            if category:
                mapped_count += 1
                category_data[category]["importance_sum"] += importance_data["importance"]
                category_data[category]["skills"].append({
                    "skill": skill_name,
                    "importance": importance_data["importance"]
                })
            else:
                # Unknown category
                category_data["Unknown"]["importance_sum"] += importance_data["importance"]
                category_data["Unknown"]["skills"].append({
                    "skill": skill_name,
                    "importance": importance_data["importance"]
                })
        
        # Build response
        category_profiles = []
        for category, data in category_data.items():
            # Sort skills by importance
            sorted_skills = sorted(
                data["skills"], 
                key=lambda x: x["importance"], 
                reverse=True
            )[:top_skills_per_category]
            
            category_profiles.append({
                "category": category,
                "importance_sum": data["importance_sum"],
                "num_role_skills": len(data["skills"]),
                "top_skills": sorted_skills
            })
        
        # Sort categories by importance
        category_profiles.sort(key=lambda x: x["importance_sum"], reverse=True)
        
        # Calculate coverage
        total_skills = len(skill_names)
        category_coverage = (mapped_count / total_skills * 100) if total_skills > 0 else 0
        
        logger.info(
            f"Category profile: {len(category_profiles)} categories, "
            f"{category_coverage:.1f}% coverage ({mapped_count}/{total_skills})"
        )
        
        return category_profiles, category_coverage
    
    @staticmethod
    def aggregate_category_gaps(
        session,
        candidate_id: str,
        role_key: str,
        missing_skills_ranked: List[dict],
        P_has_map: Dict[str, float],
        role_importance_map: Dict[str, dict],
        top_missing_per_category: int = 3
    ) -> Tuple[List[dict], dict]:
        """
        Aggregate skill gaps by category.
        
        Args:
            session: Neo4j session
            candidate_id: Candidate ID
            role_key: Role ID
            missing_skills_ranked: List of deficit dicts with skill_name, deficit, etc.
            P_has_map: Dict of {skill_name: match_strength}
            role_importance_map: Dict of {skill_name: {importance, ...}}
            top_missing_per_category: Top missing skills to show per category
            
        Returns:
            Tuple of (category_gaps, mapping_stats)
        """
        logger.info(f"Aggregating category gaps for {candidate_id} -> {role_key}")
        
        # Get all role skills
        all_role_skills = list(role_importance_map.keys())
        skill_to_category = CategoryService.get_skill_categories_batch(session, all_role_skills)
        
        # Group by category
        category_stats = defaultdict(lambda: {
            "role_skills": [],
            "match_strengths": [],
            "importance_sum": 0.0,
            "missing_skills": []
        })
        
        role_mapped_count = 0
        for skill_name, importance_data in role_importance_map.items():
            category = skill_to_category.get(skill_name) or "Unknown"
            
            if category != "Unknown":
                role_mapped_count += 1
            
            match_strength = P_has_map.get(skill_name, 0.0)
            
            category_stats[category]["role_skills"].append(skill_name)
            category_stats[category]["match_strengths"].append(match_strength)
            category_stats[category]["importance_sum"] += importance_data["importance"]
            
            # If weak/missing (match_strength < 0.5), track as missing
            if match_strength < 0.5:
                # Find full deficit info
                deficit_info = next(
                    (d for d in missing_skills_ranked if d["skill_name"] == skill_name),
                    None
                )
                if deficit_info:
                    category_stats[category]["missing_skills"].append(deficit_info)
        
        # Compute category gaps
        category_gaps = []
        for category, stats in category_stats.items():
            # Coverage: average match strength for role skills in this category
            avg_match = (
                sum(stats["match_strengths"]) / len(stats["match_strengths"])
                if stats["match_strengths"] else 0.0
            )
            
            # Gap score: importance × (1 - coverage)
            gap_score = stats["importance_sum"] * (1 - avg_match)
            
            # Sort missing skills by deficit
            missing_sorted = sorted(
                stats["missing_skills"],
                key=lambda x: x["deficit"],
                reverse=True
            )[:top_missing_per_category]
            
            category_gaps.append({
                "category": category,
                "gap_score": gap_score,
                "importance_sum": stats["importance_sum"],
                "coverage": avg_match,
                "missing_count": len(stats["missing_skills"]),
                "top_missing_skills": [
                    {
                        "skill": m["skill_name"],
                        "deficit": m["deficit"],
                        "importance": m["importance"]
                    }
                    for m in missing_sorted
                ]
            })
        
        # Sort by gap_score descending
        category_gaps.sort(key=lambda x: x["gap_score"], reverse=True)
        
        # Mapping statistics
        total_role_skills = len(all_role_skills)
        mapping_stats = {
            "total_role_skills": total_role_skills,
            "mapped_to_categories": role_mapped_count,
            "category_coverage_percent": (
                role_mapped_count / total_role_skills * 100 
                if total_role_skills > 0 else 0
            ),
            "num_categories": len([c for c in category_stats.keys() if c != "Unknown"]),
            "unknown_count": len(category_stats.get("Unknown", {}).get("role_skills", []))
        }
        
        logger.info(
            f"Category gaps: {len(category_gaps)} categories, "
            f"{mapping_stats['category_coverage_percent']:.1f}% mapped"
        )
        
        return category_gaps, mapping_stats
    
    @staticmethod
    def compute_category_gains(
        session,
        covered_deficit_skills: List[str],
        role_importance_map: Dict[str, dict],
        P_has_map: Dict[str, float]
    ) -> List[dict]:
        """
        Compute category coverage improvement from a course.
        
        Args:
            session: Neo4j session
            covered_deficit_skills: Skills taught by the course
            role_importance_map: Role importance for all skills
            P_has_map: Current match strengths
            
        Returns:
            List of {"category": str, "gain": float}
        """
        if not covered_deficit_skills:
            return []
        
        # Get categories for covered skills
        skill_to_category = CategoryService.get_skill_categories_batch(
            session, 
            covered_deficit_skills
        )
        
        # Aggregate gain by category
        category_gains = defaultdict(float)
        
        for skill in covered_deficit_skills:
            category = skill_to_category.get(skill) or "Unknown"
            
            # Gain = improvement in match_strength weighted by importance
            current_match = P_has_map.get(skill, 0.0)
            importance = role_importance_map.get(skill, {}).get("importance", 0.0)
            
            # Assume course brings match_strength from current to 0.8 (learned)
            new_match = max(current_match, 0.8)
            gain = (new_match - current_match) * importance
            
            category_gains[category] += gain
        
        # Convert to list
        result = [
            {"category": cat, "gain": gain}
            for cat, gain in category_gains.items()
            if gain > 0
        ]
        
        # Sort by gain descending
        result.sort(key=lambda x: x["gain"], reverse=True)
        
        return result
    
    @staticmethod
    def clear_cache():
        """Clear the category cache (useful for testing or updates)."""
        CategoryService._category_cache.clear()
        logger.info("Category cache cleared")
