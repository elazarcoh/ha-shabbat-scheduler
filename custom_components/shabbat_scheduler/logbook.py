"""Render this integration's own events in Home Assistant's Logbook.

Registering here is also what lets Home Assistant attribute a device's own
state change back to the rule that caused it: logbook's processor skips
attribution entirely for event types nothing describes.

TWO events are described, for two different jobs.

`EVENT_RULE_APPLIED` is fired by the engine BEFORE the condition gate and
before any service call, deliberately, because that ordering is what buys
the attribution above. It therefore cannot know how the rule turned out,
and for a long time it was the only described event - so a rule blocked by
its condition, a rule that failed all three retries and a rule that
worked produced a byte-identical logbook line. That is worse than silence:
the line for a blocked rule affirmatively said it had been applied. Its
message is now deliberately neutral ("due"), claiming nothing.

`EVENT_RULE_COMPLETED` is fired after the fact and carries the results, so
it is the one that says what actually happened. It costs a second row per
fire. That was previously judged not worth paying; the trade is now the
other way round, because "a rule that does not fire must say why" is the
binding promise this integration exists to keep, and the logbook is where
it has to be said.

Everything a row needs rides on the event payload. Logbook renders
HISTORICAL events, so a describer cannot look the rule up - it may have
been renamed or deleted by then, and an event written by an older version
of this integration may be missing fields entirely. Every read here is
therefore defensive: a describer that raises takes down the whole logbook
page, not just its own row.
"""

from __future__ import annotations

from collections.abc import Callable

from homeassistant.core import Event, HomeAssistant, callback

from .const import (
    DOMAIN,
    EVENT_RULE_APPLIED,
    EVENT_RULE_COMPLETED,
    UNKNOWN_ENTITY_PREFIX,
)

_NAME = "Shabbat Scheduler"

# One icon per outcome, so the rows are separable at a glance in a week's
# worth of logbook without reading any of them.
_ICON_DUE = "mdi:candle"
_ICON_FIRED = "mdi:candle"
_ICON_BLOCKED = "mdi:cancel"
_ICON_FAILED = "mdi:alert-circle"
_ICON_STALE = "mdi:clock-alert-outline"
_ICON_DRY_RUN = "mdi:test-tube"
_ICON_CATCH_UP = "mdi:restart"

# Which outcome a multi-call rule reports, worst first. The climate shim
# turns one authored action into up to three calls; if `set_hvac_mode`
# succeeds and `set_temperature` does not, the row must read as a failure.
# "The first call worked" is not what the family needs to know.
_OUTCOME_PRECEDENCE = ("failed", "blocked", "skipped_stale", "would_call", "called")


def _rule_label(data) -> str:
    """The rule's name, falling back to its id, never the literal "None"."""
    name = data.get("name")
    if isinstance(name, str) and name:
        return name
    rule_id = data.get("rule_id")
    if isinstance(rule_id, str) and rule_id:
        return rule_id
    return "(unknown)"


def _target_description(target) -> str:
    if not isinstance(target, dict):
        return ""
    return ", ".join(
        str(v)
        for values in target.values()
        for v in (values if isinstance(values, list) else [values])
    )


def _what(data) -> str:
    """"<action> (<targets>)", omitting either half if it is absent.

    A v2 target may be an area or a label, or absent entirely (a `notify.*`
    action needs none), so neither half can be assumed present.
    """
    action = data.get("action")
    action = action if isinstance(action, str) else ""
    where = _target_description(data.get("target"))
    if action and where:
        return f"{action} ({where})"
    return action or where


def _results(data) -> list[dict]:
    raw = data.get("results")
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def _overall(results: list[dict]) -> str | None:
    outcomes = {item.get("outcome") for item in results}
    for candidate in _OUTCOME_PRECEDENCE:
        if candidate in outcomes:
            return candidate
    return None


def _detail(results: list[dict], outcome: str, key: str) -> str:
    """The first `key` among the results carrying `outcome`."""
    for item in results:
        if item.get("outcome") == outcome:
            value = item.get(key)
            if value:
                return str(value)
    return ""


def _unknown_targets(results: list[dict]) -> list[str]:
    """Entity ids the engine reported as naming nothing that exists.

    Flattened across every call the rule made, in first-seen order: the
    climate shim turns one authored action into up to three calls, and a
    typo in the target belongs to all of them, so without flattening the
    row could read the one call that happens not to carry it.

    Read defensively, like every other read in this module: an event
    written by an older version of this integration has no such key, and
    a describer that raises takes down the whole logbook page.
    """
    seen: list[str] = []
    for item in results:
        raw = item.get("unknown_targets")
        if not isinstance(raw, list):
            continue
        for entity_id in raw:
            if isinstance(entity_id, str) and entity_id and entity_id not in seen:
                seen.append(entity_id)
    return seen


def _note_unknown(message: str, results: list[dict]) -> str:
    """Name the entity ids that do not exist, on whatever row is drawn.

    A partial typo still fires the rest of the target, so its row reads
    "fired" - and a row saying "fired" while one named entity silently
    did nothing is precisely the quiet failure this integration exists to
    prevent. A dry run's row must say it too, because a dry run is where
    the user is deliberately looking for the typo.

    Note the phrase, not the ids, is what suppresses a second copy. The
    row already lists every targeted entity id, the typo among them, so
    "is this id in the message?" would always be true and would silence
    the warning on exactly the partial-typo row that needs it. In the
    total-miss case the failed row's `error` already reads "no such
    entity: ...", which is what this checks for.
    """
    if UNKNOWN_ENTITY_PREFIX in message:
        return message
    unknown = _unknown_targets(results)
    if not unknown:
        return message
    return f"{message} — {UNKNOWN_ENTITY_PREFIX}{', '.join(unknown)}"


def _catch_up_message(results: list[dict]) -> str:
    replayed = sum(1 for item in results if item.get("outcome") == "called")
    skipped = sum(1 for item in results if item.get("outcome") == "skipped_stale")
    blocked = sum(1 for item in results if item.get("outcome") == "blocked")
    failed = sum(1 for item in results if item.get("outcome") == "failed")
    would = sum(1 for item in results if item.get("outcome") == "would_call")
    if not results:
        return "restart catch-up — no rule was due for replay"
    parts = [
        f"{count} {label}"
        for count, label in (
            (replayed, "replayed"),
            (would, "would be replayed [dry run]"),
            (blocked, "blocked"),
            (failed, "failed"),
            (skipped, "skipped as stale"),
        )
        if count
    ]
    return "restart catch-up — " + ", ".join(parts)


@callback
def async_describe_events(
    hass: HomeAssistant,
    async_describe_event: Callable[[str, str, Callable[[Event], dict]], None],
) -> None:
    """Describe the events this integration fires."""

    @callback
    def async_describe_rule_applied(event: Event) -> dict:
        """The rule came due. Says nothing about the outcome, on purpose.

        This fires before the condition gate and before any call, so any
        wording here that implied success would be a claim it cannot back.
        The outcome is the completed event's row, below.
        """
        data = event.data
        message = f"rule '{_rule_label(data)}' due"
        what = _what(data)
        if what:
            message = f"{message} — {what}"
        if data.get("dry_run"):
            message = f"{message} [dry run]"

        return {"name": _NAME, "message": message, "icon": _ICON_DUE}

    @callback
    def async_describe_rule_completed(event: Event) -> dict:
        """What actually happened. The row that has to be honest.

        Four distinguishable shapes, because the promise is that a rule
        which does not fire says WHY: fired, blocked (naming the
        condition), failed (naming the error), skipped as stale (saying
        how late). "did not run" appears in each of the three non-firing
        rows and in none of the firing ones, so it is greppable.
        """
        data = event.data
        results = _results(data)

        # Catch-up fires one final aggregate event with `rule_id: None`,
        # summarising the whole replay pass. Rendered as a summary rather
        # than as a nameless rule.
        if data.get("catch_up"):
            return {
                "name": _NAME,
                "message": _catch_up_message(results),
                "icon": _ICON_CATCH_UP,
            }

        rule = _rule_label(data)
        what = _what(data)
        outcome = _overall(results)

        if outcome == "blocked":
            reason = _detail(results, "blocked", "reason") or "condition not met"
            return {
                "name": _NAME,
                "message": f"rule '{rule}' did not run — blocked: {reason}",
                "icon": _ICON_BLOCKED,
            }

        if outcome == "failed":
            error = _detail(results, "failed", "error") or "no reason reported"
            action = _detail(results, "failed", "action") or what
            return {
                "name": _NAME,
                "message": _note_unknown(
                    f"rule '{rule}' did not run — {action} failed: {error}",
                    results,
                ),
                "icon": _ICON_FAILED,
            }

        if outcome == "skipped_stale":
            reason = _detail(results, "skipped_stale", "reason")
            message = f"rule '{rule}' did not run — skipped as stale"
            if reason:
                message = f"{message}: {reason}"
            return {"name": _NAME, "message": message, "icon": _ICON_STALE}

        if outcome == "would_call":
            message = f"rule '{rule}' would have fired [dry run]"
            if what:
                message = f"{message} — {what}"
            return {
                "name": _NAME,
                "message": _note_unknown(message, results),
                "icon": _ICON_DRY_RUN,
            }

        if outcome == "called":
            message = f"rule '{rule}' fired"
            if what:
                message = f"{message} — {what}"
            return {
                "name": _NAME,
                "message": _note_unknown(message, results),
                "icon": _ICON_FIRED,
            }

        # No recognisable outcome at all: an event from a future or older
        # version of this integration. Say that, rather than guessing.
        message = f"rule '{rule}' finished with no reported outcome"
        if what:
            message = f"{message} — {what}"
        return {"name": _NAME, "message": message, "icon": _ICON_FAILED}

    async_describe_event(DOMAIN, EVENT_RULE_APPLIED, async_describe_rule_applied)
    async_describe_event(DOMAIN, EVENT_RULE_COMPLETED, async_describe_rule_completed)
