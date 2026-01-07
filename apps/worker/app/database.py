from sqlalchemy import create_engine, Column, Integer, String, DateTime, BigInteger, Text, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
from app.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Models (duplicated from API for worker independence)
class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(BigInteger, nullable=False, index=True)
    upload_id = Column(Integer, ForeignKey("uploads.id"), nullable=False)
    status = Column(String, default="queued", nullable=False)
    progress_step = Column(String, nullable=True)
    transcript_path = Column(String, nullable=True)
    transcript_json = Column(Text, nullable=True)
    extraction_json = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    pushed_at = Column(DateTime(timezone=True), nullable=True)


class Upload(Base):
    __tablename__ = "uploads"
    
    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(BigInteger, nullable=False, index=True)
    filename = Column(String, nullable=False)
    mime = Column(String, nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    storage_path = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


def get_db():
    db = SessionLocal()
    try:
        return db
    finally:
        pass








