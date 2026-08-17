"""Shabbat Scheduler integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_state_change_event

from .const import CANDLE_SENSOR, DOMAIN, HAVDALAH_SENSOR
from .engine import ShabbatEngine
from .store import RuleStore

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

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        await data["engine"].async_shutdown()
    return unloaded
