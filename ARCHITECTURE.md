# Architecture Documentation

## System Overview

Kommo Call Analyzer is a microservices-based application for processing sales call recordings with AI and integrating with Kommo CRM.

## High-Level Architecture

```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │
       │ HTTPS
       ▼
┌─────────────────────────┐
│   Next.js Frontend      │
│   (Port 3000)           │
│   - React Components    │
│   - TypeScript          │
│   - Tailwind CSS        │
└──────┬──────────────────┘
       │
       │ REST API
       ▼
┌─────────────────────────┐      ┌──────────────┐
│   FastAPI Backend       │◄────►│  PostgreSQL  │
│   (Port 8000)           │      │              │
│   - API Routes          │      └──────────────┘
│   - Authentication      │
│   - Kommo Integration   │
└──────┬──────────────────┘
       │
       │ Task Enqueue
       ▼
┌─────────────────────────┐      ┌──────────────┐
│   Redis                 │      │  Celery      │
│   (Port 6379)           │◄────►│  Worker      │
│   - Task Broker         │      │  - FFmpeg    │
│   - Result Backend      │      │  - Whisper   │
└─────────────────────────┘      │  - LLM       │
                                 └──────────────┘
```

## Component Details

### 1. Frontend (Next.js)

**Technology**: Next.js 14 with App Router, TypeScript, Tailwind CSS

**Responsibilities**:
- User interface and interactions
- API communication
- Local state management
- Form validation
- File upload handling

**Key Routes**:
- `/login` - Authentication
- `/leads` - Lead list
- `/leads/[id]` - Lead detail and upload
- `/jobs/[id]` - Job status and results
- `/settings` - Configuration

**State Management**:
- React hooks for local state
- localStorage for API key persistence
- No global state library (MVP simplicity)

### 2. Backend API (FastAPI)

**Technology**: FastAPI, Python 3.11, SQLAlchemy

**Responsibilities**:
- HTTP API endpoints
- Request validation (Pydantic)
- Authentication/authorization
- Database operations
- Kommo API integration
- Task enqueueing

**Key Modules**:
- `main.py` - FastAPI app, routes
- `models.py` - SQLAlchemy models
- `schemas.py` - Pydantic request/response models
- `security.py` - Auth and encryption
- `clients/kommo.py` - Kommo API client
- `services/` - Business logic services

**Database Models**:
- `KommoConnection` - OAuth tokens (encrypted)
- `Upload` - File metadata
- `Job` - Processing jobs
- `FieldMapping` - Custom field mappings
- `LeadCache` - Optional lead caching

### 3. Worker (Celery)

**Technology**: Celery, Python 3.11, FFmpeg, Whisper, LLM clients

**Responsibilities**:
- Background job processing
- Audio conversion (FFmpeg)
- Transcription (Whisper/API)
- LLM extraction
- Error handling and retry

**Processing Pipeline**:
```
1. Receive task (job_id)
2. Load job and upload from DB
3. Convert file to WAV (FFmpeg)
4. Transcribe audio (Whisper)
5. Extract insights (LLM)
6. Save results to DB
7. Mark job as ready
```

**Key Modules**:
- `celery_app.py` - Celery configuration
- `tasks.py` - Task definitions
- `processor.py` - Processing logic

### 4. Database (PostgreSQL)

**Technology**: PostgreSQL 15

**Responsibilities**:
- Persistent data storage
- Transactional integrity
- Foreign key relationships

**Schema**:
```sql
kommo_connections
  ├── id (PK)
  ├── base_url
  ├── client_id, client_secret
  ├── access_token_enc (AES-GCM encrypted)
  ├── refresh_token_enc (AES-GCM encrypted)
  └── expires_at

uploads
  ├── id (PK)
  ├── lead_id
  ├── filename, mime, size_bytes
  ├── storage_path
  └── created_at

jobs
  ├── id (PK)
  ├── lead_id
  ├── upload_id (FK → uploads.id)
  ├── status (queued|converting|transcribing|extracting|ready|failed|pushed)
  ├── progress_step
  ├── transcript_path, transcript_json
  ├── extraction_json
  ├── confidence
  ├── last_error
  ├── created_at, updated_at, pushed_at

field_mappings
  ├── id (PK)
  ├── mapping_json
  └── updated_at
```

### 5. Message Broker (Redis)

**Technology**: Redis 7

**Responsibilities**:
- Celery task queue (broker)
- Celery result backend
- Optional caching (future)

**Data Structures**:
- Lists: Task queues
- Hashes: Task metadata
- Strings: Result storage

### 6. Storage Layer

**Technology**: Local filesystem or S3

**Responsibilities**:
- Store uploaded files
- Store converted audio
- Store transcripts

**Directory Structure** (local):
```
storage/
├── uploads/
│   └── <upload_id>/
│       └── original_filename.mp4
├── audio/
│   └── job_<job_id>.wav
└── transcripts/
    └── job_<job_id>.txt
```

## Data Flow

### Upload and Process Flow

```
1. User uploads file
   └─► POST /api/uploads
       ├─► Validate file (type, size)
       ├─► Save to storage
       ├─► Create Upload record
       └─► Return upload_id

2. User starts analysis
   └─► POST /api/jobs
       ├─► Create Job record
       ├─► Enqueue Celery task
       └─► Return job_id

3. Worker processes
   └─► process_call_task(job_id)
       ├─► Update status: converting
       ├─► FFmpeg: video/audio → WAV 16kHz mono
       ├─► Update status: transcribing
       ├─► Whisper/API: WAV → text + segments
       ├─► Update status: extracting
       ├─► LLM: text → structured JSON
       ├─► Save transcript + extraction
       └─► Update status: ready

4. User views results
   └─► GET /api/jobs/{job_id}
       ├─► Load job from DB
       ├─► Read transcript file
       ├─► Parse JSON fields
       └─► Return formatted response

5. User pushes to Kommo
   └─► POST /api/jobs/{job_id}/push
       ├─► Format extraction as note
       ├─► Call Kommo API: add note
       ├─► Apply field mapping
       ├─► Call Kommo API: update fields
       ├─► Update job: pushed_at
       └─► Return success
```

### Kommo Integration Flow

```
1. Initial Setup
   └─► POST /api/settings/kommo/paste
       ├─► Encrypt tokens (AES-GCM)
       ├─► Store in kommo_connections
       └─► Return success

2. Token Refresh (automatic)
   └─► On any Kommo API call
       ├─► Check expires_at
       ├─► If expired:
       │   ├─► POST Kommo OAuth refresh
       │   ├─► Get new tokens
       │   ├─► Encrypt and store
       │   └─► Update expires_at
       └─► Proceed with API call

3. Fetch Leads
   └─► GET /api/leads
       ├─► Get KommoClient (auto-refresh)
       ├─► Call Kommo API: /api/v4/leads
       ├─► Parse response
       ├─► Transform to simplified format
       └─► Return paginated leads

4. Push Results
   └─► POST /api/jobs/{job_id}/push
       ├─► Format extraction as markdown-style text
       ├─► Call Kommo: POST /api/v4/leads/{id}/notes
       ├─► If mapping exists:
       │   ├─► Apply field mapping
       │   └─► Call Kommo: PATCH /api/v4/leads/{id}
       └─► Mark job as pushed
```

## Security Architecture

### Authentication

```
┌─────────┐
│ Browser │
└────┬────┘
     │ Store in localStorage
     │
     ▼
┌─────────────────┐
│  API Key Token  │
└────┬────────────┘
     │ Authorization: Bearer <token>
     │
     ▼
┌─────────────────────┐
│  FastAPI Middleware │
│  verify_admin_key() │
└────┬────────────────┘
     │ Match ADMIN_API_KEY
     │
     ▼
┌─────────────────┐
│  API Endpoint   │
└─────────────────┘
```

### Encryption

**Kommo Tokens**:
- Algorithm: AES-256-GCM
- Key: `APP_ENCRYPTION_KEY` (32 bytes)
- Nonce: Random 12 bytes per encryption
- Storage: `access_token_enc`, `refresh_token_enc`

**Process**:
```python
1. Encrypt
   plaintext → AES-GCM → nonce + ciphertext → base64

2. Decrypt
   base64 → nonce + ciphertext → AES-GCM → plaintext
```

### Authorization

**Single Admin Mode** (MVP):
- One global `ADMIN_API_KEY`
- All users share same access
- No user accounts or roles

**Future Enhancement**:
- User accounts with bcrypt passwords
- Role-based access control (admin, user)
- Per-user API keys
- JWT tokens with expiry

## Scalability Considerations

### Horizontal Scaling

**API**:
- Stateless design
- Can run multiple instances behind load balancer
- Session data in database, not memory

**Worker**:
- Multiple workers can process jobs concurrently
- Each job is independent
- Scale based on queue length

**Bottlenecks**:
- Database connections (use connection pooling)
- Redis connections
- LLM API rate limits

### Vertical Scaling

**When to Scale**:
- API: High request latency
- Worker: Long queue wait times
- Database: High CPU/memory usage
- Redis: High memory usage

**How to Scale**:
- Increase container CPU/memory
- Use larger database instance
- Use Redis cluster for high throughput

### Performance Optimization

**Database**:
- Add indexes on frequently queried fields (lead_id, job status)
- Use connection pooling (SQLAlchemy defaults)
- Implement query result caching for leads

**Worker**:
- Use faster-whisper instead of openai-whisper (5-10x faster)
- Process smaller audio chunks for streaming
- Cache Whisper model in memory (already done)

**Storage**:
- Use S3 with CloudFront for file serving
- Implement lifecycle policies to archive old files
- Compress transcripts before storage

## Error Handling

### API Errors

```python
try:
    # Operation
except SpecificError as e:
    raise HTTPException(status_code=400, detail="User-friendly message")
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise HTTPException(status_code=500, detail="Internal server error")
```

**Error Response Format**:
```json
{
  "detail": "Error message"
}
```

### Worker Errors

```python
try:
    # Processing step
except Exception as e:
    job.status = "failed"
    job.last_error = str(e)
    db.commit()
    logger.error(f"Job {job_id} failed: {e}", exc_info=True)
```

**Retry Strategy**:
- Currently: No automatic retry
- Future: Celery retry with exponential backoff

### Kommo API Errors

```python
- 401 Unauthorized → Refresh token and retry
- 429 Rate Limited → Sleep and retry (max 3 attempts)
- 5xx Server Error → Retry with backoff
- Other → Fail with error message
```

## Monitoring and Observability

### Logging

**Levels**:
- INFO: Normal operations (job started, completed)
- WARNING: Recoverable issues (token refresh)
- ERROR: Failures (API errors, processing failures)

**Locations**:
- API: stdout → Docker logs
- Worker: stdout → Docker logs
- Database: PostgreSQL logs

### Metrics (Future)

**Application**:
- Request rate, latency, error rate
- Job completion time, failure rate
- Queue length, worker utilization

**Infrastructure**:
- CPU, memory, disk usage
- Database connections, query time
- Redis memory, connection count

### Health Checks

**API**: `GET /health`
```json
{
  "status": "ok",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

**Database**: Connection test in health endpoint

**Worker**: Celery inspect
```bash
celery -A app.celery_app inspect active
```

## Testing Strategy

### Unit Tests

**Backend**:
```python
# Test API endpoints
def test_create_job():
    response = client.post("/api/jobs", json={...})
    assert response.status_code == 200

# Test services
def test_transcription_service():
    result = transcribe(audio_path)
    assert "text" in result
```

**Frontend**:
```typescript
// Test components
describe('LeadsPage', () => {
  it('renders leads', () => {
    render(<LeadsPage />)
    expect(screen.getByText('Leads')).toBeInTheDocument()
  })
})
```

### Integration Tests

**API + Database**:
```python
def test_job_creation_flow():
    # Create upload
    upload = create_upload(...)
    # Create job
    job = create_job(upload.id)
    # Verify in database
    assert job.status == "queued"
```

**End-to-End**:
- Upload file
- Process through worker
- Verify results
- Push to Kommo (with mock)

## Deployment Architecture

### Development
- Docker Compose
- All services on one machine
- Local storage
- No HTTPS

### Production
- Kubernetes or ECS
- Separate services
- S3 storage
- HTTPS with SSL/TLS
- Managed database and Redis
- Auto-scaling

## Future Enhancements

1. **Multi-tenancy**
   - Per-organization accounts
   - Isolated data and settings
   - Organization-level billing

2. **Real-time Updates**
   - WebSocket connection
   - Live job progress updates
   - Push notifications

3. **Advanced Analytics**
   - Dashboard with charts
   - Trend analysis across calls
   - Rep performance metrics

4. **Speaker Diarization**
   - Identify who said what
   - Separate sales rep vs customer insights

5. **Batch Processing**
   - Upload multiple files
   - Process entire folder
   - Scheduled imports

6. **API Webhooks**
   - Notify external systems on completion
   - Integration with other CRMs
   - Custom workflows








