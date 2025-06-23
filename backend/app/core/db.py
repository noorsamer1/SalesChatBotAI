from sqlalchemy import create_engine
from app.core.config import settings

# Shared SQLAlchemy engine
engine = create_engine(
    f"postgresql://{settings.PG_USER}:{settings.PG_PASSWORD}@{settings.PG_HOST}:{settings.PG_PORT}/chatbot_data"
)
