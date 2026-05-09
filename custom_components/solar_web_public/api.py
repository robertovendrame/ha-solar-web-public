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
    def actual_data_url(self) -> str:
        """Return Solar.web public actual-data URL."""
        return (
            f"{self.BASE_URL}/ActualData/GetCompareDataForPublicDisplay"
            f"?PublicDisplayToken={self.token}"
        )

    @property
    def productions_url(self) -> str:
        """Return Solar.web productions and earnings URL."""
        return (
            f"{self.BASE_URL}/PvSystems/GetPvSystemProductionsAndEarningsForPublicDisplay"
            f"?token={self.token}"
        )

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

        actual_payload, actual_error = await self._safe_get_json(self.actual_data_url)
        productions_payload, productions_error = await self._safe_get_json(
            self.productions_url
        )
        chart_payload, chart_error = await self._safe_get_json(self.chart_url)

        actual_data = self._parse_actual_payload(actual_payload)
        production_data = self._parse_productions_payload(productions_payload)
        chart_data = self._parse_chart_payload(chart_payload)

        merged = {
            **page_data,
            **chart_data,
            **production_data,
            **actual_data,
        }

        merged.update(
            {
                "actual_data_url": self.actual_data_url,
                "actual_data_available": actual_payload is not None,
                "actual_data_error": actual_error,
                "actual_data_debug_keys": self._debug_keys(actual_payload),
                "actual_data_debug_preview": self._json_preview(actual_payload),
                "productions_url": self.productions_url,
                "productions_available": productions_payload is not None,
                "productions_error": productions_error,
                "productions_debug_keys": self._debug_keys(productions_payload),
                "productions_debug_preview": self._json_preview(productions_payload),
                "chart_url": self.chart_url,
                "chart_available": chart_payload is not None,
                "chart_error": chart_error,
                "chart_debug_keys": self._debug_keys(chart_payload),
                "chart_debug_preview": self._json_preview(chart_payload),
            }
        )

        return merged

    async def _safe_get_json(
        self,
        url: str,
    ) -> tuple[dict[str, Any] | list[Any] | None, str | None]:
        """Fetch JSON without failing the whole update."""

        try:
            payload = await self._async_get_json(url)
        except SolarWebPublicApiError as err:
            return None, str(err)

        return payload, None

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
                f"Solar.web returned non JSON response from {url}: {text[:300]}"
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
        peak_power_wp = self._extract_peak_power(payload)
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
            "peak_power_wp": peak_power_wp,
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
            "api_candidates": api_candidates[:60],
            "debug_preview": self._clean_preview(payload),
        }

    def _parse_actual_payload(
        self,
        payload: dict[str, Any] | list[Any] | None,
    ) -> dict[str, Any]:
        """Parse actual live data endpoint."""

        result: dict[str, Any] = {
            "current_power_w": None,
            "production_w": None,
            "consumption_w": None,
            "grid_power_w": None,
            "feed_in_w": None,
            "energy_from_grid_w": None,
            "battery_soc": None,
            "last_update": None,
        }

        if payload is None:
            return result

        flat = self._flatten_json(payload)

        result["current_power_w"] = self._find_number(
            flat,
            preferred_keys=[
                "currentpower",
                "actualpower",
                "currentpvpower",
                "pvpower",
                "pac",
                "powerac",
                "productionpower",
                "powerproduction",
                "pvanlageleistung",
                "leistung",
            ],
            deny_keys=[
                "chart",
                "axis",
                "series",
                "index",
                "count",
                "visible",
                "success",
                "error",
                "status",
                "percentage",
                "percent",
                "relative",
                "peak",
                "nominal",
                "installed",
            ],
            min_value=0,
            max_value=200000,
        )

        result["production_w"] = self._find_number(
            flat,
            preferred_keys=[
                "production",
                "pvproduction",
                "pvpower",
                "currentproduction",
                "actualproduction",
            ],
            deny_keys=[
                "today",
                "month",
                "year",
                "total",
                "energy",
                "earning",
                "money",
                "currency",
                "chart",
                "axis",
                "series",
            ],
            min_value=0,
            max_value=200000,
        )

        result["consumption_w"] = self._find_number(
            flat,
            preferred_keys=[
                "consumption",
                "load",
                "currentconsumption",
                "actualconsumption",
            ],
            deny_keys=[
                "today",
                "month",
                "year",
                "total",
                "energy",
                "earning",
                "money",
                "currency",
                "chart",
                "axis",
                "series",
            ],
            min_value=0,
            max_value=200000,
        )

        result["grid_power_w"] = self._find_number(
            flat,
            preferred_keys=[
                "gridpower",
                "grid",
                "fromgrid",
                "togrid",
                "feedin",
                "feedinpower",
                "feedpower",
                "powergrid",
            ],
            deny_keys=[
                "today",
                "month",
                "year",
                "total",
                "energy",
                "earning",
                "money",
                "currency",
                "chart",
                "axis",
                "series",
            ],
            min_value=-200000,
            max_value=200000,
        )

        result["battery_soc"] = self._find_number(
            flat,
            preferred_keys=[
                "batterysoc",
                "soc",
                "stateofcharge",
                "stateofchargepercentage",
                "batterypercentage",
            ],
            deny_keys=[
                "power",
                "energy",
                "voltage",
                "current",
            ],
            min_value=0,
            max_value=100,
        )

        result["last_update"] = self._find_string(
            flat,
            preferred_keys=[
                "lastupdate",
                "lastupdated",
                "timestamp",
                "datetime",
                "time",
                "date",
            ],
        )

        return result

    def _parse_productions_payload(
        self,
        payload: dict[str, Any] | list[Any] | None,
    ) -> dict[str, Any]:
        """Parse productions and earnings endpoint."""

        result: dict[str, Any] = {
            "today_energy_kwh": None,
            "month_energy_kwh": None,
            "year_energy_kwh": None,
            "total_energy_kwh": None,
            "today_earning": None,
            "month_earning": None,
            "year_earning": None,
            "total_earning": None,
        }

        if payload is None:
            return result

        flat = self._flatten_json(payload)

        result["today_energy_kwh"] = self._find_number(
            flat,
            preferred_keys=[
                "productiontoday",
                "todayproduction",
                "energytoday",
                "todayenergy",
                "dayproduction",
                "productionday",
                "produzioneoggi",
                "oggi",
            ],
            deny_keys=[
                "earning",
                "earnings",
                "money",
                "currency",
                "eur",
                "euro",
                "co2",
            ],
            min_value=0,
            max_value=1000000,
            convert_wh_to_kwh=True,
        )

        result["month_energy_kwh"] = self._find_number(
            flat,
            preferred_keys=[
                "productionmonth",
                "monthproduction",
                "energymonth",
                "monthenergy",
            ],
            deny_keys=[
                "earning",
                "earnings",
                "money",
                "currency",
                "eur",
                "euro",
                "co2",
            ],
            min_value=0,
            max_value=10000000,
            convert_wh_to_kwh=True,
        )

        result["year_energy_kwh"] = self._find_number(
            flat,
            preferred_keys=[
                "productionyear",
                "yearproduction",
                "energyyear",
                "yearenergy",
            ],
            deny_keys=[
                "earning",
                "earnings",
                "money",
                "currency",
                "eur",
                "euro",
                "co2",
            ],
            min_value=0,
            max_value=100000000,
            convert_wh_to_kwh=True,
        )

        result["total_energy_kwh"] = self._find_number(
            flat,
            preferred_keys=[
                "productiontotal",
                "totalproduction",
                "energytotal",
                "totalenergy",
                "overallproduction",
                "lifetimeproduction",
            ],
            deny_keys=[
                "earning",
                "earnings",
                "money",
                "currency",
                "eur",
                "euro",
                "co2",
            ],
            min_value=0,
            max_value=1000000000,
            convert_wh_to_kwh=True,
        )

        result["today_earning"] = self._find_number(
            flat,
            preferred_keys=[
                "earningtoday",
                "todayearning",
                "savingtoday",
                "todaysaving",
            ],
            min_value=0,
            max_value=1000000,
        )

        result["month_earning"] = self._find_number(
            flat,
            preferred_keys=[
                "earningmonth",
                "monthearning",
                "savingmonth",
                "monthsaving",
            ],
            min_value=0,
            max_value=1000000,
        )

        result["year_earning"] = self._find_number(
            flat,
            preferred_keys=[
                "earningyear",
                "yearearning",
                "savingyear",
                "yearsaving",
            ],
            min_value=0,
            max_value=1000000,
        )

        result["total_earning"] = self._find_number(
            flat,
            preferred_keys=[
                "earningtotal",
                "totalearning",
                "savingtotal",
                "totalsaving",
            ],
            min_value=0,
            max_value=10000000,
        )

        return result

    def _parse_chart_payload(
        self,
        payload: dict[str, Any] | list[Any] | None,
    ) -> dict[str, Any]:
        """Parse chart endpoint only as fallback.

        Avoid using generic chart numbers as live sensors, because the chart
        contains hours, indexes and plotted series that can be mistaken for
        power values.
        """

        result: dict[str, Any] = {
            "chart_last_update": None,
        }

        if payload is None:
            return result

        flat = self._flatten_json(payload)

        result["chart_last_update"] = self._find_string(
            flat,
            preferred_keys=[
                "lastupdate",
                "lastupdated",
                "timestamp",
                "datetime",
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
        min_value: float | None = None,
        max_value: float | None = None,
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
                normalized_preferred = self._normalize_key(preferred)
                if normalized_preferred in normalized_key:
                    score += 20
                elif normalized_key.endswith(normalized_preferred):
                    score += 10

            if score <= 0:
                continue

            number = self._to_number(value)
            if number is None:
                continue

            if min_value is not None and number < min_value:
                continue

            if max_value is not None and number > max_value:
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

            if not any(
                self._normalize_key(preferred) in normalized_key
                for preferred in preferred_keys
            ):
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

        if isinstance(value, (int, float)):
            return float(value)

        if isinstance(value, str):
            cleaned = value.strip()
            cleaned = cleaned.replace("\u00a0", "")
            cleaned = cleaned.replace(" ", "")

            if "," in cleaned and "." in cleaned:
                cleaned = cleaned.replace(".", "")
                cleaned = cleaned.replace(",", ".")
            elif "," in cleaned:
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

        title = self._extract_title(payload)
        if title:
            return title

        return None

    def _extract_location(self, payload: str) -> str | None:
        """Extract location from public page."""

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

    def _extract_peak_power(self, payload: str) -> int | None:
        """Extract peak power from inline config."""

        match = re.search(
            r"peakPower\s*:\s*([0-9]+)",
            payload,
            re.IGNORECASE,
        )

        if match:
            return int(match.group(1))

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
            r"(\/ActualData\/GetCompareDataForPublicDisplay\?PublicDisplayToken=[a-fA-F0-9-]{36})",
            r"(\/Chart\/GetWidgetChartForPublicDisplay\?publicDisplayToken=[a-fA-F0-9-]{36})",
            r"(\/PvSystems\/GetPvSystemProductionsAndEarningsForPublicDisplay\?token=[a-fA-F0-9-]{36})",
            r"(\/PvSystems\/GetWeatherWidgetDataForPublicDisplay\?publicDisplayToken=[a-fA-F0-9-]{36})",
            r"(\/PvSystemImages\/GetUrlForPublicDisplayToken\?token=[a-fA-F0-9-]{36})",
        ]

        for pattern in patterns:
            for match in re.findall(pattern, payload, re.IGNORECASE):
                cleaned = match.strip()
                if cleaned:
                    candidates.add(self._normalize_url(cleaned))

        candidates.add(self.actual_data_url)
        candidates.add(self.productions_url)
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
        value = value.replace("&copy;", "©")

        return value.strip()

    def _debug_keys(self, payload: Any) -> list[str]:
        """Return top-level debug keys."""

        if isinstance(payload, dict):
            return list(payload.keys())[:80]

        if isinstance(payload, list):
            return [f"list[{len(payload)}]"]

        return []

    def _json_preview(self, payload: Any) -> str | None:
        """Return short JSON preview."""

        if payload is None:
            return None

        try:
            return json.dumps(payload, ensure_ascii=False)[:3000]
        except TypeError:
            return str(payload)[:3000]