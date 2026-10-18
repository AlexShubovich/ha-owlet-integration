"""Binary sensor platform for the Owlet Smart Sock integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import OwletSockData
from .coordinator import OwletConfigEntry, OwletCoordinator
from .entity import OwletBaseEntity


@dataclass(frozen=True, kw_only=True)
class OwletBinarySensorDescription(BinarySensorEntityDescription):
    """Describe an Owlet binary sensor and how to read its state."""

    value_fn: Callable[[OwletSockData], bool | None]


BINARY_SENSORS: tuple[OwletBinarySensorDescription, ...] = (
    OwletBinarySensorDescription(
        key="monitoring",
        translation_key="monitoring",
        icon="mdi:baby-face-outline",
        value_fn=lambda sock: sock.monitoring,
    ),
    OwletBinarySensorDescription(
        key="charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        value_fn=lambda sock: (
            sock.charge_status == 1 if sock.charge_status is not None else None
        ),
    ),
    OwletBinarySensorDescription(
        key="base_station",
        translation_key="base_station",
        device_class=BinarySensorDeviceClass.POWER,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda sock: sock.base_station_on,
    ),
    OwletBinarySensorDescription(
        key="low_battery",
        device_class=BinarySensorDeviceClass.BATTERY,
        value_fn=lambda sock: sock.alerts.get("low_battery"),
    ),
    OwletBinarySensorDescription(
        key="high_heart_rate",
        translation_key="high_heart_rate",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda sock: sock.alerts.get("high_heart_rate"),
    ),
    OwletBinarySensorDescription(
        key="low_heart_rate",
        translation_key="low_heart_rate",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda sock: sock.alerts.get("low_heart_rate"),
    ),
    OwletBinarySensorDescription(
        key="low_oxygen",
        translation_key="low_oxygen",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda sock: sock.alerts.get("low_oxygen"),
    ),
    OwletBinarySensorDescription(
        key="high_oxygen",
        translation_key="high_oxygen",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda sock: sock.alerts.get("high_oxygen"),
    ),
    OwletBinarySensorDescription(
        key="lost_power",
        translation_key="lost_power",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda sock: sock.alerts.get("lost_power"),
    ),
    OwletBinarySensorDescription(
        key="sock_off",
        translation_key="sock_off",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda sock: sock.alerts.get("sock_off"),
    ),
    OwletBinarySensorDescription(
        key="sock_disconnected",
        translation_key="sock_disconnected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda sock: (
            not sock.alerts["sock_disconnected"]
            if "sock_disconnected" in sock.alerts
            else None
        ),
    ),
    OwletBinarySensorDescription(
        key="low_integrity_reading",
        translation_key="low_integrity_reading",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda sock: sock.alerts.get("low_integrity_reading"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: OwletConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Owlet binary sensors for every discovered sock."""
    coordinator = entry.runtime_data
    async_add_entities(
        OwletBinarySensor(coordinator, device, description)
        for device in coordinator.devices
        for description in BINARY_SENSORS
    )


class OwletBinarySensor(OwletBaseEntity, BinarySensorEntity):
    """A single Owlet alert / status flag."""

    entity_description: OwletBinarySensorDescription

    def __init__(
        self,
        coordinator: OwletCoordinator,
        device,
        description: OwletBinarySensorDescription,
    ) -> None:
        """Initialise the binary sensor."""
        super().__init__(coordinator, device)
        self.entity_description = description
        self._attr_unique_id = f"{device.dsn}_{description.key}"

    @property
    def is_on(self) -> bool | None:
        """Return the current state of the flag."""
        if (sock := self.sock) is None:
            return None
        return self.entity_description.value_fn(sock)
