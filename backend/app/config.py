from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    openweather_api_key: str = ""
    ollama_enabled: bool = True
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "llama3.2:1b"

    guardian_enabled: bool = True
    guardian_interval_seconds: int = 300

    demo_mode: bool = False
    app_env: str = "development"

    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"

    marine_api_url: str = "https://marine-api.open-meteo.com/v1/marine"
    weather_api_url: str = "https://api.open-meteo.com/v1/forecast"
    imd_feed_url: str = "https://mosdac.gov.in/isrocast.xml"

    frontend_url: str = "http://localhost:3000"

    bhashini_api_key: str = ""
    bhashini_base_url: str = "https://meity-auth.ulcacontrib.org/ulca/apis/v0"

    max_query_length: int = 1000
    rate_limit: str = "20/minute"

    @field_validator("marine_api_url", "weather_api_url", "imd_feed_url")
    @classmethod
    def validate_urls(cls, v):
        if v and not v.startswith("https://"):
            raise ValueError("API URLs must use HTTPS")
        return v

    @field_validator("ollama_url")
    @classmethod
    def validate_ollama_url(cls, v):
        if not v.startswith(("http://127.0.0.1", "http://localhost", "https://")):
            raise ValueError("OLLAMA_URL must use localhost or HTTPS")
        return v.rstrip("/")

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
