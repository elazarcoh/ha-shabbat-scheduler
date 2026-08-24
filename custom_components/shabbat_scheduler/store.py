"""Persistence of the rule set in Home Assistant's .storage.

.storage is the source of truth; YAML is only ever an import/export view.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime, time, timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import STORAGE_KEY, STORAGE_VERSION
from .migration import migrate_v1
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
        "migration_error": rule.migration_error,
        "migration_source": (
            dict(rule.migration_source) if rule.migration_source is not None else None
        ),
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
        migration_error=data.get("migration_error"),
        migration_source=(
            dict(data["migration_source"])
            if isinstance(data.get("migration_source"), dict)
            else None
        ),
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


class _MigratingStore(Store):
    """Home Assistant calls this when the stored version is behind.

    Whatever it returns is saved automatically, so the conversion happens
    exactly once per upgrade.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(hass, STORAGE_VERSION, STORAGE_KEY)
        self.migration_failures: list[str] = []

    async def _async_migrate_func(
        self, old_major_version: int, old_minor_version: int, old_data: dict
    ) -> dict:
        if old_major_version == 1:
            migrated, failed = migrate_v1(old_data)
            self.migration_failures = failed
            return migrated
        return old_data


class RuleStore:
    """Loads, mutates and persists the rule set."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._store: _MigratingStore = _MigratingStore(hass)
        self._rules: list[Rule] = []
        self._defaults: dict = {}
        self._enabled: bool = False
        self._dry_run: bool = False
        self._active_block: tuple[datetime, datetime] | None = None
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
    def dry_run(self) -> bool:
        return self._dry_run

    @property
    def migration_failures(self) -> list[str]:
        """Ids of rules a v1 -> v2 upgrade could not convert.

        Populated once, by `_MigratingStore._async_migrate_func`, during
        `async_load`. Empty for a store that was never migrated.
        """
        return list(self._store.migration_failures)

    @property
    def active_block(self) -> tuple[datetime, datetime] | None:
        """The (candle lighting, havdalah) pair of the block in force.

        The block itself is recomputable from these two instants, so only
        they are stored - `block.py` stays pure and out of the schema.
        """
        return self._active_block

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
        self._dry_run = data.get("dry_run", False)
        # Added after v1 shipped; absent in every store written before it.
        self._active_block = active_block_from_dict(data.get("active_block"))

    async def async_save(self) -> None:
        data = {
            "rules": [rule_to_dict(rule) for rule in self._rules],
            "defaults": self._defaults,
            "enabled": self._enabled,
            "dry_run": self._dry_run,
        }
        # Written only when there is one, so a store that never has an
        # active block keeps exactly the shape it has always had.
        if self._active_block is not None:
            data["active_block"] = active_block_to_dict(self._active_block)
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

    async def async_set_dry_run(self, value: bool) -> None:
        self._dry_run = value
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
