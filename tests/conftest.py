"""Shared fixtures.

pytest-homeassistant-custom-component ships the `hass` fixture; custom
integrations are only loaded when `enable_custom_integrations` is requested.
"""

import traceback
from datetime import time

import pytest
from aiohttp.web_urldispatcher import UrlDispatcher
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.shabbat_scheduler.const import DOMAIN
from custom_components.shabbat_scheduler.engine import ShabbatEngine
from custom_components.shabbat_scheduler.models import Rule
from custom_components.shabbat_scheduler.store import RuleStore

# TEMPORARY DIAGNOSTIC - investigating CI-only "frozen router" failures in
# test_websocket.py. Logs every REAL (non-overridden) UrlDispatcher.freeze()
# call with a stack trace, to find what freezes the router before the
# auth-view registration that fails. Remove before merging.
_real_freeze = UrlDispatcher.freeze


def _debug_freeze(self):
    print(
        f"\n### REAL UrlDispatcher.freeze() called id={id(self)} "
        f"already_frozen={self._frozen}",
        flush=True,
    )
    traceback.print_stack()
    return _real_freeze(self)


UrlDispatcher.freeze = _debug_freeze


@pytest.fixture
def rule_switch_entity_id(hass):
    """The entity_id of a rule's switch. The ONLY sanctioned way to find it.

    A rule switch's `unique_id` is stable and derived from `rule.id`; its
    `entity_id` is slugified from the rule's user-editable, often-Hebrew
    NAME and cannot be constructed from the rule id. Guessing
    `switch.<something>_rule_<id>` has produced two real bugs in this
    project, so every test goes through the registry instead.

    Returns None when no such entity is registered - which is exactly what
    the add/remove tests assert on.

    A fixture rather than an importable helper so it needs no import at
    all: `tests/` is not a package, and there is then nowhere else for a
    test to reach for a second, wronger way of doing this.
    """

    def _entity_id(entry, rule_id):
        return er.async_get(hass).async_get_entity_id(
            "switch", DOMAIN, f"{entry.entry_id}_rule_{rule_id}"
        )

    return _entity_id


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


ZMANIM = {
    "sensor.jewish_calendar_upcoming_candle_lighting": "2026-08-14T15:44:00+00:00",
    "sensor.jewish_calendar_upcoming_havdalah": "2026-08-15T17:01:00+00:00",
}


@pytest.fixture
def setup_scheduler(hass):
    """Set the integration up over the same path `tests/test_websocket.py` uses.

    Identical in behaviour to that module's local `_setup`: pin the
    timezone, publish the two Jewish Calendar sensors the engine derives a
    block from, seed the store, then load a config entry. Exposed here as a
    fixture rather than an importable helper for the same reason
    `rule_switch_entity_id` is - `tests/` is not a package, so a fixture is
    the only shape a second test module can reach without an import.

    A fixture and not a copy because `tests/test_frontend_fixture.py`
    generates a JSON fixture the frontend suite renders the card from: if
    that generator set the integration up in its own slightly different way,
    the committed payload would answer to that private setup rather than to
    the one every websocket test already pins, which is exactly the
    "tests agree with each other and with nothing else" failure it exists
    to prevent.
    """

    async def _setup(rules=(), defaults=None, enabled=False, dry_run=False):
        await hass.config.async_set_time_zone("Asia/Jerusalem")
        for entity_id, state in ZMANIM.items():
            hass.states.async_set(entity_id, state)
        store = RuleStore(hass)
        await store.async_load()
        await store.async_replace_all(defaults or {}, list(rules))
        if enabled:
            # Timers are only armed while the master switch is on.
            await store.async_set_enabled(True)
        if dry_run:
            await store.async_set_dry_run(True)
        entry = MockConfigEntry(domain=DOMAIN, title="Shabbat Scheduler")
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        return entry

    return _setup


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


@pytest.fixture
async def engine(hass, jerusalem, test_booleans):
    """A real engine over a fresh, empty store.

    Moved here from `tests/test_engine.py` in Task 10, alongside `_rule`,
    so `tests/test_execution_domains.py` could use the identical engine
    rather than constructing a second one that might drift from it.
    """
    store = RuleStore(hass)
    await store.async_load()
    return ShabbatEngine(hass, store)


@pytest.fixture
def _rule():
    """A minimally-filled-in `Rule`, for tests that only care about one field.

    Moved here in Task 10 (from a module-level function in
    `tests/test_engine.py`) so `tests/test_execution_domains.py` could use
    it too, without copying it.

    Deliberately a FIXTURE and not a plain function importable from this
    module. `rule_switch_entity_id` above already makes that call for the
    same reason and says it explicitly: `tests/` carries no `__init__.py`,
    so a bare `from tests.conftest import _rule` (or a `sys.path` trick
    reaching for the same effect) is not merely a second, redundant way to
    get this helper - it is the ONLY other way, and closing it is the
    point, not a side effect of avoiding duplication. A test file that
    wants `_rule` asks pytest for it, the same way every other fixture
    here is asked for; there is nowhere else to reach.
    """

    def _make(
        action="input_boolean.turn_on",
        entities=("input_boolean.t",),
        **kwargs,
    ):
        return Rule(
            id="r", profile=1, day="1", time=time(11, 0),
            action=action,
            target={"entity_id": list(entities)} if entities else {},
            **kwargs,
        )

    return _make
