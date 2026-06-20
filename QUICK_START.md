# VendorSentry - Quick Start Guide

## ✅ What's Already Working

### Frontend
- **Status:** ✅ RUNNING
- **URL:** http://localhost:3001
- **Technology:** React + Vite + TypeScript
- **API Configuration:** Points to http://localhost:8000/api/v1

### Backend Setup
- **Python Environment:** ✅ Created with all dependencies
- **Location:** `backend/venv/`
- **Dependencies:** FastAPI, SQLAlchemy, Celery, Anthropic SDK, etc.

## ❌ What's Blocking the Backend

### 1. Docker Desktop Not Running
The project uses Docker Compose for:
- **PostgreSQL** (database) - port 5432
- **Redis** (cache/queue) - port 6379

### 2. Database Issue
- Local PostgreSQL detected on port 5432
- But missing user `vendorsentry` / database `vendorsentry`

## 🚀 Solution Options

### OPTION A: Use Docker (Recommended - Easiest)

**Step 1: Start Docker Desktop**
- Open Docker Desktop application on Windows
- Wait for it to fully start (icon should be green)

**Step 2: Start All Services**
```bash
cd "C:\Users\TANISHK JI\OneDrive\Desktop\VendorSentry"
docker-compose up -d
```

This single command will:
- Start PostgreSQL with correct user/database
- Start Redis
- Start FastAPI backend on port 8000
- Run database migrations
- Seed sample data
- Start Celery workers for background tasks

**Step 3: Access the App**
- Frontend: http://localhost:3001
- Backend API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

---

### OPTION B: Use Local PostgreSQL (More Complex)

If you want to use your existing PostgreSQL:

**Step 1: Create Database and User**
```sql
-- Connect to PostgreSQL as admin user
psql -U postgres

-- Create user and database
CREATE USER vendorsentry WITH PASSWORD 'vendorsentry';
CREATE DATABASE vendorsentry OWNER vendorsentry;
GRANT ALL PRIVILEGES ON DATABASE vendorsentry TO vendorsentry;
```

**Step 2: Install Redis for Windows**
Download from: https://github.com/microsoftarchive/redis/releases
Or use Chocolatey: `choco install redis-64`

**Step 3: Start Redis**
```bash
redis-server
```

**Step 4: Run Migrations**
```bash
cd "C:\Users\TANISHK JI\OneDrive\Desktop\VendorSentry\backend"
venv/Scripts/alembic upgrade head
```

**Step 5: Seed Database (Optional)**
```bash
cd "C:\Users\TANISHK JI\OneDrive\Desktop\VendorSentry\backend"
venv/Scripts/python scripts/seed.py
```

**Step 6: Start Backend**
```bash
cd "C:\Users\TANISHK JI\OneDrive\Desktop\VendorSentry\backend"
venv/Scripts/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

### OPTION C: Backend-Free Testing

Test the frontend UI without backend:
- Frontend is already running on http://localhost:3001
- You'll see login page and UI components
- API calls will fail (expected without backend)

---

## 📋 Current Status Summary

| Component | Status | Port | Notes |
|-----------|--------|------|-------|
| Frontend (React) | ✅ Running | 3001 | Ready to use |
| Backend (FastAPI) | ⏳ Waiting | 8000 | Needs Docker or manual setup |
| PostgreSQL | ❌ Not ready | 5432 | Local instance exists but not configured |
| Redis | ❌ Not running | 6379 | Required for Celery tasks |
| Celery Workers | ❌ Not started | - | Needs Redis |

## 🎯 Recommended Next Steps

**If you want the full experience:**
1. Start Docker Desktop (takes ~1 minute)
2. Run: `docker-compose up -d`
3. Access http://localhost:3001

**If you just want to see the UI:**
- Frontend is already running at http://localhost:3001
- Login will fail without backend (expected)

**If you need help:**
- Check Docker status: `docker ps`
- Check backend logs: `docker-compose logs -f api`
- Check all services: `docker-compose ps`

## 🔧 Useful Commands

### Check What's Running
```bash
# Check if Docker is running
docker ps

# Check ports in use
netstat -ano | findstr "8000 5432 6379"

# Check frontend is running
curl http://localhost:3001

# Check backend health (when running)
curl http://localhost:8000/health
```

### Docker Commands
```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f

# Restart a service
docker-compose restart api

# Clean everything and start fresh
docker-compose down -v
docker-compose up -d
```

### Backend Direct Commands (without Docker)
```bash
# Activate virtual environment
cd backend
venv\Scripts\activate

# Run migrations
alembic upgrade head

# Seed data
python scripts/seed.py

# Start server
uvicorn app.main:app --reload

# Run tests
pytest -v
```

## 📁 Important Files

- **Frontend config:** `app/.env` (already configured)
- **Backend config:** `backend/.env` (already exists)
- **Docker config:** `docker-compose.yml`
- **API documentation:** See `BACKEND_INTEGRATION.md`
- **This guide:** `QUICK_START.md`

---

**Current Recommendation:** Start Docker Desktop and run `docker-compose up -d` for the easiest setup.
