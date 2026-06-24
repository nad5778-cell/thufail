from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    oracle_user: str
    oracle_password: str
    oracle_dsn: str

    oracle_pic_summary_view: str
    oracle_pic_detail_view: str

    # Read-only view/synonym exposing NATIONAL_IDENTITY, FIRST_NAME and
    # INSURANCE_COMPANY_NUMBER (e.g. a view over RPLMEMBER), used by the
    # national-identity anomaly check.
    oracle_member_view: str = "V_PIC_MEMBER"

    frontend_origin: str = "http://localhost:5173"


settings = Settings()
