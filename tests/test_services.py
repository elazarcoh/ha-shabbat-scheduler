from datetime import time

import pytest
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.shabbat_scheduler.const import DOMAIN
from custom_components.shabbat_scheduler.models import Action, Rule
from custom_components.shabbat_scheduler.store import RuleStore


async def _setup(hass, rules=()):
    await hass.config.async_set_time_zone("Asia/Jerusalem")
    store = RuleStore(hass)
    await store.async_load()
    if rules:
        await store.async_replace_all({}, list(rules))
    entry = MockConfigEntry(domain=DOMAIN, title="Shabbat Scheduler")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_simulate_returns_resolved_rules(hass):
    hass.states.async_set(
        "sensor.jewish_calendar_upcoming_candle_lighting",
        "2026-08-14T15:44:00+00:00",
    )
    hass.states.async_set(
        "sensor.jewish_calendar_upcoming_havdalah", "2026-08-15T17:01:00+00:00"
    )
    await _setup(hass, [
        Rule(id="r1", profile=1, day="1", time=time(11, 0),
             action=Action.ON, devices=("climate.a",)),
    ])

    response = await hass.services.async_call(
        DOMAIN, "simulate", {}, blocking=True, return_response=True
    )
    assert response["profile"] == 1
    assert len(response["rules"]) == 1
    assert response["rules"][0]["action"] == "on"


async def test_simulate_reports_conflicts(hass):
    hass.states.async_set(
        "sensor.jewish_calendar_upcoming_candle_lighting",
        "2026-08-14T15:44:00+00:00",
    )
    hass.states.async_set(
        "sensor.jewish_calendar_upcoming_havdalah", "2026-08-15T17:01:00+00:00"
    )
    await _setup(hass, [
        Rule(id="a", profile=1, day="1", time=time(18, 0),
             action=Action.ON, devices=("climate.a",)),
        Rule(id="b", profile=1, day="1", time=time(18, 0),
             action=Action.OFF, devices=("climate.a",)),
    ])

    response = await hass.services.async_call(
        DOMAIN, "simulate", {}, blocking=True, return_response=True
    )
    assert len(response["conflicts"]) == 1


async def test_simulate_warns_when_profile_missing(hass):
    hass.states.async_set(
        "sensor.jewish_calendar_upcoming_candle_lighting",
        "2026-08-14T15:44:00+00:00",
    )
    hass.states.async_set(
        "sensor.jewish_calendar_upcoming_havdalah", "2026-08-15T17:01:00+00:00"
    )
    await _setup(hass, [
        Rule(id="r1", profile=3, day="1", time=time(11, 0), action=Action.ON),
    ])

    response = await hass.services.async_call(
        DOMAIN, "simulate", {}, blocking=True, return_response=True
    )
    assert response["warnings"]


async def test_set_dry_run(hass):
    await _setup(hass)
    await hass.services.async_call(
        DOMAIN, "set_dry_run", {"enabled": True}, blocking=True
    )
    store = RuleStore(hass)
    await store.async_load()
    assert store.dry_run is True


async def test_yaml_export_then_import(hass):
    await _setup(hass, [
        Rule(id="r1", profile=1, day="1", time=time(11, 0),
             action=Action.ON, devices=("climate.a",)),
    ])
    exported = await hass.services.async_call(
        DOMAIN, "export_yaml", {}, blocking=True, return_response=True
    )
    assert "profiles" in exported["yaml"]

    await hass.services.async_call(
        DOMAIN, "import_yaml", {"yaml": exported["yaml"]}, blocking=True
    )
    store = RuleStore(hass)
    await store.async_load()
    assert len(store.rules) == 1


async def test_import_yaml_rejects_syntactically_invalid_yaml(hass):
    await _setup(hass, [
        Rule(id="r1", profile=1, day="1", time=time(11, 0),
             action=Action.ON, devices=("climate.a",)),
    ])

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN, "import_yaml", {"yaml": "defaults: [1, 2"}, blocking=True
        )

    store = RuleStore(hass)
    await store.async_load()
    assert len(store.rules) == 1
    assert store.rules[0].id == "r1"


async def test_import_yaml_rejects_entry_missing_action(hass):
    await _setup(hass, [
        Rule(id="r1", profile=1, day="1", time=time(11, 0),
             action=Action.ON, devices=("climate.a",)),
    ])
    bad_yaml = """
defaults: {}
profiles:
  1_day:
    day_1:
    - id: r2
      at: '11:00:00'
      devices: [climate.a]
"""

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN, "import_yaml", {"yaml": bad_yaml}, blocking=True
        )

    store = RuleStore(hass)
    await store.async_load()
    assert len(store.rules) == 1
    assert store.rules[0].id == "r1"


async def test_import_yaml_rejects_invalid_action_value(hass):
    await _setup(hass, [
        Rule(id="r1", profile=1, day="1", time=time(11, 0),
             action=Action.ON, devices=("climate.a",)),
    ])
    bad_yaml = """
defaults: {}
profiles:
  1_day:
    day_1:
    - id: r2
      at: '11:00:00'
      action: sideways
"""

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN, "import_yaml", {"yaml": bad_yaml}, blocking=True
        )

    store = RuleStore(hass)
    await store.async_load()
    assert len(store.rules) == 1
    assert store.rules[0].id == "r1"


async def test_services_removed_on_unload(hass):
    entry = await _setup(hass)

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert hass.services.has_service(DOMAIN, "simulate") is False
    assert hass.services.has_service(DOMAIN, "set_dry_run") is False
    assert hass.services.has_service(DOMAIN, "export_yaml") is False
    assert hass.services.has_service(DOMAIN, "import_yaml") is False


async def test_import_yaml_rejects_an_unknown_day_key_and_keeps_the_store(hass):
    """A typo'd day key must never reach .storage.

    _import_yaml persists BEFORE refreshing, so a stored `dya_1` used to make
    async_setup_entry raise on every restart AND make export_yaml raise, so
    the user could not dump the rules to find it.
    """
    await _setup(hass, [
        Rule(id="r1", profile=1, day="1", time=time(11, 0),
             action=Action.ON, devices=("climate.a",)),
    ])
    bad_yaml = """
defaults: {}
profiles:
  1_day:
    dya_1:
    - id: r2
      at: '23:00:00'
      action: 'off'
      devices: [climate.a]
"""

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            DOMAIN, "import_yaml", {"yaml": bad_yaml}, blocking=True
        )

    store = RuleStore(hass)
    await store.async_load()
    assert [rule.id for rule in store.rules] == ["r1"]
    assert store.rules[0].day == "1"


async def test_import_yaml_rebuilds_the_rule_switches(hass):
    """An import replaces the whole rule set.

    The change fans out over `SIGNAL_RULES_CHANGED`, so the new rules get a
    switch and the deleted rules' switches are removed - dynamically, with
    no config-entry reload.
    """
    entry = await _setup(hass, [
        Rule(id="old", profile=1, day="1", time=time(11, 0),
             action=Action.ON, devices=("climate.a",)),
    ])
    registry = er.async_get(hass)
    assert registry.async_get_entity_id(
        "switch", DOMAIN, f"{entry.entry_id}_rule_old"
    ) is not None

    await hass.services.async_call(
        DOMAIN, "import_yaml",
        {"yaml": """
defaults: {}
profiles:
  1_day:
    day_1:
    - id: fresh
      at: '11:00:00'
      action: 'on'
      devices: [climate.a]
"""},
        blocking=True,
    )
    await hass.async_block_till_done()

    fresh = registry.async_get_entity_id(
        "switch", DOMAIN, f"{entry.entry_id}_rule_fresh"
    )
    assert fresh is not None
    assert hass.states.get(fresh) is not None

    # The switch for the rule that no longer exists is gone entirely - not
    # left behind as an "unavailable" orphan that looks broken.
    assert registry.async_get_entity_id(
        "switch", DOMAIN, f"{entry.entry_id}_rule_old"
    ) is None

    store = RuleStore(hass)
    await store.async_load()
    assert [rule.id for rule in store.rules] == ["fresh"]
