"""API client for Solar Web Public."""

from __future__ import annotations

import hashlib
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
        return hashlib.sha256(self._token.encode()).hexdigest()[:16]

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

        if actual_data.get("is_online") is False:
            merged["status"] = "offline"
        elif actual_data.get("is_online") is True:
            merged["status"] = "online"

        merged.update(
            {
                "actual_data_url": self._redact_url(self.actual_data_url),
                "actual_data_available": actual_payload is not None,
                "actual_data_error": actual_error,
                "actual_data_debug_keys": self._debug_keys(actual_payload),
                "productions_url": self._redact_url(self.productions_url),
                "productions_available": productions_payload is not None,
                "productions_error": productions_error,
                "productions_debug_keys": self._debug_keys(productions_payload),
                "chart_url": self._redact_url(self.chart_url),
                "chart_available": chart_payload is not None,
                "chart_error": chart_error,
                "chart_debug_keys": self._debug_keys(chart_payload),
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
                    safe_url = self._redact_url(url)
                    raise SolarWebPublicApiError(
                        f"Solar.web returned HTTP {response.status} for {safe_url}"
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
                    safe_url = self._redact_url(url)
                    raise SolarWebPublicApiError(
                        f"Solar.web returned HTTP {response.status} for {safe_url}"
                    )

                text = await response.text()

        except aiohttp.ClientError as err:
            raise SolarWebPublicApiError(f"Connection error: {err}") from err

        try:
            return json.loads(text)
        except json.JSONDecodeError as err:
            safe_url = self._redact_url(url)
            raise SolarWebPublicApiError(
                f"Solar.web returned non JSON response from {safe_url}: {text[:300]}"
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
            "input_url": self._redact_url(self._input_url),
            "final_url": self._redact_url(final_url),
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
            "api_candidates": api_candidates[:60],
        }

    def _redact_url(self, value: str | None) -> str | None:
        """Redact Solar.web token parameters from URLs."""
        if value is None:
            return None

        return re.sub(
            r"([?&](?:token|PublicDisplayToken|publicDisplayToken)=)[^&]+",
            r"\1***",
            value,
            flags=re.IGNORECASE,
        )

    def _parse_actual_payload(
        self,
        payload: dict[str, Any] | list[Any] | None,
    ) -> dict[str, Any]:
        """Parse actual live data endpoint.

        Known payload example:
        {
          "IsOnline": true,
          "AllOnline": true,
          "P_Grid": -5472.2,
          "P_Load": -628.38,
          "P_Batt": 6.79,
          "SOC": 100.0,
          "P_PV": 6093.79
        }
        """

        result: dict[str, Any] = {
            "is_online": None,
            "all_online": None,
            "current_power_w": None,
            "production_w": None,
            "consumption_w": None,
            "grid_power_w": None,
            "feed_in_w": None,
            "energy_from_grid_w": None,
            "battery_power_w": None,
            "battery_soc": None,
            "battery_mode": None,
            "last_update": None,
        }

        if not isinstance(payload, dict):
            return result

        is_online = payload.get("IsOnline")
        all_online = payload.get("AllOnline")

        p_pv = self._to_number(payload.get("P_PV"))
        p_load = self._to_number(payload.get("P_Load"))
        p_grid = self._to_number(payload.get("P_Grid"))
        p_batt = self._to_number(payload.get("P_Batt"))
        soc = self._to_number(payload.get("SOC"))
        bat_mode = self._to_number(payload.get("BatMode"))

        result["is_online"] = is_online if isinstance(is_online, bool) else None
        result["all_online"] = all_online if isinstance(all_online, bool) else None

        if p_pv is not None:
            result["current_power_w"] = self._round_power(p_pv)
            result["production_w"] = self._round_power(p_pv)

        if p_load is not None:
            # Solar.web public endpoint may expose load as negative.
            result["consumption_w"] = self._round_power(abs(p_load))

        if p_grid is not None:
            # Negative usually means feed-in/export to grid.
            # Positive usually means import from grid.
            result["grid_power_w"] = self._round_power(p_grid)
            result["feed_in_w"] = self._round_power(abs(p_grid)) if p_grid < 0 else 0
            result["energy_from_grid_w"] = self._round_power(p_grid) if p_grid > 0 else 0

        if p_batt is not None:
            result["battery_power_w"] = self._round_power(p_batt)

        if soc is not None:
            result["battery_soc"] = self._round_percent(soc)

        if bat_mode is not None:
            result["battery_mode"] = int(bat_mode)

        return result

    def _parse_productions_payload(
        self,
        payload: dict[str, Any] | list[Any] | None,
    ) -> dict[str, Any]:
        """Parse productions and earnings endpoint.

        Known payload example:
        {
          "data": {
            "Productions": {
              "TotalUnit": "MWh",
              "MonthUnit": "kWh",
              "YearUnit": "kWh",
              "TodayUnit": "kWh",
              "Total": "17,21",
              "Month": "334,91",
              "Year": "3.322,98",
              "Today": "25,74"
            },
            "Earnings": {
              "IsoCurrency": "EUR",
              "Total": "1.459,54",
              "Month": "32,96",
              "Year": "400,24",
              "Today": "2,06"
            }
          }
        }
        """

        result: dict[str, Any] = {
            "today_energy_kwh": None,
            "month_energy_kwh": None,
            "year_energy_kwh": None,
            "total_energy_kwh": None,
            "today_earning": None,
            "month_earning": None,
            "year_earning": None,
            "total_earning": None,
            "earning_currency": None,
            "today_energy_label": None,
            "month_energy_label": None,
            "year_energy_label": None,
            "total_energy_label": None,
        }

        if not isinstance(payload, dict):
            return result

        data = payload.get("data")
        if not isinstance(data, dict):
            return result

        productions = data.get("Productions")
        earnings = data.get("Earnings")

        if isinstance(productions, dict):
            result["today_energy_kwh"] = self._energy_to_kwh(
                productions.get("Today"),
                productions.get("TodayUnit"),
            )
            result["month_energy_kwh"] = self._energy_to_kwh(
                productions.get("Month"),
                productions.get("MonthUnit"),
            )
            result["year_energy_kwh"] = self._energy_to_kwh(
                productions.get("Year"),
                productions.get("YearUnit"),
            )
            result["total_energy_kwh"] = self._energy_to_kwh(
                productions.get("Total"),
                productions.get("TotalUnit"),
            )

            result["today_energy_label"] = productions.get("TodayLabel")
            result["month_energy_label"] = productions.get("MonthLabel")
            result["year_energy_label"] = productions.get("YearLabel")
            result["total_energy_label"] = productions.get("TotalLabel")

        if isinstance(earnings, dict):
            result["today_earning"] = self._round_money(
                self._to_number(earnings.get("Today"))
            )
            result["month_earning"] = self._round_money(
                self._to_number(earnings.get("Month"))
            )
            result["year_earning"] = self._round_money(
                self._to_number(earnings.get("Year"))
            )
            result["total_earning"] = self._round_money(
                self._to_number(earnings.get("Total"))
            )
            result["earning_currency"] = earnings.get("IsoCurrency")

        return result

    def _parse_chart_payload(
        self,
        payload: dict[str, Any] | list[Any] | None,
    ) -> dict[str, Any]:
        """Parse chart endpoint only for graph metadata."""

        result: dict[str, Any] = {
            "chart_last_update": None,
            "chart_has_meter": None,
            "chart_to_grid_kwh": None,
            "chart_from_grid_kwh": None,
        }

        if not isinstance(payload, dict):
            return result

        result["chart_has_meter"] = payload.get("hasMeter")

        to_grid = self._to_number(payload.get("toGrid"))
        from_grid = self._to_number(payload.get("fromGrid"))

        if to_grid is not None:
            result["chart_to_grid_kwh"] = round(to_grid, 3)

        if from_grid is not None:
            result["chart_from_grid_kwh"] = round(from_grid, 3)

        return result

    def _energy_to_kwh(
        self,
        value: Any,
        unit: Any,
    ) -> float | int | None:
        """Convert Solar.web energy value to kWh."""

        number = self._to_number(value)
        if number is None:
            return None

        unit_string = str(unit or "").strip().lower()

        if unit_string == "wh":
            number = number / 1000
        elif unit_string == "mwh":
            number = number * 1000
        elif unit_string == "gwh":
            number = number * 1000000
        # kWh or missing unit: keep as-is

        return self._round_energy(number)

    def _round_power(self, value: float) -> int:
        """Round power value to W integer."""

        return int(round(value))

    def _round_energy(self, value: float) -> float | int:
        """Round energy value."""

        rounded = round(value, 3)
        if rounded.is_integer():
            return int(rounded)
        return rounded

    def _round_percent(self, value: float) -> float | int:
        """Round percentage."""

        rounded = round(value, 1)
        if rounded.is_integer():
            return int(rounded)
        return rounded

    def _round_money(self, value: float | None) -> float | int | None:
        """Round money value."""

        if value is None:
            return None

        rounded = round(value, 2)
        if rounded.is_integer():
            return int(rounded)
        return rounded

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
            cleaned = re.sub(r"[^0-9,\.\-]", "", cleaned)

            if cleaned in ["", "-", ".", ",", "-.", "-,"]:
                return None

            last_comma = cleaned.rfind(",")
            last_dot = cleaned.rfind(".")

            if last_comma != -1 and last_dot != -1:
                if last_comma > last_dot:
                    cleaned = cleaned.replace(".", "")
                    cleaned = cleaned.replace(",", ".")
                else:
                    cleaned = cleaned.replace(",", "")
            elif last_comma != -1:
                cleaned = cleaned.replace(",", ".")
            elif last_dot != -1 and cleaned.count(".") > 1:
                cleaned = cleaned.replace(".", "")

            try:
                return float(cleaned)
            except ValueError:
                return None

        return None

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
                    normalized = self._normalize_url(cleaned)
                    redacted = self._redact_url(normalized)
                    if redacted:
                        candidates.add(redacted)

        candidates.add(self._redact_url(self.actual_data_url) or self.actual_data_url)
        candidates.add(self._redact_url(self.productions_url) or self.productions_url)
        candidates.add(self._redact_url(self.chart_url) or self.chart_url)
        candidates.add(self._redact_url(self.weather_url) or self.weather_url)
        candidates.add(
            self._redact_url(
                f"{self.BASE_URL}/PvSystemImages/GetUrlForPublicDisplayToken"
                f"?token={self.token}"
            )
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