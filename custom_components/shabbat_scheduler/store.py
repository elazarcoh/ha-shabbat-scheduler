"""Persistence of the rule set in Home Assistant's .storage.

.storage is the source of truth; YAML is only ever an import/export view.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime, time

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import STORAGE_KEY, STORAGE_VERSION
from .models import Action, Rule


def rule_to_dict(rule: Rule) -> dict:
    """Serialise a rule for storage."""
    return {
        "id": rule.id,
        "profile": rule.profile,
        "day": rule.day,
        "time": rule.time.isoformat(),
        "action": rule.action.value,
        "devices": list(rule.devices),
        "settings": dict(rule.settings),
        "name": rule.name,
        "icon": rule.icon,
        "enabled": rule.enabled,
        "script": rule.script,
        "variables": dict(rule.variables),
        "replay_on_restart": rule.replay_on_restart,
        "color": rule.color,
    }


def rule_from_dict(data: dict) -> Rule:
    """Deserialise a stored rule."""
    return Rule(
        id=data["id"],
        profile=int(data["profile"]),
        day=str(data["day"]),
        time=time.fromisoformat(data["time"]),
        action=Action(data["action"]),
        devices=tuple(data.get("devices", ())),
        settings=dict(data.get("settings", {})),
        name=data.get("name"),
        icon=data.get("icon"),
        enabled=data.get("enabled", True),
        script=data.get("script"),
        variables=dict(data.get("variables", {})),
        replay_on_restart=data.get("replay_on_restart", False),
        color=data.get("color"),
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


class RuleStore:
    """Loads, mutates and persists the rule set."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._store: Store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
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
