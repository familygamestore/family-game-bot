from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import secrets

router = APIRouter(prefix="/api/license", tags=["license"])

class LicenseGenerateRequest(BaseModel):
    plan: str
    duration_days: int = 30
    created_by: str

class LicenseActivateRequest(BaseModel):
    license_key: str
    server_id: str
    server_name: str
    owner_id: str

class LicenseVerifyRequest(BaseModel):
    license_key: str
    server_id: str

@router.post("/generate")
async def generate_license(request: LicenseGenerateRequest, api_key: str = None):
    if api_key != "admin_key_here":
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    license_key = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(days=request.duration_days)
    
    return {
        "success": True,
        "license_key": license_key,
        "plan": request.plan,
        "expires_at": expires_at.isoformat()
    }

@router.post("/activate")
async def activate_license(request: LicenseActivateRequest):
    return {
        "success": True,
        "plan": "premium",
        "expires_at": (datetime.utcnow() + timedelta(days=30)).isoformat()
    }

@router.post("/verify")
async def verify_license(request: LicenseVerifyRequest):
    return {
        "valid": True,
        "plan": "premium",
        "expires_at": (datetime.utcnow() + timedelta(days=30)).isoformat(),
        "features": {
            "custom_commands": True,
            "voice_xp": True,
            "level_roles": True
        }
    }