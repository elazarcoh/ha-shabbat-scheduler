"""Pure translation of a desired state into the service calls needed.

Nothing here talks to Home Assistant; the engine executes what this returns.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .const import FAN_SYNONYMS
from .models import Action

_SIMPLE_DOMAINS = ("switch", "light", "input_boolean", "fan")


@dataclass(frozen=True)
class Call:
    """One service call, annotated for change reporting."""

    domain: str
    service: str
    data: dict = field(default_factory=dict)
    attribute: str = ""
    from_value: Any = None
    to_value: Any = None


def resolve_fan_mode(requested: str, supported: list[str]) -> str | None:
    """Map a requested fan mode onto one this device actually exposes."""
    if requested in supported:
        return requested
    for candidate in FAN_SYNONYMS.get(requested, ()):
        if candidate in supported:
            return candidate
    return None


def plan_calls(
    entity_id: str,
    current_state: str,
    current_attrs: dict,
    action: Action,
    settings: dict,
    force: bool,
) -> list[Call]:
    """Return only the calls whose values genuinely differ.

    `force` is set by the caller when the reading cannot be trusted (unknown,
    unavailable, or older than our last command), in which case everything is
    re-sent rather than skipped.
    """
    domain = entity_id.split(".", 1)[0]

    if domain == "climate":
        return _plan_climate(current_state, current_attrs, action, settings, force)

    if domain in _SIMPLE_DOMAINS:
        service = "turn_on" if action is Action.ON else "turn_off"
        wanted = "on" if action is Action.ON else "off"
        if not force and current_state == wanted:
            return []
        return [
            Call(
                domain=domain,
                service=service,
                data={"entity_id": entity_id},
                attribute="state",
                from_value=current_state,
                to_value=wanted,
            )
        ]

    return []


def _plan_climate(
    current_state: str,
    attrs: dict,
    action: Action,
    settings: dict,
    force: bool,
) -> list[Call]:
    if action is Action.OFF:
        if not force and current_state == "off":
            return []
        return [
            Call(
                domain="climate",
                service="turn_off",
                attribute="state",
                from_value=current_state,
                to_value="off",
            )
        ]

    calls: list[Call] = []

    hvac_mode = settings.get("hvac_mode")
    if hvac_mode is not None and (force or current_state != hvac_mode):
        calls.append(
            Call(
                domain="climate",
                service="set_hvac_mode",
                data={"hvac_mode": hvac_mode},
                attribute="hvac_mode",
                from_value=current_state,
                to_value=hvac_mode,
            )
        )

    temperature = settings.get("temperature")
    if temperature is not None and (force or attrs.get("temperature") != temperature):
        calls.append(
            Call(
                domain="climate",
                service="set_temperature",
                data={"temperature": temperature},
                attribute="temperature",
                from_value=attrs.get("temperature"),
                to_value=temperature,
            )
        )

    fan_mode = settings.get("fan_mode")
    if fan_mode is not None:
        actual = resolve_fan_mode(fan_mode, list(attrs.get("fan_modes", [])))
        if actual is None:
            # Unsupported everywhere - skip this sub-call, never fail the rule.
            return calls
        if force or attrs.get("fan_mode") != actual:
            calls.append(
                Call(
                    domain="climate",
                    service="set_fan_mode",
                    data={"fan_mode": actual},
                    attribute="fan_mode",
                    from_value=attrs.get("fan_mode"),
                    to_value=actual,
                )
            )

    return calls
