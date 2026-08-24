"""Repair issues: the point of Task 10, not decoration.

v1 hardcoded the zmanim sensors and, when they could not be read, logged a
warning and scheduled nothing - invisible unless someone went looking in
the log on the one day they cannot. And a v1 -> v2 migration can leave
rules behind, kept only as disabled stubs (Task 5's keep-disable-report
machinery); this is where the user is actually told to go look.
"""

from homeassistant.helpers.issue_registry import async_get as async_get_issue_registry
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.shabbat_scheduler.const import (
    DEFAULT_CANDLE_SENSOR,
    DEFAULT_HAVDALAH_SENSOR,
    DOMAIN,
)
from custom_components.shabbat_scheduler.engine import ShabbatEngine
from custom_components.shabbat_scheduler.repairs import (
    ISSUE_UNMIGRATED_RULES,
    ISSUE_ZMANIM_SENSOR_MISSING,
)
from custom_components.shabbat_scheduler.store import RuleStore

V1_SIMPLE_ON = {
    "id": "b", "profile": 1, "day": "erev", "time": "22:00:00", "action": "on",
    "devices": ["switch.boiler"], "settings": {},
}
V1_CUSTOM_NO_SCRIPT = {
    "id": "d", "profile": 1, "day": "1", "time": "17:00:00", "action": "custom",
    "script": None, "variables": {"minutes": 30},
}


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


async def test_migration_failures_raise_a_repair_issue(hass, hass_storage):
    """Naming the rules, so the user knows what to look at."""
    hass_storage["shabbat_scheduler.rules"] = {
        "version": 1,
        "minor_version": 1,
        "key": "shabbat_scheduler.rules",
        "data": {
            "rules": [V1_SIMPLE_ON, V1_CUSTOM_NO_SCRIPT],
            "defaults": {},
        },
    }

    entry = MockConfigEntry(domain=DOMAIN, title="Shabbat Scheduler")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    issues = async_get_issue_registry(hass)
    issue = issues.async_get_issue(DOMAIN, ISSUE_UNMIGRATED_RULES)
    assert issue is not None
    assert issue.is_fixable is False
    assert "d" in issue.translation_placeholders["rule_ids"]
    assert "b" not in issue.translation_placeholders["rule_ids"].split(", ")


async def test_no_migration_issue_when_nothing_failed(hass):
    """A store that never went through a migration must not be flagged."""
    entry = MockConfigEntry(domain=DOMAIN, title="Shabbat Scheduler")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    issues = async_get_issue_registry(hass)
    assert issues.async_get_issue(DOMAIN, ISSUE_UNMIGRATED_RULES) is None
