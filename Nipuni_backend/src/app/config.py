from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./app.db"
    CORS_ORIGINS: str = "http://localhost:5173"
    UPLOAD_DIR: str = "backend/uploads"

    class Config:
        env_file = ".env"

settings = Settings()
