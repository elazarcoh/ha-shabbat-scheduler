"""Executes the decisions the pure modules make."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict, deque
from datetime import datetime

from homeassistant.core import Context, HomeAssistant

from .const import EVENT_RULE_APPLIED
from .device_ops import plan_calls
from .models import Action, Rule
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
        try:
            await self.hass.services.async_call(
                call.domain, call.service, data,
                blocking=True, context=self._new_context(entity_id),
            )
        except Exception:  # noqa: BLE001 - one device must not abort the rest
            _LOGGER.exception("%s: %s.%s failed", entity_id, call.domain, call.service)
            result["outcome"] = "failed"
            return result

        self._last_command[entity_id] = datetime.now(tz=None).astimezone()
        result["outcome"] = "changed"
        return result
