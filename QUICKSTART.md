# Quick Start Guide

Get Kommo Call Analyzer running in 5 minutes.

## Prerequisites

- Docker Desktop (or Docker + Docker Compose)
- OpenAI API key

## Steps

### 1. Clone & Navigate

```bash
git clone <your-repo-url>
cd SalesTool
```

### 2. Run Setup Script

**On Mac/Linux:**
```bash
chmod +x setup.sh
./setup.sh
```

**On Windows:**
```bash
# Copy .env.example to .env manually
copy .env.example .env

# Edit .env with your credentials

# Start services
docker-compose up -d

# Wait 30 seconds, then run migrations
docker-compose exec api alembic upgrade head
```

### 3. Configure .env

Edit `.env` and set:

```env
# Required - Create a strong password
ADMIN_API_KEY=your-secret-password-here

# Required - Generate with: python3 -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())"
APP_ENCRYPTION_KEY=<generated-key>

# Required - Your Kommo subdomain
KOMMO_BASE_URL=https://yoursubdomain.kommo.com

# Required - Get from Kommo integrations
KOMMO_CLIENT_ID=your-client-id
KOMMO_CLIENT_SECRET=your-client-secret

# Required - Your OpenAI API key
LLM_API_KEY=sk-your-openai-key-here
```

### 4. Access Application

Open http://localhost:3000 and login with your `ADMIN_API_KEY`.

### 5. Connect Kommo

1. Go to **Settings**
2. Paste your Kommo OAuth tokens:
   - Get these from your Kommo integration settings
   - Access token
   - Refresh token
   - Expiry date (ISO format: 2024-12-31T23:59:59Z)
3. Verify "Connected" status appears

### 6. Upload Your First Call

1. Go to **Leads**
2. Click on any lead
3. Upload a call recording file
4. Wait for processing to complete
5. View results and push to Kommo

## Troubleshooting

### "Invalid API key" error
- Check `ADMIN_API_KEY` in .env matches what you entered in login

### "Kommo not connected"
- Verify `KOMMO_BASE_URL` format: https://subdomain.kommo.com
- Check tokens are valid and not expired
- Go to Settings and re-paste tokens

### "Failed to connect to API"
- Ensure Docker services are running: `docker-compose ps`
- Check API logs: `docker-compose logs api`
- Restart services: `make restart`

### Worker not processing jobs
- Check worker logs: `docker-compose logs worker`
- Restart worker: `docker-compose restart worker`
- First transcription takes longer (downloads Whisper model ~150MB)

### LLM extraction fails
- Verify `LLM_API_KEY` is correct
- Check OpenAI account has credits
- View worker logs: `docker-compose logs worker`

## Next Steps

- Read [README.md](README.md) for full documentation
- See [DEPLOYMENT.md](DEPLOYMENT.md) for production deployment
- Check [ARCHITECTURE.md](ARCHITECTURE.md) to understand the system

## Need Help?

- Check logs: `make logs`
- View API docs: http://localhost:8000/docs
- See full README for detailed troubleshooting








