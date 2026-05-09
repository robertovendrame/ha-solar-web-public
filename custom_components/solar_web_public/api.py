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
    def token(self) -> str:
        """Return Solar.web public token."""
        return self._plant_key

    @property
    def shared_url(self) -> str:
        """Return normalized shared URL."""
        return (
            "https://www.solarweb.com/PublicDisplay/PvSystem"
            f"?token={self.token}"
        )

    def _extract_plant_key(self, url: str) -> str:
        """Extract public token from Solar.web shared URL."""

        match = re.search(
            r"[?&]token=([a-fA-F0-9-]{36})",
            url,
            re.IGNORECASE,
        )

        if match:
            return match.group(1)

        raise SolarWebInvalidUrlError("Missing Solar.web public token")

    async def async_get_data(self) -> dict[str, Any]:
        """Fetch plant data from the shared public URL."""

        headers = {
            "User-Agent": "HomeAssistant-SolarWebPublic/0.1",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        try:
            async with self._session.get(
                self.shared_url,
                headers=headers,
                allow_redirects=True,
            ) as response:
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
        """Parse Solar.web public page."""

        plant_name = self._extract_text_after_solarweb(payload)
        location = self._extract_location(payload)

        return {
            "status": "online" if payload else "unknown",
            "plant_name": plant_name,
            "location": location,
            "current_power_w": None,
            "today_energy_kwh": None,
            "total_energy_kwh": None,
            "battery_soc": None,
            "grid_power_w": None,
            "last_update": None,
            "content_type": content_type,
            "payload_length": len(payload),
            "token": self.token,
        }

    def _extract_text_after_solarweb(self, payload: str) -> str | None:
        """Temporary simple extraction of plant name from HTML."""

        match = re.search(
            r"SOLAR\.WEB\s*</?[^>]*>\s*([^<]+)",
            payload,
            re.IGNORECASE,
        )

        if match:
            return match.group(1).strip()

        # Fallback for plain extracted text-like payloads
        match = re.search(
            r"SOLAR\.WEB\s+(.+?)\s+Current power",
            payload,
            re.IGNORECASE | re.DOTALL,
        )

        if match:
            return " ".join(match.group(1).split())

        return None

    def _extract_location(self, payload: str) -> str | None:
        """Temporary simple extraction of location from HTML."""

        # For now this is intentionally conservative.
        # We will improve it when we inspect the real JS/API payload.
        known_match = re.search(
            r"(Portogruaro|[A-Z][a-zA-ZÀ-ÿ'\- ]{2,})\s*© Fronius",
            payload,
            re.IGNORECASE,
        )

        if known_match:
            return known_match.group(1).strip()

        return None