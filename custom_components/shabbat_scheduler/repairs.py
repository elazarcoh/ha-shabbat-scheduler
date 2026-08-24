"""Repair issues surfaced by the Shabbat Scheduler.

Both issues here are ``is_fixable=False``: nothing in this integration can
correct a misnamed Jewish Calendar entity or resurrect a v1 rule a
v1 -> v2 migration could not translate. The point is only that the user is
told, in the one place they are guaranteed to look (Settings > Repairs),
instead of a log line during the one week nobody is reading logs.
"""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN

ISSUE_ZMANIM_SENSOR_MISSING = "zmanim_sensor_missing"
ISSUE_UNMIGRATED_RULES = "unmigrated_rules"


def async_create_zmanim_issue(
    hass: HomeAssistant, candle_sensor: str, havdalah_sensor: str
) -> None:
    """The configured zmanim sensors cannot be read right now.

    Names the entity ids actually configured, not the Jewish Calendar
    defaults - the whole point is that a second Jewish Calendar entry, or
    one simply renamed, does not share those defaults.
    """
    ir.async_create_issue(
        hass,
        DOMAIN,
        ISSUE_ZMANIM_SENSOR_MISSING,
        is_fixable=False,
        severity=ir.IssueSeverity.ERROR,
        translation_key=ISSUE_ZMANIM_SENSOR_MISSING,
        translation_placeholders={
            "candle_sensor": candle_sensor,
            "havdalah_sensor": havdalah_sensor,
        },
    )


def async_delete_zmanim_issue(hass: HomeAssistant) -> None:
    """Clear it the moment both sensors are readable again."""
    ir.async_delete_issue(hass, DOMAIN, ISSUE_ZMANIM_SENSOR_MISSING)


def async_create_unmigrated_rules_issue(hass: HomeAssistant, rule_ids: list[str]) -> None:
    """Some v1 rules survived migration only as disabled, unconvertible stubs.

    Task 5's keep-disable-report machinery stashes the original rule and the
    reason on each one (``rule.migration_error``); this is where the user is
    actually told to go look, naming which rules by id so they do not have
    to hunt through the whole rule set to find the ones that need attention.
    """
    ir.async_create_issue(
        hass,
        DOMAIN,
        ISSUE_UNMIGRATED_RULES,
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key=ISSUE_UNMIGRATED_RULES,
        translation_placeholders={"rule_ids": ", ".join(rule_ids)},
    )
