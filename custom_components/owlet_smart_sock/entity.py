"""Base entity for the Owlet Smart Sock integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import OwletDevice, OwletSockData
from .const import DOMAIN, MANUFACTURER
from .coordinator import OwletCoordinator


class OwletBaseEntity(CoordinatorEntity[OwletCoordinator]):
    """Common device info and availability for every Owlet entity."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: OwletCoordinator, device: OwletDevice) -> None:
        """Initialise the entity for a specific sock."""
        super().__init__(coordinator)
        self._dsn = device.dsn
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.dsn)},
            manufacturer=MANUFACTURER,
            name=device.name,
            model=device.model,
            sw_version=device.sw_version,
            serial_number=device.dsn,
        )

    @property
    def sock(self) -> OwletSockData | None:
        """Return the latest vitals for this sock, if any."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self._dsn)

    @property
    def available(self) -> bool:
        """Entity is available while the account polls successfully."""
        return super().available and self.sock is not None
