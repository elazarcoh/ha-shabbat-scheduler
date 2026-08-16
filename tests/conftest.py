"""Shared fixtures.

pytest-homeassistant-custom-component ships the `hass` fixture; custom
integrations are only loaded when `enable_custom_integrations` is requested.
"""

import pytest
from homeassistant.setup import async_setup_component


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Make the custom component importable in every test."""
    yield


@pytest.fixture
async def jerusalem(hass):
    """Pin the test instance to the real deployment timezone.

    The default test timezone is US/Pacific, which silently shifts every date
    calculation in this integration. Any test touching dates MUST use this.
    """
    await hass.config.async_set_time_zone("Asia/Jerusalem")
    return hass


@pytest.fixture
async def test_booleans(hass):
    """Real input_boolean entities with real turn_on/turn_off services.

    `hass.states.async_set` alone creates a state but no service, so calls
    would fail with ServiceNotFound. Setting the component up gives genuine
    end-to-end behaviour against throwaway entities rather than appliances.
    """
    await async_setup_component(
        hass,
        "input_boolean",
        {"input_boolean": {"t": {"name": "T"}, "salon": {"name": "Salon"}}},
    )
    await hass.async_block_till_done()
    return hass
