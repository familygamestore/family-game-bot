from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
from typing import Optional

router = APIRouter(prefix="/api/stats", tags=["statistics"])

@router.get("/overview")
async def get_overview_stats():
    """Get overall statistics"""
    return {
        "total_servers": 0,
        "total_users": 0,
        "total_messages": 0,
        "premium_servers": 0,
        "active_users": 0
    }

@router.get("/servers/{server_id}")
async def get_server_stats(server_id: str):
    """Get statistics for a specific server"""
    return {
        "server_id": server_id,
        "member_count": 0,
        "message_count": 0,
        "command_count": 0,
        "premium": False,
        "joined_at": datetime.utcnow().isoformat()
    }

@router.get("/daily")
async def get_daily_stats():
    """Get daily statistics for the past 30 days"""
    stats = []
    for i in range(30):
        date = (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
        stats.append({
            "date": date,
            "messages": 0,
            "commands": 0,
            "new_users": 0
        })
    return stats

@router.get("/commands")
async def get_command_stats(limit: int = 10):
    """Get most used commands statistics"""
    return [
        {"command": "!help", "count": 0},
        {"command": "!rank", "count": 0},
        {"command": "!leaderboard", "count": 0}
    ]