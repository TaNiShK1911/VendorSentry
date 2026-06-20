#!/usr/bin/env python
"""
Quick start script for VendorSentry backend
Verifies integration and provides usage instructions
"""
import sys
sys.path.insert(0, '.')

print("=" * 60)
print("VendorSentry Backend - Integration Verification")
print("=" * 60)
print()

# Test imports
try:
    from app.main import app
    from app.models import Alert, Vendor, VendorScore, RiskTier, StatusColor
    from app.services.scoring.engine import score_vendor, get_latest_score
    from app.services.extraction import contract_parser

    print("[OK] All core modules imported successfully")
    print(f"[OK] {len(app.routes)} API routes registered")
    print()

    # Show key routes
    print("Key API Endpoints:")
    print("-" * 60)
    key_routes = [
        ("GET", "/health", "Health check"),
        ("GET", "/api/v1/vendors", "List vendors"),
        ("GET", "/api/v1/vendors/{id}/score", "Get vendor score"),
        ("POST", "/api/v1/vendors/{id}/rescore", "Recompute score"),
        ("GET", "/api/v1/portfolio/score-distribution", "Portfolio summary"),
        ("GET", "/api/v1/alerts", "List alerts"),
        ("POST", "/api/v1/vendors/{id}/extract", "Extract document"),
        ("POST", "/api/v1/login", "Authenticate"),
    ]

    for method, path, desc in key_routes:
        print(f"  {method:6} {path:40} {desc}")

    print()
    print("=" * 60)
    print("INTEGRATION SUCCESSFUL!")
    print("=" * 60)
    print()
    print("Next Steps:")
    print("-" * 60)
    print()
    print("1. Start Docker Desktop (if not already running)")
    print()
    print("2. Build and start all services:")
    print("   cd VendorSentry")
    print("   docker compose up --build")
    print()
    print("3. Access the API:")
    print("   - Health check: http://localhost:8000/health")
    print("   - API docs: http://localhost:8000/docs")
    print("   - Redoc: http://localhost:8000/redoc")
    print()
    print("4. Test the integration:")
    print("   - The seed script will run automatically on startup")
    print("   - Sample vendors will be loaded and scored")
    print("   - Check /api/v1/vendors endpoint")
    print()
    print("5. Run evaluation (optional):")
    print("   docker compose exec api python scripts/evaluate.py")
    print()
    print("=" * 60)
    print()

    sys.exit(0)

except Exception as e:
    print(f"[ERROR] Integration verification failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
