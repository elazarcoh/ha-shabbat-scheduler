"""The integration serves and registers its own card."""

from unittest.mock import patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    flush_store,
)

from homeassistant.components.lovelace.resources import RESOURCE_STORAGE_KEY

from custom_components.shabbat_scheduler.const import DOMAIN
from custom_components.shabbat_scheduler.frontend import (
    CARD_URL,
    CARD_VERSION,
    async_unregister_frontend,
)


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


async def test_stale_duplicates_are_cleaned_up_when_the_collection_was_never_loaded(
    hass, hass_storage
):
    """Reproduces the real production race: `ResourceStorageCollection`
    only loads from disk lazily, the first time one of
    `async_create_item`/`async_update_item`/`async_delete_item`/
    `async_get_info` is awaited. `async_items()` does not trigger that
    load - it is a plain `list(self.data.values())` - so on a fresh boot,
    before anything else has touched the collection, it returns `[]` even
    though the store on disk already holds duplicates left over from
    earlier versions of the card. The dedup loop then finds nothing to
    update and falls through to `async_create_item`, which *does* load,
    and appends yet another copy on top of the ones already there.

    `async_setup_component(hass, "lovelace", {})` only constructs the
    (unloaded) collection; it does not load it either, so seeding
    `hass_storage` before that call and then setting up the entry
    reproduces the race precisely as it happens on a real restart.
    """
    hass_storage[RESOURCE_STORAGE_KEY] = {
        "version": 1,
        "data": {
            "items": [
                {"id": "old1", "type": "module", "url": f"{CARD_URL}?v=0.1.0"},
                {"id": "old2", "type": "module", "url": f"{CARD_URL}?v=0.1.0"},
                {"id": "old3", "type": "module", "url": f"{CARD_URL}?v=0.2.0"},
            ]
        },
    }

    await async_setup_component(hass, "lovelace", {})
    entry = MockConfigEntry(domain=DOMAIN, title="Shabbat Scheduler")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    matching = [
        item
        for item in hass.data[LOVELACE_DATA].resources.async_items()
        if item["url"].startswith(CARD_URL)
    ]
    assert len(matching) == 1
    assert matching[0]["url"] == f"{CARD_URL}?v={CARD_VERSION}"


async def test_unregistering_removes_every_matching_resource(hass):
    """`async_unregister_frontend` must not stop at the first match either
    - a user who already has duplicates (from this same bug, or from
    manual edits) must not be left with orphans after the entry unloads."""
    await async_setup_component(hass, "lovelace", {})
    resources = hass.data[LOVELACE_DATA].resources
    await resources.async_create_item(
        {"res_type": "module", "url": f"{CARD_URL}?v=0.1.0"}
    )
    await resources.async_create_item(
        {"res_type": "module", "url": f"{CARD_URL}?v=0.2.0"}
    )
    await resources.async_create_item({"res_type": "module", "url": CARD_URL})

    await async_unregister_frontend(hass)

    matching = [
        item for item in resources.async_items() if item["url"].startswith(CARD_URL)
    ]
    assert matching == []


async def test_unregistering_removes_every_matching_resource_from_an_unloaded_collection(
    hass, hass_storage
):
    """The test above seeds its resources through `async_create_item`,
    which itself calls `_async_ensure_loaded()` - so by the time
    `async_unregister_frontend` runs there, the collection is already
    loaded and the `await data.resources.async_get_info()` on the
    unregister path does nothing observable. This test constructs the
    genuinely-unloaded case instead.

    Resources are seeded straight into `hass_storage`, exactly as in
    `test_stale_duplicates_are_cleaned_up_when_the_collection_was_never_loaded`.
    To keep the collection unloaded through *setup* as well - so nothing
    upstream of unload accidentally loads it first - the static path
    registration is made to raise. `async_register_frontend`'s outer
    `try` then skips `_async_register_resource` entirely (the raise
    happens before that call is reached), which is the only other thing
    in this integration that would touch the collection. Setup still
    succeeds (registration failures never fail setup - see
    `test_an_unexpected_registration_error_does_not_fail_setup`), so the
    collection reaches `hass.config_entries.async_unload` - which calls
    `async_unregister_frontend` for real, not by calling the function
    directly - having never been loaded even once.

    Asserting against `resources.async_items()` here would be a trap: if
    the collection was never loaded, `self.data` is still an empty dict
    regardless of whether anything was actually deleted, so an in-memory
    check would pass vacuously whether or not the fix does its job (this
    was caught by first running this test against the deliberately
    broken code below and seeing it pass for the wrong reason). The only
    honest signal is what ends up back on disk, so this flushes the
    collection's `Store` and reads `hass_storage` directly - if
    `async_get_info()` never ran, the collection's in-memory data was
    never populated, there is nothing to flush, and the original
    on-disk duplicates are still sitting there untouched.
    """
    hass_storage[RESOURCE_STORAGE_KEY] = {
        "version": 1,
        "data": {
            "items": [
                {"id": "old1", "type": "module", "url": f"{CARD_URL}?v=0.1.0"},
                {"id": "old2", "type": "module", "url": f"{CARD_URL}?v=0.2.0"},
                {"id": "old3", "type": "module", "url": CARD_URL},
            ]
        },
    }

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

    # Setup must have survived the static-path failure, per the existing
    # guarantee - and, crucially for this test, that means it never reached
    # `_async_register_resource`, so the collection is still unloaded here.
    assert entry.state is ConfigEntryState.LOADED
    assert hass.data[LOVELACE_DATA].resources.loaded is False

    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    await flush_store(hass.data[LOVELACE_DATA].resources.store)
    matching = [
        item
        for item in hass_storage[RESOURCE_STORAGE_KEY]["data"]["items"]
        if item["url"].startswith(CARD_URL)
    ]
    assert matching == []


async def test_registration_is_a_no_op_when_already_current_and_unloaded(
    hass, hass_storage
):
    """The dedup code's three states - no match, stale match, current match
    - are each reachable from a freshly-unloaded collection. The first two
    are exercised elsewhere; this pins the third: a resource already at
    `CARD_VERSION`, seeded on disk rather than through the collection, so
    nothing has loaded it before setup runs. Registration must recognise it
    as already correct and leave it alone rather than updating or
    duplicating it."""
    hass_storage[RESOURCE_STORAGE_KEY] = {
        "version": 1,
        "data": {
            "items": [
                {
                    "id": "current",
                    "type": "module",
                    "url": f"{CARD_URL}?v={CARD_VERSION}",
                }
            ]
        },
    }

    await async_setup_component(hass, "lovelace", {})
    entry = MockConfigEntry(domain=DOMAIN, title="Shabbat Scheduler")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    matching = [
        item
        for item in hass.data[LOVELACE_DATA].resources.async_items()
        if item["url"].startswith(CARD_URL)
    ]
    assert matching == [
        {"id": "current", "type": "module", "url": f"{CARD_URL}?v={CARD_VERSION}"}
    ]


from pathlib import Path

from custom_components.shabbat_scheduler.frontend import CARD_FILENAME

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


# --- Final review I2: the committed bundle must match its source ---------
#
# The bundle is committed because a HACS user has no Node, and nothing
# noticed when it stopped matching frontend/src. Edit a source, skip the
# build, and every test stays green while the previous card ships - and
# because the Lovelace resource URL is stamped with the hand-maintained
# CARD_VERSION, the URL does not change either, so browsers keep serving
# the stale copy out of cache. That is precisely what
# test_the_resource_url_is_version_stamped exists to prevent.
#
# Rebuilding here was rejected: it is slow, and it needs Node on a machine
# that may not have it. Mtimes were rejected too - `git clone` stamps every
# file with the checkout time, so an mtime comparison says nothing at all
# in a fresh clone, which is the one place this has to work.
#
# So `npm run build` records what it built from, and this recomputes the
# same number in pure Python. THE FORMAT IS A CONTRACT with
# frontend/bundle-manifest.mjs, which documents it in full; change one and
# you must change the other.

import hashlib
import json

SRC = ROOT / "frontend" / "src"
MANIFEST = ROOT / "frontend" / "bundle-manifest.json"


def _sha256(path: Path) -> str:
    """SHA-256 of a file, with CRLF collapsed to LF.

    Normalised so a Windows or `core.autocrlf` checkout does not read as
    "every source file changed".
    """
    return hashlib.sha256(
        path.read_bytes().replace(b"\r\n", b"\n")
    ).hexdigest()


def _sources_hash() -> tuple[str, int]:
    files = sorted(
        p.relative_to(SRC).as_posix() for p in SRC.rglob("*.ts")
    )
    digest = hashlib.sha256()
    for rel in files:
        digest.update(f"{rel} {_sha256(SRC / rel)}\n".encode())
    return digest.hexdigest(), len(files)


def test_the_committed_bundle_matches_the_committed_sources():
    """The one guard against shipping a stale card.

    Pure stdlib on purpose: it must pass in a fresh clone on a machine
    with no Node, which is the situation of anyone installing via HACS or
    running the suite in CI without the frontend toolchain.
    """
    assert MANIFEST.is_file(), (
        "frontend/bundle-manifest.json is missing; run "
        "`npm --prefix frontend run build`"
    )
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    sources, count = _sources_hash()
    assert count > 0, "no TypeScript sources found; the check would be vacuous"
    assert manifest["source_files"] == count, (
        f"{count} source files but the manifest was built from "
        f"{manifest['source_files']}; run `npm --prefix frontend run build`"
    )
    assert manifest["sources"] == sources, (
        "frontend/src has changed since the bundle was last built. The "
        "committed bundle is stale and the version-stamped resource URL "
        "will not change, so browsers keep the old card cached. Run "
        "`npm --prefix frontend run build` and commit the result."
    )
    assert manifest["bundle"] == _sha256(WWW / CARD_FILENAME), (
        "the committed bundle is not the one this manifest was written "
        "for. Run `npm --prefix frontend run build` and commit both."
    )
