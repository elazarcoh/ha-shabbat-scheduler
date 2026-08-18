"""Shabbat Scheduler integration."""

from __future__ import annotations

from datetime import timedelta

import voluptuous as vol
import yaml
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.start import async_at_started
from homeassistant.util import dt as dt_util

from . import websocket_api
from .block import compute_block, find_conflicts, has_profile, merge_defaults, resolve_rules
from .const import CANDLE_SENSOR, DOMAIN, HAVDALAH_SENSOR, SIGNAL_RULES_CHANGED
from .engine import ShabbatEngine
from .store import RuleStore
from .yaml_io import export_yaml, import_yaml

PLATFORMS = [Platform.SWITCH, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    store = RuleStore(hass)
    await store.async_load()
    engine = ShabbatEngine(hass, store)

    @callback
    def _rules_changed() -> None:
        """The single choke point for "the rule set just changed".

        Two things have to happen and BOTH have to happen for every mutation
        path - the websocket CRUD commands, the rule switches, YAML import,
        and anything added later. Fanning out the signal tells the entities
        and any subscribed card; rescheduling is what makes the change real.

        Rescheduling here rather than in each command is deliberate. Timers
        are built only by `engine.async_refresh`, and nothing else calls it
        unprompted until the zmanim sensors change at havdalah - a week away.
        Without this a rule created for the coming Shabbat never fires, and
        worse, a deleted or retimed rule keeps its old timer and drives the
        appliance at a time the user can no longer see anywhere.

        `async_refresh` is a coroutine and this is a sync callback (the
        store's change-listener contract is `Callable[[], None]`, so it must
        stay sync), hence the task. It cannot loop: refresh only writes the
        active block via `async_set_active_block`/`async_clear_active_block`,
        and those deliberately do not notify.
        """
        async_dispatcher_send(hass, SIGNAL_RULES_CHANGED)
        hass.async_create_task(engine.async_refresh())

    store.async_set_change_listener(_rules_changed)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "store": store,
        "engine": engine,
    }

    await engine.async_refresh()

    # Re-apply the current desired state after a restart, so a reboot part-way
    # through a block does not leave devices stranded.
    #
    # Deliberately NOT inline in setup. At boot config entries are set up
    # concurrently, so jewish_calendar has often not published its sensors
    # yet: an inline catch-up would find no block, return [], and never be
    # retried - silently losing the mid-block restart it exists for. And when
    # the target devices are unavailable the staleness guard forces every
    # call, each retried RETRY_ATTEMPTS x RETRY_DELAY_SECONDS, which inline
    # would block async_setup_entry for minutes before any entity exists.
    #
    # So: wait until HA has started, then run once - as a background task -
    # the first time a block is actually computable, whether that is at start
    # or when a late jewish_calendar finally publishes.
    catch_up = {"started": False, "done": False}

    def _maybe_catch_up() -> None:
        if catch_up["done"] or not catch_up["started"]:
            return
        if engine.current_block is None:
            return
        catch_up["done"] = True
        entry.async_create_background_task(
            hass, engine.async_catch_up(), f"{DOMAIN} restart catch-up"
        )

    async def _zmanim_changed(_event) -> None:
        await engine.async_refresh()
        _maybe_catch_up()

    entry.async_on_unload(
        async_track_state_change_event(
            hass, [CANDLE_SENSOR, HAVDALAH_SENSOR], _zmanim_changed
        )
    )

    async def _simulate(call: ServiceCall) -> ServiceResponse:
        block = engine.current_block
        length = call.data.get("block_length")
        if length is not None and block is not None:
            # Re-derive a hypothetical block of the requested length.
            block = compute_block(
                block.candle_lighting,
                block.candle_lighting.replace(hour=20, minute=0)
                + timedelta(days=int(length)),
            )
        if block is None:
            return {"profile": None, "rules": [], "conflicts": [], "warnings": [
                "No block could be derived; is the Jewish Calendar integration set up?"
            ]}

        rules = [merge_defaults(store.defaults, r) for r in store.rules]
        warnings: list[str] = []
        if not has_profile(rules, block.length):
            warnings.append(
                f"No rules configured for a {block.length}-day block."
            )

        tz = dt_util.get_time_zone(hass.config.time_zone)
        resolved = resolve_rules(rules, block, tz)
        return {
            "profile": block.length,
            "rules": [
                {
                    "when": item.when.isoformat(),
                    "rule_id": item.rule.id,
                    "name": item.rule.name,
                    "action": item.rule.action.value,
                    "devices": list(item.rule.devices),
                }
                for item in resolved
            ],
            "conflicts": [
                {
                    "device": conflict.device,
                    "time": conflict.time.isoformat(),
                    "day": conflict.day,
                    "rule_ids": list(conflict.rule_ids),
                }
                for conflict in find_conflicts(rules)
            ],
            "warnings": warnings,
        }

    async def _set_dry_run(call: ServiceCall) -> None:
        await store.async_set_dry_run(bool(call.data["enabled"]))

    async def _export_yaml(_call: ServiceCall) -> ServiceResponse:
        return {"yaml": export_yaml(store.defaults, store.rules)}

    async def _import_yaml(call: ServiceCall) -> None:
        try:
            defaults, rules = import_yaml(call.data["yaml"])
        except yaml.YAMLError as err:
            raise ServiceValidationError(
                f"Could not parse YAML: {err}"
            ) from err
        except (KeyError, ValueError) as err:
            raise ServiceValidationError(
                f"Invalid rule set: {err}"
            ) from err
        await store.async_replace_all(defaults, rules)
        await engine.async_refresh()

    hass.services.async_register(
        DOMAIN, "simulate", _simulate,
        schema=vol.Schema({vol.Optional("block_length"): vol.All(int, vol.Range(1, 3))}),
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN, "set_dry_run", _set_dry_run,
        schema=vol.Schema({vol.Required("enabled"): bool}),
    )
    hass.services.async_register(
        DOMAIN, "export_yaml", _export_yaml,
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN, "import_yaml", _import_yaml,
        schema=vol.Schema({vol.Required("yaml"): str}),
    )

    websocket_api.async_register(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def _hass_started(_hass: HomeAssistant) -> None:
        catch_up["started"] = True
        # jewish_calendar may have published while we were setting up.
        await engine.async_refresh()
        _maybe_catch_up()

    # Registered last so this integration's own entities always exist before
    # any catch-up work begins.
    entry.async_on_unload(async_at_started(hass, _hass_started))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        await data["engine"].async_shutdown()
        for service in ("simulate", "set_dry_run", "export_yaml", "import_yaml"):
            hass.services.async_remove(DOMAIN, service)
    return unloaded
