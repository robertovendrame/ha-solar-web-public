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

    BASE_URL = "https://www.solarweb.com"

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
        return f"{self.BASE_URL}/PublicDisplay/PvSystem?token={self.token}"

    @property
    def chart_url(self) -> str:
        """Return Solar.web public chart URL."""
        return (
            f"{self.BASE_URL}/Chart/GetWidgetChartForPublicDisplay"
            f"?publicDisplayToken={self.token}"
        )

    @property
    def weather_url(self) -> str:
        """Return Solar.web public weather URL."""
        return (
            f"{self.BASE_URL}/PvSystems/GetWeatherWidgetDataForPublicDisplay"
            f"?publicDisplayToken={self.token}"
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
        """Fetch all available data from Solar.web public page."""

        page_payload, content_type, final_url = await self._async_get_text(
            self.shared_url,
            accept="text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        )

        page_data = self._parse_page(
            payload=page_payload,
            content_type=content_type,
            final_url=final_url,
        )

        chart_payload: dict[str, Any] | list[Any] | None = None
        chart_error: str | None = None

        try:
            chart_payload = await self._async_get_json(self.chart_url)
        except SolarWebPublicApiError as err:
            chart_error = str(err)

        chart_data = self._parse_chart_payload(chart_payload)

        return {
            **page_data,
            **chart_data,
            "chart_url": self.chart_url,
            "chart_error": chart_error,
            "chart_available": chart_payload is not None,
            "chart_debug_keys": self._debug_keys(chart_payload),
            "chart_debug_preview": self._json_preview(chart_payload),
        }

    async def _async_get_text(
        self,
        url: str,
        accept: str,
    ) -> tuple[str, str, str]:
        """Fetch text from URL."""

        headers = {
            "User-Agent": "HomeAssistant-SolarWebPublic/0.1",
            "Accept": accept,
            "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
        }

        try:
            async with self._session.get(
                url,
                headers=headers,
                allow_redirects=True,
            ) as response:
                if response.status >= 400:
                    raise SolarWebPublicApiError(
                        f"Solar.web returned HTTP {response.status} for {url}"
                    )

                content_type = response.headers.get("content-type", "")
                final_url = str(response.url)
                payload = await response.text()

        except aiohttp.ClientError as err:
            raise SolarWebPublicApiError(f"Connection error: {err}") from err

        return payload, content_type, final_url

    async def _async_get_json(self, url: str) -> dict[str, Any] | list[Any]:
        """Fetch JSON from URL."""

        headers = {
            "User-Agent": "HomeAssistant-SolarWebPublic/0.1",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": self.shared_url,
        }

        try:
            async with self._session.get(
                url,
                headers=headers,
                allow_redirects=True,
            ) as response:
                if response.status >= 400:
                    raise SolarWebPublicApiError(
                        f"Solar.web returned HTTP {response.status} for {url}"
                    )

                text = await response.text()

        except aiohttp.ClientError as err:
            raise SolarWebPublicApiError(f"Connection error: {err}") from err

        try:
            return json.loads(text)
        except json.JSONDecodeError as err:
            raise SolarWebPublicApiError(
                f"Solar.web returned non JSON response from {url}: {text[:200]}"
            ) from err

    def _parse_page(
        self,
        payload: str,
        content_type: str,
        final_url: str,
    ) -> dict[str, Any]:
        """Parse Solar.web public HTML page."""

        plant_name = self._extract_plant_name(payload)
        location = self._extract_location(payload)
        page_title = self._extract_title(payload)
        pv_system_id = self._extract_pv_system_id(payload)
        script_sources = self._extract_script_sources(payload)
        api_candidates = self._extract_api_candidates(payload)

        return {
            "status": "online" if payload else "unknown",
            "configured_token": self.token,
            "token": self.token,
            "input_url": self._input_url,
            "final_url": final_url,
            "plant_name": plant_name,
            "location": location,
            "page_title": page_title,
            "pv_system_id": pv_system_id,
            "content_type": content_type,
            "payload_length": len(payload),
            "has_api": "/api/" in payload.lower(),
            "has_public_display": "publicdisplay" in payload.lower(),
            "has_current_power": (
                "current" in payload.lower()
                and "power" in payload.lower()
            )
            or (
                "alimentazione" in payload.lower()
                and "corrente" in payload.lower()
            ),
            "has_pv_system": (
                "pvsystem" in payload.lower()
                or "pv-system" in payload.lower()
                or "pv_system" in payload.lower()
            ),
            "script_count": len(script_sources),
            "script_sources": script_sources[:30],
            "api_candidates": api_candidates[:50],
            "debug_preview": self._clean_preview(payload),
        }

    def _parse_chart_payload(
        self,
        payload: dict[str, Any] | list[Any] | None,
    ) -> dict[str, Any]:
        """Parse chart JSON payload.

        This parser is intentionally defensive because Solar.web can change
        field names. It scans the whole JSON tree and extracts the most likely
        numeric values.
        """

        result: dict[str, Any] = {
            "current_power_w": None,
            "today_energy_kwh": None,
            "total_energy_kwh": None,
            "battery_soc": None,
            "grid_power_w": None,
            "production_w": None,
            "consumption_w": None,
            "feed_in_w": None,
            "energy_from_grid_w": None,
            "last_update": None,
        }

        if payload is None:
            return result

        flat = self._flatten_json(payload)

        result["current_power_w"] = self._find_number(
            flat,
            preferred_keys=[
                "currentpower",
                "current_power",
                "powercurrent",
                "pac",
                "p_ac",
                "productionpower",
                "production_power",
                "pvpower",
                "pv_power",
                "power",
            ],
            deny_keys=[
                "max",
                "min",
                "axis",
                "scale",
                "nominal",
                "installed",
                "weather",
                "forecast",
                "expected",
            ],
        )

        result["production_w"] = self._find_number(
            flat,
            preferred_keys=[
                "production",
                "pvproduction",
                "pv_power",
                "pvpower",
                "produzione",
            ],
            deny_keys=[
                "today",
                "month",
                "year",
                "total",
                "energy",
                "earning",
                "forecast",
                "expected",
            ],
        )

        result["consumption_w"] = self._find_number(
            flat,
            preferred_keys=[
                "consumption",
                "load",
                "verbrauch",
                "consumo",
            ],
            deny_keys=[
                "today",
                "month",
                "year",
                "total",
                "energy",
                "forecast",
                "expected",
            ],
        )

        result["grid_power_w"] = self._find_number(
            flat,
            preferred_keys=[
                "grid",
                "gridpower",
                "grid_power",
                "fromgrid",
                "to_grid",
                "togrid",
                "feedin",
                "feed_in",
            ],
            deny_keys=[
                "today",
                "month",
                "year",
                "total",
                "energy",
                "earning",
            ],
        )

        result["today_energy_kwh"] = self._find_number(
            flat,
            preferred_keys=[
                "today",
                "day",
                "energytoday",
                "energy_today",
                "productiontoday",
                "production_today",
                "produzionegiorno",
            ],
            deny_keys=[
                "earning",
                "money",
                "currency",
                "euro",
                "eur",
            ],
            convert_wh_to_kwh=True,
        )

        result["total_energy_kwh"] = self._find_number(
            flat,
            preferred_keys=[
                "total",
                "overall",
                "lifetime",
                "energytotal",
                "energy_total",
                "productiontotal",
                "production_total",
            ],
            deny_keys=[
                "earning",
                "money",
                "currency",
                "euro",
                "eur",
            ],
            convert_wh_to_kwh=True,
        )

        result["battery_soc"] = self._find_number(
            flat,
            preferred_keys=[
                "battery",
                "soc",
                "stateofcharge",
                "state_of_charge",
            ],
            deny_keys=[
                "power",
                "energy",
                "voltage",
                "current",
            ],
        )

        result["last_update"] = self._find_string(
            flat,
            preferred_keys=[
                "lastupdate",
                "last_update",
                "timestamp",
                "time",
                "date",
            ],
        )

        return result

    def _flatten_json(
        self,
        value: Any,
        prefix: str = "",
    ) -> list[tuple[str, Any]]:
        """Flatten JSON object into key path/value pairs."""

        items: list[tuple[str, Any]] = []

        if isinstance(value, dict):
            for key, child in value.items():
                child_prefix = f"{prefix}.{key}" if prefix else str(key)
                items.extend(self._flatten_json(child, child_prefix))
            return items

        if isinstance(value, list):
            for index, child in enumerate(value):
                child_prefix = f"{prefix}[{index}]"
                items.extend(self._flatten_json(child, child_prefix))
            return items

        items.append((prefix, value))
        return items

    def _find_number(
        self,
        flat: list[tuple[str, Any]],
        preferred_keys: list[str],
        deny_keys: list[str] | None = None,
        convert_wh_to_kwh: bool = False,
    ) -> float | int | None:
        """Find a likely numeric value by key name."""

        deny_keys = deny_keys or []

        candidates: list[tuple[int, str, float]] = []

        for key, value in flat:
            normalized_key = self._normalize_key(key)

            if any(deny in normalized_key for deny in deny_keys):
                continue

            score = 0
            for preferred in preferred_keys:
                if preferred in normalized_key:
                    score += 10

            if score <= 0:
                continue

            number = self._to_number(value)
            if number is None:
                continue

            if convert_wh_to_kwh and self._looks_like_wh(normalized_key, number):
                number = number / 1000

            candidates.append((score, normalized_key, number))

        if not candidates:
            return None

        candidates.sort(key=lambda item: item[0], reverse=True)
        value = candidates[0][2]

        if value.is_integer():
            return int(value)

        return round(value, 3)

    def _find_string(
        self,
        flat: list[tuple[str, Any]],
        preferred_keys: list[str],
    ) -> str | None:
        """Find a likely string value by key name."""

        for key, value in flat:
            normalized_key = self._normalize_key(key)

            if not any(preferred in normalized_key for preferred in preferred_keys):
                continue

            if isinstance(value, str) and value.strip():
                return value.strip()

        return None

    def _looks_like_wh(self, key: str, value: float) -> bool:
        """Guess whether an energy value is Wh and should be converted to kWh."""

        if "kwh" in key:
            return False

        if "wh" in key:
            return True

        return abs(value) > 10000

    def _to_number(self, value: Any) -> float | None:
        """Convert value to number."""

        if isinstance(value, bool):
            return None

        if isinstance(value, int | float):
            return float(value)

        if isinstance(value, str):
            cleaned = value.strip()
            cleaned = cleaned.replace(".", "")
            cleaned = cleaned.replace(",", ".")
            cleaned = re.sub(r"[^0-9.\-]", "", cleaned)

            if cleaned in ["", "-", ".", "-."]:
                return None

            try:
                return float(cleaned)
            except ValueError:
                return None

        return None

    def _normalize_key(self, key: str) -> str:
        """Normalize a key path."""

        return re.sub(r"[^a-z0-9]+", "", key.lower())

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

        # Specific Solar.web public header:
        # <div class="pd-header-text">SOLAR.WEB</div>
        # <div class="pd-header-text">Bricchese Manuel</div>
        match = re.search(
            r'<div[^>]*class=["\'][^"\']*pd-header-text[^"\']*["\'][^>]*>\s*SOLAR\.WEB\s*</div>\s*'
            r'<div[^>]*class=["\'][^"\']*pd-header-text[^"\']*["\'][^>]*>\s*(.*?)\s*</div>',
            payload,
            re.IGNORECASE | re.DOTALL,
        )

        if match:
            value = self._clean_text(match.group(1))
            if value:
                return value

        # Fallback: widget title near plant image.
        match = re.search(
            r'<div[^>]*class=["\'][^"\']*pd-widget-title[^"\']*["\'][^>]*>\s*([^<]+?)\s*</div>\s*'
            r'<div[^>]*class=["\'][^"\']*pd-widget-body[^"\']*["\'][^>]*>\s*'
            r'<div[^>]*data-pvsystemid=',
            payload,
            re.IGNORECASE | re.DOTALL,
        )

        if match:
            value = self._clean_text(match.group(1))
            if value:
                return value

        title = self._extract_title(payload)
        if title:
            return title

        return None

    def _extract_location(self, payload: str) -> str | None:
        """Extract location from public page."""

        # Specific Solar.web public weather widget title:
        # <div class="pd-widget-title mod-left">Portogruaro</div>
        match = re.search(
            r'<div[^>]*class=["\'][^"\']*pd-widget-title[^"\']*mod-left[^"\']*["\'][^>]*>\s*(.*?)\s*</div>',
            payload,
            re.IGNORECASE | re.DOTALL,
        )

        if match:
            value = self._clean_text(match.group(1))
            if value:
                return value

        return None

    def _extract_pv_system_id(self, payload: str) -> str | None:
        """Extract PV system ID from public page."""

        match = re.search(
            r'data-pvsystemid=["\']([a-fA-F0-9-]{36})["\']',
            payload,
            re.IGNORECASE,
        )

        if match:
            return match.group(1)

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
            r"[\"']([^\"']*PvSystems[^\"']+)[\"']",
            r"[\"']([^\"']*Chart[^\"']+)[\"']",
            r"[\"']([^\"']*Energy[^\"']+)[\"']",
            r"[\"']([^\"']*Power[^\"']+)[\"']",
            r"[\"']([^\"']*Get[^\"']+)[\"']",
            r"(\/Chart\/GetWidgetChartForPublicDisplay\?publicDisplayToken=[a-fA-F0-9-]{36})",
            r"(\/PvSystems\/GetWeatherWidgetDataForPublicDisplay\?publicDisplayToken=[a-fA-F0-9-]{36})",
            r"(\/PvSystemImages\/GetUrlForPublicDisplayToken\?token=[a-fA-F0-9-]{36})",
        ]

        for pattern in patterns:
            for match in re.findall(pattern, payload, re.IGNORECASE):
                cleaned = match.strip()
                if cleaned and len(cleaned) < 500:
                    candidates.add(self._normalize_url(cleaned))

        # Force known public endpoints found in the Solar.web page.
        candidates.add(self.chart_url)
        candidates.add(self.weather_url)
        candidates.add(
            f"{self.BASE_URL}/PvSystemImages/GetUrlForPublicDisplayToken"
            f"?token={self.token}"
        )

        return sorted(candidates)

    def _normalize_url(self, value: str) -> str:
        """Normalize relative Solar.web URL."""

        value = value.strip()

        if value.startswith("//"):
            return f"https:{value}"

        if value.startswith("/"):
            return f"{self.BASE_URL}{value}"

        return value

    def _clean_preview(self, payload: str) -> str:
        """Return a short cleaned preview for diagnostics."""

        text = re.sub(
            r"<script\b[^<]*(?:(?!</script>)<[^<]*)*</script>",
            " ",
            payload,
            flags=re.IGNORECASE,
        )
        text = re.sub(
            r"<style\b[^<]*(?:(?!</style>)<[^<]*)*</style>",
            " ",
            text,
            flags=re.IGNORECASE,
        )
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
        value = value.replace("&#232;", "è")
        value = value.replace("&egrave;", "è")
        value = value.replace("&agrave;", "à")
        value = value.replace("&ograve;", "ò")
        value = value.replace("&ugrave;", "ù")
        value = value.replace("&igrave;", "ì")

        return value.strip()

    def _debug_keys(self, payload: Any) -> list[str]:
        """Return top-level debug keys."""

        if isinstance(payload, dict):
            return list(payload.keys())[:50]

        if isinstance(payload, list):
            return [f"list[{len(payload)}]"]

        return []

    def _json_preview(self, payload: Any) -> str | None:
        """Return short JSON preview."""

        if payload is None:
            return None

        try:
            return json.dumps(payload, ensure_ascii=False)[:2000]
        except TypeError:
            return str(payload)[:2000]