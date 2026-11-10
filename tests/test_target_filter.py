"""target_filter reads which entities an action takes from HA's descriptions.

Kept identical in ha-sequence-scheduler and ha-shabbat-scheduler (only the
import line differs).
"""

from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.service import async_set_service_schema
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.shabbat_scheduler import target_filter as tf


def describe_target(hass, action, entity):
    domain, service = action.split(".")
    async_mock_service(hass, domain, service)
    desc = {"fields": {}}
    if entity is not None:
        desc["target"] = {"entity": entity}
    async_set_service_schema(hass, domain, service, desc)


async def test_domain_filter_rejects_other_domains(hass):
    describe_target(hass, "input_boolean.turn_on", [{"domain": ["input_boolean"]}])
    assert tf.accepts(hass, "input_boolean.turn_on", "input_boolean.x")
    assert not tf.accepts(hass, "input_boolean.turn_on", "switch.x")
    assert tf.rejected(hass, "input_boolean.turn_on", ["switch.b", "input_boolean.a", "switch.a"]) == [
        "switch.a", "switch.b"]


async def test_a_group_is_always_accepted_since_home_assistant_expands_it(hass):
    describe_target(hass, "light.turn_on", [{"domain": ["light"]}])
    assert tf.accepts(hass, "light.turn_on", "group.downstairs")


async def test_any_matching_filter_is_enough(hass):
    describe_target(hass, "x.go", [{"domain": ["light"]}, {"domain": ["switch"]}])
    assert tf.accepts(hass, "x.go", "switch.a")
    assert not tf.accepts(hass, "x.go", "fan.a")


async def test_no_filter_or_no_description_accepts_everything(hass):
    describe_target(hass, "homeassistant.turn_on", None)  # target: {}
    assert tf.accepts(hass, "homeassistant.turn_on", "switch.a")
    async_mock_service(hass, "plain", "go")  # never described
    assert tf.accepts(hass, "plain.go", "switch.a")
    assert tf.accepts(hass, "missing.action", "switch.a")


async def test_a_filter_without_domain_or_integration_accepts_everything(hass):
    describe_target(hass, "x.go", [{"domain": ["light"]}, {"device_class": "door"}])
    assert tf.accepts(hass, "x.go", "switch.a")


async def test_features_are_not_checked(hass):
    describe_target(hass, "climate.set_fan_mode", [{"domain": ["climate"], "supported_features": [8]}])
    assert tf.accepts(hass, "climate.set_fan_mode", "climate.kids")


async def test_integration_filter_uses_the_registry_platform(hass):
    describe_target(hass, "zz.reset", [{"integration": "zz"}])
    reg = er.async_get(hass)
    mine = reg.async_get_or_create("sensor", "zz", "1", suggested_object_id="mine")
    other = reg.async_get_or_create("sensor", "other", "2", suggested_object_id="other")
    assert tf.accepts(hass, "zz.reset", mine.entity_id)
    assert not tf.accepts(hass, "zz.reset", other.entity_id)
    assert tf.accepts(hass, "zz.reset", "sensor.not_registered")


async def test_describe_names_what_it_takes_and_suggests_the_right_action(hass):
    describe_target(hass, "input_boolean.turn_on", [{"domain": ["input_boolean"]}])
    describe_target(hass, "switch.turn_on", [{"domain": ["switch"]}])
    text = tf.describe(hass, "input_boolean.turn_on", ["switch.slp"])
    assert text == (
        "input_boolean.turn_on can't act on switch.slp (it takes input_boolean entities); "
        "use switch.turn_on"
    )


async def test_no_suggestion_when_the_domain_has_no_such_action(hass):
    describe_target(hass, "input_boolean.toggle", [{"domain": ["input_boolean"]}])
    assert tf.suggestion(hass, "input_boolean.toggle", "sensor.x") is None


async def test_load_descriptions_fills_the_cache_for_real_services(hass):
    from homeassistant.setup import async_setup_component

    assert await async_setup_component(hass, "input_boolean", {})
    assert tf.entity_filters(hass, "input_boolean.turn_on") is None  # not loaded yet
    await tf.async_load_descriptions(hass)
    assert not tf.accepts(hass, "input_boolean.turn_on", "switch.x")
