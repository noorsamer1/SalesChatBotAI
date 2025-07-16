from sqlalchemy import create_engine
<<<<<<< HEAD
from app.core.config import settings

# Shared SQLAlchemy engine
engine = create_engine(
    f"postgresql://{settings.PG_USER}:{settings.PG_PASSWORD}@{settings.PG_HOST}:{settings.PG_PORT}/chatbot_data"
)
=======
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
# from sqlalchemy.ext.declarative import declarative_base

DATABASE_URL = settings.DATABASE_URL

# SQLAlchemy Engine
engine = create_engine(DATABASE_URL)
# Base = declarative_base()

# Session maker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency function for FastAPI routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
>>>>>>> master
