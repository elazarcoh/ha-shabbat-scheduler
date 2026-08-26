import asyncio
from datetime import time

import pytest
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.shabbat_scheduler.const import DOMAIN
from custom_components.shabbat_scheduler.models import Rule
from custom_components.shabbat_scheduler.store import RuleStore


async def test_rules_list_returns_rules_and_defaults(
    hass, hass_ws_client, setup_scheduler
):
    await setup_scheduler(
        [Rule(id="r1", profile=1, day="1", time=time(11, 0),
              action="climate.turn_on", target={"entity_id": ["climate.a"]})],
        defaults={"data": {"temperature": 26}},
    )
    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "shabbat_scheduler/rules/list"})
    msg = await client.receive_json()

    assert msg["success"]
    assert msg["result"]["defaults"] == {"data": {"temperature": 26}}
    assert [r["id"] for r in msg["result"]["rules"]] == ["r1"]
    assert msg["result"]["warnings"] == []


async def test_rules_list_reports_conflicts_as_warnings(
    hass, hass_ws_client, setup_scheduler
):
    await setup_scheduler([
        Rule(id="a", profile=1, day="1", time=time(18, 0),
             action="climate.turn_on", target={"entity_id": ["climate.a"]}),
        Rule(id="b", profile=1, day="1", time=time(18, 0),
             action="climate.turn_off", target={"entity_id": ["climate.a"]}),
    ])
    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "shabbat_scheduler/rules/list"})
    msg = await client.receive_json()

    assert msg["success"]
    assert msg["result"]["warnings"]


async def test_preview_resolves_the_upcoming_block(
    hass, hass_ws_client, setup_scheduler
):
    await setup_scheduler([
        Rule(id="r1", profile=1, day="1", time=time(11, 0),
             action="climate.turn_on", target={"entity_id": ["climate.a"]}),
    ])
    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "shabbat_scheduler/preview"})
    msg = await client.receive_json()

    assert msg["success"]
    assert msg["result"]["profile"] == 1
    assert len(msg["result"]["rules"]) == 1
    assert msg["result"]["rules"][0]["action"] == "climate.turn_on"
    assert msg["result"]["rules"][0]["target"] == {"entity_id": ["climate.a"]}


async def test_preview_with_block_length_resolves_a_hypothetical_block(
    hass, hass_ws_client, setup_scheduler
):
    """block_length re-derives a hypothetical block, mirroring the `simulate` service."""
    await setup_scheduler([
        Rule(id="r1", profile=1, day="1", time=time(11, 0),
             action="climate.turn_on", target={"entity_id": ["climate.a"]}),
        Rule(id="r3", profile=3, day="1", time=time(11, 0),
             action="climate.turn_on", target={"entity_id": ["climate.b"]}),
    ])
    client = await hass_ws_client(hass)
    await client.send_json(
        {"id": 1, "type": "shabbat_scheduler/preview", "block_length": 3}
    )
    msg = await client.receive_json()

    assert msg["success"]
    assert msg["result"]["profile"] == 3
    assert [r["rule_id"] for r in msg["result"]["rules"]] == ["r3"]


async def test_preview_without_block_length_uses_the_real_upcoming_block(
    hass, hass_ws_client, setup_scheduler
):
    await setup_scheduler([
        Rule(id="r1", profile=1, day="1", time=time(11, 0),
             action="climate.turn_on", target={"entity_id": ["climate.a"]}),
        Rule(id="r3", profile=3, day="1", time=time(11, 0),
             action="climate.turn_on", target={"entity_id": ["climate.b"]}),
    ])
    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "shabbat_scheduler/preview"})
    msg = await client.receive_json()

    assert msg["success"]
    assert msg["result"]["profile"] == 1
    assert [r["rule_id"] for r in msg["result"]["rules"]] == ["r1"]


async def test_rules_list_reports_not_set_up_after_unload(
    hass, hass_ws_client, setup_scheduler
):
    entry = await setup_scheduler()
    client = await hass_ws_client(hass)

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    await client.send_json({"id": 1, "type": "shabbat_scheduler/rules/list"})
    msg = await client.receive_json()

    assert not msg["success"]
    assert msg["error"]["code"] == "not_set_up"


async def test_preview_reports_not_set_up_after_unload(
    hass, hass_ws_client, setup_scheduler
):
    entry = await setup_scheduler()
    client = await hass_ws_client(hass)

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    await client.send_json({"id": 1, "type": "shabbat_scheduler/preview"})
    msg = await client.receive_json()

    assert not msg["success"]
    assert msg["error"]["code"] == "not_set_up"


async def test_preview_reports_no_block_when_zmanim_missing(hass, hass_ws_client):
    await hass.config.async_set_time_zone("Asia/Jerusalem")
    store = RuleStore(hass)
    await store.async_load()
    await store.async_replace_all({}, [
        Rule(id="r1", profile=1, day="1", time=time(11, 0),
             action="climate.turn_on", target={"entity_id": ["climate.a"]}),
    ])
    entry = MockConfigEntry(domain=DOMAIN, title="Shabbat Scheduler")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "shabbat_scheduler/preview"})
    msg = await client.receive_json()

    assert msg["success"]
    assert msg["result"]["profile"] is None
    assert msg["result"]["warnings"] == [
        {
            "kind": "no_block",
            "message": "No block could be derived from the Jewish Calendar sensors.",
        }
    ]


NEW_RULE = {
    "profile": 1,
    "day": "1",
    "time": "11:00:00",
    "action": "climate.turn_on",
    "target": {"entity_id": ["climate.a"]},
}


async def test_create_generates_an_id_and_persists(
    hass, hass_ws_client, setup_scheduler
):
    await setup_scheduler()
    client = await hass_ws_client(hass)
    await client.send_json(
        {"id": 1, "type": "shabbat_scheduler/rules/create", "rule": NEW_RULE}
    )
    msg = await client.receive_json()
    assert msg["success"]
    rule_id = msg["result"]["rule"]["id"]
    assert rule_id

    reloaded = RuleStore(hass)
    await reloaded.async_load()
    assert [r.id for r in reloaded.rules] == [rule_id]


async def test_create_ignores_a_client_supplied_id(
    hass, hass_ws_client, setup_scheduler
):
    await setup_scheduler()
    client = await hass_ws_client(hass)
    await client.send_json(
        {
            "id": 1,
            "type": "shabbat_scheduler/rules/create",
            "rule": {**NEW_RULE, "id": "client-chosen"},
        }
    )
    msg = await client.receive_json()
    assert msg["success"]
    assert msg["result"]["rule"]["id"] != "client-chosen"


async def test_create_rejects_malformed_input(hass, hass_ws_client, setup_scheduler):
    await setup_scheduler()
    client = await hass_ws_client(hass)
    await client.send_json(
        {
            "id": 1,
            "type": "shabbat_scheduler/rules/create",
            "rule": {**NEW_RULE, "day": "dya_1"},
        }
    )
    msg = await client.receive_json()
    assert not msg["success"]

    reloaded = RuleStore(hass)
    await reloaded.async_load()
    assert reloaded.rules == []


async def test_create_succeeds_but_warns_on_a_conflict(
    hass, hass_ws_client, setup_scheduler
):
    await setup_scheduler([
        Rule(id="a", profile=1, day="1", time=time(11, 0),
             action="climate.turn_off", target={"entity_id": ["climate.a"]}),
    ])
    client = await hass_ws_client(hass)
    await client.send_json(
        {"id": 1, "type": "shabbat_scheduler/rules/create", "rule": NEW_RULE}
    )
    msg = await client.receive_json()

    assert msg["success"]  # conflicts warn, they never reject
    assert msg["result"]["warnings"]


async def test_update_changes_only_supplied_fields(
    hass, hass_ws_client, setup_scheduler
):
    await setup_scheduler([
        Rule(id="r1", profile=1, day="1", time=time(11, 0),
             action="climate.turn_on", target={"entity_id": ["climate.a"]}),
    ])
    client = await hass_ws_client(hass)
    await client.send_json(
        {
            "id": 1,
            "type": "shabbat_scheduler/rules/update",
            "rule_id": "r1",
            "changes": {"enabled": False},
        }
    )
    msg = await client.receive_json()

    assert msg["success"]
    assert msg["result"]["rule"]["enabled"] is False
    assert msg["result"]["rule"]["time"] == "11:00:00"


async def test_update_of_unknown_rule_errors(hass, hass_ws_client, setup_scheduler):
    await setup_scheduler()
    client = await hass_ws_client(hass)
    await client.send_json(
        {
            "id": 1,
            "type": "shabbat_scheduler/rules/update",
            "rule_id": "nope",
            "changes": {"enabled": False},
        }
    )
    msg = await client.receive_json()
    assert not msg["success"]


async def test_delete_removes_the_rule(hass, hass_ws_client, setup_scheduler):
    await setup_scheduler([
        Rule(id="r1", profile=1, day="1", time=time(11, 0),
             action="climate.turn_on"),
    ])
    client = await hass_ws_client(hass)
    await client.send_json(
        {"id": 1, "type": "shabbat_scheduler/rules/delete", "rule_id": "r1"}
    )
    msg = await client.receive_json()
    assert msg["success"]

    reloaded = RuleStore(hass)
    await reloaded.async_load()
    assert reloaded.rules == []


async def test_defaults_update_persists(hass, hass_ws_client, setup_scheduler):
    await setup_scheduler()
    client = await hass_ws_client(hass)
    await client.send_json(
        {
            "id": 1,
            "type": "shabbat_scheduler/defaults/update",
            "defaults": {
                "target": {"entity_id": ["climate.a"]},
                "data": {"temperature": 24},
            },
        }
    )
    msg = await client.receive_json()
    assert msg["success"]
    assert msg["result"]["defaults"] == {
        "target": {"entity_id": ["climate.a"]},
        "data": {"temperature": 24},
    }

    reloaded = RuleStore(hass)
    await reloaded.async_load()
    assert reloaded.defaults["target"] == {"entity_id": ["climate.a"]}
    assert reloaded.defaults["data"] == {"temperature": 24}


async def test_defaults_update_rejects_a_string_data_payload(
    hass, hass_ws_client, setup_scheduler
):
    """`data` must be a mapping - the same guard rule fields already use.

    v1 spelled this key `settings`; the guard and the hole are identical.
    """
    await setup_scheduler()
    client = await hass_ws_client(hass)
    await client.send_json(
        {
            "id": 1,
            "type": "shabbat_scheduler/defaults/update",
            "defaults": {"data": "not_a_dict"},
        }
    )
    msg = await client.receive_json()
    assert not msg["success"]

    reloaded = RuleStore(hass)
    await reloaded.async_load()
    assert reloaded.defaults == {}


async def test_defaults_update_rejects_a_bare_string_target_payload(
    hass, hass_ws_client, setup_scheduler
):
    """`target` must be a mapping (a target selector), not a bare string.

    v1's equivalent was `devices`, which had to be a list rather than a
    bare string. Same door, same guard, v2 vocabulary.
    """
    await setup_scheduler()
    client = await hass_ws_client(hass)
    await client.send_json(
        {
            "id": 1,
            "type": "shabbat_scheduler/defaults/update",
            "defaults": {"target": "climate.a"},
        }
    )
    msg = await client.receive_json()
    assert not msg["success"]

    reloaded = RuleStore(hass)
    await reloaded.async_load()
    assert reloaded.defaults == {}


async def test_defaults_update_of_an_invalid_target_is_rejected(
    hass, hass_ws_client, setup_scheduler
):
    """The same door `ws_create` was closed against, for the same reason.

    A defaults target comes out of the SAME editor a rule's does, but
    `validate_defaults` only asks "is it a mapping" - so an identical
    selector was refused in the rule dialog and accepted here, then merged
    into every rule with no target of its own (`block.merge_defaults`) and
    refused at FIRE time on Shabbat instead of at save time in the dialog
    the author was looking at.

    `not_a_selector` is the same key
    `test_create_of_an_invalid_target_is_rejected` uses, deliberately: the
    point is that the two doors now give the same answer to one payload.
    """
    await setup_scheduler()
    client = await hass_ws_client(hass)
    await client.send_json(
        {
            "id": 1,
            "type": "shabbat_scheduler/defaults/update",
            "defaults": {"target": {"not_a_selector": ["climate.a"]}},
        }
    )
    msg = await client.receive_json()
    assert not msg["success"]
    assert msg["error"]["code"] == "invalid_rule"

    # Refused, not "refused and half-written".
    reloaded = RuleStore(hass)
    await reloaded.async_load()
    assert reloaded.defaults == {}


async def test_defaults_update_accepts_every_target_selector_a_rule_may_use(
    hass, hass_ws_client, setup_scheduler
):
    """Validated the same way, not merely validated MORE.

    A guard that rejects a bogus key is worth nothing if it also rejects
    the real ones: an area or a label is a perfectly ordinary shared
    default, and refusing them would break authoring rather than tighten
    it. Driven per selector so one over-broad schema cannot pass this.
    """
    await setup_scheduler()
    client = await hass_ws_client(hass)
    for index, target in enumerate(
        (
            {"entity_id": ["climate.a"]},
            {"area_id": ["salon"]},
            {"device_id": ["abc123"]},
            {"floor_id": ["ground"]},
            {"label_id": ["shabbat"]},
        ),
        start=1,
    ):
        await client.send_json(
            {
                "id": index,
                "type": "shabbat_scheduler/defaults/update",
                "defaults": {"target": target},
            }
        )
        msg = await client.receive_json()
        assert msg["success"], target
        assert msg["result"]["defaults"]["target"] == target


async def test_defaults_update_accepts_a_payload_with_no_target_at_all(
    hass, hass_ws_client, setup_scheduler
):
    """`target` is optional, and a data-only default is the normal case.

    The HA-side check must therefore not fire on an ABSENT target. Asserts
    key absence explicitly: `validate_defaults` returns only the keys the
    client sent, so a `target` appearing here would mean the guard had
    invented one on the way through.
    """
    await setup_scheduler()
    client = await hass_ws_client(hass)
    await client.send_json(
        {
            "id": 1,
            "type": "shabbat_scheduler/defaults/update",
            "defaults": {"data": {"temperature": 24}},
        }
    )
    msg = await client.receive_json()
    assert msg["success"]
    assert "target" not in msg["result"]["defaults"]

    reloaded = RuleStore(hass)
    await reloaded.async_load()
    assert "target" not in reloaded.defaults


ORIGINAL = Rule(
    id="r1", profile=1, day="1", time=time(11, 0),
    action="climate.turn_on", target={"entity_id": ["climate.a"]},
)


async def test_update_to_an_invalid_condition_is_rejected_and_persists_nothing(
    hass, hass_ws_client, setup_scheduler
):
    """The v2 successor to `test_update_to_custom_action_without_script`.

    That test pinned v1's one whole-rule invariant ("a custom action needs
    a script"), which Task 3 deleted along with the custom action itself.
    The invariant that replaces it is Home Assistant's own: a `condition`
    or `target` HA would refuse must be refused HERE, in the dialog the
    author is looking at, rather than at fire time on a Shabbat night. The
    YAML door already applied it; this door did not, so a shape the YAML
    import rejects could still be written over the websocket.
    """
    await setup_scheduler([ORIGINAL])
    client = await hass_ws_client(hass)
    await client.send_json(
        {
            "id": 1,
            "type": "shabbat_scheduler/rules/update",
            "rule_id": "r1",
            # Structurally a fine list-of-mappings, so rule_schema passes
            # it; HA has no `condition: sideways` platform, so HA does not.
            "changes": {"condition": [{"condition": "sideways"}]},
        }
    )
    msg = await client.receive_json()
    assert not msg["success"]
    assert msg["error"]["code"] == "invalid_rule"

    reloaded = RuleStore(hass)
    await reloaded.async_load()
    assert reloaded.rules == [ORIGINAL]


async def test_create_of_an_invalid_condition_is_rejected_and_persists_nothing(
    hass, hass_ws_client, setup_scheduler
):
    await setup_scheduler()
    client = await hass_ws_client(hass)
    await client.send_json(
        {
            "id": 1,
            "type": "shabbat_scheduler/rules/create",
            "rule": {**NEW_RULE, "condition": [{"condition": "sideways"}]},
        }
    )
    msg = await client.receive_json()
    assert not msg["success"]
    assert msg["error"]["code"] == "invalid_rule"

    reloaded = RuleStore(hass)
    await reloaded.async_load()
    assert reloaded.rules == []


async def test_create_of_an_invalid_target_is_rejected(
    hass, hass_ws_client, setup_scheduler
):
    """`target` goes through HA's own TARGET_SERVICE_FIELDS schema."""
    await setup_scheduler()
    client = await hass_ws_client(hass)
    await client.send_json(
        {
            "id": 1,
            "type": "shabbat_scheduler/rules/create",
            "rule": {**NEW_RULE, "target": {"not_a_selector": ["climate.a"]}},
        }
    )
    msg = await client.receive_json()
    assert not msg["success"]
    assert msg["error"]["code"] == "invalid_rule"

    reloaded = RuleStore(hass)
    await reloaded.async_load()
    assert reloaded.rules == []


async def test_a_rule_read_from_the_api_can_be_written_straight_back(
    hass, hass_ws_client, setup_scheduler
):
    """A read-modify-write must not be refused for fields the server added.

    `rule_to_dict` - which is what every websocket response returns -
    carries `migration_error` and `migration_source`, written by the v1
    -> v2 migration so the card can say WHICH rule it could not convert.
    `rule_from_api` used to reject them as unknown fields, so a client
    that read a rule, changed its name and sent it back was refused for a
    field it never chose to send. They are now dropped on the way in, so a
    client still cannot SET them.
    """
    await setup_scheduler([ORIGINAL])
    client = await hass_ws_client(hass)

    await client.send_json({"id": 1, "type": "shabbat_scheduler/rules/list"})
    listed = (await client.receive_json())["result"]["rules"][0]
    assert "migration_error" in listed  # the payload really does carry it

    await client.send_json(
        {
            "id": 2,
            "type": "shabbat_scheduler/rules/update",
            "rule_id": "r1",
            "changes": {**listed, "id": None, "name": "renamed"},
        }
    )
    # `id` is never updatable; drop it the way a real client would.
    msg = await client.receive_json()
    assert not msg["success"]  # ...because `id` is present, not the read-onlys

    del listed["id"]
    await client.send_json(
        {
            "id": 3,
            "type": "shabbat_scheduler/rules/update",
            "rule_id": "r1",
            "changes": {**listed, "name": "renamed"},
        }
    )
    msg = await client.receive_json()
    assert msg["success"], msg.get("error")
    assert msg["result"]["rule"]["name"] == "renamed"

    reloaded = RuleStore(hass)
    await reloaded.async_load()
    assert reloaded.rules[0].name == "renamed"
    # Dropped, not stored: the client could not set them even by echoing.
    assert reloaded.rules[0].migration_error is None
    assert reloaded.rules[0].migration_source is None


async def test_a_client_cannot_forge_the_migration_fields_on_create(
    hass, hass_ws_client, setup_scheduler
):
    """The other half of the I4 seam. `yaml_io` now PRESERVES
    `migration_error`/`migration_source`, because a YAML file is a
    serialised store; the websocket door must still drop them, because a
    client payload is an edit. A forged `migration_error` would put a
    healthy rule in the unmigrated-rules repair issue and make the card
    render a migration failure that never happened.
    """
    await setup_scheduler()
    client = await hass_ws_client(hass)
    await client.send_json(
        {
            "id": 1,
            "type": "shabbat_scheduler/rules/create",
            "rule": {
                **NEW_RULE,
                "migration_error": "forged",
                "migration_source": {"devices": ["climate.a"]},
            },
        }
    )
    msg = await client.receive_json()
    assert msg["success"], msg.get("error")
    assert msg["result"]["rule"]["migration_error"] is None
    assert msg["result"]["rule"]["migration_source"] is None

    reloaded = RuleStore(hass)
    await reloaded.async_load()
    assert reloaded.rules[0].migration_error is None
    assert reloaded.rules[0].migration_source is None


async def test_update_succeeds_but_warns_on_a_conflict(
    hass, hass_ws_client, setup_scheduler
):
    await setup_scheduler([
        Rule(id="a", profile=1, day="1", time=time(11, 0),
             action="climate.turn_on", target={"entity_id": ["climate.a"]}),
        Rule(id="b", profile=1, day="1", time=time(12, 0),
             action="climate.turn_off", target={"entity_id": ["climate.a"]}),
    ])
    client = await hass_ws_client(hass)
    await client.send_json(
        {
            "id": 1,
            "type": "shabbat_scheduler/rules/update",
            "rule_id": "b",
            "changes": {"time": "11:00:00"},
        }
    )
    msg = await client.receive_json()

    assert msg["success"]  # conflicts warn, they never reject
    assert msg["result"]["warnings"]


# --- Every mutation must reschedule the engine -------------------------
#
# Timers live only in ShabbatEngine._async_refresh. Nothing else calls it
# unprompted until the zmanim sensors roll forward at havdalah, so a rule
# created, deleted or retimed over the websocket used to leave the armed
# timers describing the PREVIOUS rule set - silently never firing a new
# rule, and still driving devices from deleted or retimed ones.
#
# 05:00Z on 15 Aug is 08:00 local, inside the block ZMANIM describes and
# before both the 11:00 and 20:00 rule times used below.


async def test_create_over_the_websocket_arms_a_timer(
    hass, hass_ws_client, setup_scheduler, freezer
):
    # Client first: the access token is minted against the real clock and
    # would look not-yet-issued once the freezer moves into the past.
    client = await hass_ws_client(hass)
    freezer.move_to("2026-08-15T05:00:00+00:00")
    entry = await setup_scheduler(enabled=True)
    engine = hass.data[DOMAIN][entry.entry_id]["engine"]
    assert engine.upcoming() == []

    await client.send_json(
        {"id": 1, "type": "shabbat_scheduler/rules/create", "rule": NEW_RULE}
    )
    msg = await client.receive_json()
    assert msg["success"]
    await hass.async_block_till_done()

    rule_id = msg["result"]["rule"]["id"]
    assert [item.rule.id for item in engine.upcoming()] == [rule_id]


async def test_delete_over_the_websocket_disarms_its_timer(
    hass, hass_ws_client, setup_scheduler, freezer
):
    client = await hass_ws_client(hass)
    freezer.move_to("2026-08-15T05:00:00+00:00")
    entry = await setup_scheduler(
        [Rule(id="r1", profile=1, day="1", time=time(11, 0),
              action="climate.turn_on", target={"entity_id": ["climate.a"]})],
        enabled=True,
    )
    engine = hass.data[DOMAIN][entry.entry_id]["engine"]
    assert [item.rule.id for item in engine.upcoming()] == ["r1"]

    await client.send_json(
        {"id": 1, "type": "shabbat_scheduler/rules/delete", "rule_id": "r1"}
    )
    assert (await client.receive_json())["success"]
    await hass.async_block_till_done()

    assert engine.upcoming() == []


async def test_update_over_the_websocket_moves_the_armed_time(
    hass, hass_ws_client, setup_scheduler, freezer
):
    client = await hass_ws_client(hass)
    freezer.move_to("2026-08-15T05:00:00+00:00")
    entry = await setup_scheduler(
        [Rule(id="r1", profile=1, day="1", time=time(11, 0),
              action="climate.turn_on", target={"entity_id": ["climate.a"]})],
        enabled=True,
    )
    engine = hass.data[DOMAIN][entry.entry_id]["engine"]
    assert [item.when.hour for item in engine.upcoming()] == [11]

    await client.send_json(
        {
            "id": 1,
            "type": "shabbat_scheduler/rules/update",
            "rule_id": "r1",
            "changes": {"time": "20:00:00"},
        }
    )
    assert (await client.receive_json())["success"]
    await hass.async_block_till_done()

    assert [item.when.hour for item in engine.upcoming()] == [20]
    assert [item.rule.time for item in engine.upcoming()] == [time(20, 0)]


async def test_subscribe_pushes_on_change(hass, hass_ws_client, setup_scheduler):
    await setup_scheduler()
    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "shabbat_scheduler/subscribe"})

    ack = await client.receive_json()
    assert ack["success"]

    # The initial snapshot is sent immediately after the subscribe response
    snapshot = await client.receive_json()
    assert snapshot["type"] == "event"
    assert [r["id"] for r in snapshot["event"]["rules"]] == []

    store = RuleStore(hass)
    await store.async_load()
    entry_store = list(hass.data[DOMAIN].values())[0]["store"]
    await entry_store.async_add(
        Rule(id="pushed", profile=1, day="1", time=time(11, 0),
             action="climate.turn_on")
    )
    await hass.async_block_till_done()

    event = await client.receive_json()
    assert event["type"] == "event"
    assert [r["id"] for r in event["event"]["rules"]] == ["pushed"]


async def test_subscribe_pushes_the_current_state_immediately(
    hass, hass_ws_client, setup_scheduler
):
    """Otherwise a client needs list AND subscribe, and a change landing
    between the two is lost silently and never re-reported."""
    await setup_scheduler([
        Rule(id="r1", profile=1, day="1", time=time(11, 0),
             action="climate.turn_on"),
    ])
    client = await hass_ws_client(hass)

    await client.send_json_auto_id({"type": "shabbat_scheduler/subscribe"})
    assert (await client.receive_json())["success"] is True

    pushed = await client.receive_json()
    assert pushed["type"] == "event"
    assert [rule["id"] for rule in pushed["event"]["rules"]] == ["r1"]
    assert pushed["event"]["block"]["length"] == 1


async def test_subscribe_stops_pushing_after_unsubscribe(
    hass, hass_ws_client, setup_scheduler
):
    await setup_scheduler()
    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "shabbat_scheduler/subscribe"})
    assert (await client.receive_json())["success"]

    # Receive and discard the initial snapshot sent by subscribe
    await client.receive_json()

    await client.send_json({"id": 2, "type": "unsubscribe_events", "subscription": 1})
    assert (await client.receive_json())["success"]

    entry_store = list(hass.data[DOMAIN].values())[0]["store"]
    await entry_store.async_add(
        Rule(id="quiet", profile=1, day="1", time=time(11, 0),
             action="climate.turn_on")
    )
    await hass.async_block_till_done()

    await client.send_json({"id": 3, "type": "shabbat_scheduler/rules/list"})
    msg = await client.receive_json()
    assert msg["id"] == 3  # no pushed event arrived in between


# --- Final review I3: mutations are admin-only ---------------------------
#
# Every command used to be callable by any authenticated user, including a
# read-only account. In a household with non-admin logins that means anyone
# could rewrite or delete the schedule driving the air conditioning.

MUTATIONS = [
    {"type": "shabbat_scheduler/rules/create", "rule": NEW_RULE},
    {
        "type": "shabbat_scheduler/rules/update",
        "rule_id": "r1",
        "changes": {"enabled": False},
    },
    {"type": "shabbat_scheduler/rules/delete", "rule_id": "r1"},
    {
        "type": "shabbat_scheduler/defaults/update",
        "defaults": {"target": {"entity_id": ["x.y"]}},
    },
    {"type": "shabbat_scheduler/rules/run_now", "rule_id": "r1"},
]


@pytest.mark.parametrize("mutation", MUTATIONS, ids=lambda m: m["type"])
async def test_a_read_only_user_cannot_mutate(
    hass, hass_ws_client, setup_scheduler, hass_read_only_access_token, mutation
):
    await setup_scheduler([
        Rule(id="r1", profile=1, day="1", time=time(11, 0),
             action="climate.turn_on", target={"entity_id": ["climate.a"]}),
    ])
    client = await hass_ws_client(hass, hass_read_only_access_token)

    await client.send_json({"id": 1, **mutation})
    msg = await client.receive_json()

    assert not msg["success"]
    assert msg["error"]["code"] == "unauthorized"

    # ...and nothing was written.
    reloaded = RuleStore(hass)
    await reloaded.async_load()
    assert [rule.id for rule in reloaded.rules] == ["r1"]
    assert reloaded.rules[0].enabled is True
    assert reloaded.defaults == {}


async def test_a_read_only_user_can_still_read(
    hass, hass_ws_client, setup_scheduler, hass_read_only_access_token
):
    """Reading is what the card does for everyone; only writing is admin."""
    await setup_scheduler([
        Rule(id="r1", profile=1, day="1", time=time(11, 0),
             action="climate.turn_on", target={"entity_id": ["climate.a"]}),
    ])
    client = await hass_ws_client(hass, hass_read_only_access_token)

    await client.send_json({"id": 1, "type": "shabbat_scheduler/rules/list"})
    msg = await client.receive_json()
    assert msg["success"]
    assert [r["id"] for r in msg["result"]["rules"]] == ["r1"]

    await client.send_json({"id": 2, "type": "shabbat_scheduler/preview"})
    assert (await client.receive_json())["success"]

    await client.send_json({"id": 3, "type": "shabbat_scheduler/subscribe"})
    assert (await client.receive_json())["success"]


# --- Final review I5: conflicts must be found through the defaults -------
#
# find_conflicts resolves rule.target, so a rule whose target comes from
# `defaults` - the shape the README documents as the common case - used to
# contribute nothing, and the card was told the schedule was clean.

CONFLICTING_PAIR = [
    Rule(id="a", profile=1, day="1", time=time(18, 0), action="climate.turn_on"),
    Rule(id="b", profile=1, day="1", time=time(18, 0), action="climate.turn_off"),
]
DEFAULT_DEVICES = {"target": {"entity_id": ["climate.a"]}}


async def test_rules_list_finds_conflicts_when_devices_come_from_defaults(
    hass, hass_ws_client, setup_scheduler
):
    await setup_scheduler(CONFLICTING_PAIR, defaults=DEFAULT_DEVICES)
    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "shabbat_scheduler/rules/list"})
    msg = await client.receive_json()

    assert msg["success"]
    assert [w["targets"] for w in msg["result"]["warnings"]] == [["climate.a"]]


async def test_create_finds_a_conflict_when_devices_come_from_defaults(
    hass, hass_ws_client, setup_scheduler
):
    await setup_scheduler(CONFLICTING_PAIR[:1], defaults=DEFAULT_DEVICES)
    client = await hass_ws_client(hass)
    await client.send_json(
        {
            "id": 1,
            "type": "shabbat_scheduler/rules/create",
            "rule": {
                "profile": 1, "day": "1", "time": "18:00:00",
                "action": "climate.turn_off",
            },
        }
    )
    msg = await client.receive_json()

    assert msg["success"]  # conflicts warn, they never reject
    assert [w["targets"] for w in msg["result"]["warnings"]] == [["climate.a"]]


async def test_update_finds_a_conflict_when_devices_come_from_defaults(
    hass, hass_ws_client, setup_scheduler
):
    await setup_scheduler(
        [
            Rule(id="a", profile=1, day="1", time=time(18, 0),
                 action="climate.turn_on"),
            Rule(id="b", profile=1, day="1", time=time(12, 0),
                 action="climate.turn_off"),
        ],
        defaults=DEFAULT_DEVICES,
    )
    client = await hass_ws_client(hass)
    await client.send_json(
        {
            "id": 1,
            "type": "shabbat_scheduler/rules/update",
            "rule_id": "b",
            "changes": {"time": "18:00:00"},
        }
    )
    msg = await client.receive_json()

    assert msg["success"]
    assert [w["targets"] for w in msg["result"]["warnings"]] == [["climate.a"]]


async def test_defaults_update_finds_the_conflict_it_creates(
    hass, hass_ws_client, setup_scheduler
):
    """Pointing the defaults at a device is itself what creates the clash."""
    await setup_scheduler(CONFLICTING_PAIR)
    client = await hass_ws_client(hass)
    await client.send_json(
        {
            "id": 1,
            "type": "shabbat_scheduler/defaults/update",
            "defaults": DEFAULT_DEVICES,
        }
    )
    msg = await client.receive_json()

    assert msg["success"]
    assert [w["targets"] for w in msg["result"]["warnings"]] == [["climate.a"]]


# --- Final review M8: deleting an unknown id is an error -----------------


async def test_delete_of_unknown_rule_errors(hass, hass_ws_client, setup_scheduler):
    """Asymmetric with rules/update until now; {"ok": True} hid a desync."""
    await setup_scheduler()
    client = await hass_ws_client(hass)
    await client.send_json(
        {"id": 1, "type": "shabbat_scheduler/rules/delete", "rule_id": "nope"}
    )
    msg = await client.receive_json()

    assert not msg["success"]
    assert msg["error"]["code"] == "not_found"


# --- Task 7: rules/run_now applies through the real fire path ------------


async def test_run_now_defaults_to_simulate(hass, hass_ws_client, setup_scheduler):
    await setup_scheduler([
        Rule(id="r1", profile=1, day="1", time=time(11, 0),
             action="input_boolean.turn_on", target={"entity_id": ["input_boolean.t"]}),
    ])
    hass.states.async_set("input_boolean.t", "off")
    client = await hass_ws_client(hass)

    await client.send_json(
        {"id": 1, "type": "shabbat_scheduler/rules/run_now", "rule_id": "r1"}
    )
    msg = await client.receive_json()

    assert msg["success"]
    assert msg["result"]["results"][0]["outcome"] == "would_call"
    assert hass.states.get("input_boolean.t").state == "off"


async def test_run_now_with_simulate_false_really_calls(
    hass, hass_ws_client, setup_scheduler, test_booleans
):
    await setup_scheduler([
        Rule(id="r1", profile=1, day="1", time=time(11, 0),
             action="input_boolean.turn_on", target={"entity_id": ["input_boolean.t"]}),
    ])
    hass.states.async_set("input_boolean.t", "off")
    client = await hass_ws_client(hass)

    await client.send_json({
        "id": 1, "type": "shabbat_scheduler/rules/run_now",
        "rule_id": "r1", "simulate": False,
    })
    msg = await client.receive_json()
    await hass.async_block_till_done()

    assert msg["success"]
    assert msg["result"]["results"][0]["outcome"] == "called"
    assert hass.states.get("input_boolean.t").state == "on"


async def test_run_now_of_an_unknown_rule_errors_cleanly(
    hass, hass_ws_client, setup_scheduler
):
    await setup_scheduler()
    client = await hass_ws_client(hass)

    await client.send_json(
        {"id": 1, "type": "shabbat_scheduler/rules/run_now", "rule_id": "nope"}
    )
    msg = await client.receive_json()

    assert not msg["success"]
    assert msg["error"]["code"] == "not_found"


async def test_run_now_merges_shared_defaults(
    hass, hass_ws_client, setup_scheduler, test_booleans
):
    """A rule with no target of its own must still resolve through the
    shared defaults - the same merge every real fire applies."""
    await setup_scheduler(
        [Rule(id="r1", profile=1, day="1", time=time(11, 0), action="input_boolean.turn_on")],
        defaults={"target": {"entity_id": ["input_boolean.t"]}},
    )
    hass.states.async_set("input_boolean.t", "off")
    client = await hass_ws_client(hass)

    await client.send_json({
        "id": 1, "type": "shabbat_scheduler/rules/run_now",
        "rule_id": "r1", "simulate": False,
    })
    msg = await client.receive_json()
    await hass.async_block_till_done()

    assert msg["success"]
    assert msg["result"]["results"][0]["outcome"] == "called"
    assert hass.states.get("input_boolean.t").state == "on"


async def test_run_now_rejects_a_malformed_at(hass, hass_ws_client, setup_scheduler):
    await setup_scheduler([
        Rule(id="r1", profile=1, day="1", time=time(11, 0), action="input_boolean.turn_on"),
    ])
    client = await hass_ws_client(hass)

    await client.send_json({
        "id": 1, "type": "shabbat_scheduler/rules/run_now",
        "rule_id": "r1", "at": "not-a-datetime",
    })
    msg = await client.receive_json()

    assert not msg["success"]


# --- Final review I4: a subscription must follow the live store ----------


async def test_subscription_serves_the_new_store_after_a_reload(
    hass, hass_ws_client, setup_scheduler
):
    """SIGNAL_RULES_CHANGED is global and the subscription outlives a reload.

    Capturing the store at subscribe time meant pushes carried the OLD
    store's contents while CRUD wrote to the new one - the card reading one
    store and writing another.
    """
    entry = await setup_scheduler()
    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "shabbat_scheduler/subscribe"})
    assert (await client.receive_json())["success"]

    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    await client.send_json(
        {"id": 2, "type": "shabbat_scheduler/rules/create", "rule": NEW_RULE}
    )
    pushed = created = None
    while pushed is None or created is None:
        msg = await client.receive_json()
        if msg["type"] == "event":
            pushed = msg
        else:
            created = msg

    assert created["success"]
    rule_id = created["result"]["rule"]["id"]
    assert [r["id"] for r in pushed["event"]["rules"]] == [rule_id]


# --- preview and simulate are one implementation -------------------------


@pytest.mark.parametrize("length", [None, 3])
async def test_preview_and_simulate_return_the_same_payload(
    hass, hass_ws_client, setup_scheduler, length
):
    """A comment claimed they "cannot drift apart" while they already had.

    They now share block.preview_payload, so this pins the claim instead of
    trusting it.
    """
    await setup_scheduler([
        Rule(id="a", profile=1, day="1", time=time(18, 0),
             action="climate.turn_on"),
        Rule(id="b", profile=1, day="1", time=time(18, 0),
             action="climate.turn_off"),
        Rule(id="c", profile=3, day="1", time=time(11, 0),
             action="climate.turn_on"),
    ], defaults={"target": {"entity_id": ["climate.a"]}})

    service_data = {} if length is None else {"block_length": length}
    from_service = await hass.services.async_call(
        DOMAIN, "simulate", service_data, blocking=True, return_response=True
    )

    client = await hass_ws_client(hass)
    command = {"id": 1, "type": "shabbat_scheduler/preview"}
    if length is not None:
        command["block_length"] = length
    await client.send_json(command)
    msg = await client.receive_json()

    assert msg["success"]
    assert msg["result"] == from_service
    # ...and both actually found the conflict hiding behind the defaults.
    if length is None:
        assert [c["targets"] for c in from_service["conflicts"]] == [["climate.a"]]


async def test_list_carries_the_block_so_the_card_can_draw_dates(
    hass, hass_ws_client, setup_scheduler
):
    entry = await setup_scheduler()
    client = await hass_ws_client(hass)

    await client.send_json_auto_id({"type": "shabbat_scheduler/rules/list"})
    result = (await client.receive_json())["result"]

    assert result["block"]["length"] == 1
    assert result["block"]["dates"]["erev"] == "2026-08-14"
    assert result["block"]["dates"]["1"] == "2026-08-15"
    assert result["block"]["candle_lighting"].startswith("2026-08-14T")
    assert result["block"]["havdalah"].startswith("2026-08-15T")


async def test_block_is_null_when_the_zmanim_are_missing(hass, hass_ws_client):
    """No Jewish Calendar sensors - the card must render a real message,
    not an empty timeline it cannot explain."""
    await hass.config.async_set_time_zone("Asia/Jerusalem")
    store = RuleStore(hass)
    await store.async_load()
    entry = MockConfigEntry(domain=DOMAIN, title="Shabbat Scheduler")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    client = await hass_ws_client(hass)
    await client.send_json_auto_id({"type": "shabbat_scheduler/rules/list"})
    result = (await client.receive_json())["result"]

    assert result["block"] is None


async def test_list_carries_the_master_entity_id(hass, hass_ws_client, setup_scheduler):
    entry = await setup_scheduler()
    client = await hass_ws_client(hass)

    await client.send_json_auto_id({"type": "shabbat_scheduler/rules/list"})
    result = (await client.receive_json())["result"]

    registry = er.async_get(hass)
    expected = registry.async_get_entity_id(
        "switch", DOMAIN, f"{entry.entry_id}_master"
    )
    assert expected is not None
    assert result["master_entity_id"] == expected
    assert hass.states.get(result["master_entity_id"]) is not None


# --- Final review I1: a block change must reach an open card -------------
#
# The only push trigger used to be SIGNAL_RULES_CHANGED, dispatched only by
# the store's change listener. `engine.current_block` also changes at
# havdalah, at hold release and on restart-restore, and none of those is a
# store mutation - so a wall tablet left open kept rendering LAST week's
# dates for the whole following week, and on a 3-day chag kept filtering
# `profile == block.length` against the stale block: showing rules that
# will not fire, hiding every rule that will, and marking nothing stale.


NEXT_WEEK_ZMANIM = {
    "sensor.jewish_calendar_upcoming_candle_lighting": "2026-08-21T15:38:00+00:00",
    "sensor.jewish_calendar_upcoming_havdalah": "2026-08-22T16:54:00+00:00",
}


async def _next_event(client, timeout=5):
    """The next pushed event, or None if none arrives.

    Bounded deliberately: the defect this covers is *silence*, and an
    unbounded `receive_json()` against silence hangs the whole suite
    instead of failing it.
    """
    try:
        return await asyncio.wait_for(client.receive_json(), timeout)
    except (TimeoutError, asyncio.TimeoutError):
        return None


async def test_the_block_rolling_forward_reaches_an_open_subscriber(
    hass, hass_ws_client, setup_scheduler
):
    """The havdalah roll-forward is not a store mutation, so nothing used
    to tell a subscribed card about it."""
    await setup_scheduler()
    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "shabbat_scheduler/subscribe"})
    assert (await client.receive_json())["success"]

    snapshot = await _next_event(client)
    assert snapshot["event"]["block"]["dates"]["erev"] == "2026-08-14"

    for entity_id, state in NEXT_WEEK_ZMANIM.items():
        hass.states.async_set(entity_id, state)
    await hass.async_block_till_done()

    engine = list(hass.data[DOMAIN].values())[0]["engine"]
    assert engine.current_block.erev_date.isoformat() == "2026-08-21", (
        "the engine itself did not advance; the test would be vacuous"
    )

    pushed = await _next_event(client)
    assert pushed is not None, "the block advanced and no card was told"
    assert pushed["type"] == "event"
    assert pushed["event"]["block"]["dates"]["erev"] == "2026-08-21"


async def test_a_refresh_that_changes_nothing_pushes_nothing(
    hass, hass_ws_client, setup_scheduler
):
    """Dispatching on every refresh rather than on a real block change
    would push on every zmanim re-publish and twice on every rule edit."""
    await setup_scheduler()
    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "shabbat_scheduler/subscribe"})
    assert (await client.receive_json())["success"]
    assert await _next_event(client) is not None  # the initial snapshot

    engine = list(hass.data[DOMAIN].values())[0]["engine"]
    before = engine.current_block
    await engine.async_refresh()
    await hass.async_block_till_done()
    assert engine.current_block == before, "the block moved; test is vacuous"

    await client.send_json({"id": 2, "type": "shabbat_scheduler/rules/list"})
    msg = await client.receive_json()
    assert msg["id"] == 2, "a refresh with no block change pushed anyway"


# --- Task 11: the per-rule outcome, on the wire --------------------------


async def test_the_payload_carries_each_rules_own_last_outcome(
    hass, hass_ws_client, setup_scheduler
):
    """One verdict per rule, not one for the whole integration.

    `engine.last_run` never reached the card at all, and could not have
    usefully: the next rule to act overwrites it, so by the time anyone
    looks it describes some other rule.
    """
    entry = await setup_scheduler([
        Rule(id="blocked", profile=1, day="1", time=time(11, 0),
             action="climate.turn_on", target={"entity_id": ["climate.a"]}),
        Rule(id="ran", profile=1, day="1", time=time(12, 0),
             action="climate.turn_off", target={"entity_id": ["climate.a"]}),
        Rule(id="never", profile=1, day="1", time=time(13, 0),
             action="climate.turn_off", target={"entity_id": ["climate.a"]}),
    ])
    store = hass.data[DOMAIN][entry.entry_id]["store"]
    await store.async_record_outcome("blocked", {
        "outcome": "blocked", "at": "2026-08-25T18:00:00+00:00",
        "detail": "condition 1 of 1 (state on input_boolean.kids) not met",
    })
    await store.async_record_outcome("ran", {
        "outcome": "called", "at": "2026-08-25T19:00:00+00:00", "detail": None,
        "unknown_targets": ["climate.typo"],
    })

    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "shabbat_scheduler/rules/list"})
    msg = await client.receive_json()
    assert msg["success"], msg.get("error")
    by_id = {rule["id"]: rule for rule in msg["result"]["rules"]}

    assert by_id["blocked"]["last_outcome"]["outcome"] == "blocked"
    assert "input_boolean.kids" in by_id["blocked"]["last_outcome"]["detail"]
    assert by_id["ran"]["last_outcome"]["outcome"] == "called"
    # The diagnostics ride ALONGSIDE the outcome rather than replacing it.
    assert by_id["ran"]["last_outcome"]["unknown_targets"] == ["climate.typo"]
    # Present and null, not absent: the card reads one field either way.
    assert "last_outcome" in by_id["never"]
    assert by_id["never"]["last_outcome"] is None


async def test_a_client_cannot_forge_a_last_outcome(
    hass, hass_ws_client, setup_scheduler
):
    """A forged verdict is the one lie this feature must make impossible.

    The card now reads `last_outcome` off every rule in the payload, so a
    read-modify-write client echoes it back and must not be refused for it
    - but a client that could SET it could make the card report "fired"
    for a rule that never ran, on the one day nobody can check.
    """
    await setup_scheduler()
    client = await hass_ws_client(hass)
    forged = {"outcome": "called", "at": "2020-01-01T00:00:00+00:00",
              "detail": "never happened"}

    await client.send_json({
        "id": 1,
        "type": "shabbat_scheduler/rules/create",
        "rule": {**NEW_RULE, "last_outcome": forged},
    })
    msg = await client.receive_json()
    # Dropped, not rejected - the echo must keep working, like the two
    # migration fields before it.
    assert msg["success"], msg.get("error")
    rule_id = msg["result"]["rule"]["id"]
    # It is not a rule field at all, so it cannot even ride along in the
    # create response.
    assert "last_outcome" not in msg["result"]["rule"]

    await client.send_json({
        "id": 2,
        "type": "shabbat_scheduler/rules/update",
        "rule_id": rule_id,
        "changes": {"last_outcome": forged, "name": "renamed"},
    })
    msg = await client.receive_json()
    assert msg["success"], msg.get("error")

    await client.send_json({"id": 3, "type": "shabbat_scheduler/rules/list"})
    listed = (await client.receive_json())["result"]["rules"][0]
    assert listed["name"] == "renamed"     # the honest half of the edit landed
    assert listed["last_outcome"] is None  # the forged half did not

    reloaded = RuleStore(hass)
    await reloaded.async_load()
    assert reloaded.last_outcome(rule_id) is None
