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


async def test_the_dry_run_key_no_longer_suppresses_the_applied_row(hass):
    """Follow-up to b1b6095: "no logbook row for a simulated run" is now
    kept by the ENGINE never firing the event at all
    (`engine.py`'s `async_apply_rule`), not by this describer special-casing
    a `dry_run` key - HA's `async_describe_events` extension point has no
    way to suppress a row entirely; a describer returning `{}` still
    produced a BLANK row (domain + timestamp only), confirmed against the
    real dev container's recorder. A real engine never fires
    EVENT_RULE_APPLIED with `dry_run: True` any more, but this proves the
    describer does not treat that key specially even if a historical event
    from an older version of this integration still carries it - it must
    render exactly like any other applied event, not crash and not go
    blank."""
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
    assert result != {}
    assert "בוקר שבת" in result["message"]
    assert "due" in result["message"]


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


def test_a_rule_due_with_replay_off_gets_its_own_row(hass):
    """The default path, and it used to render no row at all.

    Replay is off unless the author switched it on, so this is what
    happens to an ordinary rule after an ordinary restart. It has to be
    distinguishable from a stale skip - "too late to be worth repeating"
    and "nobody ever asked for it to be repeated" are different answers to
    the same question - and it has to name the rule, because the question
    is asked about one rule and not about the pass.
    """
    described = _describers(hass)
    describe = described[EVENT_RULE_COMPLETED]

    no_replay = describe(
        _completed(
            results=[
                {
                    "rule_id": "r1",
                    "outcome": "skipped_no_replay",
                    "reason": "replay is switched off for this rule",
                }
            ]
        )
    )
    stale = describe(
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

    message = no_replay["message"]
    assert "did not run" in message.lower()
    assert "replay is switched off" in message
    assert "AC on" in message
    # Not a stale skip, in either half of the row.
    assert "stale" not in message.lower()
    assert message != stale["message"]
    assert no_replay["icon"] != stale["icon"]


def test_a_replay_off_row_never_claims_the_rule_ran(hass):
    described = _describers(hass)
    message = described[EVENT_RULE_COMPLETED](
        _completed(
            results=[
                {
                    "rule_id": "r1",
                    "outcome": "skipped_no_replay",
                    "reason": "replay is switched off for this rule",
                }
            ]
        )
    )["message"].lower()
    for claim in ("fired", "applied", "succeeded", "replayed"):
        assert claim not in message


def test_a_replay_off_row_survives_a_result_with_no_reason(hass):
    """An event from an older version carries no `reason`.

    The row must still say why the rule did not run rather than trailing
    off, since that sentence is the entire purpose of the outcome.
    """
    described = _describers(hass)
    message = described[EVENT_RULE_COMPLETED](
        _completed(results=[{"rule_id": "r1", "outcome": "skipped_no_replay"}])
    )["message"]
    assert "did not run" in message.lower()
    assert "replay is switched off" in message
    assert "None" not in message


def test_the_catch_up_summary_counts_the_rules_that_had_replay_off(hass):
    """The summary used to be able to LIE, and this is the lie.

    A past-due rule with replay off produced no result, so `results` was
    empty and the summary read "no rule was due for replay" about a
    restart where several were. Replay being off is the DEFAULT, so that
    was the ordinary case rather than a rare one.
    """
    described = _describers(hass)
    message = described[EVENT_RULE_COMPLETED](
        Event(
            EVENT_RULE_COMPLETED,
            {
                "rule_id": None,
                "catch_up": True,
                "results": [
                    {"rule_id": "a", "outcome": "skipped_no_replay", "reason": "off"},
                    {"rule_id": "b", "outcome": "skipped_no_replay", "reason": "off"},
                ],
            },
        )
    )["message"]
    assert "catch-up" in message.lower()
    assert "2" in message
    assert "replay is off" in message
    # The sentence that must now be impossible whenever something was due.
    assert "no rule was due for replay" not in message


def test_the_catch_up_summary_separates_replay_off_from_stale(hass):
    described = _describers(hass)
    message = described[EVENT_RULE_COMPLETED](
        Event(
            EVENT_RULE_COMPLETED,
            {
                "rule_id": None,
                "catch_up": True,
                "results": [
                    {"rule_id": "a", "outcome": "skipped_no_replay", "reason": "off"},
                    {"rule_id": "b", "outcome": "skipped_stale", "reason": "late"},
                    {"rule_id": "c", "outcome": "skipped_stale", "reason": "late"},
                ],
            },
        )
    )["message"]
    assert "1 due but replay is off" in message
    assert "2 skipped as stale" in message


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


def test_a_would_call_outcome_still_names_an_unknown_entity(hass):
    """A dry run is exactly where the user is hunting for a typo - that
    diagnostic reaches them live, in the Simulate result the card renders
    inline (`formatOutcome` in format.ts) AND, if this describer is ever
    handed a `would_call` result at all, in the row it renders here too.

    A real engine now never fires EVENT_RULE_COMPLETED for a simulated run
    (`async_apply_rule` suppresses the event itself under `simulate` -
    follow-up to b1b6095, whose describer-side `dry_run` suppression this
    replaces), so this outcome-driven branch is reachable only via a
    historical event. It must still render sensibly rather than go blank
    or crash.
    """
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
                    "outcome": "would_call",
                }
            ],
        )
    )
    message = result["message"]
    assert "would have fired" in message
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


def test_a_fired_row_says_when_the_call_reached_nothing(hass):
    """The third diagnostic has to be visible, not merely present.

    A row reading a bare "fired" for a call that reached no entity that
    exists is a rule reporting success for having affected nothing - the
    shape this integration exists to prevent. Round-2 review finding.
    """
    described = _describers(hass)
    result = described[EVENT_RULE_COMPLETED](
        _completed(
            target={"entity_id": ["group.leftover"]},
            results=[
                {
                    "action": "climate.set_temperature",
                    "target": {"entity_id": ["group.leftover"]},
                    "data": {"temperature": 24},
                    "no_live_targets": True,
                    "outcome": "called",
                }
            ],
        )
    )
    message = result["message"]
    assert "fired" in message
    assert "reached no entity that exists" in message
    # Says it reached nothing; does NOT claim the rule failed.
    assert "did not run" not in message.lower()


def test_a_would_call_outcome_still_notes_no_live_targets(hass):
    """Same reasoning as `test_a_would_call_outcome_still_names_an_unknown_entity`,
    for the other target diagnostic."""
    described = _describers(hass)
    result = described[EVENT_RULE_COMPLETED](
        _completed(
            target={"device_id": ["deadbeef"]},
            results=[
                {
                    "action": "climate.set_temperature",
                    "target": {"device_id": ["deadbeef"]},
                    "data": {"temperature": 24},
                    "no_live_targets": True,
                    "outcome": "would_call",
                }
            ],
        )
    )
    message = result["message"]
    assert "would have fired" in message
    assert "reached no entity that exists" in message


def test_both_target_diagnostics_can_appear_on_one_row(hass):
    """A multi-call rule can carry one of each.

    The climate shim makes several calls from one authored action; the two
    diagnostics are mutually exclusive per CALL, not per rule, so a row
    has to be able to say both things.
    """
    described = _describers(hass)
    result = described[EVENT_RULE_COMPLETED](
        _completed(
            results=[
                {
                    "action": "climate.set_hvac_mode",
                    "target": {"entity_id": ["climate.slaon"]},
                    "data": {"hvac_mode": "cool"},
                    "unknown_targets": ["climate.slaon"],
                    "outcome": "called",
                },
                {
                    "action": "climate.set_temperature",
                    "target": {"entity_id": ["group.leftover"]},
                    "data": {"temperature": 24},
                    "no_live_targets": True,
                    "outcome": "called",
                },
            ]
        )
    )
    message = result["message"]
    assert "no such entity: climate.slaon" in message
    assert "reached no entity that exists" in message
    # The fixable one first.
    assert message.index("no such entity") < message.index("reached no entity")


def test_a_row_says_it_reached_nothing_only_once(hass):
    described = _describers(hass)
    result = described[EVENT_RULE_COMPLETED](
        _completed(
            results=[
                {
                    "action": "climate.set_hvac_mode",
                    "target": {"entity_id": ["group.leftover"]},
                    "data": {},
                    "no_live_targets": True,
                    "outcome": "called",
                },
                {
                    "action": "climate.set_temperature",
                    "target": {"entity_id": ["group.leftover"]},
                    "data": {"temperature": 24},
                    "no_live_targets": True,
                    "outcome": "called",
                },
            ]
        )
    )
    assert result["message"].count("reached no entity that exists") == 1


def test_a_row_with_live_targets_says_nothing_about_them(hass):
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
    assert "reached no entity" not in result["message"]


def test_a_malformed_no_live_targets_value_does_not_break_the_row(hass):
    """`is True`, not truthiness: an event written by another version of
    this integration could carry anything here, and a describer that
    raises takes down the whole logbook page."""
    described = _describers(hass)
    result = described[EVENT_RULE_COMPLETED](
        _completed(
            results=[
                {
                    "action": "climate.set_temperature",
                    "target": {"entity_id": ["climate.salon"]},
                    "data": {},
                    "no_live_targets": "yes",
                    "outcome": "called",
                }
            ]
        )
    )
    assert "fired" in result["message"]
    assert "reached no entity" not in result["message"]


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


def test_a_would_call_outcome_renders_the_dry_run_message(hass):
    """A simulated run never reaches the logbook at all in practice - the
    engine simply never fires EVENT_RULE_COMPLETED for one (follow-up to
    b1b6095: see this module's own top-of-function docstrings and
    `engine.py`'s `async_apply_rule`). This is the base case for the
    `would_call` outcome branch itself, exercised directly since nothing
    else in this file did before the describer-side `dry_run` suppression
    it replaces was removed. The "would have fired" wording still lives
    primarily in the live Simulate result the card renders
    (`format.ts`'s `formatOutcome`); this only proves the describer itself
    does not go blank or crash on a `would_call` result."""
    described = _describers(hass)
    result = described[EVENT_RULE_COMPLETED](
        _completed(
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
    assert result != {}
    assert "would have fired" in result["message"]


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
