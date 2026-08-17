"""Shabbat Scheduler integration."""

from __future__ import annotations

from datetime import timedelta

import voluptuous as vol
import yaml
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util import dt as dt_util

from .block import compute_block, find_conflicts, has_profile, merge_defaults, resolve_rules
from .const import CANDLE_SENSOR, DOMAIN, HAVDALAH_SENSOR
from .engine import ShabbatEngine
from .store import RuleStore
from .yaml_io import export_yaml, import_yaml

PLATFORMS = [Platform.SWITCH, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    store = RuleStore(hass)
    await store.async_load()
    engine = ShabbatEngine(hass, store)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "store": store,
        "engine": engine,
    }

    await engine.async_refresh()
    # Re-apply the current desired state after a restart, so a reboot part-way
    # through a block does not leave devices stranded.
    await engine.async_catch_up()

    async def _zmanim_changed(_event) -> None:
        await engine.async_refresh()

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

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        await data["engine"].async_shutdown()
        for service in ("simulate", "set_dry_run", "export_yaml", "import_yaml"):
            hass.services.async_remove(DOMAIN, service)
    return unloaded
