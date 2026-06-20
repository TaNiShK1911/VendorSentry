-- VendorSentry Database Setup
-- Run these commands in pgAdmin or PostgreSQL command line

-- Create user
CREATE USER vendorsentry WITH PASSWORD 'vendorsentry';

-- Create database
CREATE DATABASE vendorsentry OWNER vendorsentry;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE vendorsentry TO vendorsentry;

-- Connect to vendorsentry database and grant schema privileges
\c vendorsentry
GRANT ALL ON SCHEMA public TO vendorsentry;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO vendorsentry;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO vendorsentry;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO vendorsentry;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO vendorsentry;
