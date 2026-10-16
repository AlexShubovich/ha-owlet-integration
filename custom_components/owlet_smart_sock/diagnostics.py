"""Diagnostics support for the Owlet Smart Sock integration."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from .coordinator import OwletConfigEntry

# Redact anything that could identify the account or the child.
TO_REDACT = {CONF_USERNAME, CONF_PASSWORD, "dsn", "serial_number", "title"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: OwletConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    return {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": dict(entry.options),
        },
        "devices": [
            async_redact_data(asdict(device), TO_REDACT)
            for device in coordinator.devices
        ],
        "data": {
            dsn: async_redact_data(asdict(sock), TO_REDACT)
            for dsn, sock in (coordinator.data or {}).items()
        },
    }
