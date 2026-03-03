"""
Quiz Scoring Service

Handles quiz answer validation, scoring, and skill profile updates.
Uses flat skill structure - directly updates StudentSkillPortfolio.
"""

import logging
from typing import List, Dict
from datetime import datetime
from sqlalchemy.orm import Session
from collections import defaultdict

from ..models.quiz import QuizQuestion
from ..models.quiz_answer import QuizAnswer
from ..models.skill import SkillProfileClaimed
from ..models.student_skill_portfolio import StudentSkillPortfolio

logger = logging.getLogger(__name__)


def determine_level(score: float) -> str:
    """
    Determine skill level based on score.
    
    Thresholds:
    - <50: Beginner
    - 50-74: Intermediate
    - >=75: Advanced
    
    Args:
        score: Score between 0-100
        
    Returns:
        Level string: Beginner, Intermediate, or Advanced
    """
    if score < 50:
        return "Beginner"
    elif score < 75:
        return "Intermediate"
    else:
        return "Advanced"


def score_quiz_attempt(
    student_id: str,
    attempt_id: int,
    answers: List[Dict[str, any]],
    db: Session
) -> Dict[str, any]:
    """
    Score a quiz attempt and update skill profiles.
    
    Args:
        student_id: Student identifier
        attempt_id: Quiz attempt ID
        answers: List of dicts with 'question_id' and 'selected_option'
        db: Database session
        
    Returns:
        Summary dict with attempt_id, overall_verified_score, and per_skill details
        
    Raises:
        ValueError: If attempt not found (404), or invalid question_ids (400)
    """
    # 1) Load QuizQuestion rows for attempt_id + student_id
    questions = db.query(QuizQuestion).filter(
        QuizQuestion.attempt_id == attempt_id,
        QuizQuestion.student_id == student_id
    ).all()
    
    if not questions:
        raise ValueError(f"Quiz attempt {attempt_id} not found for student {student_id}")
    
    # Build question lookup map: question_id -> (correct_option, skill_name)
    question_map = {
        q.question_id: {"correct_option": q.correct_option, "skill_name": q.skill_name}
        for q in questions
    }
    
    # 2) Validate submitted question_ids exist in this attempt
    submitted_ids = {ans["question_id"] for ans in answers}
    valid_ids = set(question_map.keys())
    invalid_ids = submitted_ids - valid_ids
    
    if invalid_ids:
        raise ValueError(f"Invalid question_ids for this attempt: {sorted(invalid_ids)}")
    
    # 3) Delete previous QuizAnswer rows for this attempt_id + student_id (clean resubmits)
    db.query(QuizAnswer).filter(
        QuizAnswer.attempt_id == attempt_id,
        QuizAnswer.student_id == student_id
    ).delete()
    
    # 4) For each answer: compare with correct_option and create QuizAnswer row
    answer_map = {ans["question_id"]: ans["selected_option"] for ans in answers}
    
    # Track skill-level statistics
    skill_stats = defaultdict(lambda: {"correct": 0, "total": 0})
    
    for question_id, q_info in question_map.items():
        selected_option = answer_map.get(question_id)
        
        if not selected_option:
            # Question not answered - mark as incorrect
            is_correct = False
            selected_option = "UNANSWERED"
        else:
            is_correct = (selected_option == q_info["correct_option"])
        
        # Create QuizAnswer record
        quiz_answer = QuizAnswer(
            attempt_id=attempt_id,
            question_id=question_id,
            student_id=student_id,
            selected_option=selected_option,
            is_correct=is_correct
        )
        db.add(quiz_answer)
        
        # Update skill stats
        skill_name = q_info["skill_name"]
        skill_stats[skill_name]["total"] += 1
        if is_correct:
            skill_stats[skill_name]["correct"] += 1
    
    # 5) Aggregate per skill_name (flat skill)
    verified_scores = {}
    verified_levels = {}
    for skill_name, stats in skill_stats.items():
        if stats["total"] > 0:
            verified_score = 100.0 * stats["correct"] / stats["total"]
            verified_scores[skill_name] = verified_score
            verified_levels[skill_name] = determine_level(verified_score)
        else:
            verified_scores[skill_name] = 0.0
            verified_levels[skill_name] = "Beginner"
    
    # 6) Load claimed scores from SkillProfileClaimed for student_id
    claimed_profiles = db.query(SkillProfileClaimed).filter(
        SkillProfileClaimed.student_id == student_id
    ).all()
    
    claimed_scores = {p.skill_name: p.claimed_score for p in claimed_profiles}
    
    # 7) Calculate final_score and update StudentSkillPortfolio directly
    per_skill_results = []
    
    for skill_name, verified_score in verified_scores.items():
        verified_level = verified_levels[skill_name]
        
        # Get claimed score (default to 0 if not found)
        claimed_score = claimed_scores.get(skill_name, 0.0)
        
        # Calculate dynamic weights based on questions answered for this skill
        total_qs = skill_stats[skill_name]["total"]
        correct_qs = skill_stats[skill_name]["correct"]
        
        # w_quiz increases with more questions (50% base, up to 80% max)
        w_quiz = min(0.50 + 0.05 * total_qs, 0.80)
        w_claimed = 1.0 - w_quiz
        
        # Calculate final score
        final_score = w_quiz * verified_score + w_claimed * claimed_score
        final_level = determine_level(final_score)
        
        # Build explanation
        explanation_text = (
            f"Final score is {round(w_quiz * 100, 1)}% from quiz "
            f"({round(verified_score, 1)}) + {round(w_claimed * 100, 1)}% from "
            f"transcript ({round(claimed_score, 1)}). Weight adapts with quiz size."
        )
        
        per_skill_results.append({
            "skill_name": skill_name,
            "correct": correct_qs,
            "total_questions": total_qs,
            "verified_score": round(verified_score, 2),
            "claimed_score": round(claimed_score, 2),
            "w_quiz": round(w_quiz, 4),
            "w_claimed": round(w_claimed, 4),
            "final_score": round(final_score, 2),
            "final_level": final_level,
            "explanation_text": explanation_text,
            # Legacy fields for backward compatibility
            "parent_skill": skill_name,
            "verified_level": verified_level
        })
        
        # Upsert into StudentSkillPortfolio
        portfolio_entry = db.query(StudentSkillPortfolio).filter(
            StudentSkillPortfolio.student_id == student_id,
            StudentSkillPortfolio.skill_name == skill_name
        ).first()
        
        if portfolio_entry:
            # Update existing entry
            portfolio_entry.claimed_score = claimed_score
            portfolio_entry.verified_score = verified_score
            portfolio_entry.quiz_weight = w_quiz
            portfolio_entry.claimed_weight = w_claimed
            portfolio_entry.final_score = final_score
            portfolio_entry.final_level = final_level
            portfolio_entry.correct_count = correct_qs
            portfolio_entry.total_questions = total_qs
        else:
            # Create new entry
            portfolio_entry = StudentSkillPortfolio(
                student_id=student_id,
                skill_name=skill_name,
                claimed_score=claimed_score,
                verified_score=verified_score,
                quiz_weight=w_quiz,
                claimed_weight=w_claimed,
                final_score=final_score,
                final_level=final_level,
                correct_count=correct_qs,
                total_questions=total_qs
            )
            db.add(portfolio_entry)
    
    # Commit all changes
    db.commit()
    
    # Calculate overall statistics
    total_correct = sum(stats["correct"] for stats in skill_stats.values())
    total_questions = sum(stats["total"] for stats in skill_stats.values())
    overall_verified_score = (100.0 * total_correct / total_questions) if total_questions > 0 else 0.0
    
    # Calculate average final score across all tested skills
    average_score = sum(skill["final_score"] for skill in per_skill_results) / len(per_skill_results) if per_skill_results else 0.0
    
    logger.info(
        f"Quiz scored for student {student_id}, attempt {attempt_id}: "
        f"{total_correct}/{total_questions} correct ({overall_verified_score:.1f}%), "
        f"average final score: {average_score:.1f}%"
    )
    
    # 9) Return summary JSON with XAI fields
    return {
        "attempt_id": attempt_id,
        "total_questions": total_questions,
        "questions_correct": total_correct,
        "overall_verified_score": round(overall_verified_score, 2),
        "average_score": round(average_score, 2),
        "per_skill": per_skill_results
    }
