# VendorSentry - Manual Setup Instructions

## Current Status
✅ **Frontend:** Running on http://localhost:3001
⏳ **Backend:** Ready to start (needs database setup)

## Step-by-Step Backend Setup

### Step 1: Setup PostgreSQL Database

You have PostgreSQL running on port 5432. Now you need to create the database and user.

**Option A: Using pgAdmin (Recommended)**
1. Open **pgAdmin** (should be installed with PostgreSQL)
2. Connect to your PostgreSQL server
3. Right-click on "Databases" → Create → Database
   - Database name: `vendorsentry`
   - Owner: postgres (we'll change this)
4. Open Query Tool and run the SQL from `setup_database.sql`

**Option B: Using Command Line**
1. Find PostgreSQL installation (usually in `C:\Program Files\PostgreSQL\16\bin\`)
2. Open Command Prompt as Administrator
3. Navigate to PostgreSQL bin folder
4. Run:
   ```cmd
   psql -U postgres
   ```
5. Enter your postgres password
6. Copy and paste the contents of `setup_database.sql`

**Option C: Using Docker (If Available)**
```bash
docker-compose up -d postgres redis
```

### Step 2: Install Redis (Optional - for full functionality)

**Option A: Use Docker**
```bash
docker-compose up -d redis
```

**Option B: Install Redis for Windows**
- Download: https://github.com/microsoftarchive/redis/releases
- Or use Chocolatey: `choco install redis-64`
- Or use WSL: `wsl -d Ubuntu sudo service redis-server start`

**Option C: Skip Redis (Limited functionality)**
- Backend will work without Redis
- Background tasks (Celery workers) won't run
- You'll still have full API access

### Step 3: Start the Backend

**Run the startup script:**
```cmd
start_backend.bat
```

Or manually:
```cmd
cd backend
venv\Scripts\activate
alembic upgrade head
python scripts\seed.py
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Step 4: Verify Integration

Once backend is running:

1. **Check Health Endpoint**
   ```bash
   curl http://localhost:8000/health
   ```
   Should return: `{"status":"ok","service":"vendorsentry-api"}`

2. **Access API Documentation**
   Open: http://localhost:8000/docs

3. **Test Frontend Connection**
   Open: http://localhost:3001
   - You should see the login page
   - Click login (if seeded, use demo credentials)

## Troubleshooting

### "Database connection failed"
- ✓ PostgreSQL is running: `netstat -ano | findstr 5432`
- ✓ User exists: Run `setup_database.sql`
- ✓ Check `backend/.env` has correct DATABASE_URL

### "Port 8000 already in use"
- Find process: `netstat -ano | findstr 8000`
- Kill process: `taskkill /PID <pid> /F`

### "Cannot connect to Redis"
- Skip Redis by commenting out Celery imports in `backend/app/main.py`
- Or install Redis (see Step 2)

### "Module not found" errors
```bash
cd backend
venv\Scripts\activate
pip install -r requirements.txt
```

## Files Created

- ✅ `setup_database.sql` - SQL script to create database
- ✅ `start_backend.bat` - Windows batch script to start backend
- ✅ `QUICK_START.md` - Comprehensive setup guide
- ✅ `INTEGRATION_STATUS.md` - Integration documentation
- ✅ `app/.env` - Frontend environment (configured)
- ✅ `backend/venv/` - Python virtual environment (ready)

## Quick Reference

### Check What's Running
```bash
# Frontend
curl http://localhost:3001

# Backend
curl http://localhost:8000/health

# PostgreSQL
netstat -ano | findstr 5432

# Redis
netstat -ano | findstr 6379
```

### Start Services
```bash
# Frontend (already running)
cd app && npm run dev

# Backend
start_backend.bat

# Or use Docker for everything
docker-compose up -d
```

### Access Points
- Frontend: http://localhost:3001
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- API Health: http://localhost:8000/health

---

## Next Steps

1. ✅ Frontend is already running
2. ⏳ Setup database using `setup_database.sql`
3. ⏳ Run `start_backend.bat`
4. ✅ Access the application at http://localhost:3001

Need help? Check the error messages and see the Troubleshooting section above.
