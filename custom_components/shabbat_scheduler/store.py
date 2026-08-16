"""Persistence of the rule set in Home Assistant's .storage.

.storage is the source of truth; YAML is only ever an import/export view.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import time

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

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


class RuleStore:
    """Loads, mutates and persists the rule set."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._store: Store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._rules: list[Rule] = []
        self._defaults: dict = {}
        self._enabled: bool = False
        self._dry_run: bool = False

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

    async def async_load(self) -> None:
        data = await self._store.async_load() or {}
        self._rules = [rule_from_dict(item) for item in data.get("rules", [])]
        self._defaults = data.get("defaults", {})
        # Master switch defaults OFF so a fresh install cannot act.
        self._enabled = data.get("enabled", False)
        self._dry_run = data.get("dry_run", False)

    async def async_save(self) -> None:
        await self._store.async_save(
            {
                "rules": [rule_to_dict(rule) for rule in self._rules],
                "defaults": self._defaults,
                "enabled": self._enabled,
                "dry_run": self._dry_run,
            }
        )

    async def async_set_enabled(self, value: bool) -> None:
        self._enabled = value
        await self.async_save()

    async def async_set_dry_run(self, value: bool) -> None:
        self._dry_run = value
        await self.async_save()

    async def async_add(self, rule: Rule) -> None:
        self._rules.append(rule)
        await self.async_save()

    async def async_update(self, rule_id: str, **changes) -> None:
        self._rules = [
            replace(rule, **changes) if rule.id == rule_id else rule
            for rule in self._rules
        ]
        await self.async_save()

    async def async_delete(self, rule_id: str) -> None:
        self._rules = [rule for rule in self._rules if rule.id != rule_id]
        await self.async_save()

    async def async_replace_all(self, defaults: dict, rules: list[Rule]) -> None:
        self._defaults = dict(defaults)
        self._rules = list(rules)
        await self.async_save()
