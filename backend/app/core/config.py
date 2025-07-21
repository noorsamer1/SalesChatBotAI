import os
from dotenv import load_dotenv

load_dotenv()  # Load .env from project root

class Settings:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    APP_NAME: str = "Chatbot API"
    DATABASE_URL: str = os.getenv("DATABASE_URL")

    PG_USER: str = os.getenv("PG_USER")
    PG_PASSWORD: str = os.getenv("PG_PASSWORD")
    PG_HOST: str = os.getenv("PG_HOST", "localhost")
    PG_PORT: int = int(os.getenv("PG_PORT", "5432"))
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "change_this_default_in_production")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRATION_MINUTES: int = int(os.getenv("JWT_EXPIRATION_MINUTES", 43200))
settings = Settings()
