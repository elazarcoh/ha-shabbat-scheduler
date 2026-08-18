"""Master switch plus one switch per rule.

Per-rule switches exist so the integration is fully usable with native
entities/tile cards before any custom card ships.
"""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_RULES_CHANGED
from .engine import ShabbatEngine
from .models import Rule
from .store import RuleStore


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    store: RuleStore = data["store"]
    engine: ShabbatEngine = data["engine"]

    known: dict[str, RuleSwitch] = {}
    prefix = f"{entry.entry_id}_rule_"

    @callback
    def _sync() -> None:
        """Add entities for new rules, remove those whose rule is gone, and
        re-write the state of the ones that stayed.

        The registry scan (rather than a `known - current` diff) is what
        used to be a separate setup-time purge, folded in here so there is
        one mechanism instead of two. `known` only tracks which rules
        already have a live entity object in *this* session - it starts
        empty on every setup because entity instances never survive a
        restart - so it cannot by itself catch a registry entry orphaned
        before this session began (e.g. the store file was edited while
        HA was stopped). Scanning the registry directly still catches that.

        The state re-write is what makes a rename visible: RuleSwitch reads
        its name and icon from the live store, and Home Assistant refreshes
        both the friendly name and the registry's `original_name` from
        `entity.name` on every state write. Without it a renamed rule kept
        its old name until a restart - and renaming is the card's primary
        affordance.
        """
        current = {rule.id for rule in store.rules}

        new = [
            RuleSwitch(entry, store, engine, rule)
            for rule in store.rules
            if rule.id not in known
        ]
        for entity in new:
            known[entity.rule_id] = entity
        if new:
            async_add_entities(new)

        for rule_id in current:
            entity = known.get(rule_id)
            # `entity_id` is only assigned once the platform has finished
            # adding it, so this skips the ones just handed to
            # async_add_entities above - they write their own first state.
            if entity is not None and entity.entity_id:
                entity.async_write_ha_state()

        registry = er.async_get(hass)
        for registered in er.async_entries_for_config_entry(registry, entry.entry_id):
            if not registered.unique_id.startswith(prefix):
                continue
            rule_id = registered.unique_id[len(prefix):]
            if rule_id not in current:
                registry.async_remove(registered.entity_id)
        for rule_id in [rule_id for rule_id in known if rule_id not in current]:
            del known[rule_id]

    async_add_entities([MasterSwitch(entry, store, engine)])
    _sync()
    entry.async_on_unload(
        async_dispatcher_connect(hass, SIGNAL_RULES_CHANGED, _sync)
    )


class MasterSwitch(SwitchEntity):
    """Enables or disables the whole flow."""

    _attr_has_entity_name = False
    _attr_name = "Shabbat Scheduler"
    _attr_icon = "mdi:candle"

    def __init__(
        self, entry: ConfigEntry, store: RuleStore, engine: ShabbatEngine
    ) -> None:
        self._store = store
        self._engine = engine
        self._attr_unique_id = f"{entry.entry_id}_master"

    @property
    def is_on(self) -> bool:
        return self._store.enabled

    async def async_turn_on(self, **kwargs) -> None:
        await self._store.async_set_enabled(True)
        await self._engine.async_refresh()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        await self._store.async_set_enabled(False)
        await self._engine.async_refresh()
        self.async_write_ha_state()


class RuleSwitch(SwitchEntity):
    """Enables or disables a single rule."""

    _attr_has_entity_name = False

    def __init__(
        self,
        entry: ConfigEntry,
        store: RuleStore,
        engine: ShabbatEngine,
        rule: Rule,
    ) -> None:
        self._store = store
        self._engine = engine
        self._rule_id = rule.id
        # unique_id is stable and derived from rule.id; entity_id follows
        # the user-editable, often-Hebrew rule NAME and is not derivable
        # from it. Anything looking a rule switch up - tests included -
        # must go through the entity registry by unique_id. Confusing the
        # two has caused two real bugs in this project already.
        self._attr_unique_id = f"{entry.entry_id}_rule_{rule.id}"
        # Only a fallback for the window between the rule's deletion and
        # the entity's removal; `name`/`icon` read the live store.
        self._last_known = rule

    @property
    def rule_id(self) -> str:
        return self._rule_id

    def _current(self) -> Rule | None:
        rule = next(
            (rule for rule in self._store.rules if rule.id == self._rule_id), None
        )
        if rule is not None:
            self._last_known = rule
        return rule

    @property
    def name(self) -> str:
        """Derived from the live store, so a rename shows on the next write.

        Snapshotting this in __init__ meant `rules/update {"name": ...}`
        never reached the entity: both the friendly name and the registry's
        original_name stayed stale until a restart.
        """
        rule = self._current() or self._last_known
        return rule.name or (
            f"{rule.profile}d {rule.day} {rule.time.strftime('%H:%M')} "
            f"{rule.action.value}"
        )

    @property
    def icon(self) -> str:
        rule = self._current() or self._last_known
        return rule.icon or (
            "mdi:power-plug" if rule.action.value == "on" else "mdi:power-plug-off"
        )

    @property
    def is_on(self) -> bool:
        rule = self._current()
        return bool(rule and rule.enabled)

    @property
    def extra_state_attributes(self) -> dict:
        rule = self._current()
        if rule is None:
            return {}
        return {
            "profile": rule.profile,
            "day": rule.day,
            "time": rule.time.isoformat(),
            "action": rule.action.value,
            "devices": list(rule.devices),
        }

    async def async_turn_on(self, **kwargs) -> None:
        await self._store.async_update(self._rule_id, enabled=True)
        await self._engine.async_refresh()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        await self._store.async_update(self._rule_id, enabled=False)
        await self._engine.async_refresh()
        self.async_write_ha_state()
