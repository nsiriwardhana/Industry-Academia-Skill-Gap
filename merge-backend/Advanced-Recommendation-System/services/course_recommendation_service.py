"""
Course Recommendation Engine - Deficit-Driven Course Selection.

Recommends courses that maximize deficit reduction with:
- gain(course) = Σ deficit(skill) for skills taught
- rating_boost = (avgRating / 5) × 2
- difficulty_penalty = adjustable based on candidate level
"""
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class CourseRecommendationService:
    """
    Recommends courses optimized for skill deficit reduction.
    
    Scoring Formula:
    gain = Σ deficit(skill) for taught skills + rating_boost + difficulty_penalty
    """
    
    @staticmethod
    def recommend_courses(
        session,
        candidate_id: str,
        top_deficits: List[Dict],
        top_n: int = 10
    ) -> List[Dict]:
        """
        Recommend top-N courses based on deficit reduction.
        
        Args:
            session: Neo4j session
            candidate_id: Candidate identifier (for future personalization)
            top_deficits: List of deficit dictionaries
            top_n: Number of courses to recommend
            
        Returns:
            List of top-N course recommendation dictionaries
        """
        logger.info(f"Recommending courses for candidate: {candidate_id} (top_n={top_n})")
        
        if not top_deficits:
            logger.warning("No deficits provided - cannot recommend courses")
            return []
        
        # Create deficit lookup map
        deficit_map = {d["skill_name"]: d["deficit"] for d in top_deficits}
        deficit_skills = list(deficit_map.keys())
        
        logger.info(f"Deficit skills to cover: {deficit_skills[:10]}..." if len(deficit_skills) > 10 else f"Deficit skills to cover: {deficit_skills}")
        
        # Query: Find courses teaching deficit skills
        query_courses = """
        MATCH (c:Course)-[:TEACHES_SKILL]->(s:Skill)
        WHERE s.name IN $deficit_skills
        WITH c, collect(DISTINCT s.name) AS taught_skills
        RETURN c.id AS course_id, 
               c.name AS title, 
               c.provider AS provider, 
               c.url AS url,
               c.imageUrl AS imageUrl,
               c.avgRating AS avg_rating, 
               c.difficulty AS difficulty, 
               taught_skills
        LIMIT 500
        """
        result = session.run(query_courses, deficit_skills=deficit_skills)
        
        # Track which deficit skills have available courses
        skills_with_courses = set()
        
        course_scores = []
        
        for record in result:
            course_id = record["course_id"]
            title = record["title"]
            provider = record["provider"]
            url = record.get("url")
            imageUrl = record.get("imageUrl")
            avg_rating = record.get("avg_rating", 0.0)
            difficulty = record.get("difficulty", "unknown")
            taught_skills = record["taught_skills"]
            
            # Filter to only deficit skills
            covered_deficit_skills = [s for s in taught_skills if s in deficit_map]
            
            if not covered_deficit_skills:
                continue
            
            # Track skills that have at least one course
            skills_with_courses.update(covered_deficit_skills)
            
            # Base gain: sum of deficits for covered skills
            gain = sum(deficit_map[skill] for skill in covered_deficit_skills)
            
            # Rating boost: (avg_rating / 5) × 2 (max +2 points)
            rating_boost = (avg_rating / 5.0) * 2.0 if avg_rating else 0.0
            
            # Difficulty penalty (future: personalize based on candidate experience)
            difficulty_penalty = 0.0
            # Example: penalize advanced courses for beginners
            # if candidate_experience == "beginner" and difficulty == "advanced":
            #     difficulty_penalty = -5.0
            
            # Total score
            total_score = gain + rating_boost + difficulty_penalty
            
            course_scores.append({
                "course_id": course_id,
                "title": title,
                "provider": provider,
                "url": url,
                "imageUrl": imageUrl,
                "avg_rating": avg_rating,
                "difficulty": difficulty,
                "covered_deficit_skills": covered_deficit_skills,
                "gain_score": total_score,
            })
        
        logger.info(f"Found {len(course_scores)} courses covering {len(skills_with_courses)} out of {len(deficit_skills)} deficit skills")
        
        # Log skills that have NO courses available
        skills_without_courses = set(deficit_skills) - skills_with_courses
        if skills_without_courses:
            logger.warning(f"No courses found for {len(skills_without_courses)} skills: {list(skills_without_courses)[:5]}...")
        
        # DIVERSE COURSE SELECTION: Greedy set cover approach
        # Prioritizes courses that cover new skills not yet covered
        
        selected_courses = []
        covered_skills = set()
        remaining_courses = course_scores.copy()
        
        # Sort by gain score initially
        remaining_courses.sort(key=lambda x: x["gain_score"], reverse=True)
        
        while len(selected_courses) < top_n and remaining_courses:
            # Re-score remaining courses based on NEW skills they bring
            best_course = None
            best_adjusted_score = -float('inf')
            
            for course in remaining_courses:
                # Count how many NEW skills this course teaches
                new_skills = [s for s in course["covered_deficit_skills"] if s not in covered_skills]
                
                if not new_skills:
                    # Course teaches no new skills - heavily penalize
                    adjusted_score = course["gain_score"] * 0.1
                else:
                    # Reward based on: original score × (new_skills / total_skills)
                    diversity_bonus = len(new_skills) / len(course["covered_deficit_skills"])
                    adjusted_score = course["gain_score"] * (0.5 + diversity_bonus * 0.5)
                    
                    # Extra bonus for covering more new skills
                    adjusted_score += len(new_skills) * 2.0
                
                if adjusted_score > best_adjusted_score:
                    best_adjusted_score = adjusted_score
                    best_course = course
            
            if best_course is None:
                break
            
            # Add best course to selection
            selected_courses.append(best_course)
            covered_skills.update(best_course["covered_deficit_skills"])
            remaining_courses.remove(best_course)
        
        logger.info(f"Recommended {len(selected_courses)} courses covering {len(covered_skills)} unique skills: {list(covered_skills)}")
        
        # Log uncovered deficit skills
        uncovered_skills = set(deficit_skills) - covered_skills
        if uncovered_skills:
            logger.warning(f"{len(uncovered_skills)} deficit skills remain uncovered (no courses available): {list(uncovered_skills)[:10]}...")
        
        return selected_courses
