from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from core.config import settings

# 데이터베이스 URL (env 파일에서 로드)
DATABASE_URL = settings.DATABASE_URL

# SQLAlchemy 엔진 생성
engine = create_engine(DATABASE_URL)

# 세션 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 모델의 Base 클래스 생성
Base = declarative_base()

# DB 세션 의존성
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
