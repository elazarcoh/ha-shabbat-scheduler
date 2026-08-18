"""Render this integration's own events in Home Assistant's Logbook.

Registering here is also what lets Home Assistant attribute a device's own
state change back to the rule that caused it: logbook's processor skips
attribution entirely for event types nothing describes.
"""

from __future__ import annotations

from collections.abc import Callable

from homeassistant.core import Event, HomeAssistant, callback

from .const import DOMAIN, EVENT_RULE_APPLIED


@callback
def async_describe_events(
    hass: HomeAssistant,
    async_describe_event: Callable[[str, str, Callable[[Event], dict]], None],
) -> None:
    """Describe the events this integration fires."""

    @callback
    def async_describe_rule_applied(event: Event) -> dict:
        data = event.data
        rule = data.get("name") or data.get("rule_id", "")
        devices = ", ".join(data.get("devices") or [])
        action = data.get("action", "")

        message = f"rule {rule} ({action})"
        if devices:
            message = f"{message} — {devices}"
        if data.get("dry_run"):
            message = f"{message} [dry run]"

        return {
            "name": "Shabbat Scheduler",
            "message": message,
            "icon": "mdi:candle",
        }

    async_describe_event(DOMAIN, EVENT_RULE_APPLIED, async_describe_rule_applied)
