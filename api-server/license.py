from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import secrets
import asyncpg
import os

router = APIRouter(prefix="/api/license", tags=["license"])

DATABASE_URL = os.getenv('DATABASE_URL')

class LicenseGenerateRequest(BaseModel):
    plan: str
    duration_days: int = 30
    created_by: str

class LicenseActivateRequest(BaseModel):
    license_key: str
    server_id: str
    server_name: str
    owner_id: int

class LicenseVerifyRequest(BaseModel):
    license_key: str
    server_id: str

@router.post("/generate")
async def generate_license(request: LicenseGenerateRequest, api_key: str = Header(None)):
    if api_key != os.getenv('ADMIN_API_KEY', 'admin123'):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    if not DATABASE_URL:
        raise HTTPException(status_code=503, detail="Database not configured")
    
    license_key = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(days=request.duration_days)
    
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute(
        "INSERT INTO licenses (license_key, plan, duration_days, created_by, expires_at) VALUES ($1, $2, $3, $4, $5)",
        license_key, request.plan, request.duration_days, request.created_by, expires_at
    )
    await conn.close()
    
    return {
        "success": True,
        "license_key": license_key,
        "plan": request.plan,
        "expires_at": expires_at.isoformat()
    }

@router.post("/activate")
async def activate_license(request: LicenseActivateRequest):
    if not DATABASE_URL:
        return {"success": False, "error": "Database not configured"}
    
    conn = await asyncpg.connect(DATABASE_URL)
    
    license_row = await conn.fetchrow(
        "SELECT * FROM licenses WHERE license_key = $1 AND is_used = FALSE",
        request.license_key
    )
    
    if not license_row:
        await conn.close()
        return {"success": False, "error": "Invalid license key"}
    
    await conn.execute(
        "UPDATE licenses SET is_used = TRUE, used_by = $1, used_at = NOW() WHERE license_key = $2",
        request.server_id, request.license_key
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
        request.server_id, request.server_name, request.owner_id, 
        request.license_key, license_row['expires_at']
    )
    
    await conn.close()
    
    return {
        "success": True,
        "plan": license_row['plan'],
        "expires_at": license_row['expires_at'].isoformat()
    }

@router.post("/verify")
async def verify_license(request: LicenseVerifyRequest):
    if not DATABASE_URL:
        return {"valid": False, "error": "Database not configured"}
    
    conn = await asyncpg.connect(DATABASE_URL)
    
    row = await conn.fetchrow(
        "SELECT * FROM licenses WHERE license_key = $1 AND is_used = TRUE",
        request.license_key
    )
    
    await conn.close()
    
    if not row:
        return {"valid": False, "error": "License not found"}
    
    if row['expires_at'] and row['expires_at'] < datetime.utcnow():
        return {"valid": False, "error": "License expired"}
    
    if row['used_by'] and row['used_by'] != request.server_id:
        return {"valid": False, "error": "Server mismatch"}
    
    return {
        "valid": True,
        "plan": row['plan'],
        "expires_at": row['expires_at'].isoformat() if row['expires_at'] else None
    }
