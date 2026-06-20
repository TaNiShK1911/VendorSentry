import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.base import Base
from app.models import Vendor

@pytest.fixture
def db_session():
    # Create an in-memory SQLite database
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)
    db = SessionLocal()
    
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def setup_test_vendor(db_session):
    vendor = Vendor(id="test-id", name="Test Vendor")
    db_session.add(vendor)
    db_session.commit()
    return vendor
