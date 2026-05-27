"""XCTest connection via WebDriverAgent."""

import json
import requests
from typing import Optional, Any


class XCTestConnection:
    """Manages XCTest connection via WebDriverAgent."""

    def __init__(self, device_id: Optional[str] = None, wda_url: str = "http://localhost:8100"):
        self.device_id = device_id
        self.wda_url = wda_url.rstrip("/")
        self.session_id: Optional[str] = None

    def _request(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        """Make HTTP request to WDA."""
        url = f"{self.wda_url}{path}"
        try:
            response = requests.request(method, url, timeout=30, **kwargs)
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e)}

    def create_session(self, capabilities: Optional[dict] = None) -> str:
        """Create WDA session."""
        data = capabilities or {"capabilities": {"alwaysMatch": {}, "firstMatch": [{}]}}
        result = self._request("POST", "/session", json=data)
        self.session_id = result.get("sessionId")
        return self.session_id or ""

    def delete_session(self) -> None:
        """Delete WDA session."""
        if self.session_id:
            self._request("DELETE", f"/session/{self.session_id}")
            self.session_id = None

    def screenshot(self) -> bytes:
        """Get screenshot."""
        if not self.session_id:
            self.create_session()
        result = self._request("GET", f"/session/{self.session_id}/screenshot")
        if "value" in result and "data" in result["value"]:
            import base64
            return base64.b64decode(result["value"]["data"])
        return b""

    def tap(self, x: float, y: float) -> bool:
        """Tap at coordinates."""
        if not self.session_id:
            return False
        result = self._request(
            "POST",
            f"/session/{self.session_id}/execute/script",
            json={"script": "mobile: tap", "args": [{"x": x, "y": y}]}
        )
        return "error" not in result
