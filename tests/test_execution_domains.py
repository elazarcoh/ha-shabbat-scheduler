"""The executor must be generic, not climate-shaped.

v1 understood five domains and hard-coded them. v2's whole claim is that a
rule is any Home Assistant service call, and the only domain knowledge
left is one documented shim for climate.set_temperature. These tests are
what makes that claim answerable.

Existing coverage this file does NOT duplicate:
- `tests/test_engine.py:test_an_unsupported_domain_is_no_longer_a_thing`
  already exercises `cover.close_cover` end to end - the direct predecessor
  of the parametrised test below, kept there because it is about the v1
  allow-list being gone rather than about domain genericity as such.
- `tests/test_engine.py:test_a_rule_can_still_call_a_script` already
  exercises `script.turn_on`, and
  `tests/test_engine.py:test_a_rule_with_no_target_is_unaffected` already
  exercises `notify.persistent_notification` with no target - both fixed
  targets of a single test, not parametrised across domains.
- `tests/test_engine.py:test_failed_call_is_retried_then_notified` and
  `test_retry_succeeds_on_second_attempt` and
  `test_failure_records_the_exception_and_a_reason` all call
  `switch.turn_on`, but only to exercise retry/failure reporting.
- `tests/test_device_ops.py:test_most_actions_pass_through_untouched`
  already proves `expand_action` passes `switch.turn_on`, `scene.turn_on`
  (with data) and `notify.mobile` straight through, at the pure-function
  level with no `hass` involved. `test_no_domain_other_than_climate_is_rewritten`
  below is the broader, HA-free guard the spec asks for: nine domains,
  including one climate action (`set_hvac_mode`) that must NOT be
  mistaken for the one that IS rewritten.
- None of the above calls `switch.turn_on`/`scene.turn_on`/`script.turn_on`
  against a REAL registered service via `async_mock_service` and asserts
  on the call actually made with matching data - which is what the
  parametrised test below adds for each of seven domains.
"""

import pytest
from pytest_homeassistant_custom_component.common import async_mock_service


@pytest.mark.parametrize(
    ("action", "target", "data", "expected_domain", "expected_service"),
    [
        ("switch.turn_on", {"entity_id": ["switch.pump"]}, {},
         "switch", "turn_on"),
        ("scene.turn_on", {"entity_id": ["scene.evening"]}, {},
         "scene", "turn_on"),
        ("script.turn_on", {"entity_id": ["script.beep"]}, {},
         "script", "turn_on"),
        ("notify.persistent_notification", {}, {"message": "shalom"},
         "notify", "persistent_notification"),
        ("input_boolean.turn_off", {"entity_id": ["input_boolean.a"]}, {},
         "input_boolean", "turn_off"),
        ("lock.lock", {"entity_id": ["lock.front"]}, {},
         "lock", "lock"),
        ("cover.close_cover", {"entity_id": ["cover.blind"]}, {},
         "cover", "close_cover"),
    ],
)
async def test_the_engine_calls_any_domain_untouched(
    hass, engine, _rule, action, target, data,
    expected_domain, expected_service,
):
    """No shim, no rewriting - exactly one call, exactly as authored."""
    for entity_id in target.get("entity_id", []):
        hass.states.async_set(entity_id, "off")
    calls = async_mock_service(hass, expected_domain, expected_service)
    rule = _rule(action=action, entities=target.get("entity_id", ()), data=data)

    [result] = await engine.async_apply_rule(rule)

    assert result["outcome"] == "called"
    assert "unknown_targets" not in result
    assert "no_live_targets" not in result
    assert len(calls) == 1
    assert calls[0].domain == expected_domain
    assert calls[0].service == expected_service
    for key, value in data.items():
        assert calls[0].data[key] == value


async def test_climate_set_temperature_is_the_one_documented_exception(
    hass, engine, _rule
):
    """The single shim, and it must stay single.

    device_ops.expand_action splits this into ordered calls because
    Home Assistant's SET_TEMPERATURE_SCHEMA is PREVENT_EXTRA and refuses
    hvac_mode/fan_mode alongside a temperature.
    """
    hass.states.async_set("climate.salon", "off")
    hvac = async_mock_service(hass, "climate", "set_hvac_mode")
    temp = async_mock_service(hass, "climate", "set_temperature")
    fan = async_mock_service(hass, "climate", "set_fan_mode")

    rule = _rule(
        action="climate.set_temperature",
        entities=("climate.salon",),
        data={"hvac_mode": "cool", "temperature": 24, "fan_mode": "high"},
    )
    results = await engine.async_apply_rule(rule)

    assert [r["outcome"] for r in results] == ["called"] * 3
    assert len(hvac) == 1 and len(temp) == 1 and len(fan) == 1
    assert hvac[0].data["hvac_mode"] == "cool"
    assert temp[0].data["temperature"] == 24
    assert "hvac_mode" not in temp[0].data
    assert fan[0].data["fan_mode"] == "high"


async def test_no_domain_other_than_climate_is_rewritten():
    """The guard on the shim staying narrow.

    If a second domain ever grows special handling, this fails - which is
    the point. Domain knowledge here must justify itself as a shim.
    """
    from custom_components.shabbat_scheduler.device_ops import expand_action

    for action in (
        "switch.turn_on", "light.turn_on", "climate.set_hvac_mode",
        "scene.turn_on", "script.turn_on", "notify.notify",
        "lock.lock", "cover.open_cover", "media_player.play_media",
    ):
        data = {"anything": 1}
        assert expand_action(action, dict(data)) == [(action, data)], action
