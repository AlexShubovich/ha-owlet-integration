"""Sensor platform for the Owlet Smart Sock integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    EntityCategory,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import OwletSockData
from .const import SOCK_STATUSES
from .coordinator import OwletConfigEntry, OwletCoordinator
from .entity import OwletBaseEntity


@dataclass(frozen=True, kw_only=True)
class OwletSensorDescription(SensorEntityDescription):
    """Describe an Owlet sensor and how to read its value."""

    value_fn: Callable[[OwletSockData], float | int | str | datetime | None]
    attributes_fn: Callable[[OwletSockData], dict[str, Any]] | None = None


def _status_attributes(sock: OwletSockData) -> dict[str, Any]:
    """Expose the active alarm priority and firing alerts on the status sensor."""
    return {
        "alarm": sock.alarm,
        "active_alerts": sorted(
            name for name, firing in sock.alerts.items() if firing
        ),
    }


SENSORS: tuple[OwletSensorDescription, ...] = (
    OwletSensorDescription(
        key="status",
        translation_key="status",
        icon="mdi:baby-face-outline",
        device_class=SensorDeviceClass.ENUM,
        options=SOCK_STATUSES,
        value_fn=lambda sock: sock.status,
        attributes_fn=_status_attributes,
    ),
    OwletSensorDescription(
        key="heart_rate",
        translation_key="heart_rate",
        icon="mdi:heart-pulse",
        native_unit_of_measurement="bpm",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda sock: sock.heart_rate,
    ),
    OwletSensorDescription(
        key="oxygen_saturation",
        translation_key="oxygen_saturation",
        icon="mdi:lungs",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda sock: sock.oxygen_saturation,
    ),
    OwletSensorDescription(
        key="movement",
        translation_key="movement",
        icon="mdi:run",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda sock: sock.movement,
    ),
    OwletSensorDescription(
        # Skin temperature from REAL_TIME_VITALS `st` (Smart Sock 3/4).
        key="skin_temperature",
        translation_key="skin_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda sock: sock.skin_temperature,
    ),
    OwletSensorDescription(
        key="battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda sock: sock.battery,
    ),
    OwletSensorDescription(
        # Estimated battery runtime from REAL_TIME_VITALS `btt` (minutes).
        key="battery_time_remaining",
        translation_key="battery_time_remaining",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda sock: sock.battery_time_remaining,
    ),
    OwletSensorDescription(
        # `rsi` is the Wi-Fi signal (per the app's API). Its scale varies by
        # model, so it is exposed as a neutral unitless value rather than being
        # mislabelled as a dBm signal-strength reading.
        key="signal_strength",
        translation_key="wifi_signal",
        icon="mdi:wifi",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda sock: sock.signal_strength,
    ),
    OwletSensorDescription(
        key="last_update",
        translation_key="last_update",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda sock: sock.updated_at,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: OwletConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Owlet sensors for every discovered sock."""
    coordinator = entry.runtime_data
    async_add_entities(
        OwletSensor(coordinator, device, description)
        for device in coordinator.devices
        for description in SENSORS
    )


class OwletSensor(OwletBaseEntity, SensorEntity):
    """A single Owlet vitals reading."""

    entity_description: OwletSensorDescription

    def __init__(
        self,
        coordinator: OwletCoordinator,
        device,
        description: OwletSensorDescription,
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator, device)
        self.entity_description = description
        self._attr_unique_id = f"{device.dsn}_{description.key}"

    @property
    def native_value(self) -> float | int | str | datetime | None:
        """Return the current value for this sensor."""
        if (sock := self.sock) is None:
            return None
        return self.entity_description.value_fn(sock)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra attributes for sensors that provide them."""
        if self.entity_description.attributes_fn is None or (
            sock := self.sock
        ) is None:
            return None
        return self.entity_description.attributes_fn(sock)
