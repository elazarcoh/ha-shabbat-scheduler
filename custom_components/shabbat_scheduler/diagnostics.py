"""What 'Download diagnostics' sends for this integration.

Nothing here is a credential - the config entry holds only the two zmanim
sensor entity ids the engine reads a block from - so there is no
async_redact_data call. But a rule's own target and data are still
someone's home layout (device names, room names), and diagnostics
attached to a support request should not spell that out by default. So
this reports SHAPES (counts, kinds, whether a field is set) rather than
CONTENTS wherever the two diverge.
"""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .models import Block, Rule


def _rule_shape(rule: Rule) -> dict[str, Any]:
    """A rule's shape, not its content: what kind of thing it is, not
    which entities or rooms it names."""
    return {
        "id": rule.id,
        "profile": rule.profile,
        "day": rule.day,
        "action": rule.action,
        "has_target": bool(rule.target),
        "data_keys": sorted(rule.data.keys()),
        "condition_count": len(rule.condition),
        "replay_enabled": rule.replay.enabled,
        "enabled": rule.enabled,
        "migration_error": rule.migration_error,
    }


def _block_shape(block: Block | None) -> dict[str, Any] | None:
    if block is None:
        return None
    return {
        "length": block.length,
        "candle_lighting": block.candle_lighting.isoformat(),
        "havdalah": block.havdalah.isoformat(),
        "erev_date": block.erev_date.isoformat(),
        "day_dates": [d.isoformat() for d in block.day_dates],
    }


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> dict[str, Any]:
    """Config entry, rule count, resolved block, last run - and nothing
    that identifies a person's home beyond a service name."""
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    store = entry_data["store"]
    engine = entry_data["engine"]

    return {
        "config_entry": {
            "data_keys": sorted(config_entry.data.keys()),
            "options_keys": sorted(config_entry.options.keys()),
        },
        "enabled": store.enabled,
        "dry_run": store.dry_run,
        "rule_count": len(store.rules),
        "migration_failures": store.migration_failures,
        "current_block": _block_shape(engine.current_block),
        "upcoming_count": len(engine.upcoming()),
        "rules": [_rule_shape(rule) for rule in store.rules],
    }
