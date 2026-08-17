"""Master switch plus one switch per rule.

Per-rule switches exist so the integration is fully usable with native
entities/tile cards before any custom card ships.
"""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
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

    entities: list[SwitchEntity] = [MasterSwitch(entry, store, engine)]
    entities.extend(RuleSwitch(entry, store, engine, rule) for rule in store.rules)
    async_add_entities(entities)


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
        self._attr_unique_id = f"{entry.entry_id}_rule_{rule.id}"
        self._attr_name = rule.name or (
            f"{rule.profile}d {rule.day} {rule.time.strftime('%H:%M')} "
            f"{rule.action.value}"
        )
        self._attr_icon = rule.icon or (
            "mdi:power-plug" if rule.action.value == "on" else "mdi:power-plug-off"
        )

    def _current(self) -> Rule | None:
        return next(
            (rule for rule in self._store.rules if rule.id == self._rule_id), None
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
