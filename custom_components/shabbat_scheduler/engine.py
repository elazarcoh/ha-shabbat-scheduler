"""Executes the decisions the pure modules make."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict, deque
from datetime import datetime

from homeassistant.components import persistent_notification
from homeassistant.core import Context, HomeAssistant
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
from .device_ops import plan_calls
from .models import Action, Block, Conflict, ResolvedRule, Rule
from .store import RuleStore

_LOGGER = logging.getLogger(__name__)

_UNTRUSTED_STATES = ("unknown", "unavailable")

# How many of our own recent context ids we remember per device. Bounded so a
# long-running instance cannot grow this without limit; generous enough that
# no realistic burst of calls to one device evicts a context before anything
# could plausibly ask about it.
_CONTEXT_HISTORY_PER_DEVICE = 20


class ShabbatEngine:
    """Applies rules idempotently, one device at a time."""

    def __init__(self, hass: HomeAssistant, store: RuleStore) -> None:
        self.hass = hass
        self.store = store
        self.last_run: list[dict] = []
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
        self.hass.bus.async_fire(
            EVENT_RULE_APPLIED, {"rule_id": rule.id, "results": results}
        )
        return results

    @property
    def current_block(self) -> Block | None:
        return self._block

    def upcoming(self) -> list[ResolvedRule]:
        return list(self._upcoming)

    def _read_zmanim(self) -> tuple[datetime, datetime] | None:
        candle = self.hass.states.get(CANDLE_SENSOR)
        havdalah = self.hass.states.get(HAVDALAH_SENSOR)
        if candle is None or havdalah is None:
            return None
        start = dt_util.parse_datetime(candle.state)
        end = dt_util.parse_datetime(havdalah.state)
        if start is None or end is None:
            return None
        return start, end

    async def async_refresh(self) -> None:
        """Recompute the block and rebuild every timer."""
        for cancel in self._unsubscribes:
            cancel()
        self._unsubscribes = []
        self._upcoming = []

        zmanim = self._read_zmanim()
        if zmanim is not None:
            try:
                # Cache survives a jewish_calendar outage so the schedule is
                # never silently wiped.
                self._block = compute_block(*zmanim)
            except ValueError:
                _LOGGER.warning("Ignoring implausible zmanim pair %s", zmanim)
                persistent_notification.async_create(
                    self.hass,
                    f"The {CANDLE_SENSOR} and {HAVDALAH_SENSOR} sensors "
                    "don't describe a valid Shabbat/Chag block (havdalah "
                    "must be after candle lighting). The schedule is not "
                    "running until this is fixed.",
                    title="Shabbat Scheduler",
                )

        if self._block is None or not self.store.enabled:
            return

        rules = [merge_defaults(self.store.defaults, r) for r in self.store.rules]

        if not has_profile(rules, self._block.length):
            persistent_notification.async_create(
                self.hass,
                f"No rules are configured for a {self._block.length}-day block; "
                "nothing will run.",
                title="Shabbat Scheduler",
            )
            return

        tz = dt_util.get_time_zone(self.hass.config.time_zone)
        now = dt_util.now()
        self._upcoming = [
            item for item in resolve_rules(rules, self._block, tz) if item.when > now
        ]

        for item in self._upcoming:
            self._unsubscribes.append(
                async_track_point_in_time(
                    self.hass, self._make_callback(item), item.when
                )
            )

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

        tz = dt_util.get_time_zone(self.hass.config.time_zone)
        now = dt_util.now()
        rules = [merge_defaults(self.store.defaults, r) for r in self.store.rules]

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
        return results

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
            # Stamped before each attempt - see the note in Task 9. Stamping
            # after a successful call makes every later reading look stale.
            self._last_command[entity_id] = dt_util.utcnow()
            try:
                await self.hass.services.async_call(
                    call.domain, call.service, data,
                    blocking=True, context=self._new_context(entity_id),
                )
            except Exception:  # noqa: BLE001 - one device must not abort the rest
                _LOGGER.warning(
                    "%s: %s.%s failed (attempt %s/%s)",
                    entity_id, call.domain, call.service, attempt, RETRY_ATTEMPTS,
                )
                if attempt < RETRY_ATTEMPTS:
                    await asyncio.sleep(RETRY_DELAY_SECONDS)
                    continue
                persistent_notification.async_create(
                    self.hass,
                    f"{entity_id}: {call.domain}.{call.service} failed after "
                    f"{RETRY_ATTEMPTS} attempts.",
                    title="Shabbat Scheduler",
                )
                result["outcome"] = "failed"
                return result

            result["outcome"] = "changed"
            return result

        result["outcome"] = "failed"
        return result
