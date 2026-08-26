"""The diagnostics platform - what 'Download diagnostics' actually sends."""

from datetime import time

import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
)

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
    assert result["dry_run"] is False
    assert "migration_failures" in result
    assert result["migration_failures"] == []


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

    dumped = str(result)
    assert "master_bedroom" not in dumped
    assert "temperature" not in dumped or "22" not in dumped


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
