from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    oracle_user: str
    oracle_password: str
    oracle_dsn: str

    oracle_pic_summary_view: str
    oracle_pic_detail_view: str

    frontend_origin: str = "http://localhost:5173"


settings = Settings()
