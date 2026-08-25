"""Repair issues surfaced by the Shabbat Scheduler.

Every issue here is ``is_fixable=False``: nothing in this integration can
correct a misnamed Jewish Calendar entity, resurrect a v1 rule a v1 -> v2
migration could not translate, or un-split a rule that had to be split. The
point is only that the user is told, in the one place they are guaranteed to
look (Settings > Repairs), instead of a log line during the one week nobody
is reading logs.
"""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN

ISSUE_ZMANIM_SENSOR_MISSING = "zmanim_sensor_missing"
ISSUE_UNMIGRATED_RULES = "unmigrated_rules"
ISSUE_SPLIT_RULES = "split_rules"


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

    ``is_persistent`` is load-bearing, unlike on the zmanim issue above.
    Home Assistant reloads a non-persistent issue with ``active=False`` and
    the repairs websocket API filters inactive issues out, so without this
    the report vanished from Settings > Repairs on the first restart -
    turning the migration's promise of "kept, disabled and reported" into
    "kept and disabled", with the rules sitting there permanently inert.
    The zmanim issue can afford to be transient because it is re-raised
    from live sensor readings on every single refresh; this one describes
    durable stored state.
    """
    ir.async_create_issue(
        hass,
        DOMAIN,
        ISSUE_UNMIGRATED_RULES,
        is_fixable=False,
        is_persistent=True,
        severity=ir.IssueSeverity.WARNING,
        translation_key=ISSUE_UNMIGRATED_RULES,
        translation_placeholders={"rule_ids": ", ".join(rule_ids)},
    )


def async_delete_unmigrated_rules_issue(hass: HomeAssistant) -> None:
    """Clear it once no rule carries a migration error any more.

    Mirrors the zmanim pair: the caller derives the issue from the store's
    CURRENT contents on every setup and on every rule change, so deleting
    or re-authoring the broken rules makes the warning go away by itself.
    An issue the user cannot ever clear is an issue they learn to ignore,
    and this one shares Settings > Repairs with the zmanim error they must
    not learn to ignore.
    """
    ir.async_delete_issue(hass, DOMAIN, ISSUE_UNMIGRATED_RULES)


def async_create_split_rules_issue(hass: HomeAssistant, described: list[str]) -> None:
    """A v1 rule that spanned two domains became one v2 rule per domain.

    The migration's other reports are all about something being WRONG. This
    one is about something being different: the rules were converted
    correctly, and there are more of them than the user wrote, because v1
    drove a mixed-domain rule per entity and v2 is one rule per action (see
    `migration._domain_parts`). It is the only place this migration changes
    something the user counts, so it gets the same channel as everything
    else they need to know - a rule count changing in silence is the shape
    of thing this project exists to prevent.

    `described` is one entry per original rule, "e -> e-climate, e-switch",
    because the new ids alone would not tell anyone WHICH of their rules
    turned into which pair.

    Persistent, for the same reason as the unmigrated issue: it describes
    durable stored state, and a non-persistent issue comes back inactive
    after a restart and is filtered out of Settings > Repairs. There is
    nothing to fix here, so the ways out are Home Assistant's own dismiss
    and dropping the stashed `migration_source` (see the delete below).
    """
    ir.async_create_issue(
        hass,
        DOMAIN,
        ISSUE_SPLIT_RULES,
        is_fixable=False,
        is_persistent=True,
        severity=ir.IssueSeverity.WARNING,
        translation_key=ISSUE_SPLIT_RULES,
        translation_placeholders={"rules": "; ".join(described)},
    )


def async_delete_split_rules_issue(hass: HomeAssistant) -> None:
    """Clear it once no rule still carries the stash that marks a split.

    Derived from the store on every setup and every rule change, like the
    pair above, so it clears itself - the acknowledgement being a YAML round
    trip that drops `migration_source`, or deleting the rules. It has no
    repair ACTION, because the split is correct and permanent; what it must
    not be is an issue that can never go away, sitting in the same list as
    the zmanim error the user must not learn to ignore.
    """
    ir.async_delete_issue(hass, DOMAIN, ISSUE_SPLIT_RULES)
