"""Executes the decisions the pure modules make."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict, deque
from datetime import datetime, timedelta

from homeassistant.components import persistent_notification
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ENTITY_MATCH_ALL,
    ENTITY_MATCH_NONE,
)
from homeassistant.core import Context, CoreState, HomeAssistant
from homeassistant.helpers import condition
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import target as target_helper
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.helpers.service import async_call_from_config
from homeassistant.util import dt as dt_util

from .block import (
    compute_block,
    has_profile,
    merge_defaults,
    resolve_rules,
)
from .const import (
    DEFAULT_CANDLE_SENSOR,
    DEFAULT_HAVDALAH_SENSOR,
    EVENT_RULE_APPLIED,
    EVENT_RULE_COMPLETED,
    NO_LIVE_TARGETS_NOTE,
    OUTCOME_PRECEDENCE,
    RETRY_ATTEMPTS,
    RETRY_DELAY_SECONDS,
    SIGNAL_RULES_CHANGED,
    UNKNOWN_ENTITY_PREFIX,
)
from . import repairs
from .device_ops import expand_action
from .models import Block, ResolvedRule, Rule
from .store import RuleStore

_LOGGER = logging.getLogger(__name__)

# Fixed notification ids so a condition that is re-evaluated on every state
# change replaces its own notification instead of stacking dozens of copies,
# and can be dismissed once it clears.
_NOTIFY_ZMANIM = "shabbat_scheduler_zmanim"
_NOTIFY_NO_PROFILE = "shabbat_scheduler_no_profile"

# How many of our own recent context ids we remember. Bounded so a
# long-running instance cannot grow this without limit; generous enough that
# no realistic burst of rule applications evicts a context before anything
# could plausibly ask about it. No longer keyed per device: a target may be
# an area or a label rather than a single entity, so there is nothing to key
# on but the context itself.
_CONTEXT_HISTORY = 200

# How long after a held block's last rule the candidate block is adopted.
# Strictly greater than zero so the refresh it schedules is guaranteed to
# fall on the far side of the hold condition (`now <= tail`) and can never
# re-arm itself.
_HOLD_RELEASE_GRACE = timedelta(seconds=1)


def _condition_label(index: int, total: int, item) -> str:
    """Name one condition well enough for the user to find it in the rule.

    Its position in the rule plus its own identifying fields. Never the
    whole config: a condition may carry templates and nested conditions,
    and a logbook row is one line. `entity_id` is what almost every real
    condition is actually about.
    """
    raw = item if isinstance(item, dict) else {}
    kind = raw.get("condition")
    kind = str(kind) if kind else "condition"
    entity = raw.get("entity_id")
    if isinstance(entity, (list, tuple)):
        entity = ", ".join(str(one) for one in entity)
    where = f" on {entity}" if entity else ""
    return f"condition {index} of {total} ({kind}{where})"


# Neither of these is an entity id: `all` means every entity and `none`
# means no target at all. `states.get("all")` is None, so without excluding
# them a wildcard target would be reported as a misspelt entity called
# "all" - a loud complaint about a rule that is perfectly fine, and the
# fastest way to teach the user to ignore these warnings.
_WILDCARD_ENTITY_IDS = frozenset({ENTITY_MATCH_ALL, ENTITY_MATCH_NONE})


def _entity_id_values(target: dict) -> list:
    """This target's `entity_id`, normalised to a list of whatever it held.

    `entity_id` may be a bare string or a list; Home Assistant accepts
    both, and a migrated v1 rule or an imported YAML rule can carry
    either. Iterating a bare string without normalising it would yield its
    CHARACTERS. Values that are neither are passed through as a single
    item rather than dropped, so a malformed rule reaches Home Assistant's
    own validator with its shape intact instead of being quietly emptied.
    """
    raw = target.get(ATTR_ENTITY_ID)
    if raw is None:
        return []
    if isinstance(raw, str):
        return [raw]
    if isinstance(raw, (list, tuple, set)):
        return list(raw)
    return [raw]


def _named_entity_ids(target: dict) -> set[str]:
    """The entity ids the USER TYPED into this target, deduplicated.

    This is the only set the unknown-entity check may draw from. Anything
    that arrives by expansion - a group's members, an area's or a label's
    entities - was produced by Home Assistant from its own registries, so
    "it does not exist" is not a thing that can be said about it, and
    saying it anyway reports a misspelling the user never made.
    """
    return {
        entity_id for entity_id in _entity_id_values(target)
        if isinstance(entity_id, str)
        and entity_id not in _WILDCARD_ENTITY_IDS
    }


def _targets_every_entity(target: dict) -> bool:
    """Does this target say `entity_id: all`?

    A wildcard is not a target that resolves: HA's `expand_entity_ids`
    strips `all` before anything is resolved, so the resolved set comes
    back EMPTY while the service layer goes on to act on every entity in
    the domain. Reporting "reached no entity that exists" for that would
    be the exact inverse of the truth.
    """
    return ENTITY_MATCH_ALL in _entity_id_values(target)


def build_outcome(
    outcome: str,
    at: datetime,
    detail: str | None = None,
    *,
    unknown_targets: list[str] | None = None,
    no_live_targets: bool = False,
) -> dict:
    """One rule's durable verdict, in the shape the card reads.

    THE SHAPE, and why it has more than one axis. `outcome` answers "did
    the call happen, and if not why not" - one of `called`, `would_call`,
    `failed`, `blocked`, `skipped_stale`. The two optional keys answer a
    DIFFERENT question: "did it reach anything?". They are not outcomes and
    must not be flattened into one, because a call can genuinely have been
    made (`called`) and still have reached nothing real, and calling that
    `failed` blames a misspelling that is not there - the exact mistake
    Gap B's first fix made in both directions. `_call` and the logbook
    already keep the two apart; this keeps them apart in the store too, so
    the card can say "fired" and "reached nothing" in one breath.

    Both diagnostics are OMITTED when they do not apply, rather than
    written as `[]`/`False`. A reader that has to tell an explicit False
    from an absent key ends up rendering a warning-shaped nothing on every
    healthy rule.

    `at` is stored as an ISO string, not a datetime: this dict goes
    straight into `.storage` (JSON) and straight out over the websocket,
    and a value that survives neither trip is not a durable record.
    """
    record: dict = {"outcome": outcome, "at": at.isoformat(), "detail": detail}
    if unknown_targets:
        record["unknown_targets"] = list(unknown_targets)
    if no_live_targets:
        record["no_live_targets"] = True
    return record


def outcome_from_results(results: list[dict], at: datetime) -> dict | None:
    """Fold a rule's per-call results into the ONE verdict a row can show.

    A rule is one row on the card but may be several calls: `expand_action`
    turns an authored `climate.set_temperature` carrying an `hvac_mode`
    into up to three. So the row reports the worst outcome among them
    (`OUTCOME_PRECEDENCE`, shared with the logbook so the two renderings
    of the same verdict cannot disagree), the first reason belonging to
    that outcome, and the UNION of the target diagnostics - a typo in the
    target belongs to every call the rule makes, so reading only the call
    that happens to carry it would drop it on a rule whose first call
    succeeded.

    None when there is nothing to report at all, so a rule that somehow
    produced no results keeps its previous, true verdict instead of having
    it overwritten by an empty one.
    """
    if not results:
        return None
    outcomes = {item.get("outcome") for item in results}
    outcome = next(
        (candidate for candidate in OUTCOME_PRECEDENCE if candidate in outcomes),
        None,
    )
    if outcome is None:
        return None
    detail = next(
        (
            str(item["error"])
            for item in results
            if item.get("outcome") == outcome and item.get("error")
        ),
        None,
    )
    # dict.fromkeys: de-duplicated but in first-seen order, so the row
    # names the ids in the order the rule names them.
    unknown = list(
        dict.fromkeys(
            entity_id
            for item in results
            for entity_id in item.get("unknown_targets") or ()
        )
    )
    return build_outcome(
        outcome,
        at,
        detail,
        unknown_targets=unknown,
        no_live_targets=any(
            item.get("no_live_targets") is True for item in results
        ),
    )


class ShabbatEngine:
    """Applies rules by handing their action to Home Assistant to execute."""

    def __init__(
        self,
        hass: HomeAssistant,
        store: RuleStore,
        candle_sensor: str = DEFAULT_CANDLE_SENSOR,
        havdalah_sensor: str = DEFAULT_HAVDALAH_SENSOR,
    ) -> None:
        self.hass = hass
        self.store = store
        # Configurable since Task 10: the Jewish Calendar integration derives
        # these entity ids from its own config entry's title, so there is no
        # name every install shares. Defaulted, not required, so every
        # pre-existing direct construction of this class keeps working.
        self._candle_sensor = candle_sensor
        self._havdalah_sensor = havdalah_sensor
        self.last_run: list[dict] = []
        self.last_run_at: datetime | None = None
        # Keyed on rule id, not entity_id: a target may be an area or a
        # label rather than one device, so there is no single entity to key
        # a lock on. This still guarantees one rule's own calls do not
        # interleave with a re-entrant application of that SAME rule; it no
        # longer guarantees that two DIFFERENT rules targeting the same
        # device cannot interleave with each other.
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._our_contexts: deque[str] = deque(maxlen=_CONTEXT_HISTORY)
        self._block: Block | None = None
        self._unsubscribes: list = []
        self._upcoming: list[ResolvedRule] = []
        self._refresh_lock = asyncio.Lock()
        # Which block async_catch_up has already run for. Compared by
        # value (Block is a frozen dataclass), so a genuinely new block
        # naturally re-arms this without any explicit reset - but the
        # SAME block cannot be caught up twice. Application through
        # async_call_from_config has no "already in that state" check the
        # way v1's device comparison did, so without this a second call
        # (setup races, a manual re-trigger) would repeat every side
        # effect rather than harmlessly no-op.
        self._caught_up_for: Block | None = None

    async def async_apply_rule(self, rule: Rule, force: bool = False) -> list[dict]:
        """Apply one rule, returning a per-attribute outcome report.

        The event is fired BEFORE the calls and carries everything needed to
        describe itself. The logbook renders historical events, so a describe
        function cannot look the rule up - it may have been renamed or deleted
        by then. Firing first is also what lets Home Assistant attribute each
        device's own change back to this rule, the same way automations do.
        """
        context = Context()
        self._our_contexts.append(context.id)

        self.hass.bus.async_fire(
            EVENT_RULE_APPLIED,
            {
                "rule_id": rule.id,
                "name": rule.name,
                "action": rule.action,
                "target": dict(rule.target),
                "dry_run": self.store.dry_run,
            },
            context=context,
        )

        if rule.condition:
            blocked_by = await self._condition_block_reason(rule)
            if blocked_by is not None:
                results = [{"outcome": "blocked", "reason": blocked_by}]
                self.last_run = results
                self.last_run_at = dt_util.utcnow()
                self._fire_completed(rule, results)
                # The same words the logbook row carries, deliberately:
                # the person reading the card and the person reading the
                # logbook must not be told two different things about why
                # one rule did nothing.
                await self._async_record_outcome(
                    rule,
                    build_outcome("blocked", self.last_run_at, blocked_by),
                )
                return results

        async with self._locks[rule.id]:
            results = []
            for action, data in expand_action(rule.action, dict(rule.data)):
                results.append(
                    await self._call(rule, action, rule.target, data, context)
                )

        self.last_run = results
        self.last_run_at = dt_util.utcnow()
        self._fire_completed(rule, results)
        await self._async_record_outcome(
            rule, outcome_from_results(results, self.last_run_at)
        )
        return results

    async def _async_record_outcome(self, rule: Rule, record: dict | None) -> None:
        """Make this rule's own verdict durable, and put it on the card.

        `last_run` is ONE value for the whole integration, overwritten by
        the next rule to act, so it can say what happened most recently and
        nothing about what happened to any particular rule. That is half of
        "a rule that does not fire must say why" missing, and the half the
        card needs.

        The push is separate from the write, and has to be. The store's
        change listener reschedules the engine (`_rules_changed`,
        __init__.py), so recording through it would refresh from inside a
        rule's own application - a re-evaluation, on the one day nobody can
        intervene. `async_record_outcome` therefore stays silent and the
        signal is sent from here: its only subscribers are switch.py's
        `_sync` and websocket_api's `_forward`, neither of which writes to
        the store or refreshes, so nothing can come back round. Sent
        outside any lock, like `async_refresh`'s, because the dispatcher
        runs @callback subscribers synchronously.

        Without the push the outcome exists but appears nowhere until the
        next unrelated edit: nothing else pushes between rules, since the
        zmanim sensors do not change again until havdalah. A wall tablet
        left open through Shabbat is exactly the reader this is for.
        """
        if record is None:
            return
        await self.store.async_record_outcome(rule.id, record)
        async_dispatcher_send(self.hass, SIGNAL_RULES_CHANGED)

    def _fire_completed(self, rule: Rule, results: list[dict]) -> None:
        """Announce the outcome, carrying enough to describe itself.

        Fired after the results exist, for consumers that need them.
        EVENT_RULE_APPLIED cannot carry them: it must precede the calls so
        Home Assistant can attribute each device's change back to this rule.

        It carries `name`/`action`/`target`/`dry_run` as well as the
        results, for the same reason EVENT_RULE_APPLIED does: the logbook
        renders HISTORICAL events, so its describer cannot look the rule up
        - it may have been renamed or deleted by then. Without these the
        outcome row could not say which rule or which device it was about,
        and an outcome nobody can attribute is barely an outcome.
        """
        self.hass.bus.async_fire(
            EVENT_RULE_COMPLETED,
            {
                "rule_id": rule.id,
                "name": rule.name,
                "action": rule.action,
                "target": dict(rule.target),
                "dry_run": self.store.dry_run,
                "results": results,
            },
        )

    async def _condition_block_reason(self, rule: Rule) -> str | None:
        """None if every condition passes, else WHY the rule is blocked.

        Every condition must pass. An error counts as not passing: erring
        towards NOT acting, because an unexpected error is not consent to
        drive an appliance on a day nobody can undo it.

        Returns a reason rather than a bool because this stops at the FIRST
        failing condition, so a rule carrying three of them would otherwise
        report a bare "condition not met" and leave the user no way at all
        to tell which one held it back - on the one day they cannot
        investigate. The index and the condition's own identifying fields
        are the difference between a report and a shrug.

        `async_from_config` builds its checker straight from the raw dict
        without normalising it first (e.g. a bare `entity_id: "a.b"` string
        is never turned into `["a.b"]"), so a config that skipped schema
        validation is silently misread rather than rejected -
        `cv.CONDITION_SCHEMA` + `async_validate_condition_config` is what
        does that normalising, same as `ha_validation.py` does at
        authoring time for the identical reason.
        """
        total = len(rule.condition)
        for index, item in enumerate(rule.condition, start=1):
            label = _condition_label(index, total, item)
            try:
                validated = cv.CONDITION_SCHEMA(dict(item))
                validated = await condition.async_validate_condition_config(
                    self.hass, validated
                )
                checker = await condition.async_from_config(self.hass, validated)
                if not checker(self.hass, {}):
                    return f"{label} not met"
            except Exception as err:  # noqa: BLE001 - a broken condition blocks
                _LOGGER.exception(
                    "Rule %s: %s could not be evaluated; not acting",
                    rule.id,
                    label,
                )
                # Type-prefixed, like `_call`'s failure reason: a good many
                # Home Assistant exceptions stringify to "", and
                # "could not be evaluated: " says nothing.
                detail = (
                    f"{type(err).__name__}: {err}" if str(err)
                    else type(err).__name__
                )
                return f"{label} could not be evaluated ({detail})"
        return None

    @property
    def current_block(self) -> Block | None:
        return self._block

    def upcoming(self) -> list[ResolvedRule]:
        return list(self._upcoming)

    def _tz(self):
        """The one timezone this integration is allowed to use."""
        return dt_util.get_time_zone(self.hass.config.time_zone)

    def _merged_rules(self) -> list[Rule]:
        return [merge_defaults(self.store.defaults, r) for r in self.store.rules]

    def _read_zmanim(self) -> tuple[datetime, datetime] | None:
        """Read the two configured zmanim entities, reporting via a repair
        issue - not just a log line - when they cannot be read at all.

        v1 hardcoded the entity ids and logged a warning on this path; that
        warning is invisible on the one day anyone would need to see it, and
        the entity ids it hardcoded are only the Jewish Calendar integration's
        own default names, derived from ITS config entry's title. A second
        Jewish Calendar entry, or one simply renamed, never matches.
        """
        candle = self.hass.states.get(self._candle_sensor)
        havdalah = self.hass.states.get(self._havdalah_sensor)
        start = dt_util.parse_datetime(candle.state) if candle else None
        end = dt_util.parse_datetime(havdalah.state) if havdalah else None
        if start is None or end is None:
            repairs.async_create_zmanim_issue(
                self.hass, self._candle_sensor, self._havdalah_sensor
            )
            return None
        repairs.async_delete_zmanim_issue(self.hass)
        # HA serialises timestamp sensor states as UTC. compute_block takes
        # `.date()` of each instant while resolve_rules combines those dates
        # with the LOCAL timezone, so they must be localised here or every
        # rule binds to the wrong calendar day wherever the UTC date and the
        # local date differ (i.e. anywhere west of UTC). block.py stays pure.
        tz = self._tz()
        return start.astimezone(tz), end.astimezone(tz)

    def _tail_of(self, block: Block) -> datetime | None:
        """When the last rule of `block` is due, or None if it has none."""
        resolved = resolve_rules(self._merged_rules(), block, self._tz())
        return resolved[-1].when if resolved else None

    async def async_refresh(self) -> None:
        """Recompute the block and rebuild every timer.

        Idempotent: it cancels every timer of the block in force and rebuilds
        them from that same block.

        Serialised, because it now persists the block and therefore awaits
        part-way through. Both zmanim sensors change at the same instant, so
        two refreshes genuinely overlap; a second one entering that window
        would cancel nothing (the first has already cancelled everything) and
        then append a duplicate set of timers, firing every rule twice.

        Announces a block change, because nothing else does. The card's push
        channel is SIGNAL_RULES_CHANGED, and until this existed the only
        dispatcher of it was the store's change listener - so a block that
        rolled forward at havdalah, was adopted when a hold released, or was
        restored across a restart reached no open card at all. A wall tablet
        left open then rendered the previous week's dates for the whole
        following week, and because the card filters `profile ==
        block.length` against the block it was given, a 3-day chag showed
        the 1-day profile: rules that will not fire, every rule that will
        fire hidden, nothing marked stale. Scheduling is unaffected either
        way - the engine works from `self._block`, never from the payload -
        but "I cannot tell whether it worked" is the complaint this project
        exists to answer.

        It cannot feed itself. `_rules_changed` (__init__.py), the thing
        that calls this, is the STORE's change listener, not a dispatcher
        subscriber, so the signal never re-enters it. The only two
        subscribers are switch.py's `_sync` (adds/removes entities and
        re-writes their state) and websocket_api's `_forward` (sends one
        message); neither writes to the store and neither refreshes. And it
        is sent only on a genuine change, so the setup-path refresh and
        every no-op re-publish stay silent.

        Sent outside the lock deliberately: the dispatcher runs @callback
        subscribers synchronously, and a future subscriber that refreshed
        would deadlock rather than merely loop.
        """
        async with self._refresh_lock:
            before = self._block
            await self._async_refresh()
            changed = self._block != before

        if changed:
            async_dispatcher_send(self.hass, SIGNAL_RULES_CHANGED)

    async def _async_refresh(self) -> None:
        for cancel in self._unsubscribes:
            cancel()
        self._unsubscribes = []
        self._upcoming = []

        now = dt_util.now()

        # Before looking at the sensors: the block that was in force when
        # this process last ran may still have rules pending. The hold below
        # only exists in memory, so without this a restart between havdalah
        # and a last-day "23:00 off" would read the already-rolled-forward
        # sensors, adopt NEXT week's block, and lose that rule in silence.
        if self._block is None:
            await self._restore_persisted_block(now)

        zmanim = self._read_zmanim()
        candidate: Block | None = None

        if zmanim is None:
            self._notify_zmanim_unreadable()
        else:
            persistent_notification.async_dismiss(self.hass, _NOTIFY_ZMANIM)
            try:
                candidate = compute_block(*zmanim)
            except ValueError:
                _LOGGER.warning("Ignoring implausible zmanim pair %s", zmanim)
                persistent_notification.async_create(
                    self.hass,
                    f"The {self._candle_sensor} and {self._havdalah_sensor} sensors "
                    "don't describe a valid Shabbat/Chag block (havdalah "
                    "must be after candle lighting). The schedule is not "
                    "running until this is fixed.",
                    title="Shabbat Scheduler",
                    notification_id=_NOTIFY_ZMANIM,
                )

        if candidate is not None and candidate != self._block:
            # Both jewish_calendar sensors advance to the NEXT occurrence the
            # moment `now >= havdalah`, which happens mid-block: rules are
            # deliberately not clamped to the zmanim, so a "23:00 on the last
            # day" rule is still pending at that point. Adopting the new block
            # there would cancel it and the appliance would run all night.
            # Hold the current block until its own rule tail is spent.
            tail = self._tail_of(self._block) if self._block is not None else None
            if tail is not None and now <= tail:
                _LOGGER.debug(
                    "Zmanim rolled forward to %s, but the current block still "
                    "has rules pending until %s; keeping it until %s",
                    candidate.erev_date,
                    tail,
                    tail + _HOLD_RELEASE_GRACE,
                )
                # Arm the release. Nothing else can do it: the tail rule
                # fires on its own timer and does not refresh, and the
                # zmanim sensors now hold NEXT week's values, so they will
                # not change again until the next havdalah - and HA fires
                # EVENT_STATE_REPORTED, not state_changed, when a state is
                # re-published identically, so the state listener stays
                # silent all week. Without this the candidate is never
                # adopted, no timers exist for the block that is coming,
                # and the entire next Shabbat is silently skipped.
                #
                # Cannot spin: this fires strictly after `tail`, so the
                # refresh it triggers takes the adopt branch. It cannot
                # stack either - async_refresh cancels every subscription
                # before rebuilding, so at most one release timer exists,
                # and async_shutdown cancels it with the rest.
                self._unsubscribes.append(
                    async_track_point_in_time(
                        self.hass, self._release_hold, tail + _HOLD_RELEASE_GRACE
                    )
                )
            else:
                self._block = candidate

        if self._block is not None:
            # Persisted unconditionally, not only while it is held: the
            # restart that has to be survived can land at any point inside
            # the block, and only the two zmanim are stored, so this is a
            # no-op write once the pair is unchanged.
            await self.store.async_set_active_block(
                self._block.candle_lighting, self._block.havdalah
            )

        if self._block is None or not self.store.enabled:
            return

        rules = self._merged_rules()

        if not has_profile(rules, self._block.length):
            persistent_notification.async_create(
                self.hass,
                f"No rules are enabled for a {self._block.length}-day block; "
                "nothing will run.",
                title="Shabbat Scheduler",
                notification_id=_NOTIFY_NO_PROFILE,
            )
            return

        persistent_notification.async_dismiss(self.hass, _NOTIFY_NO_PROFILE)
        self._upcoming = [
            item
            for item in resolve_rules(rules, self._block, self._tz())
            if item.when > now
        ]

        for item in self._upcoming:
            self._unsubscribes.append(
                async_track_point_in_time(
                    self.hass, self._make_callback(item), item.when
                )
            )

    async def _restore_persisted_block(self, now: datetime) -> None:
        """Re-adopt the pre-restart block, but only while it is still live.

        "Still live" means the same test the in-memory hold uses: at least
        one of its own resolved rules is not yet due. Once the tail is spent
        the persisted pair is dropped, so it can never pin the engine to a
        block that is over - the failure mode that would be worse than the
        one this fixes.

        Nothing here re-applies anything. Restoring only decides *which*
        block async_refresh then works from; timers are still built solely
        for rules whose time is in the future, and catch-up still applies at
        most the single most recent already-passed rule per device.
        """
        pair = self.store.active_block
        if pair is None:
            return

        tz = self._tz()
        try:
            block = compute_block(pair[0].astimezone(tz), pair[1].astimezone(tz))
        except ValueError:
            _LOGGER.warning("Discarding an implausible persisted block %s", pair)
            await self.store.async_clear_active_block()
            return

        tail = self._tail_of(block)
        if tail is None or now > tail:
            await self.store.async_clear_active_block()
            return

        _LOGGER.debug(
            "Restoring the block of %s across a restart; it still has rules "
            "pending until %s",
            block.erev_date,
            tail,
        )
        self._block = block

    def _notify_zmanim_unreadable(self) -> None:
        """Say so when the zmanim sensors cannot be read at all.

        Every other failure path here is loud; this one used to return in
        silence, so a renamed or missing jewish_calendar entity left the
        integration loaded, the master switch on, and nothing ever happening.

        Two deliberate limits: nothing is said while a cached block exists
        (that path is correctly quiet and survives a jewish_calendar outage),
        and nothing is said before HA has finished starting, because config
        entries set up concurrently and jewish_calendar has simply not
        published its sensors yet at that point.
        """
        if self._block is not None or self.hass.state is not CoreState.running:
            return
        _LOGGER.warning(
            "Cannot read %s / %s; no block is known, so nothing is scheduled",
            self._candle_sensor,
            self._havdalah_sensor,
        )
        persistent_notification.async_create(
            self.hass,
            f"Shabbat Scheduler cannot read {self._candle_sensor} and "
            f"{self._havdalah_sensor}. Is the Jewish Calendar integration set up, "
            "and are those entity ids still correct? Nothing is scheduled "
            "until they can be read.",
            title="Shabbat Scheduler",
            notification_id=_NOTIFY_ZMANIM,
        )

    async def _release_hold(self, _now) -> None:
        """Re-refresh once the held block's tail is spent, adopting the next."""
        _LOGGER.debug("Held block's tail is spent; refreshing to adopt the next")
        await self.async_refresh()

    def _make_callback(self, item: ResolvedRule):
        async def _fire(_now) -> None:
            await self.async_apply_rule(item.rule)

        return _fire

    async def async_catch_up(self) -> list[dict]:
        """Replay the rules that opted in to it, after a restart.

        An opaque service call has no queryable desired state the way
        v1's `hvac_mode`/`temperature`/`fan_mode` did, so catch-up can no
        longer ask "what state should this device be in now?". Instead
        the rule's own author says what is safe to repeat
        (`rule.replay.enabled`), how stale it may be and still be worth
        repeating (`rule.replay.within`), and the rule's own condition -
        evaluated through the normal `async_apply_rule` path - still
        guards it.

        A rule that does not fire must say why: a rule replayed too late
        is reported as `skipped_stale` rather than silently dropped.

        At most once per block: application through
        `async_call_from_config` has no "already in that state" check to
        make a repeat harmless the way v1's device comparison did.
        """
        if self._block is None or not self.store.enabled:
            return []
        if self._block == self._caught_up_for:
            return []

        now = dt_util.now()
        results: list[dict] = []
        for item in resolve_rules(self._merged_rules(), self._block, self._tz()):
            if item.when > now:
                continue                      # future: armed, not replayed
            if not item.rule.replay.enabled:
                continue                      # the author did not opt in
            within = item.rule.replay.within
            if within is not None and now - item.when > within:
                skipped = {
                    "rule_id": item.rule.id,
                    "outcome": "skipped_stale",
                    "reason": f"{now - item.when} late, window {within}",
                }
                results.append(skipped)
                # Recorded here and nowhere else: this path never reaches
                # `async_apply_rule`, so the durable per-rule outcome has
                # to be written on the skip itself. It is also the outcome
                # most likely to be READ - the morning after a restart,
                # asking why the lights never came on.
                await self._async_record_outcome(
                    item.rule,
                    build_outcome(
                        "skipped_stale", dt_util.utcnow(), skipped["reason"]
                    ),
                )
                # Fired per rule, not only folded into the aggregate below.
                # This path never reaches `async_apply_rule`, so it used to
                # emit no event whatsoever: the skip lived only in the
                # aggregate `last_run`, which the next rule to run
                # overwrites. A replay skip that nothing records is exactly
                # the silence "a rule that does not fire must say why"
                # forbids.
                self._fire_completed(item.rule, [skipped])
                continue
            results.extend(await self.async_apply_rule(item.rule))

        self._caught_up_for = self._block
        self.last_run = results
        self.last_run_at = dt_util.utcnow()
        # The pass summary. `catch_up` marks it so the logbook renders it as
        # one summary row rather than as a rule with no name; `rule_id` stays
        # None for the consumers (sensor.py) that only use it as a trigger.
        self.hass.bus.async_fire(
            EVENT_RULE_COMPLETED,
            {"rule_id": None, "catch_up": True, "results": results},
        )
        return results

    async def async_shutdown(self) -> None:
        """Cancel every pending timer."""
        for cancel in self._unsubscribes:
            cancel()
        self._unsubscribes = []

    def is_our_context(self, context: Context) -> bool:
        """Was `context` one this engine itself issued?

        No longer keyed per entity: a target may be an area or a label, so
        there is no single entity to key on, and the calls a rule makes may
        not even carry an `entity_id` at all (e.g. a `notify.*` action).
        """
        return context.id in self._our_contexts

    def _inspect_target(self, target: dict) -> tuple[list[str], bool]:
        """(typed ids that do not exist, whether NOTHING real was targeted).

        TWO SEPARATE QUESTIONS, kept apart deliberately. Conflating them
        is what produced both halves of Gap B's first fix being wrong in
        the opposite direction - reporting `failed` for a rule that had
        actually worked. A false failure is not a quiet failure, but it is
        still a lie, and a spurious failure notification on Shabbat could
        push someone into intervening by hand when nothing was wrong.

        1. WHAT TO REPORT AS UNKNOWN: only ids the user typed. Drawn from
           `_named_entity_ids`, never from `selected.referenced`, because
           `referenced` is the POST-GROUP-EXPANSION set: with
           `expand_group` on, a `group.g` the user typed is replaced by
           its members, so one merely-unavailable member would be
           reported as a misspelling nobody made. `indirectly_referenced`
           (area, device, floor, label) is excluded for the same reason,
           which is HA's own stated intent - its comment on that field
           reads "Should not trigger a warning when they don't exist."

        2. WHEN NOTHING CAN HAVE HAPPENED: whether the target resolved to
           any entity that exists at all, across BOTH `referenced` and
           `indirectly_referenced`. The full resolved set is right here
           and the typed set is not: a target of
           `{entity_id: [typo], area_id: [real]}` has every TYPED id
           unknown while the area's entities fire perfectly well, so
           counting only typed ids would call that a total failure.

        The caller requires a typo as well before downgrading to
        "failed", so `nothing_real` can be true with `unknown` empty. That
        is not one special case but a CLASS: any typed `group.`-namespace
        id that HAS a state yet expands to nothing live. An existing group
        whose members are all unavailable is one shape; a leftover
        `group.x` state with no group behind it, which
        `group.expand_entity_ids` resolves to nothing, is another. None of
        them is a misspelling, and none has any id to name in an error, so
        `failed` would be wrong - but the call did reach nothing, so the
        caller says so with its own third diagnostic rather than
        reporting bare success. `{"device_id": ["deadbeef"]}` lands here
        too, for the same reason and with the same treatment.

        `entity_id: all` is excluded from `nothing_real` outright. HA
        strips the wildcard before resolving, so the resolved set comes
        back empty while the service layer goes on to act on every entity
        in the domain - the exact inverse of "reached nothing".
        """
        if not target:
            return [], False
        # The whole body, not just the resolve: a malformed target can
        # equally throw in `_named_entity_ids` or in `TargetSelection`,
        # and neither is a reason to abandon a call HA might well accept.
        try:
            typed = _named_entity_ids(target)
            selected = target_helper.async_extract_referenced_entity_ids(
                self.hass, target_helper.TargetSelection(target),
            )
            unknown = sorted(
                entity_id for entity_id in typed
                if self.hass.states.get(entity_id) is None
            )
            resolved = selected.referenced | selected.indirectly_referenced
            nothing_real = not _targets_every_entity(target) and not any(
                self.hass.states.get(entity_id) is not None
                for entity_id in resolved
            )
        except Exception:  # noqa: BLE001 - a bad target must not stop the call
            # Reached by a target HA cannot even parse, e.g. an unhashable
            # `{"entity_id": {...}}` from a hand-edited YAML import. Such a
            # rule will fail in `async_call_from_config` a few lines later,
            # with HA's own message - which is a far better diagnosis than
            # anything this method could add, so it must not pre-empt it by
            # raising from here. Covered by
            # `test_a_target_home_assistant_cannot_even_parse_does_not_raise`.
            _LOGGER.debug("could not resolve target %s", target, exc_info=True)
            return [], False
        return unknown, nothing_real

    async def _call(
        self, rule: Rule, action: str, target: dict, data: dict, context: Context
    ) -> dict:
        """One service call, retried, reported either way.

        Everything here is Home Assistant's own service machinery -
        `async_call_from_config` validates the config, resolves the target
        and makes the call. This integration's contribution is deciding
        that now is the moment.
        """
        result = {"action": action, "target": dict(target), "data": dict(data)}

        # Before the dry-run return, deliberately: a dry run is exactly
        # where you want to be told about a misspelt entity id, and a dry
        # run that reported "would_call" for a target that cannot resolve
        # would be the same quiet failure one step earlier.
        unknown, nothing_real = self._inspect_target(target)
        if unknown:
            result["unknown_targets"] = unknown
            _LOGGER.warning(
                "rule '%s' targets %s, which do not exist",
                rule.name or rule.id, ", ".join(unknown),
            )
        elif nothing_real:
            # THE THIRD DIAGNOSTIC. Nothing is misspelt and the call is
            # genuinely made, so this is not `failed` - but the target
            # resolved to no entity that exists, so the call cannot have
            # changed anything either, and bare "called" would be a
            # silent report of success by a rule that affected nothing.
            # That is the shape this integration exists to prevent, so it
            # gets a key and a log line of its own instead of a gate
            # change: `failed` here would blame a typo that is not there.
            result["no_live_targets"] = True
            _LOGGER.warning(
                "rule '%s' was called but its target %s %s - "
                "nothing can have changed",
                rule.name or rule.id, target or "none", NO_LIVE_TARGETS_NOTE,
            )

        if self.store.dry_run:
            result["outcome"] = "would_call"
            return result

        config = {"action": action, "data": data}
        if target:
            config["target"] = dict(target)

        for attempt in range(1, RETRY_ATTEMPTS + 1):
            try:
                await async_call_from_config(
                    self.hass, config, blocking=True, validate_config=True,
                    context=context,
                )
            except Exception as err:  # noqa: BLE001 - reported, never swallowed
                # This log line, and the notification below, are the only
                # forensic surface for a Shabbat-night failure, when nobody
                # can investigate live. Without them a missing service, a
                # timeout and a cloud auth error look identical - and on a
                # headless instance during Shabbat, a log line is invisible.
                # A rule that does not fire must say why.
                if attempt == RETRY_ATTEMPTS:
                    reason = (
                        f"{type(err).__name__}: {err}" if str(err)
                        else type(err).__name__
                    )
                    _LOGGER.error(
                        "%s failed after %s attempts: %s",
                        action, RETRY_ATTEMPTS, reason, exc_info=True,
                    )
                    # Keyed on the action, not an entity id: a v2 target may
                    # be an area or a label, or the call may carry no
                    # entity at all (e.g. notify.*), so there is no single
                    # entity to key the notification on the way v1 did.
                    who = rule.name or rule.id
                    persistent_notification.async_create(
                        self.hass,
                        f"Rule '{who}': {action} (target: {target or 'none'}) "
                        f"failed after {RETRY_ATTEMPTS} attempts. "
                        f"Reason: {reason}",
                        title="Shabbat Scheduler",
                        notification_id=f"shabbat_scheduler_fail_{action}",
                    )
                    result["outcome"] = "failed"
                    # The type-prefixed `reason`, not the bare `str(err)`:
                    # this dict is what the last_run sensor exposes, and a
                    # good many Home Assistant exceptions stringify to "".
                    # `{"outcome": "failed", "error": ""}` is a rule that
                    # does not say why it did not fire.
                    result["error"] = reason
                    return result
                _LOGGER.warning(
                    "%s failed (attempt %s/%s): %s: %s",
                    action, attempt, RETRY_ATTEMPTS, type(err).__name__, err,
                )
                await asyncio.sleep(RETRY_DELAY_SECONDS)
            else:
                # Downgraded only when there is a typo AND the target
                # resolved to nothing that exists, so the call cannot have
                # done anything. Reporting "called" there is the quiet
                # failure this integration exists to prevent.
                #
                # BOTH conditions are load-bearing, and each guards a lie
                # in the opposite direction:
                #  - without `unknown`, an existing group whose members
                #    all happen to be unavailable would be called a
                #    failure, with an empty list of ids to blame for it;
                #  - without `nothing_real`, a target that mixes a typo
                #    with a working area would be called a failure while
                #    the area's entities fired perfectly well.
                # A partial miss therefore stays "called": the call did
                # genuinely help the entities that exist, and
                # `unknown_targets` still reports the typo.
                if unknown and nothing_real:
                    result["outcome"] = "failed"
                    result["error"] = UNKNOWN_ENTITY_PREFIX + ", ".join(unknown)
                else:
                    result["outcome"] = "called"
                return result
        return result
