from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    gemini_api_key: str = ""
    openweather_api_key: str = ""

    guardian_enabled: bool = True
    guardian_interval_seconds: int = 300

    demo_mode: bool = False

    jwt_secret: str = "orca_dev_secret_2026"
    jwt_algorithm: str = "HS256"

    marine_api_url: str = "https://marine-api.open-meteo.com/v1/marine"
    weather_api_url: str = "https://api.open-meteo.com/v1/forecast"
    imd_feed_url: str = ""

    frontend_url: str = "http://localhost:3000"

    max_query_length: int = 1000
    rate_limit: str = "20/minute"

    @field_validator("jwt_secret")
    @classmethod
    def jwt_secret_not_default_in_prod(cls, v):
        return v

    @field_validator("marine_api_url", "weather_api_url")
    @classmethod
    def validate_urls(cls, v):
        if v and not v.startswith("https://"):
            raise ValueError("API URLs must use HTTPS")
        return v

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
