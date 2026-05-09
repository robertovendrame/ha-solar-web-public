"""API client for Solar Web Public."""

from __future__ import annotations

import json
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
        self._input_url = shared_url.strip()
        self._token = self._extract_token(self._input_url)

    @property
    def plant_key(self) -> str:
        """Return a stable plant key."""
        return self._token

    @property
    def token(self) -> str:
        """Return Solar.web public token."""
        return self._token

    @property
    def shared_url(self) -> str:
        """Return normalized Solar.web public URL."""
        return (
            "https://www.solarweb.com/PublicDisplay/PvSystem"
            f"?token={self.token}"
        )

    def _extract_token(self, url: str) -> str:
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
        """Fetch plant data from Solar.web public page."""

        headers = {
            "User-Agent": "HomeAssistant-SolarWebPublic/0.1",
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "application/json;q=0.8,*/*;q=0.7"
            ),
            "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
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
                final_url = str(response.url)
                payload = await response.text()

        except aiohttp.ClientError as err:
            raise SolarWebPublicApiError(f"Connection error: {err}") from err

        return self._parse_response(
            payload=payload,
            content_type=content_type,
            final_url=final_url,
        )

    def _parse_response(
        self,
        payload: str,
        content_type: str,
        final_url: str,
    ) -> dict[str, Any]:
        """Parse Solar.web public page."""

        plant_name = self._extract_plant_name(payload)
        location = self._extract_location(payload)
        title = self._extract_title(payload)

        script_sources = self._extract_script_sources(payload)
        api_candidates = self._extract_api_candidates(payload)

        return {
            "status": "online" if payload else "unknown",
            "plant_name": plant_name,
            "location": location,
            "page_title": title,
            "current_power_w": None,
            "today_energy_kwh": None,
            "total_energy_kwh": None,
            "battery_soc": None,
            "grid_power_w": None,
            "last_update": None,
            "token": self.token,
            "input_url": self._input_url,
            "final_url": final_url,
            "content_type": content_type,
            "payload_length": len(payload),
            "has_api": "/api/" in payload.lower(),
            "has_public_display": "publicdisplay" in payload.lower(),
            "has_current_power": (
                "current" in payload.lower()
                and "power" in payload.lower()
            ),
            "has_pv_system": (
                "pvsystem" in payload.lower()
                or "pv-system" in payload.lower()
                or "pv_system" in payload.lower()
            ),
            "script_count": len(script_sources),
            "script_sources": script_sources[:20],
            "api_candidates": api_candidates[:30],
            "debug_preview": self._clean_preview(payload),
        }

    def _extract_title(self, payload: str) -> str | None:
        """Extract HTML title."""

        match = re.search(
            r"<title[^>]*>(.*?)</title>",
            payload,
            re.IGNORECASE | re.DOTALL,
        )

        if not match:
            return None

        return self._clean_text(match.group(1))

    def _extract_plant_name(self, payload: str) -> str | None:
        """Extract plant name from public page."""

        # Common visible text pattern from Solar.web public page
        match = re.search(
            r"SOLAR\.WEB\s*</?[^>]*>\s*([^<]{2,120})",
            payload,
            re.IGNORECASE,
        )

        if match:
            value = self._clean_text(match.group(1))
            if value:
                return value

        # Fallback from text-like HTML
        match = re.search(
            r"SOLAR\.WEB\s+(.+?)\s+(Current power|Potenza|Aktuelle Leistung)",
            payload,
            re.IGNORECASE | re.DOTALL,
        )

        if match:
            value = self._clean_text(match.group(1))
            if value:
                return value

        # Fallback from title
        title = self._extract_title(payload)
        if title and "solar" not in title.lower():
            return title

        return None

    def _extract_location(self, payload: str) -> str | None:
        """Extract location from public page."""

        # Very conservative fallback.
        match = re.search(
            r"\b([A-ZÀ-Ý][a-zA-ZÀ-ÿ'\- ]{2,60})\b\s*©\s*Fronius",
            payload,
            re.IGNORECASE,
        )

        if match:
            value = self._clean_text(match.group(1))
            if value:
                return value

        return None

    def _extract_script_sources(self, payload: str) -> list[str]:
        """Extract script src links from HTML."""

        sources = re.findall(
            r"<script[^>]+src=[\"']([^\"']+)[\"']",
            payload,
            re.IGNORECASE,
        )

        return [self._normalize_url(src) for src in sources]

    def _extract_api_candidates(self, payload: str) -> list[str]:
        """Extract possible API endpoint candidates from HTML/JS text."""

        candidates: set[str] = set()

        patterns = [
            r"[\"']([^\"']*/api/[^\"']+)[\"']",
            r"[\"']([^\"']*PublicDisplay[^\"']+)[\"']",
            r"[\"']([^\"']*PvSystem[^\"']+)[\"']",
            r"[\"']([^\"']*Chart[^\"']+)[\"']",
            r"[\"']([^\"']*Energy[^\"']+)[\"']",
            r"[\"']([^\"']*Power[^\"']+)[\"']",
            r"[\"']([^\"']*Get[^\"']+)[\"']",
        ]

        for pattern in patterns:
            for match in re.findall(pattern, payload, re.IGNORECASE):
                cleaned = match.strip()
                if cleaned and len(cleaned) < 300:
                    candidates.add(self._normalize_url(cleaned))

        return sorted(candidates)

    def _normalize_url(self, value: str) -> str:
        """Normalize relative Solar.web URL."""

        value = value.strip()

        if value.startswith("//"):
            return f"https:{value}"

        if value.startswith("/"):
            return f"https://www.solarweb.com{value}"

        return value

    def _clean_preview(self, payload: str) -> str:
        """Return a short cleaned preview for diagnostics."""

        text = re.sub(r"<script\b[^<]*(?:(?!</script>)<[^<]*)*</script>", " ", payload, flags=re.IGNORECASE)
        text = re.sub(r"<style\b[^<]*(?:(?!</style>)<[^<]*)*</style>", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = self._clean_text(text)

        return text[:1000] if text else ""

    def _clean_text(self, value: str) -> str:
        """Clean extracted text."""

        value = re.sub(r"\s+", " ", value)
        value = value.replace("&amp;", "&")
        value = value.replace("&quot;", '"')
        value = value.replace("&#39;", "'")
        value = value.replace("&lt;", "<")
        value = value.replace("&gt;", ">")

        return value.strip()