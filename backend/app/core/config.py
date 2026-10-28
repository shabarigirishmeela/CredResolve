import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="allow")

    PROJECT_NAME: str = "CredResolve Intelligence — AI-Powered Collections & Recovery Platform"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "credresolve-dev-only-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Dataset path - resolve relative to workspace
    BASE_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
    DATA_RAW_DIR: str = os.getenv("DATA_RAW_DIR", os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")), "data", "raw"))
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')), 'credresolve.db')}")

    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
        "http://localhost:8000"
    ]

    # Google OAuth 2.0 — set these in your .env file to enable Google Sign-In
    # Get credentials at https://console.cloud.google.com/apis/credentials
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")

    # Default role assigned to new users who sign in with Google
    GOOGLE_DEFAULT_ROLE: str = os.getenv("GOOGLE_DEFAULT_ROLE", "agent")

settings = Settings()
