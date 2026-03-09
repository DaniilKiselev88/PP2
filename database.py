from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base

# Для SQLite
SQLALCHEMY_DATABASE_URL = "sqlite:///./points.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Создание таблиц
Base.metadata.create_all(bind=engine)
