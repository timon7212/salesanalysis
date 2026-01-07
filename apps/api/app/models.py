from sqlalchemy import Column, Integer, String, DateTime, BigInteger, Text, Float, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class KommoConnection(Base):
    __tablename__ = "kommo_connections"
    
    id = Column(Integer, primary_key=True, index=True)
    base_url = Column(String, nullable=False)
    client_id = Column(String, nullable=False)
    client_secret = Column(String, nullable=False)
    redirect_uri = Column(String, nullable=False)
    access_token_enc = Column(Text, nullable=True)
    refresh_token_enc = Column(Text, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class LeadCache(Base):
    __tablename__ = "lead_cache"
    
    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(BigInteger, unique=True, index=True, nullable=False)
    payload_json = Column(Text, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Upload(Base):
    __tablename__ = "uploads"
    
    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(BigInteger, nullable=False, index=True)
    filename = Column(String, nullable=False)
    mime = Column(String, nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    storage_path = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(BigInteger, nullable=False, index=True)
    upload_id = Column(Integer, ForeignKey("uploads.id"), nullable=False)
    status = Column(String, default="queued", nullable=False)  # queued, converting, transcribing, extracting, ready, failed, pushed
    progress_step = Column(String, nullable=True)
    transcript_path = Column(String, nullable=True)
    transcript_json = Column(Text, nullable=True)
    extraction_json = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    pushed_at = Column(DateTime(timezone=True), nullable=True)


class FieldMapping(Base):
    __tablename__ = "field_mappings"
    
    id = Column(Integer, primary_key=True, index=True)
    mapping_json = Column(Text, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())








