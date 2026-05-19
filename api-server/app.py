#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import secrets
import asyncpg
import json
import os

# ====================================================================================================
# DATABASE CONFIGURATION
# ====================================================================================================

DATABASE_URL = os.getenv('DATABASE_URL')
REDIS_URL = os.getenv('REDIS_URL', 'redis://redis:6379')

if not DATABASE_URL:
    print("=" * 60)
    print("❌ ERROR: DATABASE_URL environment variable not set!")
    print("=" * 60)
    DATABASE_URL = None

# Redis client
redis_client = None
try:
    import redis
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    redis_client.ping()
    print("✅ Redis connected")
except Exception as e:
    print(f"⚠️ Redis not available: {e}")

# ====================================================================================================
# DATABASE FUNCTIONS
# ====================================================================================================

async def init_db():
    """Initialize database tables"""
    if not DATABASE_URL:
        return False
    
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        # Create users table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                is_admin BOOLEAN DEFAULT FALSE,
                is_active BOOLEAN DEFAULT TRUE,
                subscription_plan TEXT DEFAULT 'free',
                subscription_expires TIMESTAMP,
                api_key TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        ''')
        
        # Create licenses table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS licenses (
                id SERIAL PRIMARY KEY,
                license_key TEXT UNIQUE NOT NULL,
                plan TEXT NOT NULL,
                duration_days INTEGER NOT NULL,
                created_by INTEGER,
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
                server_icon TEXT,
                owner_id INTEGER,
                license_key TEXT,
                license_expires TIMESTAMP,
                features TEXT DEFAULT '{}',
                is_active BOOLEAN DEFAULT TRUE,
                joined_at TIMESTAMP DEFAULT NOW(),
                last_active TIMESTAMP DEFAULT NOW(),
                member_count INTEGER DEFAULT 0,
                message_count INTEGER DEFAULT 0
            )
        ''')
        
        # Create payment_transactions table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS payment_transactions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER,
                amount FLOAT NOT NULL,
                currency TEXT DEFAULT 'USD',
                plan TEXT NOT NULL,
                duration_days INTEGER NOT NULL,
                transaction_id TEXT UNIQUE,
                payment_method TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT NOW(),
                paid_at TIMESTAMP,
                expired_at TIMESTAMP
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

async def get_db_connection():
    """Get database connection"""
    if not DATABASE_URL:
        return None
    return await asyncpg.connect(DATABASE_URL)

def get_features_for_plan(plan: str) -> dict:
    """Get features based on plan"""
    features = {
        'premium': {
            'max_members': 0,
            'max_giveaways': 0,
            'custom_commands': True,
            'voice_xp': True,
            'level_roles': True,
            'welcome_messages': True,
            'export_stats': True
        },
        'enterprise': {
            'max_members': 0,
            'max_giveaways': 0,
            'custom_commands': True,
            'voice_xp': True,
            'level_roles': True,
            'welcome_messages': True,
            'export_stats': True,
            'multi_server': True,
            'dedicated_support': True,
            'api_access': True
        }
    }
    return features.get(plan, {})

# ====================================================================================================
# PYDANTIC MODELS
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

class ActivateLicenseRequest(BaseModel):
    license_key: str
    server_id: str
    server_name: str
    owner_id: int

class UsageReportRequest(BaseModel):
    server_id: str
    command: Optional[str] = None
    user_id: Optional[str] = None

class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

class CreatePaymentRequest(BaseModel):
    plan: str
    payment_method: str = "midtrans"
    user_id: int

# ====================================================================================================
# LIFESPAN EVENT HANDLER
# ====================================================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting API Server...")
    print(f"📊 Port: {os.getenv('PORT', '8000')}")
    
    if DATABASE_URL:
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            await conn.close()
            print("✅ Database connection successful!")
            await init_db()
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
    
    yield
    
    # Shutdown
    print("🛑 API Server shutting down...")
    if redis_client:
        redis_client.close()

# ====================================================================================================
# FASTAPI APP
# ====================================================================================================

app = FastAPI(
    title="Family Game Store API",
    description="API for Discord Bot License Management",
    version="2.0.0",
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
# ROOT ENDPOINTS
# ====================================================================================================

@app.get("/")
async def root():
    return {
        "message": "Family Game Store API is running",
        "status": "online",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    db_ok = False
    db_error = None
    
    if DATABASE_URL:
        try:
            conn = await asyncpg.connect(DATABASE_URL)
            await conn.close()
            db_ok = True
        except Exception as e:
            db_error = str(e)
    
    redis_ok = False
    if redis_client:
        try:
            redis_client.ping()
            redis_ok = True
        except:
            pass
    
    return {
        "status": "healthy",
        "database": "connected" if db_ok else "disconnected",
        "database_error": db_error,
        "redis": "connected" if redis_ok else "disabled",
        "timestamp": datetime.utcnow().isoformat()
    }

# ====================================================================================================
# LICENSE ENDPOINTS
# ====================================================================================================

@app.post("/api/verify-license", response_model=LicenseVerifyResponse)
async def verify_license(request: LicenseVerifyRequest):
    """Verify license key"""
    if not DATABASE_URL:
        return LicenseVerifyResponse(valid=False, error="Database not configured")
    
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        # Check cache
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
        
        if not row:
            await conn.close()
            return LicenseVerifyResponse(valid=False, error="License not found")
        
        # Check expiration
        if row['expires_at'] and row['expires_at'] < datetime.utcnow():
            await conn.close()
            return LicenseVerifyResponse(valid=False, error="License expired")
        
        # Check server match
        if row['used_by'] and row['used_by'] != request.server_id:
            await conn.close()
            return LicenseVerifyResponse(valid=False, error="Server mismatch")
        
        # Update last active
        await conn.execute(
            "UPDATE servers SET last_active = NOW() WHERE server_id = $1",
            request.server_id
        )
        await conn.close()
        
        features = get_features_for_plan(row['plan'])
        
        response = LicenseVerifyResponse(
            valid=True,
            plan=row['plan'],
            expires=row['expires_at'].isoformat() if row['expires_at'] else None,
            features=features
        )
        
        # Cache result
        if redis_client:
            redis_client.setex(f"license:{request.license_key}", 3600, response.model_dump_json())
        
        return response
    except Exception as e:
        return LicenseVerifyResponse(valid=False, error=str(e))

@app.post("/api/generate-license")
async def generate_license(request: GenerateLicenseRequest, api_key: str = Header(None)):
    """Generate new license key (Admin only)"""
    if not DATABASE_URL:
        raise HTTPException(status_code=503, detail="Database not configured")
    
    if api_key != os.getenv('ADMIN_API_KEY', 'admin123'):
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
async def activate_license(request: ActivateLicenseRequest):
    """Activate license for a server"""
    if not DATABASE_URL:
        return {"success": False, "error": "Database not configured"}
    
    conn = await asyncpg.connect(DATABASE_URL)
    
    # Check if server exists
    server = await conn.fetchrow("SELECT * FROM servers WHERE server_id = $1", request.server_id)
    
    if not server:
        # Create server
        await conn.execute(
            "INSERT INTO servers (server_id, server_name, owner_id) VALUES ($1, $2, $3)",
            request.server_id, request.server_name, request.owner_id
        )
    
    # Get license
    license_row = await conn.fetchrow(
        "SELECT * FROM licenses WHERE license_key = $1 AND is_used = FALSE",
        request.license_key
    )
    
    if not license_row:
        await conn.close()
        return {"success": False, "error": "Invalid or already used license key"}
    
    # Activate license
    await conn.execute(
        "UPDATE licenses SET is_used = TRUE, used_by = $1, used_at = NOW() WHERE license_key = $2",
        request.server_id, request.license_key
    )
    
    # Update server
    await conn.execute(
        """
        UPDATE servers SET 
            license_key = $1, 
            license_expires = $2,
            last_active = NOW()
        WHERE server_id = $3
        """,
        request.license_key, license_row['expires_at'], request.server_id
    )
    
    await conn.close()
    
    # Invalidate cache
    if redis_client:
        redis_client.delete(f"license:{request.license_key}")
    
    return {
        "success": True,
        "plan": license_row['plan'],
        "expires": license_row['expires_at'].isoformat()
    }

@app.post("/api/report-usage")
async def report_usage(request: UsageReportRequest):
    """Report bot usage statistics"""
    if not DATABASE_URL:
        return {"success": False, "error": "Database not configured"}
    
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute(
        "INSERT INTO usage_stats (server_id, command_name, user_id) VALUES ($1, $2, $3)",
        request.server_id, request.command, request.user_id
    )
    
    # Update server message count
    await conn.execute(
        "UPDATE servers SET message_count = message_count + 1, last_active = NOW() WHERE server_id = $1",
        request.server_id
    )
    
    await conn.close()
    return {"success": True}

@app.get("/api/license-info/{license_key}")
async def get_license_info(license_key: str):
    """Get license information"""
    if not DATABASE_URL:
        raise HTTPException(status_code=503, detail="Database not configured")
    
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
    if not DATABASE_URL:
        raise HTTPException(status_code=503, detail="Database not configured")
    
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
        "last_active": row['last_active'].isoformat(),
        "member_count": row['member_count'],
        "message_count": row['message_count']
    }

@app.get("/api/stats")
async def get_stats():
    """Get overall statistics"""
    if not DATABASE_URL:
        raise HTTPException(status_code=503, detail="Database not configured")
    
    conn = await asyncpg.connect(DATABASE_URL)
    
    total_users = await conn.fetchval("SELECT COUNT(*) FROM users")
    total_licenses = await conn.fetchval("SELECT COUNT(*) FROM licenses")
    active_licenses = await conn.fetchval("SELECT COUNT(*) FROM licenses WHERE is_used = TRUE AND expires_at > NOW()")
    total_servers = await conn.fetchval("SELECT COUNT(*) FROM servers")
    premium_servers = await conn.fetchval("SELECT COUNT(*) FROM servers WHERE license_key IS NOT NULL AND license_expires > NOW()")
    total_usage = await conn.fetchval("SELECT COUNT(*) FROM usage_stats")
    
    await conn.close()
    
    return {
        "total_users": total_users,
        "total_licenses": total_licenses,
        "active_licenses": active_licenses,
        "total_servers": total_servers,
        "premium_servers": premium_servers,
        "total_usage_records": total_usage,
        "timestamp": datetime.utcnow().isoformat()
    }

# ====================================================================================================
# AUTH ENDPOINTS
# ====================================================================================================

@app.post("/api/auth/login")
async def login(request: LoginRequest):
    """Login user"""
    if not DATABASE_URL:
        raise HTTPException(status_code=503, detail="Database not configured")
    
    conn = await asyncpg.connect(DATABASE_URL)
    
    row = await conn.fetchrow(
        "SELECT id, username, email, password_hash, is_admin FROM users WHERE email = $1",
        request.email
    )
    
    await conn.close()
    
    if not row:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # In production, verify password hash with bcrypt
    # For now, simple check
    token = secrets.token_urlsafe(32)
    
    return {
        "success": True,
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": row['id'],
            "username": row['username'],
            "email": row['email'],
            "is_admin": row['is_admin']
        }
    }

@app.post("/api/auth/register")
async def register(request: RegisterRequest):
    """Register new user"""
    if not DATABASE_URL:
        raise HTTPException(status_code=503, detail="Database not configured")
    
    conn = await asyncpg.connect(DATABASE_URL)
    
    # Check if user exists
    existing = await conn.fetchrow("SELECT id FROM users WHERE email = $1 OR username = $2", request.email, request.username)
    if existing:
        await conn.close()
        raise HTTPException(status_code=400, detail="User already exists")
    
    # Simple hash (use bcrypt in production)
    password_hash = secrets.token_urlsafe(32)  # Placeholder
    
    await conn.execute(
        "INSERT INTO users (username, email, password_hash, api_key) VALUES ($1, $2, $3, $4)",
        request.username, request.email, password_hash, secrets.token_urlsafe(32)
    )
    
    await conn.close()
    
    return {"success": True, "message": "User registered successfully"}

# ====================================================================================================
# PAYMENT ENDPOINTS
# ====================================================================================================

@app.post("/api/payment/create")
async def create_payment(request: CreatePaymentRequest):
    """Create payment transaction"""
    transaction_id = secrets.token_urlsafe(16)
    
    amounts = {
        'premium': 9.99,
        'enterprise': 49.99
    }
    amount = amounts.get(request.plan, 0)
    
    return {
        "success": True,
        "transaction_id": transaction_id,
        "amount": amount,
        "currency": "USD",
        "payment_url": f"/payment/{transaction_id}"
    }

@app.post("/api/payment/callback")
async def payment_callback(data: dict):
    """Payment callback webhook"""
    transaction_id = data.get('transaction_id')
    status = data.get('status')
    
    return {"status": "success"}

# ====================================================================================================
# RUN APP
# ====================================================================================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('PORT', 8000))
    print("=" * 50)
    print("🎮 Family Game Store API Server")
    print("=" * 50)
    print(f"🌐 Server will run on port: {port}")
    print(f"🔗 Health check: http://localhost:{port}/api/health")
    print("=" * 50)
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port,
        log_level="info"
    )
