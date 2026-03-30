from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    admin_api_key: str
    require_api_key: bool = False
    environment: str = "development"

    class Config:
        env_file = ".env"


settings = Settings()
