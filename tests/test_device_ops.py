from custom_components.shabbat_scheduler.device_ops import (
    Call,
    plan_calls,
    resolve_fan_mode,
)
from custom_components.shabbat_scheduler.models import Action

CLIMATE_ATTRS = {
    "fan_modes": ["auto", "quiet", "low", "high"],
    "temperature": 26,
    "fan_mode": "auto",
}


def test_resolve_fan_mode_exact_match():
    assert resolve_fan_mode("quiet", ["auto", "quiet"]) == "quiet"


def test_resolve_fan_mode_falls_back_to_synonym():
    # The aux_cloud units expose "silent" where the other AC exposes "quiet".
    assert resolve_fan_mode("quiet", ["auto", "silent", "low"]) == "silent"


def test_resolve_fan_mode_returns_none_when_unsupported():
    assert resolve_fan_mode("quiet", ["auto", "high"]) is None


def test_climate_on_emits_three_separate_calls():
    calls = plan_calls(
        "climate.a", "off", CLIMATE_ATTRS, Action.ON,
        {"hvac_mode": "cool", "temperature": 24, "fan_mode": "quiet"}, force=False,
    )
    assert [c.service for c in calls] == [
        "set_hvac_mode", "set_temperature", "set_fan_mode",
    ]
    # Never the combined form - it silently fails to power on aux_cloud units.
    assert all("hvac_mode" not in c.data for c in calls if c.service == "set_temperature")


def test_already_correct_values_are_skipped():
    calls = plan_calls(
        "climate.a", "cool", CLIMATE_ATTRS, Action.ON,
        {"hvac_mode": "cool", "temperature": 26, "fan_mode": "auto"}, force=False,
    )
    assert calls == []


def test_only_differing_values_are_emitted():
    calls = plan_calls(
        "climate.a", "cool", CLIMATE_ATTRS, Action.ON,
        {"hvac_mode": "cool", "temperature": 24, "fan_mode": "auto"}, force=False,
    )
    assert [c.attribute for c in calls] == ["temperature"]
    assert calls[0].from_value == 26
    assert calls[0].to_value == 24


def test_force_emits_everything_even_when_matching():
    calls = plan_calls(
        "climate.a", "cool", CLIMATE_ATTRS, Action.ON,
        {"hvac_mode": "cool", "temperature": 26, "fan_mode": "auto"}, force=True,
    )
    assert len(calls) == 3


def test_unsupported_fan_mode_is_skipped_not_fatal():
    attrs = {**CLIMATE_ATTRS, "fan_modes": ["auto", "high"]}
    calls = plan_calls(
        "climate.a", "off", attrs, Action.ON,
        {"hvac_mode": "cool", "fan_mode": "quiet"}, force=False,
    )
    assert [c.service for c in calls] == ["set_hvac_mode"]


def test_climate_off_when_already_off_is_skipped():
    assert plan_calls("climate.a", "off", CLIMATE_ATTRS, Action.OFF, {}, force=False) == []


def test_climate_off_when_on_emits_turn_off():
    calls = plan_calls("climate.a", "cool", CLIMATE_ATTRS, Action.OFF, {}, force=False)
    assert [(c.domain, c.service) for c in calls] == [("climate", "turn_off")]


def test_switch_domain_uses_turn_on_off():
    calls = plan_calls("switch.a", "off", {}, Action.ON, {}, force=False)
    assert [(c.domain, c.service) for c in calls] == [("switch", "turn_on")]


def test_input_boolean_domain_supported_for_testing():
    calls = plan_calls("input_boolean.t", "off", {}, Action.ON, {}, force=False)
    assert [(c.domain, c.service) for c in calls] == [("input_boolean", "turn_on")]
