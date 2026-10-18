"""The Owlet Smart Sock integration."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import OwletConfigEntry, OwletCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.SWITCH,
]

# Lovelace card shipped with the integration and auto-registered so that
# `type: custom:owlet-sock-card` works without any manual resource setup.
CARD_FILENAME = "owlet-sock-card.js"
CARD_URL = f"/{DOMAIN}/{CARD_FILENAME}"
CARD_VERSION = "2.0.5"


async def async_setup_entry(hass: HomeAssistant, entry: OwletConfigEntry) -> bool:
    """Set up Owlet Smart Sock from a config entry."""
    coordinator = OwletCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await _async_register_card(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: OwletConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(
    hass: HomeAssistant, entry: OwletConfigEntry
) -> None:
    """Reload the entry when its options change (e.g. scan interval)."""
    await hass.config_entries.async_reload(entry.entry_id)


async def _async_register_card(hass: HomeAssistant) -> None:
    """Serve and load the bundled Lovelace card exactly once."""
    registered = hass.data.setdefault(DOMAIN, {})
    if registered.get("card_registered"):
        return

    card_path = Path(__file__).parent / "www" / CARD_FILENAME
    try:
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    CARD_URL, str(card_path), cache_headers=False
                )
            ]
        )
        # Cache-bust on version changes so browsers pick up new card code.
        add_extra_js_url(hass, f"{CARD_URL}?v={CARD_VERSION}")
        registered["card_registered"] = True
        _LOGGER.debug("Registered Owlet Lovelace card at %s", CARD_URL)
    except Exception as err:  # noqa: BLE001 - never block setup over the card
        # Logged once at setup; visible so a missing card is easy to diagnose.
        _LOGGER.warning(
            "Could not register the Owlet dashboard card (%s). You can add it "
            "manually as a dashboard resource: %s",
            err,
            CARD_URL,
        )
