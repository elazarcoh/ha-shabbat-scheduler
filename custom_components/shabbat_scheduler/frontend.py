"""Serving and registering the Lovelace card.

HACS treats a repository as exactly one category and this one is an
integration, so the card ships inside it rather than as a second
repository the user must install and version-match by hand.
"""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

CARD_FILENAME = "shabbat-scheduler-card.js"
CARD_URL = f"/{DOMAIN}/{CARD_FILENAME}"
# Must match frontend/src/version.ts. The bundle carries it, and
# tests/test_frontend.py fails if the two ever drift apart.
CARD_VERSION = "0.3.0"

_STATIC_REGISTERED = f"{DOMAIN}_static_registered"


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Serve the bundle and make Lovelace load it.

    Registration failures must never take the scheduler down with them -
    this integration drives real appliances on a schedule nobody can
    operate by hand, and a Lovelace/HTTP quirk must not be able to stop
    that. The two anticipated degradations (no Lovelace, YAML resource
    mode) log a warning and return from `_async_register_resource` below;
    anything else - including from the static path call itself - is
    caught here so `async_setup_entry` always completes.
    """
    try:
        if not hass.data.get(_STATIC_REGISTERED):
            await hass.http.async_register_static_paths(
                [
                    StaticPathConfig(
                        f"/{DOMAIN}",
                        str(Path(__file__).parent / "www"),
                        # The URL is version-stamped, so caching is safe and
                        # keeps the bundle out of every page load.
                        True,
                    )
                ]
            )
            # A static path cannot be unregistered, so this flag survives a
            # reload deliberately. Home Assistant does not actually raise on
            # a repeat registration of the same path: at startup the http
            # component replaces `app._router.freeze` with a permanent
            # no-op, so the router never freezes and late or duplicate
            # registrations are simply accepted. That is an internal detail
            # this integration will not depend on across versions, so the
            # guard stays - but it is here to skip pointless repeat work on
            # every reload, not to dodge an exception that would never come.
            hass.data[_STATIC_REGISTERED] = True

        await _async_register_resource(hass)
    except Exception:  # noqa: BLE001 - deliberately broad, see docstring
        _LOGGER.exception(
            "Failed to register the Shabbat Scheduler card; the schedule "
            "itself is unaffected, only the Lovelace card is unavailable"
        )


async def _async_register_resource(hass: HomeAssistant) -> None:
    """Add or update our Lovelace resource, never duplicating it."""
    data = hass.data.get(LOVELACE_DATA)
    if data is None:
        _LOGGER.warning("Lovelace is not set up; the card was not registered")
        return

    if data.resource_mode != "storage":
        # YAML mode owns its own resource list and cannot be written to.
        _LOGGER.warning(
            "Lovelace is in YAML resource mode. Add this line to your "
            "resources yourself:\n  - url: %s?v=%s\n    type: module",
            CARD_URL,
            CARD_VERSION,
        )
        return

    wanted = f"{CARD_URL}?v={CARD_VERSION}"
    for item in data.resources.async_items():
        if item["url"].startswith(CARD_URL):
            if item["url"] != wanted:
                await data.resources.async_update_item(
                    item["id"], {"url": wanted}
                )
            return

    await data.resources.async_create_item({"res_type": "module", "url": wanted})


async def async_unregister_frontend(hass: HomeAssistant) -> None:
    """Remove the Lovelace resource on unload.

    The static path stays: Home Assistant has no way to unregister one,
    and serving a file nobody references is harmless.

    A failure to tidy up this resource must not fail the unload - the rest
    of teardown (engine shutdown, service removal) still has to happen.
    """
    try:
        data = hass.data.get(LOVELACE_DATA)
        if data is None or data.resource_mode != "storage":
            return
        for item in data.resources.async_items():
            if item["url"].startswith(CARD_URL):
                await data.resources.async_delete_item(item["id"])
                return
    except Exception:  # noqa: BLE001 - deliberately broad, see docstring
        _LOGGER.exception(
            "Failed to remove the Shabbat Scheduler card's Lovelace "
            "resource; continuing unload"
        )
