"""Switch platform for the Owlet Smart Sock integration.

Exposes the base station on/off command. This writes a command to the live
device, so it is disabled by default - enable it per sock if you want to
start/stop monitoring from Home Assistant.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import OwletDevice, OwletError
from .coordinator import OwletConfigEntry, OwletCoordinator
from .entity import OwletBaseEntity

_LOGGER = logging.getLogger(__name__)

BASE_STATION_SWITCH = SwitchEntityDescription(
    key="base_station_switch",
    translation_key="base_station_switch",
    icon="mdi:radio-tower",
    entity_registry_enabled_default=False,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: OwletConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the base-station switch for every discovered sock."""
    coordinator = entry.runtime_data
    async_add_entities(
        OwletBaseStationSwitch(coordinator, device)
        for device in coordinator.devices
    )


class OwletBaseStationSwitch(OwletBaseEntity, SwitchEntity):
    """Turn the base station (monitoring) on or off."""

    entity_description = BASE_STATION_SWITCH

    def __init__(
        self, coordinator: OwletCoordinator, device: OwletDevice
    ) -> None:
        """Initialise the switch."""
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{device.dsn}_{BASE_STATION_SWITCH.key}"

    @property
    def is_on(self) -> bool | None:
        """Return whether the base station reports as on."""
        if (sock := self.sock) is None:
            return None
        return sock.base_station_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the base station on."""
        await self._async_set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the base station off."""
        await self._async_set(False)

    async def _async_set(self, turn_on: bool) -> None:
        try:
            await self.coordinator.client.async_set_base_station(
                self._dsn, turn_on
            )
        except OwletError as err:
            raise HomeAssistantError(
                f"Failed to set base station: {err}"
            ) from err
        await self.coordinator.async_request_refresh()
