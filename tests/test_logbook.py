from homeassistant.core import Event

from custom_components.shabbat_scheduler.const import (
    DOMAIN,
    EVENT_RULE_APPLIED,
    EVENT_RULE_COMPLETED,
)
from custom_components.shabbat_scheduler.logbook import async_describe_events


async def test_describe_renders_a_named_rule(hass):
    described = {}

    def _capture(domain, event_type, describe):
        # Pins the platform to THIS integration's domain: logbook only
        # attributes a device's own state change back to a rule for event
        # types registered under the domain that fires them, so a wrong
        # domain here would silently cost the attribution the whole
        # logbook.py module exists for.
        assert domain == DOMAIN
        described[event_type] = describe

    async_describe_events(hass, _capture)
    assert EVENT_RULE_APPLIED in described

    event = Event(
        EVENT_RULE_APPLIED,
        {
            "rule_id": "r1",
            "name": "בוקר שבת",
            "action": "on",
            "devices": ["climate.a", "climate.b"],
            "dry_run": False,
        },
    )
    result = described[EVENT_RULE_APPLIED](event)

    assert "בוקר שבת" in result["message"]
    assert "climate.a" in result["message"]
    assert result["name"]


async def test_describe_handles_an_unnamed_rule(hass):
    described = {}
    async_describe_events(hass, lambda d, e, f: described.__setitem__(e, f))

    event = Event(
        EVENT_RULE_APPLIED,
        {
            "rule_id": "r1",
            "name": None,
            "action": "off",
            "devices": ["climate.a"],
            "dry_run": False,
        },
    )
    result = described[EVENT_RULE_APPLIED](event)
    assert result["message"]
    # Not merely non-empty: an unnamed rule falls back to its id, and a
    # regression that formatted the missing name instead would print the
    # literal "None" into the family's logbook and still pass.
    assert "None" not in result["message"]
    assert "r1" in result["message"]


async def test_describe_marks_a_dry_run(hass):
    described = {}
    async_describe_events(hass, lambda d, e, f: described.__setitem__(e, f))

    event = Event(
        EVENT_RULE_APPLIED,
        {
            "rule_id": "r1",
            "name": "בוקר שבת",
            "action": "on",
            "devices": ["climate.a"],
            "dry_run": True,
        },
    )
    result = described[EVENT_RULE_APPLIED](event)
    assert "dry run" in result["message"].lower()


def test_only_the_applied_event_is_described(hass):
    """EVENT_RULE_COMPLETED must NOT be described.

    It fires after every rule application to carry results to the last-run
    sensor. Describing it too would put a second, duplicate row in the
    logbook for every single rule that fires.
    """
    described = {}
    async_describe_events(hass, lambda d, e, f: described.__setitem__(e, f))
    assert set(described) == {EVENT_RULE_APPLIED}
    assert EVENT_RULE_COMPLETED not in described
