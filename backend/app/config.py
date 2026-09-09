from pydantic_settings import BaseSettings
from pydantic import field_validator, model_validator


class Settings(BaseSettings):
    gemini_api_key: str = ""
    openweather_api_key: str = ""

    guardian_enabled: bool = True
    guardian_interval_seconds: int = 300

    demo_mode: bool = False
    app_env: str = "development"

    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"

    marine_api_url: str = "https://marine-api.open-meteo.com/v1/marine"
    weather_api_url: str = "https://api.open-meteo.com/v1/forecast"
    imd_feed_url: str = ""

    frontend_url: str = "http://localhost:3000"

    max_query_length: int = 1000
    rate_limit: str = "20/minute"

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret_length(cls, v):
        if v and len(v) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters")
        return v

    @model_validator(mode="after")
    def validate_production_security(self):
        if self.app_env.lower() in {"production", "prod"}:
            if not self.jwt_secret or self.jwt_secret in {
                "orca_dev_secret_2026",
                "orca_secret_key_change_in_production_2026",
            }:
                raise ValueError("JWT_SECRET must be configured in production")
            if self.demo_mode:
                raise ValueError("DEMO_MODE must be disabled in production")
        return self

    @field_validator("marine_api_url", "weather_api_url", "imd_feed_url")
    @classmethod
    def validate_urls(cls, v):
        if v and not v.startswith("https://"):
            raise ValueError("API URLs must use HTTPS")
        return v

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
