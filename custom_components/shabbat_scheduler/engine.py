"""Executes the decisions the pure modules make."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict, deque
from datetime import datetime, timedelta

from homeassistant.components import persistent_notification
from homeassistant.core import Context, CoreState, HomeAssistant
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.util import dt as dt_util

from .block import (
    compute_block,
    desired_state_at,
    has_profile,
    merge_defaults,
    resolve_rules,
)
from .const import (
    CANDLE_SENSOR,
    EVENT_RULE_APPLIED,
    HAVDALAH_SENSOR,
    RETRY_ATTEMPTS,
    RETRY_DELAY_SECONDS,
)
from .device_ops import Skip, plan_calls
from .models import Action, Block, Conflict, ResolvedRule, Rule
from .store import RuleStore

_LOGGER = logging.getLogger(__name__)

_UNTRUSTED_STATES = ("unknown", "unavailable")

# Fixed notification ids so a condition that is re-evaluated on every state
# change replaces its own notification instead of stacking dozens of copies,
# and can be dismissed once it clears.
_NOTIFY_ZMANIM = "shabbat_scheduler_zmanim"
_NOTIFY_NO_PROFILE = "shabbat_scheduler_no_profile"

# How many of our own recent context ids we remember per device. Bounded so a
# long-running instance cannot grow this without limit; generous enough that
# no realistic burst of calls to one device evicts a context before anything
# could plausibly ask about it.
_CONTEXT_HISTORY_PER_DEVICE = 20

# How long after a held block's last rule the candidate block is adopted.
# Strictly greater than zero so the refresh it schedules is guaranteed to
# fall on the far side of the hold condition (`now <= tail`) and can never
# re-arm itself.
_HOLD_RELEASE_GRACE = timedelta(seconds=1)


class ShabbatEngine:
    """Applies rules idempotently, one device at a time."""

    def __init__(self, hass: HomeAssistant, store: RuleStore) -> None:
        self.hass = hass
        self.store = store
        self.last_run: list[dict] = []
        self.last_run_at: datetime | None = None
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._last_command: dict[str, datetime] = {}
        self._our_contexts: dict[str, deque[str]] = defaultdict(
            lambda: deque(maxlen=_CONTEXT_HISTORY_PER_DEVICE)
        )
        self._block: Block | None = None
        self._unsubscribes: list = []
        self._upcoming: list[ResolvedRule] = []

    async def async_apply_rule(self, rule: Rule, force: bool = False) -> list[dict]:
        """Apply one rule, returning a per-attribute outcome report."""
        if rule.action is Action.CUSTOM:
            results = await self._apply_custom(rule)
        else:
            results = []
            for entity_id in rule.devices:
                results.extend(await self._apply_device(rule, entity_id, force))

        self.last_run = results
        self.last_run_at = dt_util.utcnow()
        self.hass.bus.async_fire(
            EVENT_RULE_APPLIED, {"rule_id": rule.id, "results": results}
        )
        return results

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
        candle = self.hass.states.get(CANDLE_SENSOR)
        havdalah = self.hass.states.get(HAVDALAH_SENSOR)
        if candle is None or havdalah is None:
            return None
        start = dt_util.parse_datetime(candle.state)
        end = dt_util.parse_datetime(havdalah.state)
        if start is None or end is None:
            return None
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
        """
        for cancel in self._unsubscribes:
            cancel()
        self._unsubscribes = []
        self._upcoming = []

        now = dt_util.now()
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
                    f"The {CANDLE_SENSOR} and {HAVDALAH_SENSOR} sensors "
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
            CANDLE_SENSOR,
            HAVDALAH_SENSOR,
        )
        persistent_notification.async_create(
            self.hass,
            f"Shabbat Scheduler cannot read {CANDLE_SENSOR} and "
            f"{HAVDALAH_SENSOR}. Is the Jewish Calendar integration set up, "
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
        """Re-apply the current desired state after a restart.

        Only the most recent already-passed rule per device is applied, and
        because application is idempotent this is safe to repeat.
        """
        if self._block is None or not self.store.enabled:
            return []

        tz = self._tz()
        now = dt_util.now()
        rules = self._merged_rules()

        devices = {device for rule in rules for device in rule.devices}
        results: list[dict] = []

        for device in sorted(devices):
            wanted = desired_state_at(rules, self._block, now, device, tz)
            if wanted is None:
                continue
            if isinstance(wanted, Conflict):
                _LOGGER.warning(
                    "%s: ambiguous desired state (rules %s); not acting",
                    device, ", ".join(wanted.rule_ids),
                )
                continue
            results.extend(await self._apply_device(wanted, device, force=False))

        # Custom rules are excluded above because desired_state_at ignores
        # them; replay them only where explicitly opted in, and only once
        # they have actually passed. Reuse resolve_rules rather than
        # hand-rolling profile/enabled/time filtering a second time - it
        # already binds each rule to the concrete datetime the on/off path
        # trusts.
        for item in resolve_rules(rules, self._block, tz):
            if (
                item.rule.action is Action.CUSTOM
                and item.rule.replay_on_restart
                and item.when <= now
            ):
                results.extend(await self._apply_custom(item.rule))

        self.last_run = results
        self.last_run_at = dt_util.utcnow()
        return results

    async def async_shutdown(self) -> None:
        """Cancel every pending timer."""
        for cancel in self._unsubscribes:
            cancel()
        self._unsubscribes = []

    async def _apply_custom(self, rule: Rule) -> list[dict]:
        if not rule.script:
            return []
        if self.store.dry_run:
            return [
                {
                    "entity_id": rule.script, "attribute": "script",
                    "outcome": "changed", "from": None, "to": "run",
                }
            ]
        await self.hass.services.async_call(
            "script", "turn_on",
            {"entity_id": rule.script, "variables": dict(rule.variables)},
            blocking=True, context=self._new_context(rule.script),
        )
        return [
            {
                "entity_id": rule.script, "attribute": "script",
                "outcome": "changed", "from": None, "to": "run",
            }
        ]

    async def _apply_device(
        self, rule: Rule, entity_id: str, force: bool
    ) -> list[dict]:
        state = self.hass.states.get(entity_id)
        if state is None:
            _LOGGER.warning("%s: entity not found", entity_id)
            return [
                {
                    "entity_id": entity_id, "attribute": "state",
                    "outcome": "failed", "from": None, "to": None,
                }
            ]

        must_apply = force or state.state in _UNTRUSTED_STATES or self._is_stale(
            entity_id, state.last_updated
        )
        calls = plan_calls(
            entity_id, state.state, dict(state.attributes),
            rule.action, rule.settings, must_apply,
        )

        if not calls:
            return [
                {
                    "entity_id": entity_id, "attribute": "state",
                    "outcome": "ok", "from": state.state, "to": state.state,
                }
            ]

        results: list[dict] = []
        async with self._locks[entity_id]:
            for call in calls:
                if isinstance(call, Skip):
                    # Nothing retries a dropped sub-call, so it is reported
                    # rather than passed over in silence.
                    _LOGGER.warning(
                        "%s: cannot apply %s=%r: %s",
                        entity_id, call.attribute, call.requested, call.reason,
                    )
                    results.append(
                        {
                            "entity_id": entity_id,
                            "attribute": call.attribute,
                            "outcome": "skipped",
                            "from": None,
                            "to": call.requested,
                            "reason": call.reason,
                        }
                    )
                    continue
                results.append(await self._execute(entity_id, call))
        return results

    def _is_stale(self, entity_id: str, last_updated: datetime) -> bool:
        """True when the reading predates our own most recent command.

        The aux_cloud units lag several seconds on fan_mode, so a naive read
        would skip a command that never actually landed.
        """
        sent = self._last_command.get(entity_id)
        return sent is not None and last_updated < sent

    def _new_context(self, entity_id: str) -> Context:
        """Create a Context for a call to `entity_id` and remember it.

        Retaining our own context ids is what lets a future enforcement
        feature distinguish "this changed because WE changed it" from "a
        human changed it" when looking at a state_changed event. Without
        this, that distinction is impossible - which is the most likely
        reason a previous, similar component ended up fighting the user.
        """
        context = Context()
        self._our_contexts[entity_id].append(context.id)
        return context

    def is_our_context(self, entity_id: str, context: Context) -> bool:
        """Was `context` one the engine itself issued for `entity_id`?"""
        return context.id in self._our_contexts.get(entity_id, ())

    async def _execute(self, entity_id: str, call) -> dict:
        result = {
            "entity_id": entity_id,
            "attribute": call.attribute,
            "from": call.from_value,
            "to": call.to_value,
        }

        if self.store.dry_run:
            result["outcome"] = "changed"
            return result

        data = {"entity_id": entity_id, **call.data}
        for attempt in range(1, RETRY_ATTEMPTS + 1):
            # Stamped BEFORE each attempt, deliberately: the entity's own
            # `last_updated` is written during the awaited call, so a stamp
            # taken afterwards is always later than that write and the
            # staleness guard would then report the reading stale forever -
            # forcing a real service call on every later apply, which is the
            # re-asserting behaviour this integration exists to avoid.
            self._last_command[entity_id] = dt_util.utcnow()
            try:
                await self.hass.services.async_call(
                    call.domain, call.service, data,
                    blocking=True, context=self._new_context(entity_id),
                )
            except Exception as err:  # noqa: BLE001 - one device must not abort the rest
                # The reason matters: this log line and the notification below
                # are the only forensic surface for a Shabbat-night failure,
                # when nobody can investigate live. Without it a missing
                # service, a timeout and a cloud auth error look identical.
                if attempt < RETRY_ATTEMPTS:
                    _LOGGER.warning(
                        "%s: %s.%s failed (attempt %s/%s): %s: %s",
                        entity_id, call.domain, call.service, attempt,
                        RETRY_ATTEMPTS, type(err).__name__, err,
                    )
                    await asyncio.sleep(RETRY_DELAY_SECONDS)
                    continue

                _LOGGER.error(
                    "%s: %s.%s failed after %s attempts: %s: %s",
                    entity_id, call.domain, call.service, RETRY_ATTEMPTS,
                    type(err).__name__, err, exc_info=True,
                )
                reason = f"{type(err).__name__}: {err}" if str(err) else type(err).__name__
                persistent_notification.async_create(
                    self.hass,
                    f"{entity_id}: {call.domain}.{call.service} failed after "
                    f"{RETRY_ATTEMPTS} attempts. Reason: {reason}",
                    title="Shabbat Scheduler",
                    notification_id=f"shabbat_scheduler_fail_{entity_id}_{call.service}",
                )
                result["outcome"] = "failed"
                result["reason"] = reason
                return result

            result["outcome"] = "changed"
            return result
