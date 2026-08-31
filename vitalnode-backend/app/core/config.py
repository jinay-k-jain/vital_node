"""
Application configuration - all settings loaded from environment variables.
Never hardcode secrets here.
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
        protected_namespaces=("settings_",),  # fixes: Field "model_path" conflict warning
    )

    # Application
    app_env: Literal["development", "production"] = "development"
    app_name: str = "VitalNode"
    app_version: str = "1.0.0"
    log_level: str = "INFO"
    demo_mode: bool = True

    # Database
    database_url: str = "postgresql+asyncpg://vitalnode_user:password@localhost:5432/vitalnode_db"
    database_sync_url: str = "postgresql://vitalnode_user:password@localhost:5432/vitalnode_db"

    # Security
    jwt_secret_key: str = "INSECURE_DEV_KEY_change_before_production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 480  # 8-hour clinical shift

    # CORS
    frontend_url: str = "http://localhost:5173"

    # Speech-to-Text
    speech_provider: Literal["mock", "openai_whisper", "google_speech", "azure_speech", "assemblyai"] = "mock"
    speech_api_key: str = ""

    # ML Engine
    ml_engine: Literal["mock", "xgboost"] = "mock"
    model_path: str = ""

    # Gemini API (used by core_engine.py for NLP)
    gemini_api_key: str = ""

    # Hospital
    hospital_name: str = "City Emergency Hospital"
    hospital_department: str = "Emergency Department"
    hospital_location: str = "Mumbai, Maharashtra"

    # Reassessment intervals (minutes)
    reassessment_critical_min: int = 5
    reassessment_high_min: int = 15
    reassessment_moderate_min: int = 30
    reassessment_low_min: int = 60

    # Surge
    surge_patient_count: int = 12

    # Feature flags
    enable_device_simulation: bool = True
    enable_audit_log: bool = True

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    def reassessment_interval_minutes(self, acuity: str) -> int:
        """Return reassessment interval in minutes for a given acuity level."""
        mapping = {
            "CRITICAL": self.reassessment_critical_min,
            "HIGH": self.reassessment_high_min,
            "MODERATE": self.reassessment_moderate_min,
            "LOW": self.reassessment_low_min,
        }
        return mapping.get(acuity.upper(), self.reassessment_low_min)


@lru_cache()
def get_settings() -> Settings:
    return Settings()
