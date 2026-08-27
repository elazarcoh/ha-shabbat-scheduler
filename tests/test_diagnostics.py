"""The diagnostics platform - what 'Download diagnostics' actually sends."""

from datetime import datetime, time
from zoneinfo import ZoneInfo

import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
)

from custom_components.shabbat_scheduler.const import DOMAIN
from custom_components.shabbat_scheduler.engine import build_outcome
from custom_components.shabbat_scheduler.models import Rule


async def test_diagnostics_report_the_rule_count_and_engine_state(
    hass, hass_client, setup_scheduler, jerusalem
):
    from pytest_homeassistant_custom_component.components.diagnostics import (
        get_diagnostics_for_config_entry,
    )

    entry = await setup_scheduler(
        rules=[
            Rule(id="r1", profile=1, day="1", time=time(11, 0),
                 action="input_boolean.turn_on",
                 target={"entity_id": ["input_boolean.t"]}),
        ],
        enabled=True,
    )
    await hass.async_block_till_done()

    result = await get_diagnostics_for_config_entry(hass, hass_client, entry)

    assert result["rule_count"] == 1
    assert result["enabled"] is True


async def test_diagnostics_do_not_include_rule_targets_or_data(
    hass, hass_client, setup_scheduler, jerusalem
):
    """The config entry holds no credentials, so nothing here is redacted -
    but a rule's own target/data is still someone's home layout, and
    diagnostics attached to a support request should not casually spell
    out every entity id in a person's house. Report SHAPE, not content."""
    from pytest_homeassistant_custom_component.components.diagnostics import (
        get_diagnostics_for_config_entry,
    )

    entry = await setup_scheduler(
        rules=[
            Rule(id="r1", profile=1, day="1", time=time(11, 0),
                 action="climate.set_temperature",
                 target={"entity_id": ["climate.master_bedroom"]},
                 data={"temperature": 22}),
        ],
        enabled=True,
    )
    await hass.async_block_till_done()

    result = await get_diagnostics_for_config_entry(hass, hass_client, entry)

    assert "master_bedroom" not in str(result)
    # By key, not by raw substring: "22" alone is fragile (any future
    # fixture date or id containing "22" would make this pass for the
    # wrong reason). Checking the rule shape directly proves the actual
    # guarantee - `data`'s VALUES never appear, only its KEYS do.
    rule_shape = result["rules"][0]
    assert "data" not in rule_shape
    assert rule_shape["data_keys"] == ["temperature"]


async def test_diagnostics_report_no_block_gracefully(
    hass, hass_client, setup_scheduler
):
    """`current_block` must resolve to either a plain dict or None, never
    raise. `setup_scheduler` publishes the two zmanim sensors
    unconditionally (see its body in conftest.py), so a block is in fact
    always computable here - this test's real assertion is "diagnostics
    reports whatever the engine has without blowing up," not "there is no
    block," which is why both shapes are accepted."""
    from pytest_homeassistant_custom_component.components.diagnostics import (
        get_diagnostics_for_config_entry,
    )

    entry = await setup_scheduler()
    await hass.async_block_till_done()

    result = await get_diagnostics_for_config_entry(hass, hass_client, entry)

    assert result["current_block"] is None or isinstance(
        result["current_block"], dict
    )


async def test_diagnostics_report_outcome_shape_not_its_detail_text(
    hass, hass_client, setup_scheduler, jerusalem
):
    """`last_outcome` is a real gap fix: the docstring promised "last run"
    all along, but the field did not exist. Its `detail` text is free-form
    and can embed entity ids (see `build_outcome`'s docstring), so this
    proves the split actually holds: `outcome`/`at`/`has_detail` (safe)
    come through, the raw `detail` string (unsafe) never does."""
    from pytest_homeassistant_custom_component.components.diagnostics import (
        get_diagnostics_for_config_entry,
    )

    entry = await setup_scheduler(
        rules=[
            Rule(id="r1", profile=1, day="1", time=time(11, 0),
                 action="input_boolean.turn_on",
                 target={"entity_id": ["input_boolean.t"]}),
        ],
        enabled=True,
    )
    await hass.async_block_till_done()

    store = hass.data[DOMAIN][entry.entry_id]["store"]
    at = datetime(2026, 8, 15, 11, 0, tzinfo=ZoneInfo("Asia/Jerusalem"))
    await store.async_record_outcome(
        "r1",
        build_outcome(
            "blocked", at,
            "condition 1 of 1 (state on input_boolean.secret_bedroom_light) "
            "not met",
        ),
    )

    result = await get_diagnostics_for_config_entry(hass, hass_client, entry)
    dumped = str(result)

    assert "input_boolean.secret_bedroom_light" not in dumped

    outcome = result["rules"][0]["last_outcome"]
    assert outcome["outcome"] == "blocked"
    assert outcome["at"] == at.isoformat()
    assert outcome["has_detail"] is True
    assert outcome["unknown_target_count"] == 0
    assert outcome["no_live_targets"] is False


async def test_diagnostics_do_not_include_the_real_rule_id(
    hass, hass_client, setup_scheduler, jerusalem
):
    """A rule's `id` is not always integration-generated - a hand-edited
    YAML import can carry a user-authored id, so it could name something
    personal. Diagnostics must report a positionally-stable stand-in
    instead of the real value."""
    from pytest_homeassistant_custom_component.components.diagnostics import (
        get_diagnostics_for_config_entry,
    )

    entry = await setup_scheduler(
        rules=[
            Rule(id="elazar_bedroom", profile=1, day="1", time=time(11, 0),
                 action="input_boolean.turn_on",
                 target={"entity_id": ["input_boolean.t"]}),
        ],
        enabled=True,
    )
    await hass.async_block_till_done()

    result = await get_diagnostics_for_config_entry(hass, hass_client, entry)
    dumped = str(result)

    assert "elazar_bedroom" not in dumped
    assert result["rules"][0]["id"] == "rule_0"
