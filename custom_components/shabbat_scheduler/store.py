"""Persistence of the rule set in Home Assistant's .storage.

.storage is the source of truth; YAML is only ever an import/export view.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime, time, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import STORAGE_KEY, STORAGE_VERSION
from .models import Replay, Rule
from .rule_schema import RuleValidationError, _duration


def _duration_to_str(value: timedelta) -> str:
    """A timedelta as 'HH:MM:SS' - the form `rule_schema._duration` (and
    so every API client) accepts. Sub-second precision is not a concept
    the API exposes, so it is dropped rather than silently rounded away
    somewhere less visible."""
    total_seconds = int(value.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def replay_to_dict(replay: Replay) -> dict:
    """Serialise a rule's replay policy.

    `within` is written as 'HH:MM:SS', the same shape `rule_schema`
    validates on the way in - `rule_to_dict` is what every websocket
    response returns, so a client that reads a rule and writes it back
    must not be rejected for round-tripping the value verbatim.
    """
    data: dict = {"enabled": replay.enabled}
    if replay.within is not None:
        data["within"] = _duration_to_str(replay.within)
    return data


def replay_from_dict(data) -> Replay:
    """Deserialise a rule's replay policy, tolerating absence only.

    `within` bounds how late a rule may fire - dropping it silently turns
    a bounded replay into an unbounded one, exactly the kind of silent
    widening this project treats as unacceptable. So a value that cannot
    be understood is never quietly discarded: it is either parsed
    correctly or raised.
    """
    if not isinstance(data, dict):
        return Replay()
    within = data.get("within")
    parsed = None
    if within is not None:
        if isinstance(within, bool):
            raise RuleValidationError(f"replay.within must be a duration, got {within!r}")
        if isinstance(within, (int, float)):
            # A store written by the pre-fix-round-1 migration (e39449b)
            # serialised `within` as a raw number of seconds. Parsing it
            # as such keeps that store's bound intact instead of
            # silently turning it into "no bound".
            parsed = timedelta(seconds=within)
        else:
            parsed = _duration(within)
    return Replay(enabled=bool(data.get("enabled", False)), within=parsed)


def rule_to_dict(rule: Rule) -> dict:
    """Serialise a rule for storage."""
    return {
        "id": rule.id,
        "profile": rule.profile,
        "day": rule.day,
        "time": rule.time.isoformat(),
        "action": rule.action,
        "target": dict(rule.target),
        "data": dict(rule.data),
        "condition": [dict(item) for item in rule.condition],
        "replay": replay_to_dict(rule.replay),
        "name": rule.name,
        "icon": rule.icon,
        "color": rule.color,
        "enabled": rule.enabled,
    }


def rule_from_dict(data: dict) -> Rule:
    """Deserialise a stored rule."""
    return Rule(
        id=data["id"],
        profile=int(data["profile"]),
        day=str(data["day"]),
        time=time.fromisoformat(data["time"]),
        action=str(data["action"]),
        target=dict(data.get("target") or {}),
        data=dict(data.get("data") or {}),
        condition=tuple(dict(item) for item in data.get("condition") or ()),
        replay=replay_from_dict(data.get("replay")),
        name=data.get("name"),
        icon=data.get("icon"),
        color=data.get("color"),
        enabled=data.get("enabled", True),
    )


def active_block_to_dict(pair: tuple[datetime, datetime]) -> dict:
    """Serialise the zmanim pair that defines the block in force."""
    return {
        "candle_lighting": pair[0].isoformat(),
        "havdalah": pair[1].isoformat(),
    }


def active_block_from_dict(data) -> tuple[datetime, datetime] | None:
    """Deserialise that pair, tolerating absence and anything malformed.

    Never raises: a `.storage` file written before this key existed, or one
    hand-edited into nonsense, must degrade to "no persisted block" rather
    than stop the integration loading.
    """
    if not isinstance(data, dict):
        return None
    try:
        candle = dt_util.parse_datetime(str(data["candle_lighting"]))
        havdalah = dt_util.parse_datetime(str(data["havdalah"]))
    except (KeyError, TypeError, ValueError):
        return None
    if candle is None or havdalah is None:
        return None
    return candle, havdalah


def last_outcomes_from_dict(data) -> dict[str, dict]:
    """Deserialise the per-rule outcome map, tolerating absence and junk.

    Never raises, for the same reason `active_block_from_dict` never does:
    a `.storage` file written before this key existed - which is every
    install in the field right now - or one hand-edited into nonsense, must
    degrade to "no outcome recorded" rather than stop the integration
    loading. An outcome is a REPORT about the past; losing one costs the
    card a line, while failing to load costs the user their whole schedule.
    That asymmetry is why nothing here is strict.

    Entries with no `outcome` are dropped: the card keys everything it says
    off that field, and `{"outcome": null}` renders as a rule claiming to
    have finished with no verdict, which is worse than saying nothing.

    Adding this key needed no STORAGE_VERSION bump precisely because of
    this function - see `test_a_store_written_before_last_outcome_existed_
    still_loads`, which writes a version-2 store with no such key at all.
    """
    if not isinstance(data, dict):
        return {}
    return {
        str(rule_id): dict(value)
        for rule_id, value in data.items()
        if isinstance(value, dict) and value.get("outcome")
    }


class _MigratingStore(Store):
    """Home Assistant calls this when the stored version is behind.

    There is currently nothing to migrate: v1 -> v2 migration support has
    been removed entirely (v1 was never shipped to a real user), and no
    version past 2 exists yet. The override is kept anyway, not deleted,
    because it is Home Assistant's own hook for a FUTURE version bump - the
    next one to actually need a migration adds its own branch here, ahead
    of the refusal below.

    Silently accepting an old, unmigrated store here would be exactly the
    silent-no-op defect class this project treats as its primary concern:
    a v1-shaped rule would load as syntactically valid v2 data - a bare
    `action: "on"` with an empty `target`/`data` and `enabled: True` - and
    then get written back out at the current version, discarding the
    original data permanently and with no trace. Refusing outright is the
    honest failure.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(hass, STORAGE_VERSION, STORAGE_KEY)

    async def _async_migrate_func(
        self, old_major_version: int, old_minor_version: int, old_data: dict
    ) -> dict:
        if old_major_version < STORAGE_VERSION:
            raise HomeAssistantError(
                f"{STORAGE_KEY} is at version {old_major_version}."
                f"{old_minor_version}, which shabbat_scheduler no longer has "
                "migration support for (v1 was never shipped to a real user, "
                "so the v1 -> v2 conversion has been removed). Delete the "
                "stored file and set the integration up again from scratch."
            )
        return old_data


class RuleStore:
    """Loads, mutates and persists the rule set."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._store: _MigratingStore = _MigratingStore(hass)
        self._rules: list[Rule] = []
        self._defaults: dict = {}
        self._enabled: bool = False
        self._active_block: tuple[datetime, datetime] | None = None
        # Keyed by rule id. NOT a field on Rule: an outcome is what
        # happened TO a rule, not part of what the rule is - putting it on
        # the dataclass would put it in `rule_to_dict`, and from there into
        # the YAML export, where a report about last Shabbat would look
        # like part of the schedule a user is meant to author.
        self._last_outcomes: dict[str, dict] = {}
        self._on_change: Callable[[], None] | None = None

    @property
    def rules(self) -> list[Rule]:
        return list(self._rules)

    @property
    def defaults(self) -> dict:
        return dict(self._defaults)

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def active_block(self) -> tuple[datetime, datetime] | None:
        """The (candle lighting, havdalah) pair of the block in force.

        The block itself is recomputable from these two instants, so only
        they are stored - `block.py` stays pure and out of the schema.
        """
        return self._active_block

    def last_outcome(self, rule_id: str) -> dict | None:
        """What happened the last time `rule_id` came due, or None.

        None, never `{}`, for a rule that has never come due: the card
        renders nothing at all for it, and an empty dict would have to be
        distinguished from a real verdict by every reader in turn.

        A copy, so a caller cannot mutate the store's own record - this is
        handed straight out over the websocket on every push.
        """
        outcome = self._last_outcomes.get(rule_id)
        return dict(outcome) if outcome is not None else None

    async def async_record_outcome(self, rule_id: str, outcome: dict) -> None:
        """Make one rule's verdict durable. REPLACES, never merges.

        Replacing matters: a rule that named a misspelt entity last week
        and names a real one today must stop being reported as a typo. A
        merge would keep the stale `unknown_targets` alongside the new
        `called` and have the card go on blaming a mistake already fixed.

        Deliberately does NOT notify. The store's change listener is
        `_rules_changed` (__init__.py), which RESCHEDULES the engine, so
        notifying from here would mean every rule that fires triggers a
        refresh from inside its own application - a re-evaluation, on the
        one day nobody can intervene. "Fire once, never re-assert."
        The engine pushes the card over SIGNAL_RULES_CHANGED instead,
        which has no path back into the store.
        """
        self._last_outcomes[rule_id] = dict(outcome)
        await self.async_save()

    def _prune_outcomes(self) -> None:
        """Forget the outcomes of rules that no longer exist.

        Runs on every save, so the map is bounded by the rule set rather
        than by how long the instance has been up: without it a user who
        creates and deletes rules over a year accumulates a verdict for
        every id they ever used, in a file loaded at every start.
        """
        live = {rule.id for rule in self._rules}
        for rule_id in [key for key in self._last_outcomes if key not in live]:
            del self._last_outcomes[rule_id]

    def async_set_change_listener(self, listener: Callable[[], None]) -> None:
        """Register the one callback fired after any rule-set change.

        The store deliberately does not know about dispatchers or entities -
        the caller decides what a change means.
        """
        self._on_change = listener

    def _notify_change(self) -> None:
        if self._on_change is not None:
            self._on_change()

    async def async_load(self) -> None:
        data = await self._store.async_load() or {}
        self._rules = [rule_from_dict(item) for item in data.get("rules", [])]
        self._defaults = data.get("defaults", {})
        # Master switch defaults OFF so a fresh install cannot act.
        self._enabled = data.get("enabled", False)
        # Added after v1 shipped; absent in every store written before it.
        self._active_block = active_block_from_dict(data.get("active_block"))
        # Absent in every store written before Task 11; see
        # `last_outcomes_from_dict` for why that needs no version bump.
        self._last_outcomes = last_outcomes_from_dict(data.get("last_outcomes"))

    async def async_save(self) -> None:
        self._prune_outcomes()
        data = {
            "rules": [rule_to_dict(rule) for rule in self._rules],
            "defaults": self._defaults,
            "enabled": self._enabled,
        }
        # Written only when there is one, so a store that never has an
        # active block keeps exactly the shape it has always had.
        if self._active_block is not None:
            data["active_block"] = active_block_to_dict(self._active_block)
        # Same additive treatment as `active_block`: a store whose rules
        # have never come due keeps exactly the shape it has always had.
        if self._last_outcomes:
            data["last_outcomes"] = {
                rule_id: dict(outcome)
                for rule_id, outcome in self._last_outcomes.items()
            }
        await self._store.async_save(data)

    async def async_set_active_block(
        self, candle_lighting: datetime, havdalah: datetime
    ) -> None:
        """Remember the block in force so it survives a restart."""
        pair = (candle_lighting, havdalah)
        if pair == self._active_block:
            return  # no write on every refresh
        self._active_block = pair
        await self.async_save()

    async def async_clear_active_block(self) -> None:
        """Forget it, once it can no longer be pending."""
        if self._active_block is None:
            return
        self._active_block = None
        await self.async_save()

    async def async_set_enabled(self, value: bool) -> None:
        self._enabled = value
        await self.async_save()
        self._notify_change()

    async def async_add(self, rule: Rule) -> None:
        self._rules.append(rule)
        await self.async_save()
        self._notify_change()

    async def async_update(self, rule_id: str, **changes) -> None:
        if not any(rule.id == rule_id for rule in self._rules):
            raise KeyError(rule_id)
        self._rules = [
            replace(rule, **changes) if rule.id == rule_id else rule
            for rule in self._rules
        ]
        await self.async_save()
        self._notify_change()

    async def async_delete(self, rule_id: str) -> None:
        self._rules = [rule for rule in self._rules if rule.id != rule_id]
        await self.async_save()
        self._notify_change()

    async def async_replace_all(self, defaults: dict, rules: list[Rule]) -> None:
        self._defaults = dict(defaults)
        self._rules = list(rules)
        await self.async_save()
        self._notify_change()
