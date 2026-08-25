from homeassistant.core import Event

from custom_components.shabbat_scheduler.const import (
    DOMAIN,
    EVENT_RULE_APPLIED,
    EVENT_RULE_COMPLETED,
)
from custom_components.shabbat_scheduler.logbook import async_describe_events


def _describers(hass):
    described = {}
    async_describe_events(hass, lambda d, e, f: described.__setitem__(e, f))
    return described


def _completed(**overrides):
    """An EVENT_RULE_COMPLETED payload of the exact shape the engine fires."""
    data = {
        "rule_id": "r1",
        "name": "AC on",
        "action": "climate.set_temperature",
        "target": {"entity_id": ["climate.salon"]},
        "dry_run": False,
        "results": [],
    }
    data.update(overrides)
    return Event(EVENT_RULE_COMPLETED, data)


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
            "action": "climate.set_temperature",
            "target": {"entity_id": ["climate.a", "climate.b"]},
            "dry_run": False,
        },
    )
    result = described[EVENT_RULE_APPLIED](event)

    assert "בוקר שבת" in result["message"]
    # The v2 payload is `action` + `target`, not v1's enum + `devices`.
    # Both halves must reach the row: naming the rule without saying what
    # it did is what the logbook is for.
    assert "climate.set_temperature" in result["message"]
    assert "climate.a" in result["message"]
    assert "climate.b" in result["message"]
    assert result["name"]


async def test_describe_handles_an_unnamed_rule(hass):
    described = _describers(hass)

    event = Event(
        EVENT_RULE_APPLIED,
        {
            "rule_id": "r1",
            "name": None,
            "action": "climate.turn_off",
            "target": {"entity_id": ["climate.a"]},
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
    described = _describers(hass)

    event = Event(
        EVENT_RULE_APPLIED,
        {
            "rule_id": "r1",
            "name": "בוקר שבת",
            "action": "climate.turn_on",
            "target": {"entity_id": ["climate.a"]},
            "dry_run": True,
        },
    )
    result = described[EVENT_RULE_APPLIED](event)
    assert "dry run" in result["message"].lower()


def test_both_events_are_described(hass):
    """EVENT_RULE_COMPLETED must be described too.

    This assertion used to run the other way: describing the completed
    event was rejected because it puts a SECOND row in the logbook for
    every rule that fires. The final review overruled that trade. The
    applied event is fired BEFORE the condition gate and before any
    service call (engine.py, deliberately, so Home Assistant can attribute
    each device's change back to the rule), so on its own it cannot
    possibly know the outcome - and a blocked or failed rule therefore
    produced a row byte-identical to a successful one. One extra row per
    fire is a cheap price for the logbook not lying about whether the
    family's air conditioning came on.
    """
    described = _describers(hass)
    assert set(described) == {EVENT_RULE_APPLIED, EVENT_RULE_COMPLETED}


def test_the_applied_row_does_not_claim_the_rule_succeeded(hass):
    """It is fired before the condition gate, so it cannot know."""
    described = _describers(hass)
    result = described[EVENT_RULE_APPLIED](
        Event(
            EVENT_RULE_APPLIED,
            {
                "rule_id": "r1",
                "name": "AC on",
                "action": "climate.set_temperature",
                "target": {"entity_id": ["climate.salon"]},
                "dry_run": False,
            },
        )
    )
    message = result["message"].lower()
    for claim in ("fired", "applied", "succeeded"):
        assert claim not in message


def test_the_three_non_firing_outcomes_render_differently(hass):
    """The whole point: fired, blocked, failed and skipped must not match.

    Before this existed the engine's own payloads for all three rendered
    the identical line "rule AC on (climate.set_temperature) —
    climate.salon", because only EVENT_RULE_APPLIED was described and it
    is fired before anything is known.
    """
    described = _describers(hass)
    describe = described[EVENT_RULE_COMPLETED]

    fired = describe(
        _completed(
            results=[
                {
                    "action": "climate.set_temperature",
                    "target": {"entity_id": ["climate.salon"]},
                    "data": {"temperature": 24},
                    "outcome": "called",
                }
            ]
        )
    )["message"]
    blocked = describe(
        _completed(
            results=[
                {
                    "outcome": "blocked",
                    "reason": "condition 1 of 2 (state on binary_sensor.gate) not met",
                }
            ]
        )
    )["message"]
    failed = describe(
        _completed(
            results=[
                {
                    "action": "climate.set_temperature",
                    "target": {"entity_id": ["climate.salon"]},
                    "data": {},
                    "outcome": "failed",
                    "error": "ServiceNotFound: climate.set_temperature",
                }
            ]
        )
    )["message"]
    skipped = describe(
        _completed(
            results=[
                {
                    "rule_id": "r1",
                    "outcome": "skipped_stale",
                    "reason": "12:00:00 late, window 2:00:00",
                }
            ]
        )
    )["message"]

    assert len({fired, blocked, failed, skipped}) == 4


def test_a_blocked_row_does_not_claim_the_rule_was_applied(hass):
    """The failure mode that is worse than silence.

    A row saying the rule ran, for a rule that did not, is what the
    reviewer found: it does not merely omit the truth, it asserts the
    opposite.
    """
    described = _describers(hass)
    result = described[EVENT_RULE_COMPLETED](
        _completed(
            results=[
                {
                    "outcome": "blocked",
                    "reason": "condition 1 of 2 (state on binary_sensor.gate) not met",
                }
            ]
        )
    )
    message = result["message"]
    assert "blocked" in message.lower()
    assert "did not run" in message.lower()
    for claim in ("fired", "applied", "succeeded"):
        assert claim not in message.lower()
    # And it says WHICH condition, not just "condition not met".
    assert "binary_sensor.gate" in message
    assert "1 of 2" in message


def test_a_failed_row_carries_the_error(hass):
    described = _describers(hass)
    result = described[EVENT_RULE_COMPLETED](
        _completed(
            results=[
                {
                    "action": "climate.set_temperature",
                    "target": {"entity_id": ["climate.salon"]},
                    "data": {},
                    "outcome": "failed",
                    "error": "ServiceNotFound: climate.set_temperature",
                }
            ]
        )
    )
    message = result["message"]
    assert "failed" in message.lower()
    assert "ServiceNotFound" in message
    assert "did not run" in message.lower()


def test_a_stale_skip_says_how_late_it_was(hass):
    described = _describers(hass)
    result = described[EVENT_RULE_COMPLETED](
        _completed(
            results=[
                {
                    "rule_id": "r1",
                    "outcome": "skipped_stale",
                    "reason": "12:00:00 late, window 2:00:00",
                }
            ]
        )
    )
    message = result["message"]
    assert "stale" in message.lower()
    assert "12:00:00 late" in message
    assert "did not run" in message.lower()


def test_a_partly_failed_rule_reports_the_failure_not_the_success(hass):
    """The climate shim makes several calls from one action.

    If the set_hvac_mode call succeeds and set_temperature does not, the
    row must not read as a clean fire just because the first call worked.
    """
    described = _describers(hass)
    result = described[EVENT_RULE_COMPLETED](
        _completed(
            results=[
                {
                    "action": "climate.set_hvac_mode",
                    "target": {"entity_id": ["climate.salon"]},
                    "data": {"hvac_mode": "cool"},
                    "outcome": "called",
                },
                {
                    "action": "climate.set_temperature",
                    "target": {"entity_id": ["climate.salon"]},
                    "data": {"temperature": 24},
                    "outcome": "failed",
                    "error": "TimeoutError",
                },
            ]
        )
    )
    assert "failed" in result["message"].lower()
    assert "TimeoutError" in result["message"]


def test_a_fired_row_names_an_entity_that_does_not_exist(hass):
    """A partial typo still fires, so its row says "fired".

    A row reading "fired" while one named entity silently did nothing is
    the quiet failure this integration exists to prevent, so the row has
    to say WHICH id named nothing. Plan-2 Gap B.
    """
    described = _describers(hass)
    result = described[EVENT_RULE_COMPLETED](
        _completed(
            target={"entity_id": ["climate.salon", "climate.slaon"]},
            results=[
                {
                    "action": "climate.set_temperature",
                    "target": {"entity_id": ["climate.salon", "climate.slaon"]},
                    "data": {"temperature": 24},
                    "unknown_targets": ["climate.slaon"],
                    "outcome": "called",
                }
            ],
        )
    )
    message = result["message"]
    assert "fired" in message
    # Not merely present as one of the listed targets - the row has to say
    # that this particular id is the one that does not exist.
    assert "no such entity: climate.slaon" in message


def test_a_dry_run_row_names_an_entity_that_does_not_exist(hass):
    """A dry run is exactly where the user is hunting for the typo."""
    described = _describers(hass)
    result = described[EVENT_RULE_COMPLETED](
        _completed(
            dry_run=True,
            target={"entity_id": ["climate.slaon"]},
            results=[
                {
                    "action": "climate.set_temperature",
                    "target": {"entity_id": ["climate.slaon"]},
                    "data": {"temperature": 24},
                    "unknown_targets": ["climate.slaon"],
                    "outcome": "would_call",
                }
            ],
        )
    )
    message = result["message"]
    assert "dry run" in message.lower()
    assert "no such entity: climate.slaon" in message


def test_a_total_miss_says_no_such_entity_exactly_once(hass):
    """The engine already puts the ids in `error`; do not say it twice."""
    described = _describers(hass)
    result = described[EVENT_RULE_COMPLETED](
        _completed(
            target={"entity_id": ["climate.slaon"]},
            results=[
                {
                    "action": "climate.set_temperature",
                    "target": {"entity_id": ["climate.slaon"]},
                    "data": {"temperature": 24},
                    "unknown_targets": ["climate.slaon"],
                    "outcome": "failed",
                    "error": "no such entity: climate.slaon",
                }
            ],
        )
    )
    message = result["message"]
    assert "did not run" in message.lower()
    assert message.count("no such entity") == 1


def test_an_unknown_target_survives_a_failure_with_another_reason(hass):
    """The climate shim makes several calls from one authored action.

    If one call carries the typo and a later one times out, the row reads
    as the failure - and the typo must not be lost with it, because it is
    the actionable half of the two.
    """
    described = _describers(hass)
    result = described[EVENT_RULE_COMPLETED](
        _completed(
            results=[
                {
                    "action": "climate.set_hvac_mode",
                    "target": {"entity_id": ["climate.salon", "climate.slaon"]},
                    "data": {"hvac_mode": "cool"},
                    "unknown_targets": ["climate.slaon"],
                    "outcome": "called",
                },
                {
                    "action": "climate.set_temperature",
                    "target": {"entity_id": ["climate.salon", "climate.slaon"]},
                    "data": {"temperature": 24},
                    "unknown_targets": ["climate.slaon"],
                    "outcome": "failed",
                    "error": "TimeoutError",
                },
            ],
        )
    )
    message = result["message"]
    assert "TimeoutError" in message
    assert "no such entity: climate.slaon" in message


def test_a_row_with_no_unknown_targets_says_nothing_about_them(hass):
    described = _describers(hass)
    result = described[EVENT_RULE_COMPLETED](
        _completed(
            results=[
                {
                    "action": "climate.set_temperature",
                    "target": {"entity_id": ["climate.salon"]},
                    "data": {"temperature": 24},
                    "outcome": "called",
                }
            ]
        )
    )
    assert "no such entity" not in result["message"]


def test_a_malformed_unknown_targets_value_does_not_break_the_row(hass):
    """Logbook renders HISTORICAL events, including ones written by an
    older version of this integration, and a describer that raises takes
    down the whole page - so every read of the payload is defensive."""
    described = _describers(hass)
    result = described[EVENT_RULE_COMPLETED](
        _completed(
            results=[
                {
                    "action": "climate.set_temperature",
                    "target": {"entity_id": ["climate.salon"]},
                    "data": {},
                    "unknown_targets": "climate.slaon",
                    "outcome": "called",
                }
            ]
        )
    )
    assert "fired" in result["message"]
    assert "no such entity" not in result["message"]


def test_a_dry_run_completion_says_it_would_have_fired(hass):
    described = _describers(hass)
    result = described[EVENT_RULE_COMPLETED](
        _completed(
            dry_run=True,
            results=[
                {
                    "action": "climate.set_temperature",
                    "target": {"entity_id": ["climate.salon"]},
                    "data": {"temperature": 24},
                    "outcome": "would_call",
                }
            ],
        )
    )
    message = result["message"].lower()
    assert "dry run" in message
    # Distinguishable from a real fire, which is the whole point of dry run.
    assert "would" in message


def test_a_catch_up_summary_renders_as_one_row(hass):
    """Catch-up fires a final aggregate event with rule_id None.

    It must not render as a nameless rule; it is the restart summary.
    """
    described = _describers(hass)
    result = described[EVENT_RULE_COMPLETED](
        Event(
            EVENT_RULE_COMPLETED,
            {
                "rule_id": None,
                "catch_up": True,
                "results": [
                    {"action": "a.b", "target": {}, "data": {}, "outcome": "called"},
                    {"rule_id": "x", "outcome": "skipped_stale", "reason": "late"},
                ],
            },
        )
    )
    message = result["message"]
    assert "catch-up" in message.lower()
    assert "None" not in message
    assert "1" in message  # counts, so "nothing happened" is not ambiguous


def test_a_catch_up_that_replayed_nothing_still_says_so(hass):
    described = _describers(hass)
    result = described[EVENT_RULE_COMPLETED](
        Event(
            EVENT_RULE_COMPLETED,
            {"rule_id": None, "catch_up": True, "results": []},
        )
    )
    assert result["message"]
    assert "None" not in result["message"]


def test_a_completed_row_survives_a_payload_with_nothing_in_it(hass):
    """Logbook describers render HISTORICAL events.

    An event written by an older version of this integration is replayed
    through today's describer, so every field has to be optional. A
    describer that raises takes the whole logbook page down.
    """
    described = _describers(hass)
    result = described[EVENT_RULE_COMPLETED](Event(EVENT_RULE_COMPLETED, {}))
    assert result["message"]
    assert "None" not in result["message"]
