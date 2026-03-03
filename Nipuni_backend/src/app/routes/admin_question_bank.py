"""
Admin Question Bank Routes

Endpoints for pre-generating questions offline using Ollama.
These operations can be slow - meant for admin use only.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Optional
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

from ..db import get_db
from ..services import question_bank_service
from ..models.question_bank import QuestionBank

router = APIRouter(prefix="/admin/question-bank", tags=["Admin - Question Bank"])
logger = logging.getLogger(__name__)


class GenerateQuestionsRequest(BaseModel):
    skill_names: List[str] = Field(..., description="List of skill names (parent skills or job skills from job_skills.csv)")
    questions_per_difficulty: int = Field(10, description="Number of questions per difficulty level (easy, medium, hard)")
    model_name: str = Field("llama3.1:8b", description="Ollama model to use")


class GenerateQuestionsResponse(BaseModel):
    status: str
    total_requested: int
    total_generated: int
    duplicates_skipped: int
    errors: int
    per_skill: dict
    message: str


class BankStatsResponse(BaseModel):
    total_questions: int
    by_skill: dict


class GenerateAndExportResponse(BaseModel):
    status: str
    generation_stats: dict
    export_file_path: str
    total_questions: int
    skills: List[str]
    format: str
    message: str


class SkillNamesResponse(BaseModel):
    skill_names: List[str]


@router.post("/generate", response_model=GenerateQuestionsResponse)
def generate_questions_for_skills(
    request: GenerateQuestionsRequest,
    db: Session = Depends(get_db)
):
    """
    Generate questions for specified skills and store in QuestionBank.
    
    **This is a slow operation** - generates questions using Ollama.
    Use this offline/admin task to pre-populate the question bank.
    
    **Supports both**:
    - Parent skills (from SkillGroupMap) - e.g., "Programming Fundamentals & C Language"
    - Job skills (from job_skills.csv) - e.g., "SQL", "Python", "JavaScript"
    
    Example request:
    ```json
    {
        "skill_names": ["Python", "SQL", "JavaScript"],
        "questions_per_difficulty": 10,
        "model_name": "llama3.1:8b"
    }
    ```
    
    This will generate 10 easy + 10 medium + 10 hard = 30 questions per skill.
    
    Use GET /admin/question-bank/skills to get a list of valid skill names.
    """
    if not request.skill_names:
        raise HTTPException(status_code=400, detail="skill_names cannot be empty")
    
    if request.questions_per_difficulty < 1 or request.questions_per_difficulty > 50:
        raise HTTPException(status_code=400, detail="questions_per_difficulty must be between 1 and 50")
    
    # Generate questions (slow operation)
    stats = question_bank_service.generate_bank_for_skills(
        db=db,
        skill_names=request.skill_names,
        questions_per_difficulty=request.questions_per_difficulty,
        model_name=request.model_name
    )
    
    # Prepare response
    success_rate = (stats["total_generated"] / stats["total_requested"] * 100) if stats["total_requested"] > 0 else 0
    
    message = f"Generated {stats['total_generated']}/{stats['total_requested']} questions ({success_rate:.1f}% success). "
    
    if stats["duplicates_skipped"] > 0:
        message += f"{stats['duplicates_skipped']} duplicates skipped. "
    
    if stats["errors"] > 0:
        message += f"{stats['errors']} errors encountered."
    
    return GenerateQuestionsResponse(
        status="completed",
        total_requested=stats["total_requested"],
        total_generated=stats["total_generated"],
        duplicates_skipped=stats["duplicates_skipped"],
        errors=stats["errors"],
        per_skill=stats["per_skill"],
        message=message.strip()
    )


@router.post("/generate-and-export", response_model=GenerateAndExportResponse)
def generate_and_export_questions(
    request: GenerateQuestionsRequest,
    format: str = Query("grouped", description="Export format: 'grouped' or 'flat'"),
    include_answers: bool = Query(True, description="Include correct answers in export"),
    include_explanations: bool = Query(True, description="Include explanations in export"),
    force: bool = Query(False, description="Overwrite existing export file"),
    db: Session = Depends(get_db)
):
    """
    Generate questions using Ollama AND export them to a JSON file in one operation.
    
    **This is a slow operation** - generates questions and saves to JSON.
    
    **Request Body** (same as /generate):
    ```json
    {
        "skill_names": ["Python Programming", "SQL"],
        "questions_per_difficulty": 10,
        "model_name": "llama3.1:8b"
    }
    ```
    
    **Query Parameters**:
    - `format`: 'grouped' (default, by skill/difficulty) or 'flat' (simple list)
    - `include_answers`: Include correct answers (default: true)
    - `include_explanations`: Include explanations (default: true)
    - `force`: Overwrite file if exists (default: false)
    
    **Response**:
    ```json
    {
        "status": "completed",
        "generation_stats": {
            "total_requested": 60,
            "total_generated": 58,
            "duplicates_skipped": 2,
            "errors": 0
        },
        "export_file_path": "exports/question_bank_20240206_143022.json",
        "total_questions": 58,
        "skills": ["Python Programming", "SQL"],
        "format": "grouped",
        "message": "Generated and exported 58 questions"
    }
    ```
    
    **Exported JSON Format** (grouped):
    ```json
    {
        "generated_at": "2024-02-06T14:30:22Z",
        "model_name": "llama3.1:8b",
        "questions_per_difficulty": 10,
        "skills": [
            {
                "skill_name": "SQL",
                "quizzes": [
                    {
                        "difficulty": "easy",
                        "questions": [
                            {
                                "question": "What is SQL?",
                                "options": ["Database language", "Programming language", "Markup language", "Style language"],
                                "answer": "A",
                                "explanation": "SQL stands for Structured Query Language..."
                            }
                        ]
                    }
                ]
            }
        ]
    }
    ```
    """
    if not request.skill_names:
        raise HTTPException(status_code=400, detail="skill_names cannot be empty")
    
    if request.questions_per_difficulty < 1 or request.questions_per_difficulty > 50:
        raise HTTPException(status_code=400, detail="questions_per_difficulty must be between 1 and 50")
    
    # Step 1: Generate questions (stores in database)
    generation_start_time = datetime.utcnow()
    
    stats = question_bank_service.generate_bank_for_skills(
        db=db,
        skill_names=request.skill_names,
        questions_per_difficulty=request.questions_per_difficulty,
        model_name=request.model_name
    )
    
    # Step 2: Query recently generated questions from database
    # Filter by: skill_names, model_name, and created within last 5 minutes
    time_threshold = generation_start_time - timedelta(minutes=5)
    
    query = db.query(QuestionBank).filter(
        QuestionBank.skill_name.in_(request.skill_names),
        QuestionBank.model_name == request.model_name,
        QuestionBank.created_at >= time_threshold
    ).order_by(
        QuestionBank.skill_name,
        QuestionBank.difficulty,
        QuestionBank.id
    )
    
    questions = query.all()
    
    if not questions:
        raise HTTPException(
            status_code=500,
            detail="Questions were generated but could not be retrieved for export"
        )
    
    # Step 3: Prepare export file path
    exports_dir = Path("exports")
    exports_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_filename = f"question_bank_{timestamp}.json"
    export_path = exports_dir / export_filename
    
    # Check if file exists
    if export_path.exists() and not force:
        raise HTTPException(
            status_code=409,
            detail=f"Export file {export_filename} already exists. Use force=true to overwrite."
        )
    
    # Step 4: Build export data
    if format == "flat":
        export_data = _export_flat_with_metadata(
            questions,
            request.model_name,
            request.questions_per_difficulty,
            include_answers,
            include_explanations
        )
    else:  # grouped (default)
        export_data = _export_grouped_with_metadata(
            questions,
            request.model_name,
            request.questions_per_difficulty,
            include_answers,
            include_explanations
        )
    
    # Step 5: Write to file
    with open(export_path, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    # Step 6: Prepare response
    success_rate = (stats["total_generated"] / stats["total_requested"] * 100) if stats["total_requested"] > 0 else 0
    
    message = f"Generated and exported {stats['total_generated']}/{stats['total_requested']} questions ({success_rate:.1f}% success). "
    message += f"Exported to {export_filename}."
    
    return GenerateAndExportResponse(
        status="completed",
        generation_stats={
            "total_requested": stats["total_requested"],
            "total_generated": stats["total_generated"],
            "duplicates_skipped": stats["duplicates_skipped"],
            "errors": stats["errors"],
            "per_skill": stats["per_skill"]
        },
        export_file_path=str(export_path),
        total_questions=len(questions),
        skills=request.skill_names,
        format=format,
        message=message.strip()
    )


@router.get("/stats", response_model=BankStatsResponse)
def get_question_bank_statistics(db: Session = Depends(get_db)):
    """
    Get statistics about the current question bank.
    
    Returns total count and breakdown by skill/difficulty.
    """
    stats = question_bank_service.get_bank_statistics(db)
    
    return BankStatsResponse(
        total_questions=stats["total_questions"],
        by_skill=stats["by_skill"]
    )


@router.get("/skill-names", response_model=SkillNamesResponse)
def get_available_skill_names(
    include_child_skills: bool = Query(False, description="Include child skill names in addition to job skills"),
    db: Session = Depends(get_db)
):
    """
    Get list of valid skill names for question generation.
    
    Returns skill names from:
    1. **Job skills** (job_skills.csv JobSkillName column) - e.g., "SQL", "Python", "AWS"
    2. **Child skills** (child_skills_unique.csv) - optional, if include_child_skills=true
    
    **Response:**
    ```json
    {
        "skill_names": [
            "Python",
            "Java",
            "SQL",
            "JavaScript",
            "..."
        ]
    }
    ```
    
    **Query Parameters:**
    - `include_child_skills`: Include child skill names (default: false)
    
    **Examples:**
    - `/admin/question-bank/skill-names` - Job skills only
    - `/admin/question-bank/skill-names?include_child_skills=true` - Job skills + child skills
    
    Skill names are sorted alphabetically and deduplicated.
    """
    import pandas as pd
    from pathlib import Path
    
    skill_names = []
    
    # Always try to read job_skills.csv first
    try:
        job_skills_path = Path(__file__).parent.parent.parent.parent / "data" / "job_skills.csv"
        if job_skills_path.exists():
            df = pd.read_csv(job_skills_path)
            if "JobSkillName" in df.columns:
                job_skills = df["JobSkillName"].dropna().unique().tolist()
                skill_names.extend(job_skills)
    except Exception as e:
        logger.warning(f"Error reading job_skills.csv: {e}")
    
    # Optionally include child skills
    if include_child_skills:
        try:
            child_skills_path = Path(__file__).parent.parent.parent.parent / "data" / "child_skills_unique.csv"
            if child_skills_path.exists():
                df = pd.read_csv(child_skills_path)
                if "child_skill" in df.columns:
                    child_skills = df["child_skill"].dropna().unique().tolist()
                    skill_names.extend(child_skills)
        except Exception as e:
            logger.warning(f"Error reading child_skills_unique.csv: {e}")
    
    # Fallback: if no skills found, query QuestionBank
    if not skill_names:
        try:
            distinct_skills = db.query(QuestionBank.skill_name).distinct().all()
            if distinct_skills:
                skill_names = [skill[0] for skill in distinct_skills if skill[0]]
        except Exception as e:
            logger.warning(f"Error querying QuestionBank: {e}")
    
    # Sort alphabetically and remove duplicates
    skill_names = sorted(list(set(skill_names)))
    
    return SkillNamesResponse(skill_names=skill_names)


@router.delete("/clear")
def clear_question_bank(
    skill_name: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Clear questions from the bank.
    
    - If skill_name is provided: clears only that skill
    - If skill_name is None: clears entire bank (use with caution!)
    """
    from ..models.question_bank import QuestionBank
    
    if skill_name:
        deleted = db.query(QuestionBank).filter(
            QuestionBank.skill_name == skill_name
        ).delete()
        db.commit()
        return {"status": "success", "deleted": deleted, "skill": skill_name}
    else:
        # Clear entire bank
        deleted = db.query(QuestionBank).delete()
        db.commit()
        return {"status": "success", "deleted": deleted, "message": "Entire question bank cleared"}


@router.get("/export")
def export_questions_json(
    skills: Optional[List[str]] = Query(None, description="Specific skills to export (all if omitted)"),
    format: str = Query("grouped", description="Export format: 'grouped' or 'flat'"),
    include_answers: bool = Query(True, description="Include correct answers"),
    include_explanations: bool = Query(True, description="Include explanations"),
    db: Session = Depends(get_db)
):
    """
    Export questions from QuestionBank as JSON.
    
    **Query Parameters:**
    - `skills`: Comma-separated skill names (optional, exports all if omitted)
    - `format`: 'grouped' (by skill/difficulty) or 'flat' (simple list)
    - `include_answers`: Include correct answers (default: true)
    - `include_explanations`: Include explanations (default: true)
    
    **Examples:**
    - `/admin/question-bank/export` - Export all questions (grouped)
    - `/admin/question-bank/export?skills=Python&skills=SQL` - Export specific skills
    - `/admin/question-bank/export?format=flat&include_answers=false` - Flat format without answers
    
    **Response Formats:**
    
    Grouped format:
    ```json
    {
      "generated_at": "2024-01-15T10:30:00Z",
      "total_skills": 2,
      "total_questions": 60,
      "skills": [
        {
          "skill_name": "Python Programming",
          "quizzes": [
            {
              "difficulty": "easy",
              "questions": [
                {
                  "id": 1,
                  "question": "What is Python?",
                  "options": ["A lang", "A snake", "A tool", "A framework"],
                  "answer": "A",
                  "explanation": "...",
                  "source": "ollama",
                  "model": "llama3.1:8b"
                }
              ]
            }
          ]
        }
      ]
    }
    ```
    
    Flat format:
    ```json
    [
      {
        "id": 1,
        "skill_name": "Python Programming",
        "difficulty": "easy",
        "question": "What is Python?",
        "options": ["A lang", "A snake", "A tool", "A framework"],
        "answer": "A",
        "explanation": "...",
        "model": "llama3.1:8b",
        "created_at": "2024-01-15T10:00:00"
      }
    ]
    ```
    """
    from datetime import datetime
    
    # Query questions
    query = db.query(QuestionBank)
    
    if skills:
        query = query.filter(QuestionBank.skill_name.in_(skills))
    
    query = query.order_by(
        QuestionBank.skill_name,
        QuestionBank.difficulty,
        QuestionBank.created_at,
        QuestionBank.id
    )
    
    questions = query.all()
    
    if not questions:
        return JSONResponse(content={
            "message": "No questions found",
            "total_questions": 0,
            "skills_requested": skills
        })
    
    # Export based on format
    if format == "flat":
        data = _export_flat(questions, include_answers, include_explanations)
    else:  # grouped (default)
        data = _export_grouped(questions, include_answers, include_explanations)
    
    return JSONResponse(content=data)


def _export_grouped(questions: List[QuestionBank], include_answers: bool, include_explanations: bool) -> dict:
    """Export in grouped format (by skill and difficulty)."""
    from datetime import datetime
    
    skills_dict = {}
    
    for q in questions:
        if q.skill_name not in skills_dict:
            skills_dict[q.skill_name] = {
                "skill_name": q.skill_name,
                "quizzes": {}
            }
        
        if q.difficulty not in skills_dict[q.skill_name]["quizzes"]:
            skills_dict[q.skill_name]["quizzes"][q.difficulty] = {
                "difficulty": q.difficulty,
                "questions": []
            }
        
        # Parse options JSON
        try:
            options = json.loads(q.options_json)
            if isinstance(options, dict):
                options_list = [options.get(k, "") for k in ["A", "B", "C", "D"]]
            else:
                options_list = options
        except:
            options_list = []
        
        question_obj = {
            "id": q.id,
            "question": q.question_text,
            "options": options_list
        }
        
        if include_answers:
            question_obj["answer"] = q.correct_option
        
        if include_explanations and q.explanation:
            question_obj["explanation"] = q.explanation
        
        question_obj["source"] = "ollama"
        question_obj["model"] = q.model_name
        
        skills_dict[q.skill_name]["quizzes"][q.difficulty]["questions"].append(question_obj)
    
    # Convert to list format
    skills_list = []
    for skill_name, skill_data in skills_dict.items():
        quizzes_list = list(skill_data["quizzes"].values())
        skills_list.append({
            "skill_name": skill_name,
            "quizzes": quizzes_list
        })
    
    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "total_skills": len(skills_list),
        "total_questions": len(questions),
        "skills": skills_list
    }


def _export_flat(questions: List[QuestionBank], include_answers: bool, include_explanations: bool) -> list:
    """Export in flat format (simple list)."""
    flat_list = []
    
    for q in questions:
        # Parse options JSON
        try:
            options = json.loads(q.options_json)
            if isinstance(options, dict):
                options_list = [options.get(k, "") for k in ["A", "B", "C", "D"]]
            else:
                options_list = options
        except:
            options_list = []
        
        question_obj = {
            "id": q.id,
            "skill_name": q.skill_name,
            "difficulty": q.difficulty,
            "question": q.question_text,
            "options": options_list
        }
        
        if include_answers:
            question_obj["answer"] = q.correct_option
        
        if include_explanations and q.explanation:
            question_obj["explanation"] = q.explanation
        
        question_obj["model"] = q.model_name
        question_obj["created_at"] = q.created_at.isoformat() if q.created_at else None
        
        flat_list.append(question_obj)
    
    return flat_list


def _export_grouped_with_metadata(
    questions: List[QuestionBank],
    model_name: str,
    questions_per_difficulty: int,
    include_answers: bool,
    include_explanations: bool
) -> dict:
    """Export in grouped format with metadata."""
    skills_dict = {}
    
    for q in questions:
        if q.skill_name not in skills_dict:
            skills_dict[q.skill_name] = {
                "skill_name": q.skill_name,
                "quizzes": {}
            }
        
        if q.difficulty not in skills_dict[q.skill_name]["quizzes"]:
            skills_dict[q.skill_name]["quizzes"][q.difficulty] = {
                "difficulty": q.difficulty,
                "questions": []
            }
        
        # Parse options JSON
        try:
            options = json.loads(q.options_json)
            if isinstance(options, dict):
                options_list = [options.get(k, "") for k in ["A", "B", "C", "D"]]
            else:
                options_list = options
        except:
            options_list = []
        
        question_obj = {
            "question": q.question_text,
            "options": options_list
        }
        
        if include_answers:
            question_obj["answer"] = q.correct_option
        
        if include_explanations and q.explanation:
            question_obj["explanation"] = q.explanation
        
        skills_dict[q.skill_name]["quizzes"][q.difficulty]["questions"].append(question_obj)
    
    # Convert to list format
    skills_list = []
    for skill_name, skill_data in skills_dict.items():
        quizzes_list = list(skill_data["quizzes"].values())
        skills_list.append({
            "skill_name": skill_name,
            "quizzes": quizzes_list
        })
    
    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "model_name": model_name,
        "questions_per_difficulty": questions_per_difficulty,
        "skills": skills_list
    }


def _export_flat_with_metadata(
    questions: List[QuestionBank],
    model_name: str,
    questions_per_difficulty: int,
    include_answers: bool,
    include_explanations: bool
) -> dict:
    """Export in flat format with metadata wrapper."""
    flat_list = []
    
    for q in questions:
        # Parse options JSON
        try:
            options = json.loads(q.options_json)
            if isinstance(options, dict):
                options_list = [options.get(k, "") for k in ["A", "B", "C", "D"]]
            else:
                options_list = options
        except:
            options_list = []
        
        question_obj = {
            "skill_name": q.skill_name,
            "difficulty": q.difficulty,
            "question": q.question_text,
            "options": options_list
        }
        
        if include_answers:
            question_obj["answer"] = q.correct_option
        
        if include_explanations and q.explanation:
            question_obj["explanation"] = q.explanation
        
        flat_list.append(question_obj)
    
    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "model_name": model_name,
        "questions_per_difficulty": questions_per_difficulty,
        "questions": flat_list
    }
