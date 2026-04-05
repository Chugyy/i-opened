from pydantic import Field
from pydantic_settings import BaseSettings
import pathlib
from dotenv import load_dotenv

env_path = pathlib.Path(__file__).parent / ".env"
root_env_path = pathlib.Path(__file__).parent.parent / ".env"
load_dotenv(env_path)
load_dotenv(root_env_path)


class Settings(BaseSettings):
    app_name: str = Field("i-opened", env="APP_NAME")
    debug: bool = Field(True, env="DEBUG")
    host: str = Field("0.0.0.0", env="HOST")
    port: int = Field(8000, env="PORT")
    production: bool = Field(False, env="PRODUCTION")

    db_host: str = Field("localhost", env="DB_HOST")
    db_port: int = Field(5432, env="DB_PORT")
    db_name: str = Field("i-opened-db", env="DB_NAME")
    db_user: str = Field("hugohoarau", env="DB_USER")
    db_password: str = Field("", env="DB_PASSWORD")

    frontend_url: str = Field("http://localhost:3000", env="FRONTEND_URL")

    jwt_secret_key: str = Field("change-this", env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    jwt_expiration_hours: int = Field(24, env="JWT_EXPIRATION_HOURS")

    google_client_id: str = Field("", env="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field("", env="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str = Field("", env="GOOGLE_REDIRECT_URI")

    smtp_host: str = Field("", env="SMTP_HOST")
    smtp_port: int = Field(587, env="SMTP_PORT")
    smtp_email: str = Field("", env="SMTP_EMAIL")
    smtp_password: str = Field("", env="SMTP_PASSWORD")

    unipile_dsn: str = Field("", env="UNIPILE_DSN")
    unipile_api_key: str = Field("", env="UNIPILE_API_KEY")
    unipile_account_id: str = Field("", env="UNIPILE_ACCOUNT_ID")

    class Config:
        env_file_encoding = "utf-8"

settings = Settings()
