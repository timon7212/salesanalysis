from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# Auth
class LoginRequest(BaseModel):
    api_key: str


# Kommo
class KommoConnectionInfo(BaseModel):
    base_url: str
    connected: bool
    expires_at: Optional[datetime] = None
    account_info: Optional[dict] = None


class KommoTokenPaste(BaseModel):
    access_token: str
    refresh_token: str
    expires_at: str


class Lead(BaseModel):
    lead_id: int
    lead_name: str
    pipeline: Optional[str] = None
    status: Optional[str] = None
    price: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    contact_name: Optional[str] = None


class LeadsResponse(BaseModel):
    leads: List[Lead]
    total: int
    page: int
    page_size: int


# Upload
class UploadResponse(BaseModel):
    upload_id: int
    filename: str
    size_bytes: int
    created_at: datetime


# Job
class CreateJobRequest(BaseModel):
    lead_id: int
    upload_id: int


class EvidenceQuote(BaseModel):
    text: str
    timestamp: Optional[str] = None


class Concern(BaseModel):
    type: str
    severity: int = Field(..., ge=1, le=5)
    detail: str
    evidence_quotes: List[EvidenceQuote] = []


class NextStep(BaseModel):
    action: str
    owner: str
    suggested_due_days: Optional[int] = None


class Qualification(BaseModel):
    budget: Optional[str] = None
    timeline: Optional[str] = None
    decision_maker: Optional[str] = None
    need: Optional[str] = None
    score: int = Field(..., ge=0, le=100)


class ExtractionResult(BaseModel):
    call_summary: List[str]
    concerns: List[Concern]
    next_steps: List[NextStep]
    qualification: Qualification
    confidence: float = Field(..., ge=0.0, le=1.0)


class TranscriptSegment(BaseModel):
    start: float
    end: float
    text: str
    speaker: Optional[str] = None


class JobResponse(BaseModel):
    job_id: int
    lead_id: int
    upload_id: int
    status: str
    progress_step: Optional[str] = None
    transcript: Optional[str] = None
    transcript_segments: Optional[List[TranscriptSegment]] = None
    extraction: Optional[ExtractionResult] = None
    confidence: Optional[float] = None
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    pushed_at: Optional[datetime] = None


# Field Mapping
class FieldMappingResponse(BaseModel):
    mapping: dict


class FieldMappingUpdate(BaseModel):
    mapping: dict


# Q&A
class AskQuestionRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)


class AskQuestionResponse(BaseModel):
    question: str
    answer: str
    timestamp: datetime


# Health
class HealthResponse(BaseModel):
    status: str
    timestamp: datetime








