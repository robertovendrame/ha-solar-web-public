"""API client for Solar Web Public."""

from __future__ import annotations

import re
from typing import Any

import aiohttp


class SolarWebPublicApiError(Exception):
    """Generic Solar Web Public API error."""


class SolarWebInvalidUrlError(SolarWebPublicApiError):
    """Invalid Solar Web shared URL."""


class SolarWebPublicClient:
    """Client for Solar.web shared/public plant pages."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        shared_url: str,
    ) -> None:
        self._session = session
        self._shared_url = shared_url.strip()
        self._plant_key = self._extract_plant_key(self._shared_url)

    @property
    def plant_key(self) -> str:
        """Return a stable plant key."""
        return self._plant_key

    @property
    def shared_url(self) -> str:
        """Return shared URL."""
        return self._shared_url

    def _extract_plant_key(self, url: str) -> str:
        """Extract a stable ID from the shared Solar.web URL."""

        patterns = [
            r"/pv-systems/([^/?#]+)",
            r"/Home/GuestLogOn\?pvSystemId=([^&#]+)",
            r"pvSystemId=([^&#]+)",
            r"plantId=([^&#]+)",
            r"sid=([^&#]+)",
            r"token=([^&#]+)",
            r"id=([^&#]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                return match.group(1)

        # Fallback: use a sanitized URL fragment.
        sanitized = re.sub(r"[^a-zA-Z0-9]+", "_", url).strip("_")
        if sanitized:
            return sanitized[-64:]

        raise SolarWebInvalidUrlError("Invalid Solar.web shared URL")

    async def async_get_data(self) -> dict[str, Any]:
        """Fetch plant data from the shared URL."""

        try:
            async with self._session.get(self._shared_url) as response:
                if response.status >= 400:
                    raise SolarWebPublicApiError(
                        f"Solar.web returned HTTP {response.status}"
                    )

                content_type = response.headers.get("content-type", "")
                text = await response.text()

        except aiohttp.ClientError as err:
            raise SolarWebPublicApiError(f"Connection error: {err}") from err

        return self._parse_response(text, content_type)

    def _parse_response(
        self,
        payload: str,
        content_type: str,
    ) -> dict[str, Any]:
        """
        Parse Solar.web shared page.

        This is intentionally temporary.
        Here we will insert the real parser from your working tests.
        """

        return {
            "status": "online" if payload else "unknown",
            "current_power_w": None,
            "today_energy_kwh": None,
            "total_energy_kwh": None,
            "battery_soc": None,
            "grid_power_w": None,
            "last_update": None,
            "content_type": content_type,
            "payload_length": len(payload),
        }