"""Config and options flow for the Owlet Smart Sock integration."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import OwletAuthenticationError, OwletClient, OwletConnectionError
from .const import (
    CONF_REGION,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    REGION_WORLD,
    REGIONS,
)
from .coordinator import OwletConfigEntry

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): TextSelector(
            TextSelectorConfig(type=TextSelectorType.EMAIL)
        ),
        vol.Required(CONF_PASSWORD): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
        vol.Required(CONF_REGION, default=REGION_WORLD): SelectSelector(
            SelectSelectorConfig(
                options=list(REGIONS),
                translation_key="region",
                mode=SelectSelectorMode.DROPDOWN,
            )
        ),
    }
)


async def _validate_login(
    hass: HomeAssistant, username: str, password: str, region: str
) -> None:
    """Attempt a full login so bad credentials fail fast in the UI."""
    client = OwletClient(
        username=username,
        password=password,
        region=region,
        session=async_get_clientsession(hass),
    )
    await client.authenticate()


class OwletConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the UI-driven setup of an Owlet account."""

    VERSION = 1

    reauth_entry: OwletConfigEntry | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect account credentials and create the entry."""
        errors: dict[str, str] = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME]
            await self.async_set_unique_id(username.lower())
            self._abort_if_unique_id_configured()

            errors = await self._async_try_login(user_input)
            if not errors:
                return self.async_create_entry(title=username, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Start the re-authentication flow after credentials are rejected."""
        self.reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Prompt for a new password and update the existing entry."""
        assert self.reauth_entry is not None
        errors: dict[str, str] = {}

        if user_input is not None:
            data = {**self.reauth_entry.data, CONF_PASSWORD: user_input[CONF_PASSWORD]}
            errors = await self._async_try_login(data)
            if not errors:
                return self.async_update_reload_and_abort(
                    self.reauth_entry, data=data
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_PASSWORD): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    )
                }
            ),
            description_placeholders={
                CONF_USERNAME: self.reauth_entry.data[CONF_USERNAME]
            },
            errors=errors,
        )

    async def _async_try_login(self, data: Mapping[str, Any]) -> dict[str, str]:
        """Validate credentials and translate failures into form errors."""
        errors: dict[str, str] = {}
        try:
            await _validate_login(
                self.hass,
                data[CONF_USERNAME],
                data[CONF_PASSWORD],
                data[CONF_REGION],
            )
        except OwletAuthenticationError:
            errors["base"] = "invalid_auth"
        except OwletConnectionError:
            errors["base"] = "cannot_connect"
        except Exception:  # noqa: BLE001 - surface unexpected issues safely
            _LOGGER.exception("Unexpected error validating Owlet credentials")
            errors["base"] = "unknown"
        return errors

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: OwletConfigEntry,
    ) -> OwletOptionsFlow:
        """Return the options flow handler."""
        return OwletOptionsFlow()


class OwletOptionsFlow(OptionsFlow):
    """Allow the polling interval to be tuned after setup."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the integration options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL, default=current
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=MIN_SCAN_INTERVAL,
                            max=MAX_SCAN_INTERVAL,
                            step=1,
                            unit_of_measurement="seconds",
                            mode=NumberSelectorMode.BOX,
                        )
                    )
                }
            ),
        )
