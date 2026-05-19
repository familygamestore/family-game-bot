#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
import secrets
import asyncpg
import json

# ====================================================================================================
# DATABASE CONFIGURATION
# ====================================================================================================
DATABASE_URL = 'postgresql://postgres:postgres123@localhost:5432/botdb'

# Redis - Optional, skip if not available
try:
    import redis
    redis_client = redis.from_url('redis://localhost:6379', decode_responses=True)
    print("✅ Redis connected")
except:
    redis_client = None
    print("⚠️  Redis not available, running without cache")

# ====================================================================================================
# DATABASE FUNCTIONS
# ====================================================================================================
async def init_db():
    """Initialize database tables"""
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        # Create licenses table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS licenses (
                id SERIAL PRIMARY KEY,
                license_key TEXT UNIQUE NOT NULL,
                plan TEXT NOT NULL,
                duration_days INTEGER NOT NULL,
                created_by TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                used_by TEXT,
                used_at TIMESTAMP,
                is_used BOOLEAN DEFAULT FALSE,
                expires_at TIMESTAMP
            )
        ''')
        
        # Create servers table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS servers (
                id SERIAL PRIMARY KEY,
                server_id TEXT UNIQUE NOT NULL,
                server_name TEXT NOT NULL,
                owner_id TEXT NOT NULL,
                license_key TEXT,
                license_expires TIMESTAMP,
                joined_at TIMESTAMP DEFAULT NOW(),
                last_active TIMESTAMP DEFAULT NOW()
            )
        ''')
        
        # Create usage_stats table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS usage_stats (
                id SERIAL PRIMARY KEY,
                server_id TEXT NOT NULL,
                command_name TEXT,
                user_id TEXT,
                recorded_at TIMESTAMP DEFAULT NOW()
            )
        ''')
        
        await conn.close()
        print("✅ Database tables created/verified")
        return True
    except Exception as e:
        print(f"❌ Database init error: {e}")
        return False

# ====================================================================================================
# LIFESPAN EVENT HANDLER (Modern FastAPI)
# ====================================================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting API Server...")
    print(f"📊 Database URL: {DATABASE_URL}")
    
    # Test database connection
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        await conn.close()
        print("✅ Database connection successful!")
        
        # Initialize tables
        await init_db()
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("💡 Make sure PostgreSQL is running and database 'botdb' exists")
        print("   Run: psql -U postgres -c 'CREATE DATABASE botdb;'")
    
    yield  # Server runs here
    
    # Shutdown
    print("🛑 API Server shutting down...")
    if redis_client:
        redis_client.close()
        print("✅ Redis connection closed")

# ====================================================================================================
# FASTAPI APP
# ====================================================================================================
app = FastAPI(
    title="Family Game Store API", 
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ====================================================================================================
# MODELS
# ====================================================================================================
class LicenseVerifyRequest(BaseModel):
    license_key: str
    server_id: str

class LicenseVerifyResponse(BaseModel):
    valid: bool
    plan: Optional[str] = None
    expires: Optional[str] = None
    features: Optional[dict] = None
    error: Optional[str] = None

class GenerateLicenseRequest(BaseModel):
    plan: str
    duration: int = 30
    created_by: str

class UsageReportRequest(BaseModel):
    license_key: str
    server_id: str
    command: Optional[str] = None
    user_count: int = 0
    message_count: int = 0
    invite_count: int = 0

# ====================================================================================================
# API ENDPOINTS
# ====================================================================================================
@app.get("/")
async def root():
    return {"message": "Family Game Store API is running", "status": "online"}

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    db_ok = False
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        await conn.close()
        db_ok = True
    except:
        pass
    
    redis_ok = redis_client is not None and redis_client.ping() if redis_client else False
    
    return {
        "status": "healthy",
        "database": "connected" if db_ok else "disconnected",
        "redis": "connected" if redis_ok else "disabled",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.post("/api/verify-license", response_model=LicenseVerifyResponse)
async def verify_license(request: LicenseVerifyRequest):
    """Verify license key"""
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        # Check cache first
        if redis_client:
            cached = redis_client.get(f"license:{request.license_key}")
            if cached:
                await conn.close()
                data = json.loads(cached)
                return LicenseVerifyResponse(**data)
        
        # Query database
        row = await conn.fetchrow(
            "SELECT * FROM licenses WHERE license_key = $1 AND is_used = TRUE",
            request.license_key
        )
        await conn.close()
        
        if not row:
            return LicenseVerifyResponse(valid=False, error="License not found")
        
        # Check expiration
        if row['expires_at'] and row['expires_at'] < datetime.utcnow():
            return LicenseVerifyResponse(valid=False, error="License expired")
        
        # Check server match
        if row['used_by'] and row['used_by'] != request.server_id:
            return LicenseVerifyResponse(valid=False, error="Server mismatch")
        
        features = {
            'premium': {
                'max_members': 0,
                'max_giveaways': 0,
                'custom_commands': True,
                'voice_xp': True,
                'level_roles': True
            },
            'enterprise': {
                'max_members': 0,
                'max_giveaways': 0,
                'custom_commands': True,
                'voice_xp': True,
                'level_roles': True,
                'multi_server': True
            }
        }
        
        response = LicenseVerifyResponse(
            valid=True,
            plan=row['plan'],
            expires=row['expires_at'].isoformat() if row['expires_at'] else None,
            features=features.get(row['plan'], {})
        )
        
        # Cache result
        if redis_client:
            redis_client.setex(f"license:{request.license_key}", 3600, response.model_dump_json())
        
        return response
    except Exception as e:
        return LicenseVerifyResponse(valid=False, error=str(e))

@app.post("/api/generate-license")
async def generate_license(request: GenerateLicenseRequest, api_key: str = None):
    """Generate new license key (Admin only)"""
    if api_key != "admin123":
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    license_key = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(days=request.duration)
    
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute(
        "INSERT INTO licenses (license_key, plan, duration_days, created_by, expires_at) VALUES ($1, $2, $3, $4, $5)",
        license_key, request.plan, request.duration, request.created_by, expires_at
    )
    await conn.close()
    
    return {
        "success": True,
        "license_key": license_key,
        "plan": request.plan,
        "expires": expires_at.isoformat()
    }

@app.post("/api/activate-license")
async def activate_license(license_key: str, server_id: str, server_name: str, owner_id: str):
    """Activate license for a server"""
    conn = await asyncpg.connect(DATABASE_URL)
    
    license_row = await conn.fetchrow(
        "SELECT * FROM licenses WHERE license_key = $1 AND is_used = FALSE",
        license_key
    )
    
    if not license_row:
        await conn.close()
        return {"success": False, "error": "Invalid or already used license key"}
    
    await conn.execute(
        "UPDATE licenses SET is_used = TRUE, used_by = $1, used_at = NOW() WHERE license_key = $2",
        server_id, license_key
    )
    
    await conn.execute(
        """
        INSERT INTO servers (server_id, server_name, owner_id, license_key, license_expires)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (server_id) DO UPDATE SET
            license_key = $4,
            license_expires = $5,
            last_active = NOW()
        """,
        server_id, server_name, owner_id, license_key, license_row['expires_at']
    )
    
    await conn.close()
    
    # Invalidate cache
    if redis_client:
        redis_client.delete(f"license:{license_key}")
    
    return {
        "success": True,
        "plan": license_row['plan'],
        "expires": license_row['expires_at'].isoformat()
    }

@app.post("/api/report-usage")
async def report_usage(request: UsageReportRequest):
    """Report bot usage statistics"""
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute(
        "INSERT INTO usage_stats (server_id, command_name, user_id) VALUES ($1, $2, $3)",
        request.server_id, request.command, None
    )
    await conn.close()
    return {"success": True}

@app.get("/api/license-info/{license_key}")
async def get_license_info(license_key: str):
    """Get license information"""
    conn = await asyncpg.connect(DATABASE_URL)
    row = await conn.fetchrow("SELECT * FROM licenses WHERE license_key = $1", license_key)
    await conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="License not found")
    
    return {
        "license_key": row['license_key'],
        "plan": row['plan'],
        "is_used": row['is_used'],
        "used_by": row['used_by'],
        "expires_at": row['expires_at'].isoformat() if row['expires_at'] else None,
        "created_at": row['created_at'].isoformat()
    }

@app.get("/api/server-info/{server_id}")
async def get_server_info(server_id: str):
    """Get server information"""
    conn = await asyncpg.connect(DATABASE_URL)
    row = await conn.fetchrow("SELECT * FROM servers WHERE server_id = $1", server_id)
    await conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Server not found")
    
    return {
        "server_id": row['server_id'],
        "server_name": row['server_name'],
        "owner_id": row['owner_id'],
        "license_key": row['license_key'],
        "license_expires": row['license_expires'].isoformat() if row['license_expires'] else None,
        "joined_at": row['joined_at'].isoformat(),
        "last_active": row['last_active'].isoformat()
    }

@app.get("/api/stats")
async def get_stats():
    """Get overall statistics"""
    conn = await asyncpg.connect(DATABASE_URL)
    
    total_licenses = await conn.fetchval("SELECT COUNT(*) FROM licenses")
    active_licenses = await conn.fetchval("SELECT COUNT(*) FROM licenses WHERE is_used = TRUE AND expires_at > NOW()")
    total_servers = await conn.fetchval("SELECT COUNT(*) FROM servers")
    total_usage = await conn.fetchval("SELECT COUNT(*) FROM usage_stats")
    
    await conn.close()
    
    return {
        "total_licenses": total_licenses,
        "active_licenses": active_licenses,
        "total_servers": total_servers,
        "total_usage_records": total_usage,
        "timestamp": datetime.utcnow().isoformat()
    }

# ====================================================================================================
# RUN APP
# ====================================================================================================
if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("🎮 Family Game Store API Server")
    print("=" * 50)
    print(f"📊 Database: {DATABASE_URL}")
    print(f"🌐 Server will run on: http://0.0.0.0:8000")
    print(f"🔍 Health check: http://localhost:8000/api/health")
    print(f"📈 Stats: http://localhost:8000/api/stats")
    print("=" * 50)
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info"
    )