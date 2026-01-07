from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
import json
import logging

from app.database import get_db, engine
from app import models, schemas
from app.config import settings
from app.security import verify_admin_key, encryptor
from app.clients.kommo import KommoClient, refresh_kommo_token, parse_kommo_lead
from app.services.storage import storage_service
from app.celery_client import celery_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Kommo Call Analyzer API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=schemas.HealthResponse)
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow()}


async def get_kommo_client(db: Session) -> KommoClient:
    """Get Kommo client with valid token"""
    conn = db.query(models.KommoConnection).first()
    
    if not conn or not conn.access_token_enc:
        raise HTTPException(status_code=400, detail="Kommo not connected")
    
    access_token = encryptor.decrypt(conn.access_token_enc)
    
    # Check if token expired
    if conn.expires_at and conn.expires_at < datetime.utcnow():
        # Refresh token
        try:
            refresh_token = encryptor.decrypt(conn.refresh_token_enc)
            token_data = await refresh_kommo_token(
                conn.base_url,
                conn.client_id,
                conn.client_secret,
                refresh_token,
                conn.redirect_uri
            )
            
            # Update tokens
            conn.access_token_enc = encryptor.encrypt(token_data["access_token"])
            conn.refresh_token_enc = encryptor.encrypt(token_data["refresh_token"])
            conn.expires_at = datetime.utcnow() + timedelta(seconds=token_data["expires_in"])
            db.commit()
            
            access_token = token_data["access_token"]
        except Exception as e:
            logger.error(f"Failed to refresh token: {e}")
            raise HTTPException(status_code=401, detail="Failed to refresh Kommo token")
    
    return KommoClient(conn.base_url, access_token)


# Kommo Settings Endpoints

@app.get("/api/settings/kommo/info", dependencies=[Depends(verify_admin_key)])
async def get_kommo_info(db: Session = Depends(get_db)):
    """Get current Kommo connection info"""
    conn = db.query(models.KommoConnection).first()
    
    if not conn or not conn.access_token_enc:
        return {
            "base_url": settings.kommo_base_url,
            "connected": False,
            "expires_at": None,
            "account_info": None
        }
    
    # Try to get account info
    try:
        client = await get_kommo_client(db)
        account_info = await client.get_account_info()
        await client.close()
        
        return {
            "base_url": conn.base_url,
            "connected": True,
            "expires_at": conn.expires_at,
            "account_info": account_info
        }
    except Exception as e:
        return {
            "base_url": conn.base_url,
            "connected": False,
            "expires_at": conn.expires_at,
            "account_info": None
        }


@app.post("/api/settings/kommo/paste", dependencies=[Depends(verify_admin_key)])
async def paste_kommo_tokens(
    tokens: schemas.KommoTokenPaste,
    db: Session = Depends(get_db)
):
    """Manually paste Kommo tokens (MVP mode)"""
    conn = db.query(models.KommoConnection).first()
    
    if not conn:
        conn = models.KommoConnection(
            base_url=settings.kommo_base_url,
            client_id=settings.kommo_client_id,
            client_secret=settings.kommo_client_secret,
            redirect_uri=settings.kommo_redirect_uri
        )
        db.add(conn)
    
    conn.access_token_enc = encryptor.encrypt(tokens.access_token)
    conn.refresh_token_enc = encryptor.encrypt(tokens.refresh_token)
    conn.expires_at = datetime.fromisoformat(tokens.expires_at.replace('Z', '+00:00'))
    conn.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Tokens saved successfully"}


# Leads Endpoints

@app.get("/api/leads", response_model=schemas.LeadsResponse, dependencies=[Depends(verify_admin_key)])
async def list_leads(
    query: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    pipeline_id: Optional[int] = None,
    responsible_user_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """List Kommo leads with pagination and filters"""
    try:
        client = await get_kommo_client(db)
    except Exception as e:
        logger.error(f"Failed to get Kommo client: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to connect to Kommo: {str(e)}")
    
    try:
        logger.info(f"Fetching leads: page={page}, limit={page_size}, query={query}, pipeline_id={pipeline_id}, responsible_user_id={responsible_user_id}")
        result = await client.list_leads(
            query=query, 
            page=page, 
            limit=page_size,
            pipeline_id=pipeline_id,
            responsible_user_id=responsible_user_id
        )
        logger.info(f"Kommo API response keys: {result.keys() if result else 'None'}")
        
        leads = []
        if "_embedded" in result and "leads" in result["_embedded"]:
            lead_list = result["_embedded"]["leads"]
            logger.info(f"Found {len(lead_list)} leads in response")
            for lead_data in lead_list:
                leads.append(parse_kommo_lead(lead_data))
        else:
            logger.warning(f"No leads in response. Response structure: {list(result.keys()) if result else 'empty'}")
        
        # Handle different _page response formats from Kommo API
        page_info = result.get("_page", {})
        if isinstance(page_info, dict):
            total = page_info.get("total", len(leads))
        elif isinstance(page_info, int):
            total = page_info
        else:
            total = len(leads)
        
        return {
            "leads": leads,
            "total": total,
            "page": page,
            "page_size": page_size
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch leads: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch leads: {str(e)}")
    finally:
        await client.close()


@app.get("/api/leads/filters/pipelines", dependencies=[Depends(verify_admin_key)])
async def get_pipelines(db: Session = Depends(get_db)):
    """Get all pipelines for filtering"""
    client = await get_kommo_client(db)
    
    try:
        result = await client.get_pipelines()
        
        pipelines = []
        if "_embedded" in result and "pipelines" in result["_embedded"]:
            for pipeline_data in result["_embedded"]["pipelines"]:
                pipelines.append({
                    "id": pipeline_data.get("id"),
                    "name": pipeline_data.get("name"),
                    "sort": pipeline_data.get("sort", 0)
                })
        
        # Sort by sort field
        pipelines.sort(key=lambda x: x.get("sort", 0))
        
        return {"pipelines": pipelines}
    except Exception as e:
        logger.error(f"Failed to fetch pipelines: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch pipelines: {e}")
    finally:
        await client.close()


@app.get("/api/leads/filters/users", dependencies=[Depends(verify_admin_key)])
async def get_users(db: Session = Depends(get_db)):
    """Get all users for filtering"""
    client = await get_kommo_client(db)
    
    try:
        result = await client.get_users()
        
        users = []
        if "_embedded" in result and "users" in result["_embedded"]:
            for user_data in result["_embedded"]["users"]:
                users.append({
                    "id": user_data.get("id"),
                    "name": user_data.get("name"),
                    "email": user_data.get("email")
                })
        
        return {"users": users}
    except Exception as e:
        logger.error(f"Failed to fetch users: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch users: {e}")
    finally:
        await client.close()


@app.get("/api/leads/{lead_id}", dependencies=[Depends(verify_admin_key)])
async def get_lead(lead_id: int, db: Session = Depends(get_db)):
    """Get single lead details"""
    try:
        client = await get_kommo_client(db)
    except Exception as e:
        logger.error(f"Failed to get Kommo client: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to connect to Kommo: {str(e)}")
    
    try:
        logger.info(f"Fetching lead {lead_id}")
        result = await client.get_lead(lead_id)
        logger.info(f"Lead response keys: {result.keys() if result else 'None'}")
        
        # Kommo API can return lead directly or in _embedded
        if "_embedded" in result and "leads" in result["_embedded"]:
            if len(result["_embedded"]["leads"]) > 0:
                lead_data = result["_embedded"]["leads"][0]
                return parse_kommo_lead(lead_data)
        elif "id" in result:
            # Lead returned directly
            return parse_kommo_lead(result)
        
        logger.error(f"Lead {lead_id} not found in response: {result}")
        raise HTTPException(status_code=404, detail="Lead not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch lead {lead_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch lead: {str(e)}")
    finally:
        await client.close()


# Upload Endpoints

@app.post("/api/uploads", response_model=schemas.UploadResponse, dependencies=[Depends(verify_admin_key)])
async def create_upload(
    file: UploadFile = File(...),
    lead_id: int = Form(...),
    db: Session = Depends(get_db)
):
    """Upload a file for a lead"""
    # Validate file
    allowed_extensions = [".mp4", ".mov", ".m4a", ".mp3", ".wav"]
    file_ext = "." + file.filename.split(".")[-1].lower() if "." in file.filename else ""
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Check file size
    file.file.seek(0, 2)
    size_bytes = file.file.tell()
    file.file.seek(0)
    
    max_size = settings.max_upload_mb * 1024 * 1024
    if size_bytes > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size: {settings.max_upload_mb}MB"
        )
    
    # Create upload record
    upload = models.Upload(
        lead_id=lead_id,
        filename=file.filename,
        mime=file.content_type or "application/octet-stream",
        size_bytes=size_bytes,
        storage_path=""  # Will be updated after save
    )
    db.add(upload)
    db.flush()
    
    # Save file
    storage_path = storage_service.save_upload(upload.id, file.filename, file.file)
    upload.storage_path = storage_path
    db.commit()
    db.refresh(upload)
    
    return {
        "upload_id": upload.id,
        "filename": upload.filename,
        "size_bytes": upload.size_bytes,
        "created_at": upload.created_at
    }


# Job Endpoints

@app.post("/api/jobs", dependencies=[Depends(verify_admin_key)])
async def create_job(
    request: schemas.CreateJobRequest,
    db: Session = Depends(get_db)
):
    """Create and start a processing job"""
    # Verify upload exists
    upload = db.query(models.Upload).filter(models.Upload.id == request.upload_id).first()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")
    
    # Create job
    job = models.Job(
        lead_id=request.lead_id,
        upload_id=request.upload_id,
        status="queued",
        progress_step="queued"
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    # Enqueue Celery task
    from app.celery_client import process_call_task
    process_call_task.delay(job.id)
    
    return {"job_id": job.id, "status": "queued"}


@app.get("/api/leads/{lead_id}/jobs", dependencies=[Depends(verify_admin_key)])
async def get_lead_jobs(lead_id: int, db: Session = Depends(get_db)):
    """Get all jobs for a specific lead"""
    jobs = db.query(models.Job).filter(
        models.Job.lead_id == lead_id
    ).order_by(models.Job.created_at.desc()).all()
    
    results = []
    for job in jobs:
        # Parse extraction_json if exists
        extraction = None
        if job.extraction_json:
            try:
                extraction = json.loads(job.extraction_json)
            except:
                pass
        
        # Parse transcript_json if exists
        transcript_segments = None
        if job.transcript_json:
            try:
                transcript_data = json.loads(job.transcript_json)
                transcript_segments = transcript_data.get("segments", [])
            except:
                pass
        
        # Get upload info
        upload = db.query(models.Upload).filter(models.Upload.id == job.upload_id).first()
        
        results.append({
            "job_id": job.id,
            "status": job.status,
            "upload": {
                "filename": upload.filename if upload else "Unknown",
                "size_bytes": upload.size_bytes if upload else 0
            } if upload else None,
            "created_at": job.created_at,
            "updated_at": job.updated_at,
            "pushed_at": job.pushed_at,
            "confidence": job.confidence,
            "extraction": extraction,
            "transcript_segments": transcript_segments,
            "has_transcript": bool(transcript_segments)
        })
    
    return results


@app.get("/api/jobs/{job_id}", response_model=schemas.JobResponse, dependencies=[Depends(verify_admin_key)])
async def get_job(job_id: int, db: Session = Depends(get_db)):
    """Get job status and results"""
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Parse JSON fields
    transcript_segments = None
    if job.transcript_json:
        try:
            transcript_data = json.loads(job.transcript_json)
            transcript_segments = transcript_data.get("segments", [])
        except:
            pass
    
    extraction = None
    if job.extraction_json:
        try:
            extraction = json.loads(job.extraction_json)
        except:
            pass
    
    # Read transcript text
    transcript = None
    if job.transcript_path:
        try:
            full_path = storage_service.get_full_path(job.transcript_path)
            with open(full_path, "r", encoding="utf-8") as f:
                transcript = f.read()
        except:
            pass
    
    return {
        "job_id": job.id,
        "lead_id": job.lead_id,
        "upload_id": job.upload_id,
        "status": job.status,
        "progress_step": job.progress_step,
        "transcript": transcript,
        "transcript_segments": transcript_segments,
        "extraction": extraction,
        "confidence": job.confidence,
        "last_error": job.last_error,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "pushed_at": job.pushed_at
    }


@app.post("/api/jobs/{job_id}/ask", response_model=schemas.AskQuestionResponse, dependencies=[Depends(verify_admin_key)])
async def ask_question(job_id: int, request: schemas.AskQuestionRequest, db: Session = Depends(get_db)):
    """Ask a question about the call transcript using LLM"""
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Get transcript
    transcript_text = ""
    if job.transcript_path:
        try:
            full_path = storage_service.get_full_path(job.transcript_path)
            with open(full_path, "r", encoding="utf-8") as f:
                transcript_text = f.read()
        except:
            pass
    
    if not transcript_text:
        raise HTTPException(status_code=400, detail="No transcript available for this job")
    
    # Build Q&A prompt
    prompt = f"""You are an AI assistant helping to analyze a sales call transcript.
Your task is to answer questions about the call STRICTLY based on the transcript provided.

CRITICAL RULES:
- Answer ONLY based on the transcript content
- If the answer is not in the transcript, say "This information is not mentioned in the transcript"
- Do NOT make assumptions or invent information
- Quote relevant parts of the transcript when possible
- Be concise and direct

TRANSCRIPT:
{transcript_text}

USER QUESTION:
{request.question}

Provide a clear, factual answer based ONLY on the transcript above:"""
    
    # Call LLM
    import httpx
    from app.config import settings
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{settings.llm_api_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.llm_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": settings.llm_model,
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant that answers questions about call transcripts. Always base your answers strictly on the provided transcript."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 500
                }
            )
            response.raise_for_status()
            
            data = response.json()
            answer = data["choices"][0]["message"]["content"]
            
            return {
                "question": request.question,
                "answer": answer,
                "timestamp": datetime.utcnow()
            }
    
    except Exception as e:
        logger.error(f"LLM Q&A failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process question: {str(e)}")


@app.post("/api/jobs/{job_id}/push", dependencies=[Depends(verify_admin_key)])
async def push_to_kommo(job_id: int, db: Session = Depends(get_db)):
    """Push job results back to Kommo"""
    job = db.query(models.Job).filter(models.Job.id == job_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != "ready":
        raise HTTPException(status_code=400, detail="Job not ready")
    
    if not job.extraction_json:
        raise HTTPException(status_code=400, detail="No extraction data")
    
    extraction = json.loads(job.extraction_json)
    
    # Parse transcript segments
    transcript_segments = []
    if job.transcript_json:
        try:
            transcript_data = json.loads(job.transcript_json)
            transcript_segments = transcript_data.get("segments", [])
        except:
            pass
    
    # Get Kommo client and push
    client = await get_kommo_client(db)
    
    try:
        # 1. Add transcript as separate note with speaker breakdown
        if transcript_segments:
            transcript_note = format_transcript_note(transcript_segments, extraction.get("speaker_roles", {}))
            await client.add_note_to_lead(job.lead_id, transcript_note)
        
        # 2. Add analysis note
        analysis_note = format_extraction_note(extraction)
        await client.add_note_to_lead(job.lead_id, analysis_note)
        
        # 3. Update custom fields if mapping exists
        mapping_record = db.query(models.FieldMapping).first()
        if mapping_record:
            mapping = json.loads(mapping_record.mapping_json)
            custom_fields = apply_field_mapping(extraction, mapping)
            
            if custom_fields:
                await client.update_lead_fields(job.lead_id, custom_fields)
        
        # Update job
        job.pushed_at = datetime.utcnow()
        job.status = "pushed"
        db.commit()
        
        return {"message": "Successfully pushed to Kommo"}
    
    finally:
        await client.close()


# Field Mapping Endpoints

@app.get("/api/settings/mapping", dependencies=[Depends(verify_admin_key)])
async def get_field_mapping(db: Session = Depends(get_db)):
    """Get current field mapping"""
    mapping_record = db.query(models.FieldMapping).first()
    
    if not mapping_record:
        # Return default mapping
        default_mapping = {
            "qualification.score": None,
            "qualification.budget": None,
            "qualification.timeline": None,
            "confidence": None
        }
        return {"mapping": default_mapping}
    
    return {"mapping": json.loads(mapping_record.mapping_json)}


@app.put("/api/settings/mapping", dependencies=[Depends(verify_admin_key)])
async def update_field_mapping(
    update: schemas.FieldMappingUpdate,
    db: Session = Depends(get_db)
):
    """Update field mapping"""
    mapping_record = db.query(models.FieldMapping).first()
    
    if not mapping_record:
        mapping_record = models.FieldMapping(
            mapping_json=json.dumps(update.mapping)
        )
        db.add(mapping_record)
    else:
        mapping_record.mapping_json = json.dumps(update.mapping)
        mapping_record.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": "Mapping updated successfully"}


# Helper Functions

def format_transcript_note(segments: list, speaker_roles: dict) -> str:
    """Format transcript with speaker breakdown as a readable note"""
    lines = ["📝 Call Transcript", ""]
    
    # Helper to get role
    def get_role(speaker: str) -> str:
        role = speaker_roles.get(speaker, "Unknown")
        if role == "Sales Rep":
            return "🎤 Sales Rep"
        elif role == "Customer":
            return "👤 Customer"
        else:
            return f"🗣️ {speaker}"
    
    # Format each segment
    for segment in segments:
        speaker = segment.get("speaker", "Unknown")
        text = segment.get("text", "")
        start = segment.get("start", 0)
        
        # Format timestamp
        minutes = int(start // 60)
        seconds = int(start % 60)
        timestamp = f"[{minutes}:{seconds:02d}]"
        
        # Add segment
        role_label = get_role(speaker)
        lines.append(f"{timestamp} {role_label}")
        lines.append(f"{text}")
        lines.append("")  # Empty line between segments
    
    return "\n".join(lines)


def format_extraction_note(extraction: dict) -> str:
    """Format extraction data as a readable note"""
    lines = ["📞 Call Analysis Results", ""]
    
    # Summary
    if extraction.get("call_summary"):
        lines.append("📋 Summary:")
        for point in extraction["call_summary"]:
            lines.append(f"  • {point}")
        lines.append("")
    
    # Concerns
    if extraction.get("concerns"):
        lines.append("⚠️ Concerns:")
        for concern in extraction["concerns"]:
            severity = "🔴" * concern["severity"]
            lines.append(f"  {severity} {concern['type'].upper()}: {concern['detail']}")
        lines.append("")
    
    # Next Steps
    if extraction.get("next_steps"):
        lines.append("✅ Next Steps:")
        for step in extraction["next_steps"]:
            lines.append(f"  • {step['action']} (Owner: {step['owner']})")
        lines.append("")
    
    # Qualification
    if extraction.get("qualification"):
        qual = extraction["qualification"]
        lines.append("🎯 Qualification:")
        lines.append(f"  Score: {qual.get('score', 'N/A')}/100")
        if qual.get("budget"):
            lines.append(f"  Budget: {qual['budget']}")
        if qual.get("timeline"):
            lines.append(f"  Timeline: {qual['timeline']}")
        if qual.get("decision_maker"):
            lines.append(f"  Decision Maker: {qual['decision_maker']}")
        lines.append("")
    
    # Confidence
    if extraction.get("confidence"):
        confidence_pct = int(extraction["confidence"] * 100)
        lines.append(f"🎲 Confidence: {confidence_pct}%")
    
    return "\n".join(lines)


def apply_field_mapping(extraction: dict, mapping: dict) -> dict:
    """Apply field mapping to extraction data"""
    custom_fields = {}
    
    for key, field_id in mapping.items():
        if field_id is None:
            continue
        
        # Navigate nested keys
        value = extraction
        for part in key.split("."):
            value = value.get(part)
            if value is None:
                break
        
        if value is not None:
            custom_fields[int(field_id)] = value
    
    return custom_fields


from datetime import timedelta


