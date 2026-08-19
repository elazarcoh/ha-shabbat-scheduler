"""The integration serves and registers its own card."""

from homeassistant.config_entries import ConfigEntryState
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.shabbat_scheduler.const import DOMAIN
from custom_components.shabbat_scheduler.frontend import CARD_URL


async def _setup(hass):
    await async_setup_component(hass, "lovelace", {})
    entry = MockConfigEntry(domain=DOMAIN, title="Shabbat Scheduler")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_the_card_is_registered_as_a_lovelace_resource(hass):
    await _setup(hass)

    urls = [
        item["url"] for item in hass.data[LOVELACE_DATA].resources.async_items()
    ]
    assert any(url.startswith(CARD_URL) for url in urls)


async def test_registering_twice_does_not_duplicate_the_resource(hass):
    """A reload must not leave the user with two copies of the card,
    which load twice and fight over the custom element name."""
    entry = await _setup(hass)
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    matching = [
        item
        for item in hass.data[LOVELACE_DATA].resources.async_items()
        if item["url"].startswith(CARD_URL)
    ]
    assert len(matching) == 1


async def test_the_resource_url_is_version_stamped(hass):
    """Otherwise a browser serves the old bundle from cache after an update."""
    await _setup(hass)

    url = next(
        item["url"]
        for item in hass.data[LOVELACE_DATA].resources.async_items()
        if item["url"].startswith(CARD_URL)
    )
    assert "?v=" in url


async def test_setup_survives_yaml_resource_mode(hass):
    """In YAML mode resources cannot be created programmatically. That must
    degrade to a log line, not a failed setup that takes the scheduler down
    with it - the schedule matters more than the card."""
    await async_setup_component(hass, "lovelace", {})
    hass.data[LOVELACE_DATA].resource_mode = "yaml"

    entry = MockConfigEntry(domain=DOMAIN, title="Shabbat Scheduler")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    # And the scheduler itself is fully up, not merely 'not errored'.
    assert hass.data[DOMAIN][entry.entry_id]["engine"] is not None
