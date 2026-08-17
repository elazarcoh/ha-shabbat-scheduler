"""Single-instance config flow - all configuration lives in the rule store."""

from __future__ import annotations

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import DOMAIN


class ShabbatSchedulerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Nothing to ask for; the integration is configured through its rules."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> ConfigFlowResult:
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        return self.async_create_entry(title="Shabbat Scheduler", data={})
