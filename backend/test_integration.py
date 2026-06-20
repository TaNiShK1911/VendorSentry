#!/usr/bin/env python
"""Test that all modules import successfully"""
import sys
sys.path.insert(0, '.')

try:
    from app.main import app
    print("[OK] Main app imports successfully")

    print(f"[OK] Total routes: {len(app.routes)}")
    print("[OK] Sample routes:")
    for route in app.routes[:15]:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            methods = ','.join(route.methods) if route.methods else 'N/A'
            print(f"  {methods:10} {route.path}")

    from app.models import Alert, AlertType, AlertSeverity, RiskTier, StatusColor
    print("[OK] All models import successfully")

    from app.services.scoring.engine import score_vendor, get_latest_score
    print("[OK] Scoring engine imports successfully")

    from app.services.extraction import contract_parser
    print("[OK] Extraction services import successfully")

    print("\n[SUCCESS] All imports successful - backend integration complete!")
    print("\nNext steps:")
    print("1. Start Docker Desktop")
    print("2. Run: docker compose up --build")
    print("3. API will be available at http://localhost:8000")
    print("4. API docs at http://localhost:8000/docs")

except Exception as e:
    print(f"[ERROR] Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
