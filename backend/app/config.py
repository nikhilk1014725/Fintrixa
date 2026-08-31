from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://fintrixa:fintrixa@localhost:5432/fintrixa"

    class Config:
        env_file = ".env"


settings = Settings()
