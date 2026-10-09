"""
Configuration.

12-factor principle: config lives in the environment, not in code.
Nothing here is hard-coded — everything has a sane default for local dev,
and every value can be overridden by an env var (or a .env file locally).
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # --- Service ---
    APP_NAME: str = "defect-classifier"
    PORT: int = 8000
    LOG_LEVEL: str = "info"

    # --- Model ---
    MODEL_NAME: str = "openai/clip-vit-base-patch32"
    DEFAULT_LABELS: list[str] = [
        "corroded metal surface",
        "clean undamaged metal surface",
        "weld defect",
        "crack in hull plating",
    ]

    # --- Cache (backing service — see app/cache.py) ---
    CACHE_BACKEND: str = "memory"  # "memory" or "redis"
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL_SECONDS: int = 3600
    CACHE_MAX_ITEMS: int = 512  # only used by the in-memory backend

    # --- Rate limiting ---
    RATE_LIMIT: str = "10/minute"

    # --- Feedback storage ---
    FEEDBACK_DB_PATH: str = "./data/feedback.db"


settings = Settings()
