"""Data update coordinator for the Owlet Smart Sock integration."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    OwletAuthenticationError,
    OwletClient,
    OwletConnectionError,
    OwletDevice,
    OwletSockData,
)
from .const import CONF_REGION, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

type OwletConfigEntry = ConfigEntry[OwletCoordinator]


class OwletCoordinator(DataUpdateCoordinator[dict[str, OwletSockData]]):
    """Poll the Owlet cloud and share the latest vitals with every entity."""

    config_entry: OwletConfigEntry

    def __init__(self, hass: HomeAssistant, entry: OwletConfigEntry) -> None:
        """Initialise the coordinator from a config entry."""
        scan_interval = entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = OwletClient(
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
            region=entry.data[CONF_REGION],
            session=async_get_clientsession(hass),
        )

    @property
    def devices(self) -> list[OwletDevice]:
        """Return the devices discovered for this account."""
        return self.client.devices

    async def _async_setup(self) -> None:
        """Authenticate and discover devices once before the first refresh."""
        try:
            await self.client.authenticate()
            devices = await self.client.async_get_devices()
        except OwletAuthenticationError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except OwletConnectionError as err:
            raise UpdateFailed(str(err)) from err

        if not devices:
            # Logged once at setup only - never on every poll.
            _LOGGER.warning("No Owlet Smart Sock found on this account")

    async def _async_update_data(self) -> dict[str, OwletSockData]:
        """Fetch the latest vitals for every discovered sock."""
        try:
            if not self.client.devices:
                await self.client.async_get_devices()

            data: dict[str, OwletSockData] = {}
            for device in self.client.devices:
                data[device.dsn] = await self.client.async_get_vitals(
                    device.dsn
                )
            return data
        except OwletAuthenticationError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except OwletConnectionError as err:
            raise UpdateFailed(str(err)) from err
