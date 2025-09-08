# app/core/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    AWS_REGION: str = "il-central-1"
    S3_BUCKET: str
    SNS_TOPIC_EVENTS_ARN: str
    SNS_TOPIC_STUDIO_EMAILS_ARN: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()
