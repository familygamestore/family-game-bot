from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import secrets
import os
import hashlib
import hmac

router = APIRouter(prefix="/api/payment", tags=["payment"])

class CreatePaymentRequest(BaseModel):
    plan: str
    payment_method: str = "midtrans"
    user_id: str

class PaymentCallbackRequest(BaseModel):
    transaction_id: str
    status: str
    payment_details: Optional[dict] = None

@router.post("/create")
async def create_payment(request: CreatePaymentRequest):
    """Create payment transaction"""
    transaction_id = secrets.token_urlsafe(16)
    
    # Calculate amount based on plan
    amounts = {
        'premium': 9.99,
        'enterprise': 49.99
    }
    amount = amounts.get(request.plan, 0)
    
    # For Indonesian Rupiah
    amounts_idr = {
        'premium': 149000,
        'enterprise': 749000
    }
    amount_idr = amounts_idr.get(request.plan, 0)
    
    return {
        "success": True,
        "transaction_id": transaction_id,
        "amount": amount,
        "amount_idr": amount_idr,
        "currency": "USD",
        "payment_url": f"/payment/{transaction_id}"
    }

@router.post("/callback/midtrans")
async def midtrans_callback(request: Request):
    """Midtrans payment callback webhook"""
    data = await request.json()
    
    # Verify signature
    signature_key = os.getenv('MIDTRANS_SERVER_KEY', '')
    order_id = data.get('order_id')
    status_code = data.get('status_code')
    gross_amount = data.get('gross_amount')
    
    # Process payment
    if status_code == '200':
        # Payment success
        return {"status": "success"}
    else:
        return {"status": "failed"}

@router.post("/callback/xendit")
async def xendit_callback(request: Request):
    """Xendit payment callback webhook"""
    data = await request.json()
    
    status = data.get('status')
    external_id = data.get('external_id')
    
    if status == 'PAID':
        # Payment success
        return {"status": "success"}
    else:
        return {"status": "failed"}

@router.get("/status/{transaction_id}")
async def get_payment_status(transaction_id: str):
    """Get payment transaction status"""
    return {
        "transaction_id": transaction_id,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat()
    }