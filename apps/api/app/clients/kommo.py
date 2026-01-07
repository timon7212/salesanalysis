import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from app.config import settings
from app.security import encryptor
import logging

logger = logging.getLogger(__name__)


class KommoClient:
    def __init__(self, base_url: str, access_token: str):
        self.base_url = base_url.rstrip('/')
        self.access_token = access_token
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        await self.client.aclose()
    
    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v4/{endpoint}"
        headers = self._headers()
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await self.client.request(method, url, headers=headers, **kwargs)
                
                if response.status_code == 401:
                    raise Exception("Unauthorized - token may be expired")
                
                if response.status_code == 429:
                    # Rate limited
                    retry_after = int(response.headers.get("Retry-After", 60))
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_after)
                        continue
                    raise Exception(f"Rate limited. Retry after {retry_after}s")
                
                response.raise_for_status()
                return response.json()
            
            except httpx.HTTPStatusError as e:
                if attempt == max_retries - 1:
                    logger.error(f"Kommo API error: {e.response.status_code} - {e.response.text}")
                    raise Exception(f"Kommo API error: {e.response.status_code}")
                await asyncio.sleep(2 ** attempt)
            
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"Kommo request failed: {str(e)}")
                    raise
                await asyncio.sleep(2 ** attempt)
    
    async def get_account_info(self) -> Dict[str, Any]:
        """Get current account information"""
        return await self._request("GET", "account")
    
    async def list_leads(
        self,
        query: Optional[str] = None,
        page: int = 1,
        limit: int = 50,
        pipeline_id: Optional[int] = None,
        responsible_user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """List leads with pagination and filters"""
        params = {
            "page": page,
            "limit": limit
        }
        
        if query:
            params["query"] = query
        
        if pipeline_id:
            params["filter[pipeline_id]"] = pipeline_id
        
        if responsible_user_id:
            params["filter[responsible_user_id]"] = responsible_user_id
        
        return await self._request("GET", "leads", params=params)
    
    async def get_lead(self, lead_id: int) -> Dict[str, Any]:
        """Get single lead by ID"""
        result = await self._request("GET", f"leads/{lead_id}")
        return result
    
    async def get_pipelines(self) -> Dict[str, Any]:
        """Get all pipelines"""
        return await self._request("GET", "leads/pipelines")
    
    async def get_users(self) -> Dict[str, Any]:
        """Get all users"""
        return await self._request("GET", "users")
    
    async def add_note_to_lead(self, lead_id: int, note_text: str) -> Dict[str, Any]:
        """Add a note to a lead"""
        payload = {
            "note_type": "common",
            "params": {
                "text": note_text
            }
        }
        
        return await self._request(
            "POST",
            f"leads/{lead_id}/notes",
            json=[payload]
        )
    
    async def update_lead_fields(self, lead_id: int, custom_fields: Dict[int, Any]) -> Dict[str, Any]:
        """Update custom fields on a lead"""
        custom_fields_values = []
        for field_id, value in custom_fields.items():
            custom_fields_values.append({
                "field_id": field_id,
                "values": [{"value": value}]
            })
        
        payload = {
            "custom_fields_values": custom_fields_values
        }
        
        return await self._request("PATCH", f"leads/{lead_id}", json=payload)


async def refresh_kommo_token(
    base_url: str,
    client_id: str,
    client_secret: str,
    refresh_token: str,
    redirect_uri: str
) -> Dict[str, Any]:
    """Refresh Kommo OAuth token"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{base_url}/oauth2/access_token",
            json={
                "client_id": client_id,
                "client_secret": client_secret,
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "redirect_uri": redirect_uri
            }
        )
        response.raise_for_status()
        return response.json()


def parse_kommo_lead(lead_data: Dict[str, Any]) -> Dict[str, Any]:
    """Parse Kommo lead data into simplified format"""
    try:
        contacts = lead_data.get("_embedded", {}).get("contacts", [])
        contact_name = None
        if contacts and len(contacts) > 0:
            contact = contacts[0]
            contact_name = contact.get("name")
        
        pipeline_id = lead_data.get("pipeline_id")
        status_id = lead_data.get("status_id")
        
        # Safe datetime parsing
        created_at = None
        if lead_data.get("created_at"):
            try:
                created_at = datetime.fromtimestamp(lead_data.get("created_at"))
            except (ValueError, OSError):
                created_at = None
        
        updated_at = None
        if lead_data.get("updated_at"):
            try:
                updated_at = datetime.fromtimestamp(lead_data.get("updated_at"))
            except (ValueError, OSError):
                updated_at = None
        
        responsible_user_id = lead_data.get("responsible_user_id")
        
        return {
            "lead_id": lead_data.get("id"),
            "lead_name": lead_data.get("name", "Untitled"),
            "pipeline_id": pipeline_id,
            "pipeline": str(pipeline_id) if pipeline_id else None,
            "status": str(status_id) if status_id else None,
            "price": lead_data.get("price"),
            "responsible_user_id": responsible_user_id,
            "created_at": created_at,
            "updated_at": updated_at,
            "contact_name": contact_name
        }
    except Exception as e:
        logger.error(f"Error parsing lead data: {e}", exc_info=True)
        # Return minimal valid data
        return {
            "lead_id": lead_data.get("id", 0),
            "lead_name": lead_data.get("name", "Error parsing lead"),
            "pipeline": None,
            "status": None,
            "price": None,
            "created_at": None,
            "updated_at": None,
            "contact_name": None
        }


import asyncio


