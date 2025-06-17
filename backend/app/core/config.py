import os
from dotenv import load_dotenv

load_dotenv()  # Load .env from project root

class Settings:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY")
    APP_NAME: str = "Chatbot API"
    PG_USER: str = os.getenv("PG_USER")
    PG_PASSWORD: str = os.getenv("PG_PASSWORD")
    PG_HOST: str = os.getenv("PG_HOST", "localhost")
    PG_PORT: int = int(os.getenv("PG_PORT", "5432"))

settings = Settings()
