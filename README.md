# Kommo Call Analyzer MVP

A full-stack web application for analyzing sales call recordings with AI, integrating with Kommo CRM.

## Features

- **Kommo Integration**: OAuth2 token management, fetch leads, push analysis results back to Kommo
- **File Upload**: Support for audio (MP3, WAV, M4A) and video (MP4, MOV) files up to 200MB
- **Audio Processing**: Automatic audio extraction from video using FFmpeg
- **Transcription**: Pluggable transcription (local Whisper or API-based)
- **LLM Extraction**: Structured insights extraction using OpenAI or compatible LLM
  - Call summary (bullet points)
  - Concerns with severity (1-5), evidence quotes, and timestamps
  - Next steps with owner and due dates
  - Qualification (budget, timeline, decision maker, need, score 0-100)
  - Confidence score (0-1)
- **Background Processing**: Celery workers with Redis for async job processing
- **Custom Field Mapping**: Map extracted fields to Kommo custom fields
- **Modern UI**: Next.js 14 with TypeScript, Tailwind CSS, and shadcn/ui components

## Tech Stack

### Frontend
- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Components**: shadcn/ui (Radix UI primitives)
- **Icons**: Lucide React

### Backend
- **API**: FastAPI (Python)
- **Task Queue**: Celery with Redis broker
- **Database**: PostgreSQL
- **ORM**: SQLAlchemy
- **Migrations**: Alembic
- **Transcription**: faster-whisper / openai-whisper (local) or API
- **Audio Processing**: FFmpeg

### Infrastructure
- **Containerization**: Docker & Docker Compose
- **Services**: Web, API, Worker, Redis, PostgreSQL

## Prerequisites

- Docker & Docker Compose
- Node.js 20+ (for local development)
- Python 3.11+ (for local development)

## Quick Start

### 1. Clone and Setup

```bash
git clone <your-repo>
cd SalesTool
```

### 2. Configure Environment

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# Security (REQUIRED)
ADMIN_API_KEY=your-secret-admin-key-here
APP_ENCRYPTION_KEY=your-32-byte-base64-encoded-key

# Database (auto-configured for Docker)
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/kommo_call_analyzer

# Redis (auto-configured for Docker)
REDIS_URL=redis://redis:6379/0

# Storage
STORAGE_MODE=local
LOCAL_STORAGE_PATH=./storage

# Kommo Integration (REQUIRED)
KOMMO_BASE_URL=https://yoursubdomain.kommo.com
KOMMO_CLIENT_ID=your-kommo-client-id
KOMMO_CLIENT_SECRET=your-kommo-client-secret
KOMMO_REDIRECT_URI=http://localhost:3000/settings/kommo/callback

# Transcription
TRANSCRIBE_PROVIDER=whisper_local

# LLM (REQUIRED)
LLM_PROVIDER=openai
LLM_API_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-your-openai-api-key
LLM_MODEL=gpt-4-turbo-preview

# Upload Limits
MAX_UPLOAD_MB=200

# Next.js (auto-configured)
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. Generate Encryption Key

```bash
python3 -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"
```

Use the output as your `APP_ENCRYPTION_KEY`.

### 4. Start All Services

```bash
make up
```

This will:
- Start PostgreSQL and Redis
- Build and start the API, Worker, and Web services
- Run database migrations automatically

Wait for all services to be healthy (30-60 seconds).

### 5. Access the Application

Open your browser to:
- **Web UI**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs

Login with your `ADMIN_API_KEY`.

## Usage Workflow

### 1. Configure Kommo Integration

1. Navigate to **Settings** in the UI
2. In the **Kommo Integration** tab:
   - Option A: Use OAuth (future enhancement)
   - Option B (MVP): Paste your access token, refresh token, and expiry date
3. Verify connection shows "Connected" status

### 2. View Leads

1. Navigate to **Leads**
2. Browse or search for leads from your Kommo account
3. Click **View** on any lead

### 3. Upload and Analyze Call

1. On the lead detail page, click the upload area
2. Select an audio or video file (MP3, WAV, M4A, MP4, MOV)
3. Wait for upload to complete
4. You'll be redirected to the job detail page

### 4. Monitor Processing

The job will progress through stages:
- **Queued**: Waiting to start
- **Converting**: Extracting/converting audio
- **Transcribing**: Speech-to-text processing
- **Extracting**: LLM analyzing transcript
- **Ready**: Complete and ready to push

The page auto-refreshes every 3 seconds while processing.

### 5. Review Results

Once ready, view two tabs:
- **Extraction**: Structured insights (summary, concerns, next steps, qualification)
- **Transcript**: Full text transcript

### 6. Push to Kommo

Click **Push to Kommo** to:
- Create a formatted note in the lead
- Update custom fields (if mapping configured)

### 7. Configure Field Mapping (Optional)

1. Go to **Settings** → **Field Mapping**
2. Enter Kommo custom field IDs for each extraction field
3. Save mapping

Example:
```json
{
  "qualification.score": "12345",
  "qualification.budget": "12346",
  "qualification.timeline": "12347",
  "confidence": "12348"
}
```

## Development

### Backend Development

```bash
# Enter API container
make shell-api

# Run migrations
make db-migrate

# Create new migration
make create-migration msg="add_new_field"

# View logs
make logs
```

### Frontend Development

```bash
cd apps/web
npm install
npm run dev
```

The Next.js dev server will run on http://localhost:3000 with hot reload.

### Database Access

```bash
# Connect to PostgreSQL
make shell-db

# Reset database (WARNING: deletes all data)
make db-reset
```

## Architecture

### Data Flow

1. **Upload**: User uploads file → API saves to storage → Creates Upload record
2. **Job Creation**: API creates Job record → Enqueues Celery task
3. **Worker Processing**:
   - Converts file to 16kHz mono WAV
   - Transcribes audio (Whisper or API)
   - Extracts insights (LLM)
   - Saves results to database
4. **Results**: User views results in UI
5. **Push**: User clicks Push → API sends note + fields to Kommo

### Database Schema

```
kommo_connections
  - Stores encrypted OAuth tokens
  - Auto-refreshes expired tokens

uploads
  - File metadata and storage paths

jobs
  - Processing status and progress
  - Links to upload and lead
  - Stores transcript and extraction JSON

field_mappings
  - Custom field mapping configuration

lead_cache (optional)
  - Caches lead data from Kommo
```

### Security

- **API Authentication**: Bearer token (ADMIN_API_KEY) on all protected endpoints
- **Token Encryption**: Kommo tokens encrypted at rest using AES-GCM
- **CORS**: Configured for frontend origin
- **No User Accounts**: Single admin key for MVP simplicity

## API Endpoints

### Health
- `GET /health` - Health check (no auth)

### Leads
- `GET /api/leads?query=&page=&page_size=` - List leads with pagination
- `GET /api/leads/{lead_id}` - Get single lead

### Uploads
- `POST /api/uploads` - Upload file (multipart form)

### Jobs
- `POST /api/jobs` - Create processing job
- `GET /api/jobs/{job_id}` - Get job status and results
- `POST /api/jobs/{job_id}/push` - Push results to Kommo

### Settings
- `GET /api/settings/kommo/info` - Get connection status
- `POST /api/settings/kommo/paste` - Paste OAuth tokens
- `GET /api/settings/mapping` - Get field mapping
- `PUT /api/settings/mapping` - Update field mapping

Full API documentation: http://localhost:8000/docs

## Makefile Commands

```bash
make up          # Start all services
make down        # Stop all services
make logs        # View logs (all services)
make restart     # Restart all services
make clean       # Stop and remove volumes (WARNING: deletes data)
make db-migrate  # Run database migrations
make db-reset    # Reset database and migrations
make shell-api   # Open shell in API container
make shell-worker # Open shell in worker container
make shell-db    # Open PostgreSQL shell
```

## Troubleshooting

### Kommo Connection Issues

**Problem**: "Kommo not connected" error

**Solutions**:
1. Verify `KOMMO_BASE_URL` format: `https://yoursubdomain.kommo.com`
2. Check tokens are valid and not expired
3. Verify Kommo API access in your account
4. Check API logs: `docker-compose logs api`

### Transcription Fails

**Problem**: Job stuck in "transcribing" or fails with error

**Solutions**:
1. Check worker logs: `docker-compose logs worker`
2. Verify audio file is valid (play it locally)
3. For `whisper_local`: First run takes time downloading model (~150MB)
4. For `api` mode: Verify `TRANSCRIBE_API_URL` and `TRANSCRIBE_API_KEY`

### LLM Extraction Fails

**Problem**: Job fails at "extracting" stage

**Solutions**:
1. Verify `LLM_API_KEY` is valid
2. Check API rate limits
3. View worker logs for detailed error
4. Ensure model supports JSON mode (`gpt-4-turbo-preview` or `gpt-3.5-turbo-1106`)

### Upload Size Limit

**Problem**: "File too large" error

**Solutions**:
1. Increase `MAX_UPLOAD_MB` in `.env`
2. Check available disk space
3. Consider using S3 storage for large files

### Worker Not Processing

**Problem**: Jobs stay in "queued" status

**Solutions**:
1. Check worker is running: `docker-compose ps worker`
2. Restart worker: `docker-compose restart worker`
3. Check Redis connection: `docker-compose logs redis`
4. View worker logs: `docker-compose logs worker`

### Database Migration Errors

**Problem**: Migration fails or tables missing

**Solutions**:
```bash
# Reset database (WARNING: deletes all data)
make db-reset

# Or manually run migrations
make db-migrate
```

## Advanced Configuration

### S3 Storage (Optional)

To use S3-compatible storage instead of local disk:

```env
STORAGE_MODE=s3
S3_ENDPOINT=https://s3.amazonaws.com
S3_BUCKET=kommo-recordings
S3_ACCESS_KEY=your-access-key
S3_SECRET_KEY=your-secret-key
S3_REGION=us-east-1
```

Note: S3 implementation is stubbed and requires completion.

### External Transcription API

To use an external transcription service:

```env
TRANSCRIBE_PROVIDER=api
TRANSCRIBE_API_URL=https://api.transcription-service.com/v1/transcribe
TRANSCRIBE_API_KEY=your-api-key
```

API should accept multipart file upload and return:
```json
{
  "text": "full transcript",
  "segments": [
    {"start": 0.0, "end": 5.2, "text": "Hello", "speaker": "Agent"}
  ]
}
```

### Alternative LLM Provider

To use a different LLM (compatible with OpenAI API):

```env
LLM_PROVIDER=generic
LLM_API_BASE_URL=https://your-llm-api.com/v1
LLM_API_KEY=your-key
LLM_MODEL=your-model-name
```

## Production Deployment

For production deployment, consider:

1. **Security**:
   - Use strong `ADMIN_API_KEY` and `APP_ENCRYPTION_KEY`
   - Enable HTTPS/TLS
   - Restrict CORS origins
   - Use secrets management (AWS Secrets Manager, HashiCorp Vault)

2. **Scaling**:
   - Run multiple worker instances
   - Use managed PostgreSQL (RDS, CloudSQL)
   - Use managed Redis (ElastiCache, MemoryStore)
   - Deploy API behind load balancer

3. **Storage**:
   - Use S3 or equivalent for file storage
   - Enable S3 lifecycle policies for cleanup

4. **Monitoring**:
   - Add application monitoring (Sentry, DataDog)
   - Set up log aggregation (CloudWatch, ELK)
   - Monitor Celery queue lengths

5. **Backups**:
   - Automated PostgreSQL backups
   - S3 bucket versioning

## Sample Extraction Output

```json
{
  "call_summary": [
    "Customer inquired about enterprise plan features",
    "Discussed implementation timeline of 2-3 months",
    "Customer has budget allocated for Q1"
  ],
  "concerns": [
    {
      "type": "pricing",
      "severity": 3,
      "detail": "Customer mentioned competitor pricing is 20% lower",
      "evidence_quotes": [
        {"text": "Your competitor is offering similar features at $8k/month", "timestamp": "05:32"}
      ]
    }
  ],
  "next_steps": [
    {
      "action": "Send detailed pricing breakdown and ROI analysis",
      "owner": "sales rep",
      "suggested_due_days": 2
    },
    {
      "action": "Schedule technical demo with CTO",
      "owner": "customer",
      "suggested_due_days": 7
    }
  ],
  "qualification": {
    "budget": "confirmed",
    "timeline": "2-3 months, starting Q1",
    "decision_maker": "VP of Engineering (John Smith)",
    "need": "Replace legacy CRM system, improve sales pipeline visibility",
    "score": 85
  },
  "confidence": 0.92
}
```

## License

Proprietary - All rights reserved

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review logs: `make logs`
3. Check API docs: http://localhost:8000/docs
4. Contact development team

---

**Built with ❤️ using Next.js, FastAPI, and OpenAI**








