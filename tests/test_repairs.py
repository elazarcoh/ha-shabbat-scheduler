"""Repair issues: the point of Task 10, not decoration.

v1 hardcoded the zmanim sensors and, when they could not be read, logged a
warning and scheduled nothing - invisible unless someone went looking in
the log on the one day they cannot. And a v1 -> v2 migration can leave
rules behind, kept only as disabled stubs (Task 5's keep-disable-report
machinery); this is where the user is actually told to go look.
"""

from dataclasses import replace

from homeassistant.helpers.issue_registry import async_get as async_get_issue_registry
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.shabbat_scheduler.const import (
    DEFAULT_CANDLE_SENSOR,
    DEFAULT_HAVDALAH_SENSOR,
    DOMAIN,
)
from custom_components.shabbat_scheduler.engine import ShabbatEngine
from custom_components.shabbat_scheduler.repairs import (
    ISSUE_SPLIT_RULES,
    ISSUE_UNMIGRATED_RULES,
    ISSUE_ZMANIM_SENSOR_MISSING,
)
from custom_components.shabbat_scheduler.store import RuleStore

V1_SIMPLE_ON = {
    "id": "b", "profile": 1, "day": "erev", "time": "22:00:00", "action": "on",
    "devices": ["switch.boiler"], "settings": {},
}
V1_CUSTOM_NO_SCRIPT = {
    "id": "d", "profile": 1, "day": "1", "time": "17:00:00", "action": "custom",
    "script": None, "variables": {"minutes": 30},
}


async def test_a_missing_sensor_raises_a_repair_issue(hass, jerusalem):
    """v1 logged a warning and scheduled nothing - invisible unless you
    went looking in the log on the one day you cannot."""
    store = RuleStore(hass)
    await store.async_load()
    engine = ShabbatEngine(hass, store)

    await engine.async_refresh()

    issues = async_get_issue_registry(hass)
    issue = issues.async_get_issue(DOMAIN, ISSUE_ZMANIM_SENSOR_MISSING)
    assert issue is not None
    assert issue.is_fixable is False
    assert issue.severity == "error"


async def test_the_zmanim_issue_names_the_configured_entities(hass, jerusalem):
    """Named after what is actually configured, not the Jewish Calendar's
    own defaults - the whole point of a second, differently-named entry."""
    store = RuleStore(hass)
    await store.async_load()
    engine = ShabbatEngine(
        hass,
        store,
        candle_sensor="sensor.jc_home_upcoming_candle_lighting",
        havdalah_sensor="sensor.jc_home_upcoming_havdalah",
    )

    await engine.async_refresh()

    issues = async_get_issue_registry(hass)
    issue = issues.async_get_issue(DOMAIN, ISSUE_ZMANIM_SENSOR_MISSING)
    assert issue is not None
    assert issue.translation_placeholders["candle_sensor"] == (
        "sensor.jc_home_upcoming_candle_lighting"
    )
    assert issue.translation_placeholders["havdalah_sensor"] == (
        "sensor.jc_home_upcoming_havdalah"
    )


async def test_the_zmanim_issue_clears_once_both_sensors_are_readable(hass, jerusalem):
    store = RuleStore(hass)
    await store.async_load()
    engine = ShabbatEngine(hass, store)
    await engine.async_refresh()

    issues = async_get_issue_registry(hass)
    assert issues.async_get_issue(DOMAIN, ISSUE_ZMANIM_SENSOR_MISSING) is not None

    hass.states.async_set(DEFAULT_CANDLE_SENSOR, "2026-08-14T15:44:00+00:00")
    hass.states.async_set(DEFAULT_HAVDALAH_SENSOR, "2026-08-15T17:01:00+00:00")
    await engine.async_refresh()

    assert issues.async_get_issue(DOMAIN, ISSUE_ZMANIM_SENSOR_MISSING) is None


async def test_migration_failures_raise_a_repair_issue(hass, hass_storage):
    """Naming the rules, so the user knows what to look at."""
    hass_storage["shabbat_scheduler.rules"] = {
        "version": 1,
        "minor_version": 1,
        "key": "shabbat_scheduler.rules",
        "data": {
            "rules": [V1_SIMPLE_ON, V1_CUSTOM_NO_SCRIPT],
            "defaults": {},
        },
    }

    entry = MockConfigEntry(domain=DOMAIN, title="Shabbat Scheduler")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    issues = async_get_issue_registry(hass)
    issue = issues.async_get_issue(DOMAIN, ISSUE_UNMIGRATED_RULES)
    assert issue is not None
    assert issue.is_fixable is False
    assert "d" in issue.translation_placeholders["rule_ids"]
    assert "b" not in issue.translation_placeholders["rule_ids"].split(", ")


async def test_no_migration_issue_when_nothing_failed(hass):
    """A store that never went through a migration must not be flagged."""
    entry = MockConfigEntry(domain=DOMAIN, title="Shabbat Scheduler")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    issues = async_get_issue_registry(hass)
    assert issues.async_get_issue(DOMAIN, ISSUE_UNMIGRATED_RULES) is None


async def test_the_unmigrated_issue_is_persistent(hass, hass_storage):
    """Without `is_persistent`, Home Assistant reloads the issue with
    `active=False` and the repairs websocket API filters inactive issues
    out - so the one place the user was told disappears on restart.
    """
    hass_storage["shabbat_scheduler.rules"] = {
        "version": 1, "minor_version": 1, "key": "shabbat_scheduler.rules",
        "data": {"rules": [V1_CUSTOM_NO_SCRIPT], "defaults": {}},
    }
    entry = MockConfigEntry(domain=DOMAIN, title="Shabbat Scheduler")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    issue = async_get_issue_registry(hass).async_get_issue(
        DOMAIN, ISSUE_UNMIGRATED_RULES
    )
    assert issue is not None
    assert issue.is_persistent is True


async def test_the_unmigrated_issue_is_re_raised_on_a_later_setup(hass, hass_storage):
    """The migration runs ONCE, ever.

    `store.migration_failures` is populated only inside the store's
    `_async_migrate_func`, which Home Assistant calls only while the stored
    version is behind. Deriving the issue from it meant the user was told
    on the upgrade and never again, while the rules sat there permanently
    inert. Derive it from the store's CURRENT contents instead.
    """
    hass_storage["shabbat_scheduler.rules"] = {
        "version": 1, "minor_version": 1, "key": "shabbat_scheduler.rules",
        "data": {"rules": [V1_SIMPLE_ON, V1_CUSTOM_NO_SCRIPT], "defaults": {}},
    }
    entry = MockConfigEntry(domain=DOMAIN, title="Shabbat Scheduler")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    issues = async_get_issue_registry(hass)
    assert issues.async_get_issue(DOMAIN, ISSUE_UNMIGRATED_RULES) is not None

    # Second setup: the store is already at version 2, so nothing migrates
    # and `migration_failures` is empty - but rule "d" is still broken.
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    issues.async_delete(DOMAIN, ISSUE_UNMIGRATED_RULES)
    assert issues.async_get_issue(DOMAIN, ISSUE_UNMIGRATED_RULES) is None

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    issue = issues.async_get_issue(DOMAIN, ISSUE_UNMIGRATED_RULES)
    assert issue is not None
    assert "d" in issue.translation_placeholders["rule_ids"]


async def test_the_unmigrated_issue_clears_once_the_rules_are_repaired(
    hass, hass_storage
):
    """Deferred minor #5: it was raised once and never cleared.

    A user who deletes or re-authors the broken rules had no way to make
    the warning go away, which trains people to ignore Repairs.
    """
    hass_storage["shabbat_scheduler.rules"] = {
        "version": 1, "minor_version": 1, "key": "shabbat_scheduler.rules",
        "data": {"rules": [V1_SIMPLE_ON, V1_CUSTOM_NO_SCRIPT], "defaults": {}},
    }
    entry = MockConfigEntry(domain=DOMAIN, title="Shabbat Scheduler")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    issues = async_get_issue_registry(hass)
    assert issues.async_get_issue(DOMAIN, ISSUE_UNMIGRATED_RULES) is not None

    store = hass.data[DOMAIN][entry.entry_id]["store"]
    keep = [rule for rule in store.rules if rule.migration_error is None]
    await store.async_replace_all(store.defaults, keep)
    await hass.async_block_till_done()

    assert issues.async_get_issue(DOMAIN, ISSUE_UNMIGRATED_RULES) is None


async def test_a_yaml_round_trip_no_longer_destroys_the_repair_warning(
    hass, hass_storage
):
    """I4, end to end through the real services.

    The documented recovery route is export -> edit -> import, and
    `import_yaml` calls `async_replace_all` with the WHOLE rule set. While
    the export omitted `migration_error`/`migration_source` and the import
    stripped both, following that advice deleted the stashed v1 payload
    permanently AND cleared the flag this issue is derived from - so the
    warning vanished and the rule was left a disabled stub pointing at a
    service that does not exist, with nothing anywhere saying why.
    """
    hass_storage["shabbat_scheduler.rules"] = {
        "version": 1, "minor_version": 1, "key": "shabbat_scheduler.rules",
        "data": {"rules": [V1_SIMPLE_ON, V1_CUSTOM_NO_SCRIPT], "defaults": {}},
    }
    entry = MockConfigEntry(domain=DOMAIN, title="Shabbat Scheduler")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    issues = async_get_issue_registry(hass)
    assert issues.async_get_issue(DOMAIN, ISSUE_UNMIGRATED_RULES) is not None

    exported = await hass.services.async_call(
        DOMAIN, "export_yaml", {}, blocking=True, return_response=True
    )
    # The documented inspection route: the original v1 rule is IN the dump.
    assert "migration_source" in exported["yaml"]
    assert "script" in exported["yaml"]

    await hass.services.async_call(
        DOMAIN, "import_yaml", {"yaml": exported["yaml"]}, blocking=True
    )
    await hass.async_block_till_done()

    issue = issues.async_get_issue(DOMAIN, ISSUE_UNMIGRATED_RULES)
    assert issue is not None, "the round trip deleted the only warning"
    assert "d" in issue.translation_placeholders["rule_ids"]

    store = hass.data[DOMAIN][entry.entry_id]["store"]
    stub = next(rule for rule in store.rules if rule.id == "d")
    assert stub.migration_error == "a custom rule with no script has nothing to call"
    assert stub.migration_source == V1_CUSTOM_NO_SCRIPT
    assert stub.enabled is False
    # And it survives the write to .storage, not just the in-memory swap.
    reloaded = RuleStore(hass)
    await reloaded.async_load()
    assert next(r for r in reloaded.rules if r.id == "d").migration_source == (
        V1_CUSTOM_NO_SCRIPT
    )


# --- A split rule changed the rule COUNT; the user has to be told ---------
#     A v1 mixed-domain rule becomes one v2 rule per domain (see
#     migration._domain_parts). That is the only place this migration alters
#     something the user counts, and a rule count changing under someone
#     silently is the shape of thing this project exists to avoid.


V1_MIXED = {
    "id": "e", "profile": 1, "day": "1", "time": "12:00:00", "action": "on",
    "devices": ["climate.salon", "switch.boiler"],
    "settings": {"temperature": 26},
}


async def _setup_v1(hass, hass_storage, rules, defaults=None):
    hass_storage["shabbat_scheduler.rules"] = {
        "version": 1, "minor_version": 1, "key": "shabbat_scheduler.rules",
        "data": {"rules": rules, "defaults": defaults or {}},
    }
    entry = MockConfigEntry(domain=DOMAIN, title="Shabbat Scheduler")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_a_split_rule_raises_a_repair_issue_naming_both_halves(
    hass, hass_storage
):
    """Named, and named with the ORIGINAL id, or the user cannot tell which
    of their rules turned into which pair."""
    await _setup_v1(hass, hass_storage, [V1_MIXED])

    issue = async_get_issue_registry(hass).async_get_issue(
        DOMAIN, ISSUE_SPLIT_RULES
    )
    assert issue is not None
    described = issue.translation_placeholders["rules"]
    assert "e" in described
    assert "e-climate" in described and "e-switch" in described
    # It describes durable stored state, so it must survive a restart the
    # way the unmigrated-rules issue has to.
    assert issue.is_persistent is True
    assert issue.is_fixable is False


async def test_the_split_issue_is_not_raised_when_nothing_was_split(
    hass, hass_storage
):
    await _setup_v1(hass, hass_storage, [V1_SIMPLE_ON])

    issues = async_get_issue_registry(hass)
    assert issues.async_get_issue(DOMAIN, ISSUE_SPLIT_RULES) is None


async def test_the_split_issue_survives_a_restart(hass, hass_storage):
    """The I2 lesson, applied to the new issue: it must be derived from the
    STORE on every setup, not from the one-shot migration event."""
    entry = await _setup_v1(hass, hass_storage, [V1_MIXED])
    issues = async_get_issue_registry(hass)

    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    issues.async_delete(DOMAIN, ISSUE_SPLIT_RULES)
    # Second setup: the store is already at version 2, so nothing migrates.
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert issues.async_get_issue(DOMAIN, ISSUE_SPLIT_RULES) is not None


async def test_the_split_issue_clears_once_the_rules_are_re_authored(
    hass, hass_storage
):
    """It has no repair action - the split is correct and permanent - so the
    only ways out are Home Assistant's own dismiss and a YAML round trip
    that drops the stashed source. The second one must work, or this becomes
    an issue nobody can ever clear, in the same list as the zmanim error
    they must not learn to ignore."""
    entry = await _setup_v1(hass, hass_storage, [V1_MIXED])
    issues = async_get_issue_registry(hass)
    assert issues.async_get_issue(DOMAIN, ISSUE_SPLIT_RULES) is not None

    store = hass.data[DOMAIN][entry.entry_id]["store"]
    acknowledged = [
        replace(rule, migration_source=None) for rule in store.rules
    ]
    await store.async_replace_all(store.defaults, acknowledged)
    await hass.async_block_till_done()

    assert issues.async_get_issue(DOMAIN, ISSUE_SPLIT_RULES) is None


async def test_the_two_migration_issues_are_independent(hass, hass_storage):
    """A mixed rule with one unsupported half raises BOTH: the working half
    was restructured, the other half never worked. Each issue tells its own
    half, and neither hides the other."""
    mixed_with_a_lock = {
        "id": "m", "profile": 1, "day": "1", "time": "12:00:00", "action": "on",
        "devices": ["climate.salon", "lock.front"],
        "settings": {"temperature": 26},
    }
    await _setup_v1(hass, hass_storage, [mixed_with_a_lock])

    issues = async_get_issue_registry(hass)
    split = issues.async_get_issue(DOMAIN, ISSUE_SPLIT_RULES)
    unmigrated = issues.async_get_issue(DOMAIN, ISSUE_UNMIGRATED_RULES)
    assert split is not None
    assert "m-climate" in split.translation_placeholders["rules"]
    assert unmigrated is not None
    assert "m-lock" in unmigrated.translation_placeholders["rule_ids"]
