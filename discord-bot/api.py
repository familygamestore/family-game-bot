import aiohttp
import os
from typing import Optional, Dict, Any

API_URL = os.getenv('API_URL', 'http://localhost:8000')

class APIClient:
    """API client for bot-server communication"""
    
    def __init__(self):
        self.session = None
    
    async def get_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None
    
    async def verify_license(self, license_key: str, server_id: str) -> Dict[str, Any]:
        """Verify license key with API"""
        session = await self.get_session()
        try:
            async with session.post(f'{API_URL}/api/verify-license', json={
                'license_key': license_key,
                'server_id': server_id
            }) as resp:
                return await resp.json()
        except Exception as e:
            return {'valid': False, 'error': str(e)}
    
    async def report_usage(self, license_key: str, server_id: str, command: str = None) -> bool:
        """Report bot usage to API"""
        session = await self.get_session()
        try:
            async with session.post(f'{API_URL}/api/report-usage', json={
                'license_key': license_key,
                'server_id': server_id,
                'command': command
            }) as resp:
                data = await resp.json()
                return data.get('success', False)
        except Exception:
            return False
    
    async def get_server_stats(self, server_id: str) -> Optional[Dict]:
        """Get server statistics from API"""
        session = await self.get_session()
        try:
            async with session.get(f'{API_URL}/api/server-stats/{server_id}') as resp:
                return await resp.json()
        except Exception:
            return None

api_client = APIClient()