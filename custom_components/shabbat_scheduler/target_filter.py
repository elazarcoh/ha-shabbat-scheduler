"""Which entities an action can act on, from Home Assistant's own descriptions.

Home Assistant skips a targeted entity an action cannot handle (for example
`input_boolean.turn_on` on a `switch`) and only logs a warning, so the call
"succeeds" having done nothing. Every action's description declares which
entities it takes (`target: {entity: [{domain: [...], integration: ...}]}`);
HA's own target picker filters on the same data. This module reads it.

Only `domain` and `integration` are checked, the two things the call itself
filters on silently. Device classes and supported features are left alone.
When a description is missing, or has no entity filter (`homeassistant.*`
takes anything), every entity is accepted: unknown never means wrong.

Kept identical in ha-sequence-scheduler and ha-shabbat-scheduler.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import service as service_helper

_LOGGER = logging.getLogger(__name__)


async def async_load_descriptions(hass: HomeAssistant) -> None:
    """Fill HA's description cache so the sync functions below can use it.

    Cheap after the first call (HA caches per action); the frontend's
    `get_services` fills the same cache. Never raises: an integration whose
    descriptions can't load leaves its actions unchecked, not the caller
    broken.
    """
    try:
        await service_helper.async_get_all_descriptions(hass)
    except Exception:  # noqa: BLE001 - a check that can't load must not block saving
        _LOGGER.warning("Could not load action descriptions; targets go unchecked", exc_info=True)


def entity_filters(hass: HomeAssistant, action: str) -> list[dict[str, Any]] | None:
    """The action's entity filters, or None when anything goes (or nobody knows)."""
    domain, _, service = action.lower().partition(".")
    description = service_helper.async_get_cached_service_description(hass, domain, service)
    if not description:
        return None
    target = description.get("target")
    if not isinstance(target, dict):
        return None
    entity = target.get("entity")
    filters = entity if isinstance(entity, list) else [entity] if isinstance(entity, dict) else []
    filters = [f for f in filters if isinstance(f, dict)]
    if not filters or any(not _checked(f) for f in filters):
        return None
    return filters


def _checked(f: dict[str, Any]) -> bool:
    return bool(f.get("domain") or f.get("integration"))


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    return [value] if isinstance(value, str) else list(value)


def _matches(hass: HomeAssistant, f: dict[str, Any], entity_id: str) -> bool:
    domains = _as_list(f.get("domain"))
    if domains and entity_id.partition(".")[0] not in domains:
        return False
    integration = f.get("integration")
    if integration:
        entry = er.async_get(hass).async_get(entity_id)
        # Not in the registry: the platform is unknown, so don't call it wrong.
        if entry is not None and entry.platform != integration:
            return False
    return True


def accepts(hass: HomeAssistant, action: str, entity_id: str) -> bool:
    """Can `action` act on `entity_id`? True when it can't be told.

    A `group.` entity is always accepted: an entity action expands an old
    style group into its members before filtering, so naming one is fine
    and its members are what get checked.
    """
    if entity_id.startswith("group."):
        return True
    filters = entity_filters(hass, action)
    return filters is None or any(_matches(hass, f, entity_id) for f in filters)


def rejected(hass: HomeAssistant, action: str, entity_ids: Iterable[str]) -> list[str]:
    """The entities `action` would skip, sorted."""
    return sorted(e for e in set(entity_ids) if not accepts(hass, action, e))


def describe(hass: HomeAssistant, action: str, entity_ids: Iterable[str]) -> str:
    """'input_boolean.turn_on can't act on switch.x; use switch.turn_on'."""
    bad = sorted(set(entity_ids))
    text = f"{action} can't act on {', '.join(bad)}"
    filters = entity_filters(hass, action) or []
    takes = sorted({d for f in filters for d in _as_list(f.get("domain"))})
    if takes:
        text += f" (it takes {', '.join(takes)} entities)"
    fixes = sorted({s for e in bad if (s := suggestion(hass, action, e))})
    if fixes:
        text += f"; use {' / '.join(fixes)}"
    return text


def suggestion(hass: HomeAssistant, action: str, entity_id: str) -> str | None:
    """The same action in the entity's own domain, if it exists and fits."""
    service = action.lower().partition(".")[2]
    candidate = f"{entity_id.partition('.')[0]}.{service}"
    if candidate == action.lower() or not hass.services.has_service(*candidate.split(".")):
        return None
    return candidate if accepts(hass, candidate, entity_id) else None
