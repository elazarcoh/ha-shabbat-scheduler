from datetime import time

from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.shabbat_scheduler.const import DOMAIN
from custom_components.shabbat_scheduler.models import Replay, Rule
from custom_components.shabbat_scheduler.store import RuleStore


async def _setup(hass, rules=()):
    await hass.config.async_set_time_zone("Asia/Jerusalem")
    store = RuleStore(hass)
    await store.async_load()
    for rule in rules:
        await store.async_add(rule)

    entry = MockConfigEntry(domain=DOMAIN, title="Shabbat Scheduler")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_entry_sets_up_and_unloads(hass):
    entry = await _setup(hass)
    assert entry.entry_id in hass.data[DOMAIN]

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.entry_id not in hass.data[DOMAIN]


async def test_only_one_instance_allowed(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] == "form"
    # Neither default zmanim entity exists in this hass instance, so the
    # form has no default to fall back on and must be filled explicitly.
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "candle_sensor": "sensor.jewish_calendar_upcoming_candle_lighting",
            "havdalah_sensor": "sensor.jewish_calendar_upcoming_havdalah",
        },
    )
    assert result["type"] == "create_entry"

    second = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert second["type"] == "abort"
    assert second["reason"] == "single_instance_allowed"


async def test_master_switch_defaults_off(hass):
    await _setup(hass)
    state = hass.states.get("switch.shabbat_scheduler")
    assert state is not None
    assert state.state == STATE_OFF


async def test_master_switch_turns_on_and_persists(hass):
    await _setup(hass)
    await hass.services.async_call(
        "switch", "turn_on",
        {"entity_id": "switch.shabbat_scheduler"}, blocking=True,
    )
    assert hass.states.get("switch.shabbat_scheduler").state == STATE_ON

    reloaded = RuleStore(hass)
    await reloaded.async_load()
    assert reloaded.enabled is True


async def test_one_switch_per_rule(hass, rule_switch_entity_id):
    entry = await _setup(hass, [
        Rule(id="r1", profile=1, day="1", time=time(11, 0),
             action="input_boolean.turn_on", name="בוקר שבת"),
    ])
    entity_id = rule_switch_entity_id(entry, "r1")
    assert entity_id is not None
    assert hass.states.get(entity_id) is not None

    entry_reg = er.async_get(hass).async_get(entity_id)
    assert entry_reg.unique_id == f"{entry.entry_id}_rule_r1"


async def test_rule_switch_toggle_persists(hass, rule_switch_entity_id):
    entry = await _setup(hass, [
        Rule(id="r1", profile=1, day="1", time=time(11, 0),
             action="input_boolean.turn_on"),
    ])
    entity_id = rule_switch_entity_id(entry, "r1")
    assert entity_id is not None
    await hass.services.async_call(
        "switch", "turn_off", {"entity_id": entity_id}, blocking=True
    )

    reloaded = RuleStore(hass)
    await reloaded.async_load()
    assert reloaded.rules[0].enabled is False


async def test_next_block_sensor_reports_length(hass):
    hass.states.async_set(
        "sensor.jewish_calendar_upcoming_candle_lighting",
        "2026-08-14T15:44:00+00:00",
    )
    hass.states.async_set(
        "sensor.jewish_calendar_upcoming_havdalah", "2026-08-15T17:01:00+00:00"
    )
    await _setup(hass)
    state = hass.states.get("sensor.shabbat_scheduler_next_block")
    assert state is not None
    assert state.state == "1"


async def test_next_action_sensor_unknown_when_master_off(hass):
    hass.states.async_set(
        "sensor.jewish_calendar_upcoming_candle_lighting",
        "2026-08-14T15:44:00+00:00",
    )
    hass.states.async_set(
        "sensor.jewish_calendar_upcoming_havdalah", "2026-08-15T17:01:00+00:00"
    )
    await _setup(hass, [
        Rule(id="r1", profile=1, day="1", time=time(11, 0),
             action="input_boolean.turn_on"),
    ])
    assert hass.states.get("sensor.shabbat_scheduler_next_action").state == "unknown"


async def test_last_run_sensor_exists(hass):
    await _setup(hass)
    state = hass.states.get("sensor.shabbat_scheduler_last_run")
    assert state is not None
    assert state.state == "unknown"


async def test_last_run_sensor_reports_timestamp_after_a_run(hass, test_booleans):
    entry = await _setup(hass)
    hass.states.async_set("input_boolean.t", "off")
    engine = hass.data[DOMAIN][entry.entry_id]["engine"]

    await engine.async_apply_rule(
        Rule(
            id="r1", profile=1, day="1", time=time(11, 0),
            action="input_boolean.turn_on",
            target={"entity_id": ["input_boolean.t"]},
        )
    )
    await hass.async_block_till_done()

    state = hass.states.get("sensor.shabbat_scheduler_last_run")
    assert state.state != "unknown"
    assert state.attributes["result_count"] == 1


async def test_last_run_sensor_distinguishes_empty_run_from_never_ran(hass):
    """A run that genuinely happened but produced zero results must still be
    distinguishable from a sensor that has never run at all - that is the
    whole point of last_run.

    Comparing against the never-ran baseline (rather than just asserting
    != "unknown") matters: under the pre-fix len()-based implementation,
    the never-ran state is "0" - not "unknown" - and an empty-results run
    is also "0", so the two are silently identical. Only a direct
    before/after comparison exposes that ambiguity.

    v2 note: the empty-results path used to be a CUSTOM rule with no
    script configured. `expand_action` now always yields at least one call
    for any action, so `async_apply_rule` can no longer return []. The
    surviving zero-results run is a catch-up with nothing opted in to
    replay - which still stamps `last_run`/`last_run_at` and still fires
    EVENT_RULE_COMPLETED, so the ambiguity being guarded is unchanged.
    """
    entry = await _setup(hass)
    never_ran_state = hass.states.get("sensor.shabbat_scheduler_last_run").state

    engine = hass.data[DOMAIN][entry.entry_id]["engine"]
    _zmanim(hass)
    await engine.store.async_set_enabled(True)
    await engine.store.async_replace_all({}, [
        Rule(id="r1", profile=1, day="1", time=time(11, 0),
             action="input_boolean.turn_on",
             target={"entity_id": ["input_boolean.t"]}),
    ])
    await engine.async_refresh()
    results = await engine.async_catch_up()

    assert results == []  # confirms this is the ambiguous empty-results path
    await hass.async_block_till_done()

    state = hass.states.get("sensor.shabbat_scheduler_last_run")
    assert state.state != never_ran_state
    assert state.attributes["result_count"] == 0
    await engine.async_shutdown()


# --- Final review C2: restart catch-up must not be a one-shot inline in ----
# --- setup (it usually no-ops, and sometimes blocks setup for minutes) -----

import asyncio

from custom_components.shabbat_scheduler.const import CANDLE_SENSOR, HAVDALAH_SENSOR
from custom_components.shabbat_scheduler.engine import ShabbatEngine


def _zmanim(hass):
    hass.states.async_set(CANDLE_SENSOR, "2026-08-14T15:44:00+00:00")
    hass.states.async_set(HAVDALAH_SENSOR, "2026-08-15T17:01:00+00:00")


async def _entry_with(hass, rules, enabled=True):
    await hass.config.async_set_time_zone("Asia/Jerusalem")
    store = RuleStore(hass)
    await store.async_load()
    await store.async_replace_all({}, list(rules))
    if enabled:
        await store.async_set_enabled(True)
    entry = MockConfigEntry(domain=DOMAIN, title="Shabbat Scheduler")
    entry.add_to_hass(hass)
    return entry


async def test_catch_up_runs_when_zmanim_arrive_after_setup(
    hass, test_booleans, freezer
):
    """At boot, config entries set up concurrently.

    jewish_calendar may not have published its sensors when this integration
    is set up, so an inline one-shot catch-up sees no block, returns [], and
    is never retried - losing exactly the mid-block restart the feature
    exists for. It must run when the block first becomes computable.
    """
    freezer.move_to("2026-08-15T08:30:00+00:00")  # 11:30 Asia/Jerusalem
    entry = await _entry_with(hass, [
        Rule(id="on", profile=1, day="1", time=time(11, 0),
             action="input_boolean.turn_on",
             target={"entity_id": ["input_boolean.t"]},
             # v2: catch-up is opt-in per rule.
             replay=Replay(enabled=True)),
    ])
    hass.states.async_set("input_boolean.t", "off")

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    # No zmanim yet: nothing can be caught up.
    assert hass.states.get("input_boolean.t").state == "off"

    _zmanim(hass)
    await hass.async_block_till_done(wait_background_tasks=True)

    assert hass.states.get("input_boolean.t").state == "on"


async def test_catch_up_runs_at_most_once_per_setup(
    hass, test_booleans, freezer, monkeypatch
):
    freezer.move_to("2026-08-15T08:30:00+00:00")
    runs = []
    original = ShabbatEngine.async_catch_up

    async def counting(self):
        runs.append(1)
        return await original(self)

    monkeypatch.setattr(ShabbatEngine, "async_catch_up", counting)

    _zmanim(hass)
    entry = await _entry_with(hass, [
        Rule(id="on", profile=1, day="1", time=time(11, 0),
             action="input_boolean.turn_on",
             target={"entity_id": ["input_boolean.t"]},
             # v2: catch-up is opt-in per rule.
             replay=Replay(enabled=True)),
    ])
    hass.states.async_set("input_boolean.t", "off")

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert len(runs) == 1

    # jewish_calendar republishes (it does so routinely); catch-up must not
    # run a second time and re-apply anything.
    hass.states.async_set(CANDLE_SENSOR, "2026-08-14T15:44:01+00:00")
    await hass.async_block_till_done(wait_background_tasks=True)
    assert len(runs) == 1


async def test_setup_completes_while_an_unavailable_device_is_retried(
    hass, freezer
):
    """Unavailable devices force a call, retried 3x30s each.

    Inline in setup that is ~12 minutes of blocked async_setup_entry for four
    ACs before any of this integration's own entities exist.
    """
    freezer.move_to("2026-08-15T08:30:00+00:00")
    gate = asyncio.Event()
    reached = []

    async def hanging_turn_on(call):
        reached.append(call)
        await gate.wait()

    hass.services.async_register("fan", "turn_on", hanging_turn_on)
    hass.states.async_set("fan.ac", "unavailable")
    _zmanim(hass)

    entry = await _entry_with(hass, [
        Rule(id="on", profile=1, day="1", time=time(11, 0),
             action="fan.turn_on", target={"entity_id": ["fan.ac"]},
             replay=Replay(enabled=True)),
    ])

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # The catch-up call is still in flight against the stuck device...
    assert reached, "expected catch-up to have started the device call"
    assert not gate.is_set()
    # ...yet setup finished and this integration's entities exist.
    assert hass.states.get("switch.shabbat_scheduler") is not None
    assert hass.states.get("sensor.shabbat_scheduler_next_block") is not None

    gate.set()
    await hass.async_block_till_done(wait_background_tasks=True)
