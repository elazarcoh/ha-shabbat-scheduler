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
CARD_VERSION = "0.1.0"

_STATIC_REGISTERED = f"{DOMAIN}_static_registered"


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Serve the bundle and make Lovelace load it."""
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
        # A static path cannot be unregistered, so this survives a reload
        # deliberately - registering it twice raises.
        hass.data[_STATIC_REGISTERED] = True

    await _async_register_resource(hass)


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
    """
    data = hass.data.get(LOVELACE_DATA)
    if data is None or data.resource_mode != "storage":
        return
    for item in data.resources.async_items():
        if item["url"].startswith(CARD_URL):
            await data.resources.async_delete_item(item["id"])
            return
