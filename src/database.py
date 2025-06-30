import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models.base import Base # ESTA LINHA É CRÍTICA!

if os.environ.get("TESTING") == "True":
    SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
else:
    SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:admin123@db:5432/estacionamento")

engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()