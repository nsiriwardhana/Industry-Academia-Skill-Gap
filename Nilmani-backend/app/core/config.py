from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os
from pathlib import Path

# Load .env from root directory (4 levels up: app/core/config.py)
env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

MAX_QUESTIONS = 7

class Settings(BaseSettings):
    """
    Central configuration object for the application.
    Loaded once and reused everywhere.
    """

    # ========= Ollama =========
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "mistral")
    OLLAMA_EMBEDDING_MODEL: str = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")

    # ========= Application =========
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # ========= Interview Settings =========
    MAX_INTERVIEW_QUESTIONS: int = int(
        os.getenv("MAX_INTERVIEW_QUESTIONS", 7)
    )

    # ========= Security (future-ready) =========
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key")

    #========== Gemini =========
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    CHAT_MODEL: str = os.getenv("CHAT_MODEL", "gemini-1.5-flash")
    # EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "gemini-embed-001")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "models/embedding-001")

    # ========= Speech Emotion Recognition =========
    SER_MODEL_PATH: str = os.getenv(
        "SER_MODEL_PATH",
        str(Path(__file__).resolve().parent.parent / "models" / "ser_wav2vec2_bilstm_attention.pth"),
    )
    SER_METADATA_PATH: str = os.getenv(
        "SER_METADATA_PATH",
        str(Path(__file__).resolve().parent.parent / "models" / "ser_metadata.json"),
    )
    SER_SAMPLE_RATE: int = int(os.getenv("SER_SAMPLE_RATE", 16000))
    SER_MAX_SECONDS: int = int(os.getenv("SER_MAX_SECONDS", 4))
    
    


# Singleton settings object
settings = Settings()
