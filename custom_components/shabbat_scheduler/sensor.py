"""Diagnostic sensors: what block is next, what fires next, what last ran."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, EVENT_RULE_APPLIED
from .engine import ShabbatEngine


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    engine: ShabbatEngine = hass.data[DOMAIN][entry.entry_id]["engine"]
    async_add_entities(
        [
            NextBlockSensor(entry, engine),
            NextActionSensor(entry, engine),
            LastRunSensor(entry, engine),
        ]
    )


class _Base(SensorEntity):
    _attr_has_entity_name = False

    def __init__(self, entry: ConfigEntry, engine: ShabbatEngine, key: str) -> None:
        self._engine = engine
        self._attr_unique_id = f"{entry.entry_id}_{key}"


class NextBlockSensor(_Base):
    _attr_name = "Shabbat Scheduler Next Block"
    _attr_icon = "mdi:calendar-range"

    def __init__(self, entry: ConfigEntry, engine: ShabbatEngine) -> None:
        super().__init__(entry, engine, "next_block")

    @property
    def native_value(self):
        block = self._engine.current_block
        return block.length if block else None

    @property
    def extra_state_attributes(self) -> dict:
        block = self._engine.current_block
        if block is None:
            return {}
        return {
            "candle_lighting": block.candle_lighting.isoformat(),
            "havdalah": block.havdalah.isoformat(),
            "erev_date": block.erev_date.isoformat(),
            "day_dates": [day.isoformat() for day in block.day_dates],
        }


class NextActionSensor(_Base):
    _attr_name = "Shabbat Scheduler Next Action"
    _attr_icon = "mdi:clock-outline"

    def __init__(self, entry: ConfigEntry, engine: ShabbatEngine) -> None:
        super().__init__(entry, engine, "next_action")

    @property
    def native_value(self):
        upcoming = self._engine.upcoming()
        return upcoming[0].when.isoformat() if upcoming else None

    @property
    def extra_state_attributes(self) -> dict:
        upcoming = self._engine.upcoming()
        if not upcoming:
            return {}
        item = upcoming[0]
        return {
            "rule_id": item.rule.id,
            "name": item.rule.name,
            "action": item.rule.action.value,
            "devices": list(item.rule.devices),
        }


class LastRunSensor(_Base):
    _attr_name = "Shabbat Scheduler Last Run"
    _attr_icon = "mdi:history"
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry, engine: ShabbatEngine) -> None:
        super().__init__(entry, engine, "last_run")

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        @callback
        def _on_rule_applied(_event: Event) -> None:
            self.async_write_ha_state()

        self.async_on_remove(
            self.hass.bus.async_listen(EVENT_RULE_APPLIED, _on_rule_applied)
        )

    @property
    def native_value(self):
        last_run_at = self._engine.last_run_at
        return last_run_at.isoformat() if last_run_at else None

    @property
    def extra_state_attributes(self) -> dict:
        results = self._engine.last_run
        return {"results": results, "result_count": len(results)}
