#!/bin/bash

echo "==================================="
echo "Kommo Call Analyzer - Quick Setup"
echo "==================================="
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop and try again."
    exit 1
fi

echo "✅ Docker is running"

# Check if .env exists
if [ ! -f .env ]; then
    echo ""
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    echo "✅ Created .env file"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and configure:"
    echo "   - ADMIN_API_KEY (create a strong password)"
    echo "   - APP_ENCRYPTION_KEY (run: python3 -c \"import os, base64; print(base64.b64encode(os.urandom(32)).decode())\")"
    echo "   - KOMMO_BASE_URL, KOMMO_CLIENT_ID, KOMMO_CLIENT_SECRET"
    echo "   - LLM_API_KEY (your OpenAI API key)"
    echo ""
    read -p "Press Enter to continue after editing .env..."
else
    echo "✅ .env file exists"
fi

# Generate encryption key if needed
if grep -q "your-32-byte-base64-encoded-key" .env 2>/dev/null; then
    echo ""
    echo "Generating APP_ENCRYPTION_KEY..."
    NEW_KEY=$(python3 -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())")
    sed -i.bak "s|your-32-byte-base64-encoded-key|$NEW_KEY|g" .env
    rm .env.bak 2>/dev/null
    echo "✅ Generated encryption key"
fi

echo ""
echo "Starting services with Docker Compose..."
echo ""

# Start services
docker-compose up -d

echo ""
echo "Waiting for services to be healthy (30 seconds)..."
sleep 30

echo ""
echo "Running database migrations..."
docker-compose exec -T api alembic upgrade head

echo ""
echo "==================================="
echo "✅ Setup Complete!"
echo "==================================="
echo ""
echo "Access the application:"
echo "  Web UI:   http://localhost:3000"
echo "  API:      http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
echo ""
echo "Login with your ADMIN_API_KEY from .env"
echo ""
echo "Useful commands:"
echo "  make logs     - View all logs"
echo "  make down     - Stop services"
echo "  make restart  - Restart services"
echo ""








