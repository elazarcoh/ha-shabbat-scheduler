"""Turning one authored action into the service calls to actually make.

Almost nothing belongs here. The integration's job is to decide WHEN
something happens; Home Assistant decides what. This module exists for
the single exception documented below, and stays free of Home Assistant
so that exception is testable without an instance.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_CLIMATE_SET_TEMPERATURE = "climate.set_temperature"
_CLIMATE_SET_HVAC_MODE = "climate.set_hvac_mode"
_HVAC_MODE = "hvac_mode"


def expand_action(action: str, data: dict) -> list[tuple[str, dict]]:
    """The calls one authored action becomes. Usually itself.

    THE ONE COMPATIBILITY SHIM. `climate.set_temperature` carrying an
    `hvac_mode` is split into `set_hvac_mode` then `set_temperature`,
    because several climate integrations - the `aux_cloud` units this was
    written for among them - intermittently fail to power on when both
    arrive together. The most-used third-party scheduler in the ecosystem
    hardcodes the same split for the same reason, which is the evidence
    that this is a real hardware quirk and not this project's special
    case.

    An author writes the one natural action; this makes it work. Every
    other action passes through untouched, and no other domain knowledge
    belongs in this file.
    """
    if action != _CLIMATE_SET_TEMPERATURE or _HVAC_MODE not in data:
        return [(action, data)]

    rest = {key: value for key, value in data.items() if key != _HVAC_MODE}
    return [
        (_CLIMATE_SET_HVAC_MODE, {_HVAC_MODE: data[_HVAC_MODE]}),
        (_CLIMATE_SET_TEMPERATURE, rest),
    ]


# --- Deprecated: dead climate-planner remnant, kept only to import -------
#
# `engine.py` still does `from .device_ops import Skip, plan_calls` at
# module level, and `__init__.py` imports `engine` at module level too -
# deleting these here would make the whole package unimportable and every
# test in the repo uncollectable, per the plan's standing rule (a task may
# break behaviour, never importability). `engine.py`'s caller already
# passes `rule.action` as a plain string where this expects the old
# `Action` enum, so it is not functionally reachable in a working state
# today regardless. Task 6 replaces `_apply_device` with a path built on
# `expand_action` above and deletes this stub along with the import.
@dataclass(frozen=True)
class Skip:
    """Superseded by `expand_action`'s plain pass-through. See Task 6."""

    attribute: str
    requested: Any = None
    reason: str = ""


def plan_calls(*_args, **_kwargs):
    """Superseded by `expand_action`. See Task 6."""
    raise NotImplementedError(
        "plan_calls was removed in Task 2 (climate execution planner is "
        "gone); engine.py's caller is rewritten against expand_action in "
        "Task 6"
    )
