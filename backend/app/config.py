from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    database_url: str = "postgresql+psycopg://propcheck:propcheck@localhost:5434/propcheck"
    test_database_url: str = "postgresql+psycopg://propcheck:propcheck@localhost:5434/propcheck_test"

    jwt_secret: str = "dev-only-insecure-jwt-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24
    cookie_name: str = "propcheck_session"
    cookie_secure: bool = False

    file_signing_secret: str = "dev-only-insecure-file-secret-change-me"
    signed_url_ttl_seconds: int = 600

    cors_origins: str = "http://localhost:3000"
    api_public_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"

    storage_backend: str = "local"
    storage_dir: str = "./storage"
    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""

    paystack_secret_key: str = ""
    paystack_public_key: str = ""
    paystack_callback_url: str = "http://localhost:3000/dashboard/renter/reservations"

    auth_rate_limit_per_minute: int = 20

    # Comma-separated states the product serves. Each must exist in app/reference LOCATIONS.
    active_states: str = "Lagos,Rivers,Enugu,Anambra,Imo"
    nearby_default_radius_km: float = 3.0
    nearby_max_radius_km: float = 10.0

    max_image_bytes: int = 5 * 1024 * 1024
    max_document_bytes: int = 10 * 1024 * 1024

    property_verification_days: int = 180
    agent_verification_days: int = 365
    reservation_terms_version: str = "DEMO-2026-10-v1"
    reservation_deposit_percent: int = 10

    @field_validator("paystack_secret_key")
    @classmethod
    def _secret_must_be_test(cls, v: str) -> str:
        if v and not v.startswith("sk_test_"):
            raise ValueError("Only Paystack TEST secret keys (sk_test_...) are allowed in this MVP.")
        return v

    @field_validator("paystack_public_key")
    @classmethod
    def _public_must_be_test(cls, v: str) -> str:
        if v and not v.startswith("pk_test_"):
            raise ValueError("Only Paystack TEST public keys (pk_test_...) are allowed in this MVP.")
        return v

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
