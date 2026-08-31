"""The config flow: which two zmanim sensors define a block, and later
the options flow that lets them be changed without removing the
integration."""

from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.shabbat_scheduler.const import (
    CONF_AUTO_DISARM,
    CONF_CANDLE_SENSOR,
    CONF_HAVDALAH_SENSOR,
    DEFAULT_AUTO_DISARM,
    DEFAULT_CANDLE_SENSOR,
    DEFAULT_HAVDALAH_SENSOR,
    DOMAIN,
)


async def test_the_flow_offers_the_zmanim_sensors(hass):
    hass.states.async_set(DEFAULT_CANDLE_SENSOR, "2026-08-14T15:44:00+00:00")
    hass.states.async_set(DEFAULT_HAVDALAH_SENSOR, "2026-08-15T17:01:00+00:00")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    assert result["type"] == "form"
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})

    assert result["type"] == "create_entry"
    assert result["data"][CONF_CANDLE_SENSOR] == DEFAULT_CANDLE_SENSOR
    assert result["data"][CONF_HAVDALAH_SENSOR] == DEFAULT_HAVDALAH_SENSOR
    # Off by default on a fresh install - see const.py's DEFAULT_AUTO_DISARM.
    assert result["data"][CONF_AUTO_DISARM] == DEFAULT_AUTO_DISARM is False


async def test_custom_sensor_names_are_accepted(hass):
    """The whole point: a second Jewish Calendar entry names its sensors
    after its own title, so the defaults do not exist for everyone."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_CANDLE_SENSOR: "sensor.jc_home_upcoming_candle_lighting",
            CONF_HAVDALAH_SENSOR: "sensor.jc_home_upcoming_havdalah",
        },
    )

    assert result["type"] == "create_entry"
    assert result["data"][CONF_CANDLE_SENSOR] == "sensor.jc_home_upcoming_candle_lighting"
    assert result["data"][CONF_HAVDALAH_SENSOR] == "sensor.jc_home_upcoming_havdalah"


async def test_a_second_instance_is_refused(hass):
    entry = MockConfigEntry(domain=DOMAIN, title="Shabbat Scheduler")
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )

    assert result["type"] == "abort"
    assert result["reason"] == "single_instance_allowed"


async def test_the_engine_reads_the_configured_sensors(hass, jerusalem):
    """The whole point, proven end to end: an entry configured with
    non-default sensor names must actually resolve a block from THOSE
    entities, not merely accept their names in the form. A test that only
    checks the config entry's stored data, or only the failure path, would
    pass identically whether `_read_zmanim` used `self._candle_sensor` or
    the old hardcoded `DEFAULT_CANDLE_SENSOR` constant - this one would not,
    because the default entity ids are deliberately never set here at all.
    """
    candle_sensor = "sensor.jc_home_upcoming_candle_lighting"
    havdalah_sensor = "sensor.jc_home_upcoming_havdalah"
    hass.states.async_set(candle_sensor, "2026-08-14T15:44:00+00:00")
    hass.states.async_set(havdalah_sensor, "2026-08-15T17:01:00+00:00")

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Shabbat Scheduler",
        data={
            CONF_CANDLE_SENSOR: candle_sensor,
            CONF_HAVDALAH_SENSOR: havdalah_sensor,
        },
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    engine = hass.data[DOMAIN][entry.entry_id]["engine"]

    assert engine.current_block is not None
    assert engine.current_block.candle_lighting.astimezone(dt_util.UTC) == dt_util.parse_datetime(
        "2026-08-14T15:44:00+00:00"
    )
    assert engine.current_block.havdalah.astimezone(dt_util.UTC) == dt_util.parse_datetime(
        "2026-08-15T17:01:00+00:00"
    )


async def test_the_options_flow_can_change_them_later(hass):
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Shabbat Scheduler",
        data={
            CONF_CANDLE_SENSOR: DEFAULT_CANDLE_SENSOR,
            CONF_HAVDALAH_SENSOR: DEFAULT_HAVDALAH_SENSOR,
        },
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == "form"
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_CANDLE_SENSOR: "sensor.jc_home_upcoming_candle_lighting",
            CONF_HAVDALAH_SENSOR: "sensor.jc_home_upcoming_havdalah",
        },
    )
    await hass.async_block_till_done()

    assert result["type"] == "create_entry"
    assert entry.options[CONF_CANDLE_SENSOR] == "sensor.jc_home_upcoming_candle_lighting"
    assert entry.options[CONF_HAVDALAH_SENSOR] == "sensor.jc_home_upcoming_havdalah"

    # The change took effect without a restart: the reloaded engine reads
    # the new entity ids, not the ones the entry was created with.
    engine = hass.data[DOMAIN][entry.entry_id]["engine"]
    assert engine._candle_sensor == "sensor.jc_home_upcoming_candle_lighting"
    assert engine._havdalah_sensor == "sensor.jc_home_upcoming_havdalah"


async def test_auto_disarm_can_be_turned_on_via_options(hass):
    """The whole point of the option: a household can opt into the master

    switch resetting itself, and the reloaded engine actually picks it up -
    not just a value sitting unread in the config entry.
    """
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Shabbat Scheduler",
        data={
            CONF_CANDLE_SENSOR: DEFAULT_CANDLE_SENSOR,
            CONF_HAVDALAH_SENSOR: DEFAULT_HAVDALAH_SENSOR,
        },
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    engine = hass.data[DOMAIN][entry.entry_id]["engine"]
    assert engine._auto_disarm_enabled is False  # off by default

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_CANDLE_SENSOR: DEFAULT_CANDLE_SENSOR,
            CONF_HAVDALAH_SENSOR: DEFAULT_HAVDALAH_SENSOR,
            CONF_AUTO_DISARM: True,
        },
    )
    await hass.async_block_till_done()

    assert result["type"] == "create_entry"
    assert entry.options[CONF_AUTO_DISARM] is True

    reloaded_engine = hass.data[DOMAIN][entry.entry_id]["engine"]
    assert reloaded_engine._auto_disarm_enabled is True


async def test_auto_disarm_explicitly_off_in_options_does_not_fall_back_to_data(hass):
    """Regression guard for `_configured_bool` (__init__.py).

    An `entry.options.get(key) or entry.data.get(key, default)` idiom -
    correct for a sensor id, where an empty string is not a real value -
    is WRONG for a bool: `False or entry.data[key]` evaluates the RIGHT
    side, so an explicit "off" in options would silently read back as
    whatever "on" the entry was originally created with. This entry is
    deliberately created with auto_disarm ON in `data`, then turned off
    via options, to catch exactly that regression.
    """
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Shabbat Scheduler",
        data={
            CONF_CANDLE_SENSOR: DEFAULT_CANDLE_SENSOR,
            CONF_HAVDALAH_SENSOR: DEFAULT_HAVDALAH_SENSOR,
            CONF_AUTO_DISARM: True,
        },
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.data[DOMAIN][entry.entry_id]["engine"]._auto_disarm_enabled is True

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_CANDLE_SENSOR: DEFAULT_CANDLE_SENSOR,
            CONF_HAVDALAH_SENSOR: DEFAULT_HAVDALAH_SENSOR,
            CONF_AUTO_DISARM: False,
        },
    )
    await hass.async_block_till_done()

    assert entry.options[CONF_AUTO_DISARM] is False
    reloaded_engine = hass.data[DOMAIN][entry.entry_id]["engine"]
    assert reloaded_engine._auto_disarm_enabled is False
