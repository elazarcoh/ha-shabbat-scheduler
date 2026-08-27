"""Repair issues: the point of Task 10, not decoration.

v1 hardcoded the zmanim sensors and, when they could not be read, logged a
warning and scheduled nothing - invisible unless someone went looking in
the log on the one day they cannot.
"""

from homeassistant.helpers.issue_registry import async_get as async_get_issue_registry

from custom_components.shabbat_scheduler.const import (
    DEFAULT_CANDLE_SENSOR,
    DEFAULT_HAVDALAH_SENSOR,
    DOMAIN,
)
from custom_components.shabbat_scheduler.engine import ShabbatEngine
from custom_components.shabbat_scheduler.repairs import ISSUE_ZMANIM_SENSOR_MISSING
from custom_components.shabbat_scheduler.store import RuleStore


async def test_a_missing_sensor_raises_a_repair_issue(hass, jerusalem):
    """v1 logged a warning and scheduled nothing - invisible unless you
    went looking in the log on the one day you cannot."""
    store = RuleStore(hass)
    await store.async_load()
    engine = ShabbatEngine(hass, store)

    await engine.async_refresh()

    issues = async_get_issue_registry(hass)
    issue = issues.async_get_issue(DOMAIN, ISSUE_ZMANIM_SENSOR_MISSING)
    assert issue is not None
    assert issue.is_fixable is False
    assert issue.severity == "error"


async def test_the_zmanim_issue_names_the_configured_entities(hass, jerusalem):
    """Named after what is actually configured, not the Jewish Calendar's
    own defaults - the whole point of a second, differently-named entry."""
    store = RuleStore(hass)
    await store.async_load()
    engine = ShabbatEngine(
        hass,
        store,
        candle_sensor="sensor.jc_home_upcoming_candle_lighting",
        havdalah_sensor="sensor.jc_home_upcoming_havdalah",
    )

    await engine.async_refresh()

    issues = async_get_issue_registry(hass)
    issue = issues.async_get_issue(DOMAIN, ISSUE_ZMANIM_SENSOR_MISSING)
    assert issue is not None
    assert issue.translation_placeholders["candle_sensor"] == (
        "sensor.jc_home_upcoming_candle_lighting"
    )
    assert issue.translation_placeholders["havdalah_sensor"] == (
        "sensor.jc_home_upcoming_havdalah"
    )


async def test_the_zmanim_issue_clears_once_both_sensors_are_readable(hass, jerusalem):
    store = RuleStore(hass)
    await store.async_load()
    engine = ShabbatEngine(hass, store)
    await engine.async_refresh()

    issues = async_get_issue_registry(hass)
    assert issues.async_get_issue(DOMAIN, ISSUE_ZMANIM_SENSOR_MISSING) is not None

    hass.states.async_set(DEFAULT_CANDLE_SENSOR, "2026-08-14T15:44:00+00:00")
    hass.states.async_set(DEFAULT_HAVDALAH_SENSOR, "2026-08-15T17:01:00+00:00")
    await engine.async_refresh()

    assert issues.async_get_issue(DOMAIN, ISSUE_ZMANIM_SENSOR_MISSING) is None
