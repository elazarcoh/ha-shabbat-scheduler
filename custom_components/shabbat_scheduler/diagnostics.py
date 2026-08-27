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


def _outcome_shape(outcome: dict[str, Any] | None) -> dict[str, Any] | None:
    """A rule's last outcome, shape not content.

    `outcome`/`at` are safe: one of a fixed small vocabulary and an ISO
    timestamp, neither naming an entity or a room. `detail` is free text
    that can and does embed entity ids (e.g. "condition 1 of 1 (state on
    input_boolean.kids) not met"), so only whether one exists is reported,
    never the string itself - the same shape-not-content split every other
    field in this file already makes.
    """
    if outcome is None:
        return None
    return {
        "outcome": outcome.get("outcome"),
        "at": outcome.get("at"),
        "has_detail": bool(outcome.get("detail")),
        "unknown_target_count": len(outcome.get("unknown_targets") or []),
        "no_live_targets": bool(outcome.get("no_live_targets")),
    }


def _rule_shape(
    rule: Rule, index: int, last_outcome: dict[str, Any] | None
) -> dict[str, Any]:
    """A rule's shape, not its content: what kind of thing it is, not
    which entities or rooms it names.

    `id` is reported as a positionally-stable `rule_{index}`, not the real
    id: ids are not always integration-generated - a hand-edited YAML
    import (`yaml_io.py`) or a migrated v1 rule can carry a user-authored
    id - so the real one could name something personal, narrowly
    contradicting this file's "nothing that identifies a person's home"
    promise for the sake of a field nothing here actually needs.
    """
    return {
        "id": f"rule_{index}",
        "profile": rule.profile,
        "day": rule.day,
        "action": rule.action,
        "has_target": bool(rule.target),
        "data_keys": sorted(rule.data.keys()),
        "condition_count": len(rule.condition),
        "replay_enabled": rule.replay.enabled,
        "enabled": rule.enabled,
        "migration_error": rule.migration_error,
        "last_outcome": _outcome_shape(last_outcome),
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
        "rule_count": len(store.rules),
        "migration_failures": store.migration_failures,
        "current_block": _block_shape(engine.current_block),
        "upcoming_count": len(engine.upcoming()),
        "rules": [
            _rule_shape(rule, index, store.last_outcome(rule.id))
            for index, rule in enumerate(store.rules)
        ],
    }
