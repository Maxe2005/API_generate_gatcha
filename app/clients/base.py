import httpx
from typing import Any, Dict, Optional

class AsyncHttpClient:
    """
    Base class for HTTP clients to ensure DRY principle for setup and error handling.
    """
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = self._get_headers()

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}" 
        }

    async def _post_request(self, endpoint: str = "", payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generic POST request handler.
        """
        url = f"{self.base_url}{endpoint}"
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=self.headers, timeout=30.0)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                # In a real app, log this error specifically
                raise Exception(f"External API Error: {e.response.text}") from e
            except Exception as e:
                raise Exception(f"Connection Error: {str(e)}") from e
