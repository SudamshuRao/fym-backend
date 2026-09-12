"""
App-wide settings, loaded from environment variables (with sane local
defaults). Uses pydantic-settings so misconfigured env vars fail loudly
at startup rather than causing confusing runtime errors later.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql://fym_user:fym_pass@localhost:5432/fym_db"

    # Auth
    jwt_secret_key: str = "change-me-in-production"  # override via env in real deployments
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days - fine for a personal-use app

    # App
    app_name: str = "FYM (Fit Your Macros)"
    debug: bool = True

    # Ollama (local, free LLM inference - used for recipe generation)
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"


settings = Settings()
