from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class LicenseBase(BaseModel):
    license_key: str
    plan: str
    duration_days: int
    created_by: str
    created_at: datetime
    is_used: bool
    used_by: Optional[str] = None
    used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

class LicenseCreate(BaseModel):
    plan: str
    duration_days: int = 30

class LicenseActivate(BaseModel):
    license_key: str
    server_id: str
    server_name: str

class LicenseVerify(BaseModel):
    license_key: str
    server_id: str

class LicenseResponse(BaseModel):
    valid: bool
    plan: Optional[str] = None
    expires_at: Optional[datetime] = None
    error: Optional[str] = None

class ServerBase(BaseModel):
    server_id: str
    server_name: str
    owner_id: str

class ServerCreate(ServerBase):
    pass

class ServerResponse(ServerBase):
    joined_at: datetime
    last_active: datetime
    is_premium: bool

class UserBase(BaseModel):
    username: str
    email: str

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    is_admin: bool
    created_at: datetime
    subscription_plan: str
    subscription_expires: Optional[datetime] = None

class PaymentCreate(BaseModel):
    plan: str
    payment_method: str = "midtrans"

class PaymentResponse(BaseModel):
    success: bool
    transaction_id: str
    payment_url: str
    amount: float

class StatsResponse(BaseModel):
    total_servers: int
    total_users: int
    total_messages: int
    premium_servers: int
    active_users: int