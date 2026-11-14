from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root = parent directory of backend/
PROJECT_ROOT = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    COLLEGE_API_BASE_URL: str
    COLLEGE_PARTICIPANT_KEY: str

    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = ""
    DEEPGRAM_API_KEY: str = ""
    ELEVENLABS_API_KEY: str = ""

    DATABASE_URL: str = ""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()
