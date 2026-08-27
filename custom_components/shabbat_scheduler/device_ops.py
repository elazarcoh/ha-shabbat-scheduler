"""Turning one authored action into the service calls to actually make.

Almost nothing belongs here. The integration's job is to decide WHEN
something happens; Home Assistant decides what. This module exists for
the single exception documented below, and stays free of Home Assistant
so that exception is testable without an instance.
"""

from __future__ import annotations

import logging

# stdlib only - this module imports zero Home Assistant, by constraint.
_LOGGER = logging.getLogger(__name__)

_CLIMATE_SET_TEMPERATURE = "climate.set_temperature"
_CLIMATE_SET_HVAC_MODE = "climate.set_hvac_mode"
_CLIMATE_SET_FAN_MODE = "climate.set_fan_mode"
_HVAC_MODE = "hvac_mode"
_FAN_MODE = "fan_mode"


def expand_action(action: str, data: dict) -> list[tuple[str, dict]]:
    """The calls one authored action becomes. Usually itself.

    THE ONE COMPATIBILITY SHIM. `climate.set_temperature` carrying an
    `hvac_mode` and/or a `fan_mode` is split into up to three calls, in
    order - `set_hvac_mode`, `set_temperature`, `set_fan_mode` - for THREE
    separate reasons, and keeping them apart is the point: anyone later
    deciding whether this shim can be deleted needs to know which parts
    Home Assistant forces and which are a hardware quirk that could
    outlive any schema change. `docs/known-behaviours.md` quotes the real
    `SET_TEMPERATURE_SCHEMA` in full.

    1. `fan_mode` is peeled off because the schema genuinely rejects it.
       It names no key at all in `SET_TEMPERATURE_SCHEMA`, and
       `make_entity_service_schema` defaults to PREVENT_EXTRA, so the
       combined call is refused with "extra keys not allowed" - HA's own
       validator, not a hardware opinion. It was a first-class v1 feature
       (how one unit gets `silent` and another `quiet`), so it gets its
       own call rather than being dropped.
    2. `hvac_mode` is peeled off for a HARDWARE reason, not a schema one.
       `vol.Optional(ATTR_HVAC_MODE)` is right there in
       `SET_TEMPERATURE_SCHEMA` - HA would accept it alongside a
       temperature perfectly happily. It is split anyway because several
       climate integrations, the `aux_cloud` units this was written for
       among them, intermittently fail to power on when mode and
       temperature arrive in one call. The ecosystem's most-used
       third-party scheduler hardcodes the identical split, which is the
       evidence this is a real shared quirk and not this project's
       special case.
    3. `set_temperature` is only emitted if at least one key besides
       `hvac_mode`/`fan_mode` remains, because
       `cv.has_at_least_one_key(temperature, target_temp_high,
       target_temp_low)` rejects the empty `{}` the other way - "must
       contain at least one of...". Emitting a call guaranteed to fail
       would only produce a retry storm and a notification.

    Any key this shim does not recognise (`swing_mode`, `humidity`, a
    future addition) rides along on the `set_temperature` call rather than
    being silently dropped - the same outcome as if hvac_mode/fan_mode
    were absent and no split happened at all, so HA rejects it loudly
    instead of it vanishing with no trace.

    A NULL `hvac_mode`/`fan_mode` is the one exception to that paragraph,
    and it follows from reason 3 rather than contradicting it. A null is not
    a mode: `set_hvac_mode` requires one, so peeling off
    `{hvac_mode: None}` emits a call that cannot succeed - the retry storm
    reason 3 exists to prevent - and leaving it on the `set_temperature`
    call is no better, because `SET_TEMPERATURE_SCHEMA` coerces it through
    `vol.Coerce(HVACMode)`, which a null fails, taking the temperature down
    with it. So a null mode neither splits nor rides along: it is dropped,
    and logged, because there is no v2 equivalent to v1's `Skip` channel for
    "asked for, cannot be done". This is not only a hypothetical author
    typo - a rule authored directly against the API or via YAML import can
    carry a null `hvac_mode`/`fan_mode` just as easily.

    An author writes the one natural action; this makes it work. Every
    other action passes through untouched, and no other domain knowledge
    belongs in this file.
    """
    if action != _CLIMATE_SET_TEMPERATURE:
        # Every other action passes through untouched, including a
        # directly-authored `set_hvac_mode` carrying a null: this shim owns
        # the split, not the payload of calls it did not invent.
        return [(action, data)]

    # Null modes are dropped BEFORE anything else looks at the payload, so
    # neither the split below nor the surviving `set_temperature` call can
    # carry one. Everything after this point can safely test key presence.
    for key in (_HVAC_MODE, _FAN_MODE):
        if key in data and data[key] is None:
            _LOGGER.warning(
                "%s carries a null %s, which is not a mode, so it has been "
                "dropped: set_%s requires a value, and leaving it on the "
                "set_temperature call would make Home Assistant refuse that "
                "call too.", action, key, key,
            )
    data = {
        key: value
        for key, value in data.items()
        if value is not None or key not in (_HVAC_MODE, _FAN_MODE)
    }

    if _HVAC_MODE not in data and _FAN_MODE not in data:
        # No split is needed. Note `data` can be EMPTY here, if the only keys
        # present were null modes - in which case this emits
        # `set_temperature {}` and Home Assistant refuses it. That is a known,
        # documented inconsistency with the mode-only case, not an oversight:
        # see "A mode-only null payload still emits a call Home Assistant
        # refuses" in docs/known-behaviours.md before changing it. Returning
        # `[]` is the obvious fix and is the wrong one today, because the
        # engine builds `last_run` from what this yields, so an empty
        # expansion would record the rule as fired having silently done
        # nothing - the defect class this project cares most about.
        return [(action, data)]

    calls: list[tuple[str, dict]] = []
    if _HVAC_MODE in data:
        calls.append((_CLIMATE_SET_HVAC_MODE, {_HVAC_MODE: data[_HVAC_MODE]}))
    temperature_data = {
        key: value for key, value in data.items() if key not in (_HVAC_MODE, _FAN_MODE)
    }
    if temperature_data:
        calls.append((_CLIMATE_SET_TEMPERATURE, temperature_data))
    if _FAN_MODE in data:
        calls.append((_CLIMATE_SET_FAN_MODE, {_FAN_MODE: data[_FAN_MODE]}))
    return calls
