"""Websocket commands. Transport only - logic lives in block.py/store.py."""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import timedelta
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.util import dt as dt_util

from .block import compute_block, find_conflicts, has_profile, merge_defaults, resolve_rules
from .const import DOMAIN, SIGNAL_RULES_CHANGED
from .rule_schema import (
    RuleValidationError,
    changes_from_api,
    rule_from_api,
    validate_defaults,
    validate_rule,
)
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


@websocket_api.websocket_command(
    {
        vol.Required("type"): "shabbat_scheduler/rules/create",
        vol.Required("rule"): dict,
    }
)
@websocket_api.async_response
async def ws_create(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    data = _entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_set_up", "Integration is not set up")
        return
    store = data["store"]
    try:
        rule = rule_from_api(msg["rule"], uuid.uuid4().hex)
    except RuleValidationError as err:
        connection.send_error(msg["id"], "invalid_rule", str(err))
        return

    await store.async_add(rule)
    connection.send_result(
        msg["id"],
        {"rule": rule_to_dict(rule), "warnings": _conflict_warnings(store.rules)},
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "shabbat_scheduler/rules/update",
        vol.Required("rule_id"): str,
        vol.Required("changes"): dict,
    }
)
@websocket_api.async_response
async def ws_update(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    data = _entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_set_up", "Integration is not set up")
        return
    store = data["store"]
    try:
        changes = changes_from_api(msg["changes"])
    except RuleValidationError as err:
        connection.send_error(msg["id"], "invalid_rule", str(err))
        return

    existing = next((r for r in store.rules if r.id == msg["rule_id"]), None)
    if existing is None:
        connection.send_error(msg["id"], "not_found", f"No rule {msg['rule_id']}")
        return

    updated = replace(existing, **changes)
    try:
        validate_rule(updated)
    except RuleValidationError as err:
        connection.send_error(msg["id"], "invalid_rule", str(err))
        return

    await store.async_update(msg["rule_id"], **changes)

    connection.send_result(
        msg["id"],
        {"rule": rule_to_dict(updated), "warnings": _conflict_warnings(store.rules)},
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "shabbat_scheduler/rules/delete",
        vol.Required("rule_id"): str,
    }
)
@websocket_api.async_response
async def ws_delete(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    data = _entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_set_up", "Integration is not set up")
        return
    await data["store"].async_delete(msg["rule_id"])
    connection.send_result(msg["id"], {"ok": True})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "shabbat_scheduler/defaults/update",
        vol.Required("defaults"): dict,
    }
)
@websocket_api.async_response
async def ws_defaults(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    data = _entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_set_up", "Integration is not set up")
        return
    store = data["store"]
    try:
        defaults = validate_defaults(msg["defaults"])
    except RuleValidationError as err:
        connection.send_error(msg["id"], "invalid_rule", str(err))
        return

    await store.async_replace_all(defaults, store.rules)
    connection.send_result(
        msg["id"],
        {"defaults": store.defaults, "warnings": _conflict_warnings(store.rules)},
    )


@callback
@websocket_api.websocket_command({vol.Required("type"): "shabbat_scheduler/subscribe"})
def ws_subscribe(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    data = _entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_set_up", "Integration is not set up")
        return
    store = data["store"]

    @callback
    def _forward() -> None:
        connection.send_message(
            websocket_api.event_message(msg["id"], _state_payload(store))
        )

    connection.subscriptions[msg["id"]] = async_dispatcher_connect(
        hass, SIGNAL_RULES_CHANGED, _forward
    )
    connection.send_result(msg["id"])


@callback
def async_register(hass: HomeAssistant) -> None:
    """Register every websocket command for this integration."""
    websocket_api.async_register_command(hass, ws_list)
    websocket_api.async_register_command(hass, ws_preview)
    websocket_api.async_register_command(hass, ws_create)
    websocket_api.async_register_command(hass, ws_update)
    websocket_api.async_register_command(hass, ws_delete)
    websocket_api.async_register_command(hass, ws_defaults)
    websocket_api.async_register_command(hass, ws_subscribe)
