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
