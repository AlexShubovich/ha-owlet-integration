"""Async client for the Owlet Smart Sock cloud API.

The authentication handshake (Firebase -> owletdata mini-token -> Ayla access
token) and the vitals property parsing are ported from the original
``jlamendo/ha-sensor.owlet`` ``sensor.py`` and rewritten on top of ``aiohttp``
so the integration never blocks Home Assistant's event loop.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
import json
import logging
import time
from typing import Any

from aiohttp import ClientError, ClientResponseError, ClientSession, ClientTimeout

from homeassistant.util import dt as dt_util

from .const import (
    ANDROID_CERT,
    ANDROID_PACKAGE,
    FIREBASE_SIGNIN_URL,
    REGIONS,
    STATUS_CHARGED,
    STATUS_CHARGING,
    STATUS_DISCONNECTED,
    STATUS_ERROR,
    STATUS_MONITORING,
    STATUS_NO_SIGNAL,
)

_LOGGER = logging.getLogger(__name__)

# Alert property name -> friendly key exposed to Home Assistant.
ALERT_PROPERTIES: dict[str, str] = {
    "LOW_INTEG_READ": "low_integrity_reading",
    "LOW_BATT_ALRT": "low_battery",
    "HIGH_HR_ALRT": "high_heart_rate",
    "LOW_HR_ALRT": "low_heart_rate",
    "LOW_OX_ALRT": "low_oxygen",
    "SOCK_DISCON_ALRT": "sock_disconnected",
    "DISCOMFORT_ALRT": "discomfort",
}

REQUEST_TIMEOUT = ClientTimeout(total=30)


class OwletError(Exception):
    """Base error for the Owlet client."""


class OwletAuthenticationError(OwletError):
    """Raised when the Owlet credentials are rejected."""


class OwletConnectionError(OwletError):
    """Raised when the Owlet cloud cannot be reached."""


@dataclass
class OwletDevice:
    """Metadata describing a single Owlet device/account pairing."""

    dsn: str
    name: str
    model: str
    sw_version: str | None = None


@dataclass
class OwletSockData:
    """Normalised snapshot of a sock's vitals for one update cycle."""

    dsn: str
    status: str
    monitoring: bool = False
    heart_rate: int | None = None
    oxygen_saturation: int | None = None
    movement: int | None = None
    battery: int | None = None
    signal_strength: int | None = None
    charge_status: int | None = None
    base_station_on: bool | None = None
    alarm: str | None = None
    alerts: dict[str, bool] = field(default_factory=dict)
    updated_at: datetime | None = None


class OwletClient:
    """Minimal async wrapper around the Owlet cloud API."""

    def __init__(
        self,
        username: str,
        password: str,
        region: str,
        session: ClientSession,
    ) -> None:
        """Initialise the client for a single Owlet account."""
        self._username = username
        self._password = password
        self._region = region
        self._session = session
        self._config = REGIONS[region]

        self._token: str | None = None
        self._token_expires: float = 0.0
        self._auth_lock = asyncio.Lock()
        self._devices: list[OwletDevice] = []
        # Once credentials are rejected we refuse to contact the login
        # endpoints again. Owlet/Firebase rate-limit and can lock an account
        # for a long time if bad credentials are retried in a loop. The flag is
        # only cleared by a successful login; a reauth creates a fresh client.
        self._auth_failed = False

    @property
    def devices(self) -> list[OwletDevice]:
        """Return the devices discovered on the account."""
        return self._devices

    async def authenticate(self) -> None:
        """Run the full three-step login and cache an Ayla access token.

        If a previous attempt was rejected we fail fast without contacting the
        login servers again, so bad credentials can never be retried in a loop.
        """
        async with self._auth_lock:
            if self._auth_failed:
                raise OwletAuthenticationError(
                    "Owlet credentials were rejected; not retrying to avoid "
                    "locking the account. Re-enter your password to try again."
                )
            try:
                jwt = await self._firebase_login()
                mini_token = await self._owletdata_login(jwt)
                await self._ayla_login(mini_token)
            except OwletAuthenticationError:
                # Latch on rejected credentials. Transient connection errors
                # are not latched, so genuine outages still recover on their
                # own once connectivity returns.
                self._auth_failed = True
                raise

    async def _firebase_login(self) -> str:
        """Exchange credentials for a Firebase JWT (step 1)."""
        try:
            async with self._session.post(
                f"{FIREBASE_SIGNIN_URL}?key={self._config['api_key']}",
                json={
                    "email": self._username,
                    "password": self._password,
                    "returnSecureToken": True,
                },
                headers={
                    "X-Android-Package": ANDROID_PACKAGE,
                    "X-Android-Cert": ANDROID_CERT,
                },
                timeout=REQUEST_TIMEOUT,
            ) as resp:
                body = await resp.json(content_type=None)
                if resp.status == 400:
                    message = body.get("error", {}).get("message", "")
                    _LOGGER.debug("Firebase rejected credentials: %s", message)
                    raise OwletAuthenticationError(
                        f"Invalid Owlet credentials ({message})"
                    )
                resp.raise_for_status()
                return body["idToken"]
        except OwletError:
            raise
        except (TimeoutError, ClientError) as err:
            raise OwletConnectionError(
                f"Error contacting Firebase: {err}"
            ) from err
        except (KeyError, json.JSONDecodeError) as err:
            raise OwletAuthenticationError(
                "Unexpected response from Firebase sign-in"
            ) from err

    async def _owletdata_login(self, jwt: str) -> str:
        """Exchange the Firebase JWT for an owletdata mini-token (step 2)."""
        try:
            async with self._session.get(
                self._config["url_mini"],
                headers={"Authorization": jwt},
                timeout=REQUEST_TIMEOUT,
            ) as resp:
                resp.raise_for_status()
                return (await resp.json(content_type=None))["mini_token"]
        except ClientResponseError as err:
            if err.status in (401, 403):
                raise OwletAuthenticationError(
                    "owletdata.com rejected the session token"
                ) from err
            raise OwletConnectionError(
                f"Error contacting owletdata.com: {err}"
            ) from err
        except (TimeoutError, ClientError) as err:
            raise OwletConnectionError(
                f"Error contacting owletdata.com: {err}"
            ) from err
        except (KeyError, json.JSONDecodeError) as err:
            raise OwletAuthenticationError(
                "Unexpected response from owletdata.com"
            ) from err

    async def _ayla_login(self, mini_token: str) -> None:
        """Exchange the mini-token for an Ayla access token (step 3)."""
        try:
            async with self._session.post(
                self._config["url_signin"],
                json={
                    "app_id": self._config["app_id"],
                    "app_secret": self._config["app_secret"],
                    "provider": "owl_id",
                    "token": mini_token,
                },
                timeout=REQUEST_TIMEOUT,
            ) as resp:
                resp.raise_for_status()
                body = await resp.json(content_type=None)
                self._token = body["access_token"]
                # Refresh a minute before the real expiry for safety.
                self._token_expires = time.time() + body["expires_in"] - 60
        except ClientResponseError as err:
            if err.status in (401, 403):
                raise OwletAuthenticationError(
                    "Ayla rejected the Owlet mini-token"
                ) from err
            raise OwletConnectionError(f"Error contacting Ayla: {err}") from err
        except (TimeoutError, ClientError) as err:
            raise OwletConnectionError(f"Error contacting Ayla: {err}") from err
        except (KeyError, json.JSONDecodeError) as err:
            raise OwletAuthenticationError(
                "Unexpected response from Ayla sign-in"
            ) from err

    async def _async_ensure_token(self) -> None:
        """Re-authenticate when there is no token or it has expired."""
        if self._token is None or time.time() >= self._token_expires:
            await self.authenticate()

    async def _api_get(self, route: str) -> Any:
        """Perform an authenticated GET against the Ayla data service."""
        await self._async_ensure_token()
        url = f"{self._config['url_base']}{route}"
        try:
            async with self._session.get(
                url,
                headers={"Authorization": f"auth_token {self._token}"},
                timeout=REQUEST_TIMEOUT,
            ) as resp:
                if resp.status == 401:
                    # Token went stale early; refresh once and retry.
                    await self.authenticate()
                    async with self._session.get(
                        url,
                        headers={"Authorization": f"auth_token {self._token}"},
                        timeout=REQUEST_TIMEOUT,
                    ) as retry:
                        retry.raise_for_status()
                        return await retry.json(content_type=None)
                resp.raise_for_status()
                return await resp.json(content_type=None)
        except (TimeoutError, ClientError) as err:
            raise OwletConnectionError(f"Error calling {route}: {err}") from err

    async def _api_post(self, route: str, body: dict[str, Any]) -> None:
        """Perform an authenticated POST against the Ayla data service."""
        await self._async_ensure_token()
        url = f"{self._config['url_base']}{route}"
        try:
            async with self._session.post(
                url,
                json=body,
                headers={"Authorization": f"auth_token {self._token}"},
                timeout=REQUEST_TIMEOUT,
            ) as resp:
                resp.raise_for_status()
        except (TimeoutError, ClientError) as err:
            raise OwletConnectionError(f"Error calling {route}: {err}") from err

    async def async_get_devices(self) -> list[OwletDevice]:
        """Discover every sock registered to the account."""
        raw = await self._api_get("/devices.json")
        devices: list[OwletDevice] = []
        for entry in raw or []:
            device = entry.get("device", {})
            dsn = device.get("dsn")
            if not dsn:
                continue
            devices.append(
                OwletDevice(
                    dsn=dsn,
                    name=device.get("product_name")
                    or device.get("model")
                    or "Owlet Smart Sock",
                    model=device.get("model") or "Smart Sock",
                    sw_version=device.get("sw_version"),
                )
            )
        self._devices = devices
        return devices

    async def _async_activate_sock(self, dsn: str) -> None:
        """Ask the sock to start streaming real-time vitals."""
        try:
            await self._api_post(
                f"/dsns/{dsn}/properties/APP_ACTIVE/datapoints.json",
                {"datapoint": {"metadata": {}, "value": 1}},
            )
        except OwletConnectionError as err:
            # Activation is best-effort; log and continue to read whatever
            # the sock last reported.
            _LOGGER.debug("Could not activate sock %s: %s", dsn, err)

    async def async_get_vitals(self, dsn: str) -> OwletSockData:
        """Fetch and normalise the current vitals for a single sock."""
        await self._async_activate_sock(dsn)
        raw = await self._api_get(f"/dsns/{dsn}/properties.json")

        props: dict[str, dict[str, Any]] = {}
        for item in raw or []:
            prop = item.get("property", {})
            name = prop.get("name")
            if name:
                props[name] = prop

        return _parse_vitals(dsn, props)


def _prop_value(props: dict[str, dict[str, Any]], name: str) -> Any:
    """Return a raw property value or ``None`` when absent."""
    prop = props.get(name)
    if prop is None:
        return None
    return prop.get("value")


def _as_int(value: Any) -> int | None:
    """Best-effort conversion of a property value to ``int``."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_vitals(dsn: str, props: dict[str, dict[str, Any]]) -> OwletSockData:
    """Translate raw Ayla properties into an :class:`OwletSockData`.

    Handles both Smart Sock 3 (a single ``REAL_TIME_VITALS`` JSON blob) and
    Smart Sock 2 (discrete properties), mirroring the original integration.
    """
    heart_rate: int | None = None
    oxygen_saturation: int | None = None
    movement: int | None = None
    battery: int | None = None
    signal_strength: int | None = None
    charge_status: int | None = None
    base_station_on: int | None = None
    updated_at: datetime | None = None

    if "REAL_TIME_VITALS" in props:
        # Smart Sock 3
        try:
            rt = json.loads(props["REAL_TIME_VITALS"]["value"])
        except (json.JSONDecodeError, KeyError, TypeError):
            rt = {}
        heart_rate = _as_int(rt.get("hr"))
        oxygen_saturation = _as_int(rt.get("ox"))
        movement = _as_int(rt.get("mv"))
        battery = _as_int(rt.get("bat"))
        signal_strength = _as_int(rt.get("rsi"))
        charge_status = _as_int(rt.get("chg"))
        base_station_on = _as_int(rt.get("bso"))
        updated = props["REAL_TIME_VITALS"].get("data_updated_at")
        if updated:
            updated_at = dt_util.parse_datetime(updated)
    elif "CHARGE_STATUS" in props:
        # Smart Sock 2
        heart_rate = _as_int(_prop_value(props, "HEART_RATE"))
        oxygen_saturation = _as_int(_prop_value(props, "OXYGEN_LEVEL"))
        movement = _as_int(_prop_value(props, "MOVEMENT"))
        battery = _as_int(_prop_value(props, "BATT_LEVEL"))
        signal_strength = _as_int(_prop_value(props, "BLE_RSSI"))
        charge_status = _as_int(_prop_value(props, "CHARGE_STATUS"))
        base_station_on = _as_int(_prop_value(props, "BASE_STATION_ON"))
    else:
        # No recognisable vitals payload -> treat as an error state.
        return OwletSockData(dsn=dsn, status=STATUS_ERROR)

    alerts = {
        friendly: bool(_prop_value(props, raw_name))
        for raw_name, friendly in ALERT_PROPERTIES.items()
        if raw_name in props
    }

    alarm: str | None = None
    for level in ("HIGH", "MED", "LOW"):
        if _as_int(_prop_value(props, f"PREVIEW_{level}_PRIORITY_ALARM")) == 1:
            alarm = level.lower()
            break

    # --- Derive the overall status (ported truth table) --------------------
    low_hr_alert = alerts.get("low_heart_rate", False)
    low_ox_alert = alerts.get("low_oxygen", False)
    bpm_ok = bool(heart_rate and heart_rate > 0 and not low_hr_alert)
    spo2_ok = bool(
        oxygen_saturation and oxygen_saturation > 0 and not low_ox_alert
    )
    low_integrity = alerts.get("low_integrity_reading", False) or (
        not bpm_ok and not spo2_ok
    )
    base_station_dc = base_station_on != 1 and low_integrity

    if base_station_dc:
        status = STATUS_DISCONNECTED
    elif low_integrity:
        if charge_status == 1:
            status = STATUS_CHARGING
        elif charge_status == 2:
            status = STATUS_CHARGED
        else:
            status = STATUS_NO_SIGNAL
    else:
        status = STATUS_MONITORING

    monitoring = status == STATUS_MONITORING

    return OwletSockData(
        dsn=dsn,
        status=status,
        monitoring=monitoring,
        # Live vitals are only meaningful while the sock is actively reading.
        heart_rate=heart_rate if monitoring else None,
        oxygen_saturation=oxygen_saturation if monitoring else None,
        movement=movement if monitoring else None,
        battery=battery,
        signal_strength=signal_strength,
        charge_status=charge_status,
        base_station_on=(
            bool(base_station_on) if base_station_on is not None else None
        ),
        alarm=alarm,
        alerts=alerts,
        updated_at=updated_at,
    )
