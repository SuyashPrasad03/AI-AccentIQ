"""
Single source of truth for all application configuration.
Loaded from environment variables / .env via pydantic-settings.
Import `settings` from here everywhere — never read os.environ directly.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App / General ─────────────────────────────────────────
    app_env: Literal["development", "staging", "production"] = "development"
    jwt_secret: str = "changeme_generate_with_openssl_rand_hex_32"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    # ── Backend server ────────────────────────────────────────
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS_ORIGINS as comma-separated or JSON array."""
        v = self.cors_origins.strip()
        if v.startswith("["):
            import json
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, ValueError):
                pass
        return [origin.strip() for origin in v.split(",") if origin.strip()]

    # ── MySQL ─────────────────────────────────────────────────
    mysql_host: str = "mysql"
    mysql_port: int = 3306
    mysql_user: str = "pronunciation"
    mysql_password: str = "changeme_mysql_password"
    mysql_database: str = "accentiq"

    @property
    def mysql_dsn(self) -> str:
        from urllib.parse import quote_plus
        encoded_password = quote_plus(self.mysql_password)
        return (
            f"mysql+pymysql://{self.mysql_user}:{encoded_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
        )

    # ── MongoDB ───────────────────────────────────────────────
    mongo_uri: str = "mongodb://mongo:27017"
    mongo_database: str = "accentiq"

    # ── Storage ───────────────────────────────────────────────
    storage_backend: Literal["local", "s3"] = "local"
    storage_local_root: str = "/app/storage"
    s3_bucket: str = ""
    s3_region: str = "ap-south-1"
    s3_endpoint_url: str = ""
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""

    # ── Audio processing ──────────────────────────────────────
    audio_min_duration_seconds: float = 10.0
    audio_max_duration_seconds: float = 45.0
    audio_max_size_bytes: int = 52_428_800  # 50 MB

    # ── WhisperX ──────────────────────────────────────────────
    whisperx_model_size: str = "small"
    whisperx_device: str = "cpu"
    hf_token: str = ""

    # ── OpenRouter / Gemini ───────────────────────────────────
    openrouter_api_key: str = ""
    openrouter_model: str = "google/gemini-flash-1.5"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # ── Deepgram (cloud ASR — zero RAM alternative to WhisperX) ──
    deepgram_api_key: str = ""

    # ── Email / OTP ───────────────────────────────────────────
    smtp_host: str = "smtp.resend.com"
    smtp_port: int = 465
    smtp_user: str = "resend"
    smtp_password: str = ""
    smtp_from_address: str = "noreply@accentiq.example.com"
    smtp_from_name: str = "AccentIQ"
    email_console_fallback: bool = True
    otp_rate_limit_per_hour: int = 5
    otp_expiry_minutes: int = 10

    # Resend HTTP API — works on Render/Railway where SMTP is blocked
    resend_api_key: str = ""
    # Brevo (Sendinblue) HTTP API — free 300/day, sends to ANY recipient
    brevo_api_key: str = ""

    # ── Anonymous quota ───────────────────────────────────────
    anonymous_free_analyses: int = 3

    # ── RAG / Embeddings ──────────────────────────────────────
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    rag_similarity_threshold: float = 0.35
    rag_top_k: int = 5

    # ── DPDP / Retention ──────────────────────────────────────
    audio_retention_days: int = 30
    privacy_policy_version: str = "1.0"

    # ── Sentry ────────────────────────────────────────────────
    sentry_dsn: str = ""


@lru_cache
def get_settings() -> Settings:
    """
    Return a cached Settings instance.
    Use this as a FastAPI dependency: Depends(get_settings).
    """
    return Settings()


# Module-level singleton — safe to import directly in non-DI contexts.
settings: Settings = get_settings()
