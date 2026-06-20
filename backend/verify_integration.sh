#!/bin/bash
# Quick verification script for the integrated VendorSentry backend

echo "VendorSentry Backend Integration Verification"
echo "=============================================="
echo ""

# Test imports
echo "Testing Python imports..."
python test_integration.py
if [ $? -eq 0 ]; then
    echo "✓ All imports successful"
else
    echo "✗ Import test failed"
    exit 1
fi

echo ""
echo "Testing with pytest..."
pytest tests/ -q
if [ $? -eq 0 ]; then
    echo "✓ All tests passed"
else
    echo "✗ Some tests failed"
    exit 1
fi

echo ""
echo "=============================================="
echo "Backend integration verified successfully!"
echo ""
echo "Next steps:"
echo "1. Start Docker Desktop"
echo "2. Run: docker compose up --build"
echo "3. Visit http://localhost:8000/docs"
