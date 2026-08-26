"""Websocket commands. Transport only - logic lives in block.py/store.py."""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import datetime
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import target as target_helper
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.util import dt as dt_util

from . import ha_validation
from .block import block_payload, conflict_warnings, merge_defaults, preview_payload
from .const import DOMAIN, MAX_PROFILE, MIN_PROFILE, SIGNAL_RULES_CHANGED
from .rule_schema import (
    RuleValidationError,
    changes_from_api,
    rule_from_api,
    validate_defaults,
)
from .store import rule_to_dict


def _entry_data(hass: HomeAssistant) -> dict | None:
    """The single config entry's data, or None when not set up."""
    entries = list(hass.data.get(DOMAIN, {}).values())
    return entries[0] if entries else None


def _resolver(hass: HomeAssistant):
    """Resolve a target selector to the entity ids it actually covers.

    Verified against the installed 2026.8.2: `TargetSelection.__init__`
    takes the target dict directly (`helpers/target.py:72`), and
    `async_extract_referenced_entity_ids` - a plain function despite the
    `async_` name, so it is called directly, not awaited - returns a
    `SelectedEntities` whose `referenced` holds what was named outright
    and whose `indirectly_referenced` holds what an area, device, floor
    or label expanded into (`:117-125`). A conflict cares about both: an
    area target and a bare entity target for that same entity must
    resolve to the same id to ever be recognised as overlapping.

    Getting either name wrong yields a silently empty set here, which
    reports NO conflicts on a genuinely conflicting schedule - the
    failure mode worth re-checking this against future HA versions for.
    """

    def resolve(target: dict) -> frozenset[str]:
        selection = target_helper.TargetSelection(dict(target))
        selected = target_helper.async_extract_referenced_entity_ids(hass, selection)
        return frozenset(selected.referenced | selected.indirectly_referenced)

    return resolve


def _conflict_warnings(hass: HomeAssistant, store) -> list[dict]:
    """Conflict warnings for the whole rule set of `store`.

    Takes the store, not a rule list, precisely so no caller can forget to
    merge the defaults first - see block.conflict_warnings.
    """
    return conflict_warnings(store.defaults, store.rules, _resolver(hass))


def _state_payload(hass: HomeAssistant, data: dict) -> dict:
    """Everything the card renders. One shape, used by list and subscribe."""
    store, engine = data["store"], data["engine"]
    return {
        "defaults": store.defaults,
        "rules": [
            {
                **rule_to_dict(rule),
                # Attached here, not in `rule_to_dict`, because it is not
                # part of a rule: it is what HAPPENED to one. Keeping it
                # out of `rule_to_dict` keeps it out of `.storage`'s rule
                # entries and out of the YAML export, where a report about
                # last Shabbat would read as part of the schedule.
                #
                # Always present, `None` for a rule that has never come
                # due, so the card has one field to read rather than a key
                # that may or may not exist. `rule_schema` drops it on the
                # way back in, so a client can echo a rule it read here
                # without being refused - and cannot forge a verdict.
                "last_outcome": store.last_outcome(rule.id),
            }
            for rule in store.rules
        ],
        "enabled": store.enabled,
        "dry_run": store.dry_run,
        "warnings": _conflict_warnings(hass, store),
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
        vol.Optional("block_length"): vol.All(int, vol.Range(MIN_PROFILE, MAX_PROFILE)),
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
            _resolver(hass),
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
        # The other half of validation, and the same one the YAML import
        # already applies (services.py). Without it a `target` or
        # `condition` shape that a YAML import rejects can still be
        # written through this door, and it then fails at fire time on
        # Shabbat instead of in the dialog the author is looking at.
        await ha_validation.async_validate_rule(hass, rule)
    except RuleValidationError as err:
        connection.send_error(msg["id"], "invalid_rule", str(err))
        return

    await store.async_add(rule)
    connection.send_result(
        msg["id"],
        {"rule": rule_to_dict(rule), "warnings": _conflict_warnings(hass, store)},
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

    # Validated on the MERGED rule, not on `changes`: `condition` and
    # `target` are validated together with whatever the rule already
    # carries, and a partial update that changes only `target` must still
    # be checked against HA's own schema. Nothing is persisted until it
    # passes - a rejected update must leave the store exactly as it was.
    updated = replace(existing, **changes)
    try:
        await ha_validation.async_validate_rule(hass, updated)
    except RuleValidationError as err:
        connection.send_error(msg["id"], "invalid_rule", str(err))
        return

    await store.async_update(msg["rule_id"], **changes)

    connection.send_result(
        msg["id"],
        {"rule": rule_to_dict(updated), "warnings": _conflict_warnings(hass, store)},
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
        vol.Required("type"): "shabbat_scheduler/rules/run_now",
        vol.Required("rule_id"): str,
        vol.Optional("simulate", default=True): bool,
        vol.Optional("at"): str,
    }
)
@websocket_api.async_response
async def ws_run_now(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    """Apply one rule right now, through the exact path a real fire uses.

    `simulate` defaults to True so an accidental or malformed call from a
    future client version cannot silently make a real call.
    """
    data = _entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_set_up", "Integration is not set up")
        return
    store, engine = data["store"], data["engine"]

    existing = next((r for r in store.rules if r.id == msg["rule_id"]), None)
    if existing is None:
        connection.send_error(msg["id"], "not_found", f"No rule {msg['rule_id']}")
        return

    at: datetime | None = None
    if "at" in msg:
        at = dt_util.parse_datetime(msg["at"])
        if at is None:
            connection.send_error(
                msg["id"], "invalid_rule",
                f"at is not a valid ISO 8601 datetime: {msg['at']!r}",
            )
            return

    # Merged with the shared defaults first, exactly as every real fire
    # does (`engine._merged_rules()`) - a rule whose target/data come from
    # the defaults must run_now the same way it would really fire, not
    # against its own bare, possibly-empty target.
    rule = merge_defaults(store.defaults, existing)
    results = await engine.async_apply_rule(rule, simulate=msg["simulate"], at=at)
    connection.send_result(msg["id"], {"results": results})


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
        # The same second door `ws_create`/`ws_update` put a rule's target
        # through, for the same reason. `validate_defaults` only asks "is it
        # a mapping", so without this an identical target - authored in the
        # same editor, in the same card - was refused in the rule dialog and
        # accepted here, then merged into every rule that has no target of
        # its own and refused at FIRE time on Shabbat instead.
        ha_validation.validate_defaults_for_ha(defaults)
    except RuleValidationError as err:
        connection.send_error(msg["id"], "invalid_rule", str(err))
        return

    await store.async_replace_all(defaults, store.rules)
    connection.send_result(
        msg["id"],
        {"defaults": store.defaults, "warnings": _conflict_warnings(hass, store)},
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
    websocket_api.async_register_command(hass, ws_run_now)
    websocket_api.async_register_command(hass, ws_defaults)
    websocket_api.async_register_command(hass, ws_subscribe)
