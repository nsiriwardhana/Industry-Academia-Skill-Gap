import os
import csv
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter()


def _ensure_dir():
    path = os.path.abspath(settings.VALIDATION_DIR)
    os.makedirs(path, exist_ok=True)
    return path


def _append_csv(path: str, header: list, row: list):
    exists = os.path.exists(path)
    with open(path, "a", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not exists:
            writer.writerow(header)
        writer.writerow(row)


def _ensure_csv_with_header(path: str, header: list):
    """Create a CSV file with just a header row if it doesn't exist yet."""
    if os.path.exists(path):
      return

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)


class QuestionRating(BaseModel):
    job_id: str
    question_id: str
    question_text: str
    rater_id: Optional[str] = None
    relevance: int
    clarity: int
    realism: int
    comment: Optional[str] = ""
    timestamp: Optional[str] = None


class AnswerRating(BaseModel):
    question_id: str
    answer_id: str
    answer_text: str
    human_score: float
    system_score: float
    rater_id: Optional[str] = None
    timestamp: Optional[str] = None


@router.post("/validation/question-rating")
async def post_question_rating(payload: QuestionRating):
    if not settings.VALIDATION_ENABLED:
        raise HTTPException(status_code=403, detail="Validation endpoints disabled")

    path = _ensure_dir()
    filename = os.path.join(path, "question_ratings.csv")
    ts = payload.timestamp or datetime.utcnow().isoformat()
    header = [
        "job_id",
        "question_id",
        "question_text",
        "rater_id",
        "relevance",
        "clarity",
        "realism",
        "comment",
        "timestamp",
    ]
    row = [
        payload.job_id,
        payload.question_id,
        payload.question_text,
        payload.rater_id or "",
        payload.relevance,
        payload.clarity,
        payload.realism,
        payload.comment or "",
        ts,
    ]
    _append_csv(filename, header, row)
    return {"status": "ok", "file": filename}


@router.post("/validation/answer-rating")
async def post_answer_rating(payload: AnswerRating):
    if not settings.VALIDATION_ENABLED:
        raise HTTPException(status_code=403, detail="Validation endpoints disabled")

    path = _ensure_dir()
    filename = os.path.join(path, "answer_ratings.csv")
    ts = payload.timestamp or datetime.utcnow().isoformat()
    header = [
        "question_id",
        "answer_id",
        "answer_text",
        "human_score",
        "system_score",
        "rater_id",
        "timestamp",
    ]
    row = [
        payload.question_id,
        payload.answer_id,
        payload.answer_text,
        payload.human_score,
        payload.system_score,
        payload.rater_id or "",
        ts,
    ]
    _append_csv(filename, header, row)
    return {"status": "ok", "file": filename}


@router.get("/validation/export")
async def export_validation(file: str = "question_ratings.csv"):
    if not settings.VALIDATION_ENABLED:
        raise HTTPException(status_code=403, detail="Validation endpoints disabled")

    path = _ensure_dir()
    allowed = {"question_ratings.csv", "answer_ratings.csv"}
    if file not in allowed:
        raise HTTPException(status_code=400, detail="Invalid file requested")

    filepath = os.path.join(path, file)

    if file == "question_ratings.csv":
        _ensure_csv_with_header(
            filepath,
            [
                "job_id",
                "question_id",
                "question_text",
                "rater_id",
                "relevance",
                "clarity",
                "realism",
                "comment",
                "timestamp",
            ],
        )
    elif file == "answer_ratings.csv":
        _ensure_csv_with_header(
            filepath,
            [
                "question_id",
                "answer_id",
                "answer_text",
                "human_score",
                "system_score",
                "rater_id",
                "timestamp",
            ],
        )

    return FileResponse(filepath, filename=file)
