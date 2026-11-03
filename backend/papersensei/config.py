from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Runtime configuration from the environment (prefix ``PAPERSENSEI_``) or ``.env``."""

    model_config = SettingsConfigDict(env_prefix="PAPERSENSEI_", env_file=".env", extra="ignore")

    # "anthropic" uses Claude; "scripted" is a deterministic offline model for tests and demos.
    llm: str = "anthropic"
    model: str = "claude-opus-5-5"
    scripted_delay: float = 0.0
    plan_effort: str = "medium"
    lesson_effort: str = "medium"
    tutor_effort: str = "low"

    data_dir: Path = ROOT / "data"
    sample_pdf: Path = ROOT / "samples" / "hybrid-retrieval.pdf"
    max_pages: int = 40
    max_upload_mb: int = 25
    max_lessons: int = 6
    # A lesson whose quotes don't check out against the paper is regenerated once.
    min_grounding: float = 0.6
    cors_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
