"""Shabbat Scheduler integration."""

from __future__ import annotations

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

from . import repairs, websocket_api
from .block import preview_payload
from .const import (
    CONF_CANDLE_SENSOR,
    CONF_HAVDALAH_SENSOR,
    DEFAULT_CANDLE_SENSOR,
    DEFAULT_HAVDALAH_SENSOR,
    DOMAIN,
    MAX_PROFILE,
    MIN_PROFILE,
    SIGNAL_RULES_CHANGED,
)
from .engine import ShabbatEngine
from .frontend import async_register_frontend, async_unregister_frontend
from .ha_validation import async_validate_rule
from .rule_schema import RuleValidationError
from .store import RuleStore
from .yaml_io import export_yaml, import_yaml

PLATFORMS = [Platform.SWITCH, Platform.SENSOR]


def _configured_sensor(entry: ConfigEntry, key: str, default: str) -> str:
    """The entity id for `key`: options override data, which overrides the
    Jewish Calendar's own default name - the same precedence `ConfigEntry`
    uses everywhere else a value can be both set at setup and changed later.
    """
    return entry.options.get(key) or entry.data.get(key, default)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    store = RuleStore(hass)
    await store.async_load()

    # What this session last reported, so a rule toggle that changes nothing
    # about the migration state does not re-write the issue registry.
    # `None`, not `()`, until the first pass: a store with nothing broken
    # still has to issue one delete, in case a previous install left a
    # persistent issue behind and the rules were repaired while unloaded.
    reported_unmigrated: dict[str, tuple[str, ...] | None] = {"ids": None}
    reported_split: dict[str, tuple[str, ...] | None] = {"rules": None}

    @callback
    def _sync_split_issue() -> None:
        """Report the rules a mixed-domain v1 rule was split into.

        Derived from the store, and for the same reason the unmigrated issue
        is (see below): the migration runs once ever, so anything keyed on
        the migration EVENT is gone by the second restart.

        The marker is a stashed `migration_source` with no
        `migration_error`. `migration.migrate_v1` writes that pair on each
        part of a rule it had to split, and on nothing else - a rule it
        could not convert carries both fields, and a rule it converted
        whole carries neither. The one other way to arrive here is a YAML
        import that deliberately carries a `migration_source`, which is the
        user's own doing and is also how they acknowledge this issue.

        Grouped by the ORIGINAL rule id, because "e-climate, e-switch" on
        its own does not tell anyone which of their rules those came from.
        """
        groups: dict[str, list[str]] = {}
        for rule in store.rules:
            if rule.migration_error or not rule.migration_source:
                continue
            source_id = str(rule.migration_source.get("id") or "?")
            groups.setdefault(source_id, []).append(rule.id)

        described = tuple(
            f"{source} → {', '.join(parts)}"
            for source, parts in sorted(groups.items())
        )
        if described == reported_split["rules"]:
            return
        reported_split["rules"] = described
        if described:
            repairs.async_create_split_rules_issue(hass, list(described))
        else:
            repairs.async_delete_split_rules_issue(hass)

    @callback
    def _sync_unmigrated_issue() -> None:
        """Report the rules that are still unmigrated, from the STORE.

        Not from `store.migration_failures`: that list is populated only
        inside the store's `_async_migrate_func`, which Home Assistant calls
        only while the stored version is behind. The migration therefore
        happens exactly once, ever - so the user was told on the upgrade and
        never again, while the kept-but-disabled rules sat there permanently
        inert. Deriving it from `rule.migration_error` re-raises it on every
        setup for as long as anything is actually broken.

        And it CLEARS. A user who deletes or re-authors the broken rules had
        no way to make the warning go away, which teaches people to ignore
        Settings > Repairs - where the unreadable-zmanim error also lives.
        Same create/delete-on-every-refresh shape as the zmanim pair.
        """
        unmigrated = tuple(rule.id for rule in store.rules if rule.migration_error)
        if unmigrated == reported_unmigrated["ids"]:
            return
        reported_unmigrated["ids"] = unmigrated
        if unmigrated:
            repairs.async_create_unmigrated_rules_issue(hass, list(unmigrated))
        else:
            repairs.async_delete_unmigrated_rules_issue(hass)

    _sync_unmigrated_issue()
    _sync_split_issue()

    candle_sensor = _configured_sensor(entry, CONF_CANDLE_SENSOR, DEFAULT_CANDLE_SENSOR)
    havdalah_sensor = _configured_sensor(
        entry, CONF_HAVDALAH_SENSOR, DEFAULT_HAVDALAH_SENSOR
    )
    engine = ShabbatEngine(hass, store, candle_sensor, havdalah_sensor)

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
        stay sync), hence the task. It cannot loop. Two independent reasons:
        refresh writes to the store only via `async_set_active_block` /
        `async_clear_active_block`, which deliberately do not notify; and
        `async_refresh` now dispatches SIGNAL_RULES_CHANGED itself when the
        block changes, which cannot re-enter here either - this function is
        the STORE's change listener, not a dispatcher subscriber. The signal
        reaches only switch.py's `_sync` and the websocket subscribers,
        neither of which writes to the store or refreshes.

        The cost is that a rule edit which also moves the block (it can: the
        hold decision reads the rule set's own tail) pushes the card twice.
        Both pushes carry the same full snapshot, so that is a wasted frame,
        not a wrong one.
        """
        async_dispatcher_send(hass, SIGNAL_RULES_CHANGED)
        # Cheap, synchronous, and the only way either migration report can
        # clear without a restart: this is the choke point every mutation
        # path goes through, including the YAML import that is the
        # documented way to repair - or to acknowledge - those rules.
        _sync_unmigrated_issue()
        _sync_split_issue()
        hass.async_create_task(engine.async_refresh())

    store.async_set_change_listener(_rules_changed)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "store": store,
        "engine": engine,
        "entry_id": entry.entry_id,
    }

    await engine.async_refresh()

    await async_register_frontend(hass)

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
            hass, [candle_sensor, havdalah_sensor], _zmanim_changed
        )
    )

    async def _simulate(call: ServiceCall) -> ServiceResponse:
        # Literally the same call `preview` makes over the websocket. The
        # two used to build this separately, with a comment claiming they
        # "cannot drift apart" - they already had: this one returned
        # bare-string warnings and conflicts with no kind/profile.
        return preview_payload(
            store.defaults,
            store.rules,
            engine.current_block,
            dt_util.get_time_zone(hass.config.time_zone),
            websocket_api._resolver(hass),
            call.data.get("block_length"),
        )

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

        # yaml_io only checks shape (rule_schema.rule_from_api); target and
        # condition still need Home Assistant's own schemas, which yaml_io
        # cannot import without crossing the purity boundary. Applied here,
        # before anything is persisted, for the same reason the malformed-
        # defaults guard runs first: a rule that fails this after being
        # written to .storage would brick every later setup.
        for rule in rules:
            try:
                await async_validate_rule(hass, rule)
            except RuleValidationError as err:
                raise ServiceValidationError(
                    f"Invalid rule set: {err}"
                ) from err

        await store.async_replace_all(defaults, rules)
        await engine.async_refresh()

    hass.services.async_register(
        DOMAIN, "simulate", _simulate,
        schema=vol.Schema({vol.Optional("block_length"): vol.All(int, vol.Range(MIN_PROFILE, MAX_PROFILE))}),
        supports_response=SupportsResponse.ONLY,
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
        for service in ("simulate", "export_yaml", "import_yaml"):
            hass.services.async_remove(DOMAIN, service)
        await async_unregister_frontend(hass)
    return unloaded
