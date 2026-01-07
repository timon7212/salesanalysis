# Deployment Guide

## Local Development Setup

### Prerequisites
- Docker Desktop installed and running
- Git
- Text editor

### Steps

1. **Clone Repository**
```bash
git clone <repository-url>
cd SalesTool
```

2. **Configure Environment**
```bash
# Copy example env
cp .env.example .env

# Edit .env with your credentials
# REQUIRED fields:
# - ADMIN_API_KEY (create a strong password)
# - APP_ENCRYPTION_KEY (generate with: python3 -c "import os, base64; print(base64.b64encode(os.urandom(32)).decode())")
# - KOMMO_BASE_URL, KOMMO_CLIENT_ID, KOMMO_CLIENT_SECRET
# - LLM_API_KEY (OpenAI API key)
```

3. **Start Services**
```bash
make up
```

Wait 30-60 seconds for all services to start.

4. **Verify Installation**
- Web UI: http://localhost:3000
- API: http://localhost:8000/health
- API Docs: http://localhost:8000/docs

5. **Login**
Use the `ADMIN_API_KEY` from your `.env` file to login at http://localhost:3000/login

## Production Deployment

### AWS Deployment (Recommended)

#### Architecture
- **Frontend**: AWS Amplify or Vercel
- **API**: ECS Fargate or App Runner
- **Worker**: ECS Fargate
- **Database**: RDS PostgreSQL
- **Cache**: ElastiCache Redis
- **Storage**: S3

#### Steps

1. **Setup Infrastructure**

Create RDS PostgreSQL instance:
```bash
aws rds create-db-instance \
  --db-instance-identifier kommo-analyzer-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --master-username admin \
  --master-user-password <password> \
  --allocated-storage 20
```

Create ElastiCache Redis:
```bash
aws elasticache create-cache-cluster \
  --cache-cluster-id kommo-analyzer-redis \
  --cache-node-type cache.t3.micro \
  --engine redis \
  --num-cache-nodes 1
```

Create S3 bucket:
```bash
aws s3 mb s3://kommo-analyzer-storage
```

2. **Build and Push Docker Images**

```bash
# API
cd apps/api
docker build -t kommo-analyzer-api:latest .
docker tag kommo-analyzer-api:latest <ecr-repo>/kommo-analyzer-api:latest
docker push <ecr-repo>/kommo-analyzer-api:latest

# Worker
cd ../worker
docker build -t kommo-analyzer-worker:latest .
docker tag kommo-analyzer-worker:latest <ecr-repo>/kommo-analyzer-worker:latest
docker push <ecr-repo>/kommo-analyzer-worker:latest
```

3. **Deploy API to ECS**

Create task definition with:
- Container: `kommo-analyzer-api:latest`
- Environment variables from Secrets Manager
- Port mapping: 8000
- Health check: `/health`

4. **Deploy Worker to ECS**

Create task definition with:
- Container: `kommo-analyzer-worker:latest`
- Environment variables from Secrets Manager
- No port mapping (internal only)

5. **Deploy Frontend**

Option A - Vercel:
```bash
cd apps/web
vercel --prod
```

Option B - AWS Amplify:
- Connect GitHub repo
- Build settings: `npm run build`
- Environment variables: `NEXT_PUBLIC_API_URL`

6. **Configure DNS**
- Point domain to CloudFront/ALB
- Setup SSL certificate

7. **Run Migrations**
```bash
# SSH into API container or run task
docker exec -it <api-container> alembic upgrade head
```

### Docker Swarm Deployment

1. **Initialize Swarm**
```bash
docker swarm init
```

2. **Deploy Stack**
```bash
docker stack deploy -c docker-compose.yml kommo
```

3. **Scale Workers**
```bash
docker service scale kommo_worker=3
```

### Kubernetes Deployment

See `k8s/` directory for Kubernetes manifests (if available).

## Environment Variables for Production

```env
# Security - USE SECRETS MANAGER!
ADMIN_API_KEY=<from-secrets-manager>
APP_ENCRYPTION_KEY=<from-secrets-manager>

# Database
DATABASE_URL=postgresql://user:pass@rds-endpoint:5432/dbname

# Redis
REDIS_URL=redis://elasticache-endpoint:6379/0

# Storage
STORAGE_MODE=s3
S3_BUCKET=kommo-analyzer-storage
S3_REGION=us-east-1

# Kommo
KOMMO_BASE_URL=https://yoursubdomain.kommo.com
KOMMO_CLIENT_ID=<from-secrets-manager>
KOMMO_CLIENT_SECRET=<from-secrets-manager>
KOMMO_REDIRECT_URI=https://yourdomain.com/settings/kommo/callback

# LLM
LLM_PROVIDER=openai
LLM_API_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=<from-secrets-manager>
LLM_MODEL=gpt-4-turbo-preview

# Limits
MAX_UPLOAD_MB=200

# Frontend
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
```

## Security Checklist

- [ ] Changed default `ADMIN_API_KEY`
- [ ] Generated secure `APP_ENCRYPTION_KEY`
- [ ] All secrets in secrets manager (not .env)
- [ ] HTTPS/TLS enabled
- [ ] CORS restricted to frontend domain
- [ ] Database not publicly accessible
- [ ] Redis not publicly accessible
- [ ] S3 bucket not public
- [ ] CloudWatch logging enabled
- [ ] Backup strategy configured

## Monitoring

### CloudWatch Metrics to Monitor
- API response times
- Worker task completion rate
- Celery queue length
- Database connections
- Redis memory usage
- S3 storage usage

### CloudWatch Alarms
- API error rate > 5%
- Worker failures > 10/hour
- Database CPU > 80%
- Redis memory > 80%

### Logging
- Application logs to CloudWatch
- Access logs to S3
- Error tracking with Sentry

## Backup Strategy

1. **Database**
   - Automated RDS snapshots (daily)
   - Point-in-time recovery enabled
   - Retention: 30 days

2. **Files**
   - S3 versioning enabled
   - Lifecycle policy: archive to Glacier after 90 days
   - Retention: 1 year

3. **Configuration**
   - Infrastructure as Code (Terraform/CloudFormation)
   - Secrets in AWS Secrets Manager
   - Version control for all code

## Scaling

### Horizontal Scaling
```bash
# Scale API
aws ecs update-service --service kommo-api --desired-count 3

# Scale Workers
aws ecs update-service --service kommo-worker --desired-count 5
```

### Vertical Scaling
- Increase RDS instance size
- Increase ECS task CPU/memory
- Increase Redis instance size

### Auto-Scaling
Configure ECS Service Auto Scaling based on:
- CPU utilization > 70%
- Memory utilization > 80%
- Celery queue length > 100

## Cost Optimization

1. **Compute**
   - Use Spot instances for workers
   - Use Graviton2 (ARM) instances
   - Scale down during off-hours

2. **Storage**
   - Use S3 Intelligent-Tiering
   - Delete old transcripts after 90 days
   - Compress stored files

3. **Database**
   - Use Aurora Serverless v2 for variable load
   - Enable automated pause for dev/staging

## Troubleshooting Production

### High API Latency
- Check RDS performance insights
- Review slow query logs
- Add database indexes
- Enable API caching

### Worker Backlog
- Scale up worker count
- Check for failed tasks
- Review worker logs
- Optimize transcription settings

### Out of Memory
- Increase task memory limits
- Review memory leaks in logs
- Scale to larger instance types

### High Costs
- Review CloudWatch cost insights
- Delete unused resources
- Optimize storage with lifecycle policies
- Use Reserved Instances for stable workloads








