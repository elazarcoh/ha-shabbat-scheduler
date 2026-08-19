"""The integration serves and registers its own card."""

from unittest.mock import patch

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


async def test_the_static_path_is_registered_exactly_once_across_a_reload(hass):
    """Pins the `_STATIC_REGISTERED` guard's actual behaviour.

    Home Assistant does not raise on a repeat `async_register_static_paths`
    call for the same path in 2026.8.2 (the http component patches its
    router to accept late registrations) - so a functional test has to
    count calls, not rely on an exception that will never come.
    """
    # `hass.http` only exists once the http component itself is set up;
    # normally that happens as a manifest dependency during entry setup,
    # too late to patch onto. Set it up explicitly first so there's
    # something to wrap.
    await async_setup_component(hass, "http", {})
    with patch.object(
        hass.http,
        "async_register_static_paths",
        wraps=hass.http.async_register_static_paths,
    ) as mock_register:
        entry = await _setup(hass)
        await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()

    assert mock_register.call_count == 1


async def test_an_unexpected_registration_error_does_not_fail_setup(hass):
    """Only the two anticipated branches (no Lovelace, YAML mode) are
    allowed to degrade gracefully by design; anything else - a bug in this
    integration, an HA internals change, whatever - must still not take
    the scheduler down. It drives real air conditioners on days nobody can
    operate them by hand."""
    await async_setup_component(hass, "lovelace", {})
    await async_setup_component(hass, "http", {})
    entry = MockConfigEntry(domain=DOMAIN, title="Shabbat Scheduler")
    entry.add_to_hass(hass)

    with patch.object(
        hass.http,
        "async_register_static_paths",
        side_effect=RuntimeError("boom"),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert hass.data[DOMAIN][entry.entry_id]["engine"] is not None


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


from pathlib import Path

from custom_components.shabbat_scheduler.frontend import (
    CARD_FILENAME,
    CARD_VERSION,
)

# Anchored to this file, not to the working directory: pytest is routinely
# invoked from somewhere other than the repo root (an editor's test runner,
# a CI step that cds into a subdirectory), and a cwd-relative path turns
# every bundle test below into a confusing FileNotFoundError there.
ROOT = Path(__file__).resolve().parent.parent
WWW = ROOT / "custom_components" / "shabbat_scheduler" / "www"


def test_the_built_bundle_is_committed():
    """A HACS user has no Node. The bundle must be in the repository."""
    bundle = WWW / CARD_FILENAME
    assert bundle.is_file()
    assert bundle.stat().st_size > 1000


def test_the_bundle_defines_the_card_element():
    """A stub that merely mentions the card's name is not a card. Require
    all five custom elements the card is built from, plus the actual
    browser registration call Lit's @customElement decorator compiles to
    (`customElements.define(...)`, stable under minification since it is a
    global-API property access, not a renameable local identifier)."""
    text = (WWW / CARD_FILENAME).read_text(encoding="utf-8")
    for tag in (
        "shabbat-scheduler-card",
        "shabbat-block-header",
        "shabbat-day-group",
        "shabbat-rule-row",
        "shabbat-warnings",
    ):
        assert tag in text
    assert "customElements.define" in text


def test_the_bundle_version_matches_the_url_stamp():
    """Otherwise the resource URL never changes and browsers keep serving
    a stale card out of cache after an update. Ties the check to the actual
    `const CARD_VERSION = '...'` declaration rollup carries over verbatim
    from frontend/src/version.ts, so a drift between that file and this
    module's CARD_VERSION is caught - and requires the real registration
    call too, so a stub that merely echoes the version string cannot pass."""
    text = (WWW / CARD_FILENAME).read_text(encoding="utf-8")
    assert f"const CARD_VERSION = '{CARD_VERSION}';" in text
    assert "customElements.define" in text
