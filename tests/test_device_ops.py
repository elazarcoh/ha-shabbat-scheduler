from custom_components.shabbat_scheduler.device_ops import expand_action


def test_most_actions_pass_through_untouched():
    assert expand_action("switch.turn_on", {}) == [("switch.turn_on", {})]
    assert expand_action("scene.turn_on", {"transition": 2}) == [
        ("scene.turn_on", {"transition": 2})
    ]
    assert expand_action("notify.mobile", {"message": "hi"}) == [
        ("notify.mobile", {"message": "hi"})
    ]


def test_set_temperature_with_hvac_mode_is_split():
    """Sent together, several climate integrations silently fail to power on."""
    assert expand_action(
        "climate.set_temperature", {"temperature": 26, "hvac_mode": "cool"}
    ) == [
        ("climate.set_hvac_mode", {"hvac_mode": "cool"}),
        ("climate.set_temperature", {"temperature": 26}),
    ]


def test_set_temperature_without_hvac_mode_is_left_alone():
    assert expand_action("climate.set_temperature", {"temperature": 26}) == [
        ("climate.set_temperature", {"temperature": 26})
    ]


def test_the_split_keeps_every_other_key_on_the_temperature_call():
    calls = expand_action(
        "climate.set_temperature",
        {"temperature": 26, "hvac_mode": "cool", "target_temp_high": 28},
    )
    assert calls[1] == (
        "climate.set_temperature",
        {"temperature": 26, "target_temp_high": 28},
    )


def test_the_split_does_not_mutate_the_caller_s_data():
    data = {"temperature": 26, "hvac_mode": "cool"}
    expand_action("climate.set_temperature", data)
    assert data == {"temperature": 26, "hvac_mode": "cool"}


def test_no_other_climate_service_is_touched():
    assert expand_action("climate.set_hvac_mode", {"hvac_mode": "cool"}) == [
        ("climate.set_hvac_mode", {"hvac_mode": "cool"})
    ]
    assert expand_action("climate.turn_off", {}) == [("climate.turn_off", {})]


def test_the_fan_synonym_table_is_gone():
    """It encoded two AC brands from one house into shared code."""
    import custom_components.shabbat_scheduler.const as const

    assert not hasattr(const, "FAN_SYNONYMS")


def test_fan_mode_gets_its_own_call_not_smuggled_into_set_temperature():
    """HA's set_temperature schema is PREVENT_EXTRA - fan_mode alongside
    temperature is rejected outright, not just a hardware quirk."""
    assert expand_action(
        "climate.set_temperature",
        {"temperature": 26, "hvac_mode": "cool", "fan_mode": "high"},
    ) == [
        ("climate.set_hvac_mode", {"hvac_mode": "cool"}),
        ("climate.set_temperature", {"temperature": 26}),
        ("climate.set_fan_mode", {"fan_mode": "high"}),
    ]


def test_hvac_mode_only_does_not_emit_an_empty_set_temperature_call():
    """set_temperature requires at least one of temperature/target_temp_*;
    an empty {} is rejected by HA, so it must not be emitted at all."""
    assert expand_action("climate.set_temperature", {"hvac_mode": "cool"}) == [
        ("climate.set_hvac_mode", {"hvac_mode": "cool"})
    ]


def test_fan_mode_only_produces_just_the_fan_mode_call():
    assert expand_action("climate.set_temperature", {"fan_mode": "silent"}) == [
        ("climate.set_fan_mode", {"fan_mode": "silent"})
    ]


def test_an_unrecognized_climate_key_rides_along_on_the_temperature_call():
    """swing_mode/humidity are not among the three keys this shim knows
    about, and were never a v1 concept either way. Silently dropping an
    authored key is the wrong default: it should ride along on
    set_temperature and be loudly rejected by HA's PREVENT_EXTRA schema,
    the same way it would be rejected if hvac_mode/fan_mode were absent
    and no split happened at all."""
    assert expand_action(
        "climate.set_temperature",
        {"temperature": 26, "hvac_mode": "cool", "swing_mode": "vertical"},
    ) == [
        ("climate.set_hvac_mode", {"hvac_mode": "cool"}),
        ("climate.set_temperature", {"temperature": 26, "swing_mode": "vertical"}),
    ]


# --- Row 40 at the shim: a None is not a mode ----------------------------


def test_a_null_hvac_mode_does_not_trigger_the_split():
    """`if _HVAC_MODE in data` tested key membership, so a null split off a
    `climate.set_hvac_mode {hvac_mode: None}` - a call guaranteed to fail,
    which is exactly what shim reason 3 refuses to emit."""
    assert expand_action(
        "climate.set_temperature", {"hvac_mode": None, "temperature": 24}
    ) == [("climate.set_temperature", {"temperature": 24})]


def test_a_null_fan_mode_does_not_trigger_the_split():
    assert expand_action(
        "climate.set_temperature", {"fan_mode": None, "temperature": 24}
    ) == [("climate.set_temperature", {"temperature": 24})]


def test_a_null_mode_is_not_left_riding_along_on_the_temperature_call():
    """Dropped rather than carried: `SET_TEMPERATURE_SCHEMA` coerces
    `hvac_mode` through `vol.Coerce(HVACMode)`, which a None fails, so
    carrying it would take the temperature down with it."""
    for key in ("hvac_mode", "fan_mode"):
        calls = expand_action("climate.set_temperature", {key: None, "temperature": 24})
        assert all(key not in data for _action, data in calls), key


def test_all_null_modes_leave_the_temperature_call_alone():
    assert expand_action(
        "climate.set_temperature",
        {"hvac_mode": None, "fan_mode": None, "temperature": 24},
    ) == [("climate.set_temperature", {"temperature": 24})]


def test_a_real_mode_still_splits_exactly_as_before():
    """The guard must not be so wide it stops the shim doing its job."""
    assert expand_action(
        "climate.set_temperature",
        {"hvac_mode": "cool", "temperature": 24, "fan_mode": "quiet"},
    ) == [
        ("climate.set_hvac_mode", {"hvac_mode": "cool"}),
        ("climate.set_temperature", {"temperature": 24}),
        ("climate.set_fan_mode", {"fan_mode": "quiet"}),
    ]
