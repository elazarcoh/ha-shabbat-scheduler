"""Websocket commands. Transport only - logic lives in block.py/store.py."""

from __future__ import annotations

import uuid
from dataclasses import replace
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.util import dt as dt_util

from .block import block_payload, conflict_warnings, preview_payload
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


def _conflict_warnings(store) -> list[dict]:
    """Conflict warnings for the whole rule set of `store`.

    Takes the store, not a rule list, precisely so no caller can forget to
    merge the defaults first - see block.conflict_warnings.
    """
    return conflict_warnings(store.defaults, store.rules)


def _state_payload(hass: HomeAssistant, data: dict) -> dict:
    """Everything the card renders. One shape, used by list and subscribe."""
    store, engine = data["store"], data["engine"]
    return {
        "defaults": store.defaults,
        "rules": [rule_to_dict(rule) for rule in store.rules],
        "enabled": store.enabled,
        "dry_run": store.dry_run,
        "warnings": _conflict_warnings(store),
        # The card draws dates and the zmanim markers from this, and picks
        # which profile to show from its length. None when the Jewish
        # Calendar sensors give us nothing to derive a block from.
        "block": block_payload(engine.current_block),
        # Resolved here rather than guessed by the card: a rule switch's
        # entity_id is slugified from a user-editable, often-Hebrew name
        # and cannot be constructed from a unique_id. Guessing it has
        # caused two real bugs in this project already.
        "master_entity_id": _master_entity_id(hass, data["entry_id"]),
    }


def _master_entity_id(hass: HomeAssistant, entry_id: str) -> str | None:
    """The master switch's entity_id, or None if it is not registered."""
    return er.async_get(hass).async_get_entity_id(
        "switch", DOMAIN, f"{entry_id}_master"
    )


@callback
@websocket_api.websocket_command({vol.Required("type"): "shabbat_scheduler/rules/list"})
def ws_list(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    data = _entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_set_up", "Integration is not set up")
        return
    connection.send_result(msg["id"], _state_payload(hass, data))


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
    connection.send_result(
        msg["id"],
        # The same call the `simulate` service makes, so the two answers
        # are one implementation rather than two that agree by hand.
        preview_payload(
            store.defaults,
            store.rules,
            engine.current_block,
            dt_util.get_time_zone(hass.config.time_zone),
            msg.get("block_length"),
        ),
    )


@websocket_api.require_admin
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
        {"rule": rule_to_dict(rule), "warnings": _conflict_warnings(store)},
    )


@websocket_api.require_admin
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
        {"rule": rule_to_dict(updated), "warnings": _conflict_warnings(store)},
    )


@websocket_api.require_admin
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
    store = data["store"]
    # Symmetric with ws_update: a delete of something that is not there is
    # the card and the store disagreeing, and saying {"ok": True} hides it.
    if not any(rule.id == msg["rule_id"] for rule in store.rules):
        connection.send_error(msg["id"], "not_found", f"No rule {msg['rule_id']}")
        return
    await store.async_delete(msg["rule_id"])
    connection.send_result(msg["id"], {"ok": True})


@websocket_api.require_admin
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
        {"defaults": store.defaults, "warnings": _conflict_warnings(store)},
    )


@callback
@websocket_api.websocket_command({vol.Required("type"): "shabbat_scheduler/subscribe"})
def ws_subscribe(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    data = _entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_set_up", "Integration is not set up")
        return
    @callback
    def _forward() -> None:
        # Resolved per push, never captured. SIGNAL_RULES_CHANGED is global
        # and this subscription outlives a config-entry reload, so a store
        # captured at subscribe time would keep serving the DEAD store's
        # contents while the CRUD commands - which resolve _entry_data
        # freshly - write to the new one: the card would read one store and
        # write another. Quiet when the entry is gone; the next
        # subscribe/list reports not_set_up loudly enough.
        current = _entry_data(hass)
        if current is None:
            return
        connection.send_message(
            websocket_api.event_message(msg["id"], _state_payload(hass, current))
        )

    connection.subscriptions[msg["id"]] = async_dispatcher_connect(
        hass, SIGNAL_RULES_CHANGED, _forward
    )
    connection.send_result(msg["id"])
    # The current state, before any change happens. Without it a client
    # must also call rules/list, and a change landing between the two
    # calls is missed with nothing to re-report it.
    _forward()


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
