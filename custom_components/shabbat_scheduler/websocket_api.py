"""Websocket commands. Transport only - logic lives in block.py/store.py."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.util import dt as dt_util

from .block import compute_block, find_conflicts, has_profile, merge_defaults, resolve_rules
from .const import DOMAIN
from .store import rule_to_dict


def _entry_data(hass: HomeAssistant) -> dict | None:
    """The single config entry's data, or None when not set up."""
    entries = list(hass.data.get(DOMAIN, {}).values())
    return entries[0] if entries else None


def _conflict_warnings(rules) -> list[dict]:
    return [
        {
            "kind": "conflict",
            "device": conflict.device,
            "profile": conflict.profile,
            "day": conflict.day,
            "time": conflict.time.isoformat(),
            "rule_ids": list(conflict.rule_ids),
        }
        for conflict in find_conflicts(rules)
    ]


def _state_payload(store) -> dict:
    """Everything the card renders. One shape, used by list and subscribe."""
    return {
        "defaults": store.defaults,
        "rules": [rule_to_dict(rule) for rule in store.rules],
        "enabled": store.enabled,
        "dry_run": store.dry_run,
        "warnings": _conflict_warnings(store.rules),
    }


@callback
@websocket_api.websocket_command({vol.Required("type"): "shabbat_scheduler/rules/list"})
def ws_list(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    data = _entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_set_up", "Integration is not set up")
        return
    connection.send_result(msg["id"], _state_payload(data["store"]))


@callback
@websocket_api.websocket_command(
    {
        vol.Required("type"): "shabbat_scheduler/preview",
        vol.Optional("block_length"): vol.All(int, vol.Range(1, 3)),
    }
)
def ws_preview(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    data = _entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_set_up", "Integration is not set up")
        return
    store, engine = data["store"], data["engine"]
    block = engine.current_block
    length = msg.get("block_length")
    if length is not None and block is not None:
        # Re-derive a hypothetical block of the requested length, mirroring
        # the `simulate` service in __init__.py so the two cannot drift apart.
        block = compute_block(
            block.candle_lighting,
            block.candle_lighting.replace(hour=20, minute=0)
            + timedelta(days=int(length)),
        )

    if block is None:
        connection.send_result(
            msg["id"],
            {
                "profile": None,
                "rules": [],
                "conflicts": [],
                "warnings": [
                    {
                        "kind": "no_block",
                        "message": "No block could be derived from the "
                        "Jewish Calendar sensors.",
                    }
                ],
            },
        )
        return

    rules = [merge_defaults(store.defaults, rule) for rule in store.rules]
    warnings: list[dict] = []
    if not has_profile(rules, block.length):
        warnings.append(
            {
                "kind": "no_profile",
                "message": f"No enabled rules for a {block.length}-day block.",
            }
        )

    tz = dt_util.get_time_zone(hass.config.time_zone)
    connection.send_result(
        msg["id"],
        {
            "profile": block.length,
            "rules": [
                {
                    "when": item.when.isoformat(),
                    "rule_id": item.rule.id,
                    "name": item.rule.name,
                    "action": item.rule.action.value,
                    "devices": list(item.rule.devices),
                }
                for item in resolve_rules(rules, block, tz)
            ],
            "conflicts": _conflict_warnings(rules),
            "warnings": warnings,
        },
    )


@callback
def async_register(hass: HomeAssistant) -> None:
    """Register every websocket command for this integration."""
    websocket_api.async_register_command(hass, ws_list)
    websocket_api.async_register_command(hass, ws_preview)
