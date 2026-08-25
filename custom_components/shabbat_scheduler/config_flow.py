"""Config flow: which two zmanim sensors define a Shabbat/Chag block.

Single instance, as before - but no longer no-input. `CANDLE_SENSOR`/
`HAVDALAH_SENSOR` used to be hardcoded to the Jewish Calendar integration's
own default entity ids, which are derived from ITS config entry's title.
Anyone who named theirs differently, or runs two (for different locations
or candle-lighting offsets), gets sensors by other names - so those are
only this form's suggested defaults, offered when an entity by that name
happens to exist, never assumed.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector

from .const import (
    CONF_CANDLE_SENSOR,
    CONF_HAVDALAH_SENSOR,
    DEFAULT_CANDLE_SENSOR,
    DEFAULT_HAVDALAH_SENSOR,
    DOMAIN,
)


def _sensor_selector() -> selector.EntitySelector:
    return selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor"))


def _schema(hass: HomeAssistant, current: dict[str, Any] | None = None) -> vol.Schema:
    """A form for both zmanim sensors.

    `current` is the config entry's already-configured values, when there
    are any (the options flow re-editing them); otherwise the Jewish
    Calendar's own default names are offered, but ONLY while an entity by
    that name actually exists - the whole point of this task is that it
    often does not.
    """
    current = current or {}

    def _default(key: str, fallback: str) -> str:
        value = current.get(key, fallback)
        return value if hass.states.get(value) is not None else vol.UNDEFINED

    return vol.Schema(
        {
            vol.Required(
                CONF_CANDLE_SENSOR,
                default=_default(CONF_CANDLE_SENSOR, DEFAULT_CANDLE_SENSOR),
            ): _sensor_selector(),
            vol.Required(
                CONF_HAVDALAH_SENSOR,
                default=_default(CONF_HAVDALAH_SENSOR, DEFAULT_HAVDALAH_SENSOR),
            ): _sensor_selector(),
        }
    )


class ShabbatSchedulerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Single instance; the only choice is which zmanim sensors to read."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            return self.async_create_entry(title="Shabbat Scheduler", data=user_input)

        return self.async_show_form(step_id="user", data_schema=_schema(self.hass))

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> ShabbatSchedulerOptionsFlow:
        return ShabbatSchedulerOptionsFlow()


class ShabbatSchedulerOptionsFlow(OptionsFlowWithReload):
    """Change the configured zmanim sensors later, without removing the integration.

    `OptionsFlowWithReload` reloads the config entry automatically once the
    options actually change, so a renamed sensor takes effect immediately
    rather than only after the next Home Assistant restart.
    """

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(
            step_id="init", data_schema=_schema(self.hass, current)
        )
