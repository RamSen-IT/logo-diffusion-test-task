from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    redis_url: str = "redis://localhost:6379/0"
    env: str = "development"

    model_config = {"env_file": ".env"}


settings = Settings()
