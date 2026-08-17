"""Diagnostic sensors: what block is next, what fires next, what last ran."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
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

    def __init__(self, entry: ConfigEntry, engine: ShabbatEngine) -> None:
        super().__init__(entry, engine, "last_run")

    @property
    def native_value(self):
        return len(self._engine.last_run)

    @property
    def extra_state_attributes(self) -> dict:
        return {"results": self._engine.last_run}
