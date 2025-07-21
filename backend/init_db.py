# init_db.py

from app.models.models import Base
from app.core.db import engine

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("All missing tables created!")
