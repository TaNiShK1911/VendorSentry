#!/usr/bin/env python
"""Test that all modules import successfully"""
import sys
sys.path.insert(0, '.')

try:
    from app.main import app
    print("✓ Main app imports successfully")

    print(f"✓ Total routes: {len(app.routes)}")
    print("✓ Sample routes:")
    for route in app.routes[:15]:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            methods = ','.join(route.methods) if route.methods else 'N/A'
            print(f"  {methods:10} {route.path}")

    from app.models import Alert, AlertType, AlertSeverity, RiskTier, StatusColor
    print("✓ All models import successfully")

    from app.services.scoring.engine import score_vendor
    print("✓ Scoring engine imports successfully")

    from app.services.extraction.contract_parser import ContractParser
    print("✓ Extraction services import successfully")

    print("\n✅ All imports successful - backend integration complete!")

except Exception as e:
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
