from .admin import router as admin_router
from .transcript import router as transcript_router
from .skills import router as skills_router
from .quiz import router as quiz_router
from .admin_question_bank import router as admin_question_bank_router
from .admin_question_persistence import router as admin_question_persistence_router
from .xai import router as xai_router
from .jobs import router as jobs_router, job_router
from .profile import router as profile_router

__all__ = [
    "admin_router", 
    "transcript_router", 
    "skills_router", 
    "quiz_router",
    "admin_question_bank_router",
    "admin_question_persistence_router",
    "xai_router",
    "jobs_router",
    "job_router",
    "profile_router"
]
