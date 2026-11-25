from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    jwt_secret: str
    jwt_expire_hours: int = 24
    cors_origins: str = "http://localhost:3000"
    model_dir: str = "/opt/models"
    # Name of the model to make active at startup (e.g. "distilbert"); empty = keep the
    # current active model, or pick the one with the best f1_score.
    active_model: str = ""
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "sentiboard"


settings = Settings()
