from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    database_url: str = "postgresql+asyncpg://propcheck:propcheck@localhost:5434/propcheck"
    test_database_url: str = "postgresql+asyncpg://propcheck:propcheck@localhost:5434/propcheck_test"

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

    # Rate limiting (docs/RATE_LIMITING.md). Rates are "<count>/<second|minute|hour|day>".
    rate_limit_enabled: bool = True
    # Shared counters for production / several API processes. Empty = in-memory development fallback.
    redis_url: str = ""
    # Proxies whose X-Forwarded-For is believed (comma-separated IPs or CIDRs), e.g. the Next.js server.
    trusted_proxies: str = "127.0.0.1,::1"
    rate_limit_login: str = "5/minute"  # per IP + account
    rate_limit_login_ip: str = "30/minute"  # per IP, across accounts (password spraying)
    rate_limit_register: str = "5/hour"  # per IP
    rate_limit_password_reset: str = "3/hour"  # per IP + account (for the planned reset endpoint)
    rate_limit_property_search: str = "60/minute"  # per IP
    rate_limit_nearby_search: str = "60/minute"  # per IP
    rate_limit_house_search: str = "5/hour"  # per user (IP if anonymous)
    rate_limit_reports: str = "5/hour"  # per user (IP if anonymous)
    rate_limit_uploads: str = "20/hour"  # per user
    rate_limit_reservations: str = "10/minute"  # per user

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

    @field_validator("database_url", "test_database_url")
    @classmethod
    def _use_async_driver(cls, v: str) -> str:
        """The app is fully async (asyncpg). Older .env files with a sync driver keep working."""
        scheme, sep, rest = v.partition("://")
        if sep and scheme in ("postgres", "postgresql", "postgresql+psycopg", "postgresql+psycopg2"):
            return f"postgresql+asyncpg://{rest}"
        return v

    @field_validator("trusted_proxies")
    @classmethod
    def _valid_proxies(cls, v: str) -> str:
        import ipaddress

        for part in filter(None, (p.strip() for p in v.split(","))):
            ipaddress.ip_network(part, strict=False)  # raises on a typo instead of silently trusting nothing
        return v

    @field_validator("*", mode="after")
    @classmethod
    def _valid_rates(cls, v, info):
        if info.field_name.startswith("rate_limit_") and isinstance(v, str):
            from app.rates import parse_rate

            parse_rate(v)
        return v

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
