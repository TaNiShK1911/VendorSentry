#!/bin/bash
# Quick verification script - checks if all key files exist

echo "VendorSentry Dev B Implementation Verification"
echo "=============================================="
echo ""

# Check critical files
files=(
    "backend/app/main.py"
    "backend/app/api/vendors.py"
    "backend/app/api/scoring.py"
    "backend/app/api/alerts.py"
    "backend/app/api/extraction.py"
    "backend/app/api/reports.py"
    "backend/app/api/auth.py"
    "backend/app/models/vendor.py"
    "backend/app/schemas/vendor.py"
    "backend/app/services/scoring/engine.py"
    "backend/app/services/alerts/dedup.py"
    "backend/app/services/monitoring/cert_watcher.py"
    "backend/app/services/monitoring/breach_watcher.py"
    "backend/scripts/seed.py"
    "docker-compose.yml"
    "backend/Dockerfile"
    "backend/requirements.txt"
)

missing=0
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file"
    else
        echo "❌ MISSING: $file"
        ((missing++))
    fi
done

echo ""
echo "=============================================="
if [ $missing -eq 0 ]; then
    echo "✅ All critical files present!"
    echo ""
    echo "To start the application:"
    echo "  make dev"
    echo ""
    echo "Or manually:"
    echo "  docker compose up --build -d"
    echo "  docker compose exec api python scripts/seed.py"
    echo ""
    echo "API will be available at http://localhost:8000"
    echo "Docs at http://localhost:8000/docs"
    exit 0
else
    echo "❌ $missing file(s) missing!"
    exit 1
fi
