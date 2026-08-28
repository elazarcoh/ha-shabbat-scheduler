"""The card inside a real Home Assistant.

happy-dom proves the elements render in a fake DOM. Only this proves they
render in Home Assistant - which is where an earlier card on this project
looked correct and was not.

Navigation target: dev/seed.py seeds the card onto a dashboard at
/shabbat-scheduler/0, not the plan's original /lovelace/0. In Home
Assistant 2026.8 the built-in default dashboard's panel is registered
with no config (kept only for backward compatibility) and the frontend
client-side redirects any visit to it - including a direct link to
/lovelace/0 - to the new built-in /home panel instead of rendering the
saved views. That is confirmed, reproducible behavior of this real HA
release, not a harness bug; see dev/seed.py's seed_dashboard() docstring.
A dashboard created the way a real user would (lovelace/dashboards/create)
is unaffected, so that is where the card actually lives here.
"""

import json
import urllib.request

from playwright.sync_api import expect

# Must match dev/seed.py's DASHBOARD_URL_PATH - that script creates the
# dashboard this test navigates to.
DASHBOARD_URL_PATH = "shabbat-scheduler"


# --- driving Home Assistant's own pickers ---------------------------------
#
# These are HA frontend internals, not a public API. They were found by
# dumping shadow roots against the running dev instance, and the structure
# is written down in dev/README.md so the next person does not have to.
#
# Three things about them are easy to get wrong:
#
# 1. The two pickers have DIFFERENT triggers. `ha-service-picker` slots an
#    `ha-picker-field`; `ha-target-picker` slots an `ha-button` labelled
#    "Add target". No single selector opens both.
# 2. Once an action is set, `ha-service-control` renders its OWN
#    `ha-selector.target-selector`, holding a SECOND `ha-target-picker`
#    and a second `ha-picker-combo-box`. Every target locator below is
#    therefore scoped to `shabbat-target-editor` and never to the dialog:
#    unscoped it is ambiguous, and the one it would reach is HA's
#    internal one, whose value this card deliberately discards - so the
#    test would author a target that never reaches the rule.
# 3. The results list is a `lit-virtualizer`, so only the rows currently
#    on screen exist in the DOM. Search first, then read rows.
ACTION_PICKER = "shabbat-service-editor ha-service-control ha-service-picker"
TARGET_PICKER = "shabbat-target-editor ha-target-picker"
SERVICE_FIELDS = "shabbat-service-editor ha-service-control ha-settings-row"


def _choose(picker, trigger, query, *narrow):
    """Open one of HA's combo-box pickers and choose exactly one row.

    `narrow` is applied as successive text filters and the result MUST
    match exactly one row. Asserting that instead of clicking `.first` is
    deliberate: searching the action list for 'set_temperature' returns
    both climate's and water_heater's, and searching an entity name
    returns the generic_thermostat's backing input_boolean alongside the
    climate entity. A `.first` that silently picked the wrong domain
    would leave a test that passes while authoring a rule against an
    entirely different integration.
    """
    picker.locator(trigger).first.click()
    combo = picker.locator("ha-picker-combo-box")
    combo.locator("input").first.fill(query)
    rows = combo.locator(".combo-box-row")
    for term in narrow:
        rows = rows.filter(has_text=term)
    expect(rows).to_have_count(1, timeout=15_000)
    rows.click()
    # The popover closing is how we know the choice was taken, and it is
    # also what must happen before the next picker can be clicked.
    expect(combo).to_have_count(0, timeout=15_000)


def _set_action(dialog, query, *narrow):
    picker = dialog.locator(ACTION_PICKER)
    picker.wait_for(timeout=15_000)
    _choose(picker, "ha-picker-field", query, *narrow)


def _set_target_entity(dialog, query, *narrow):
    # Wait on the `ha-selector` the card actually renders, not on the
    # picker: the whole point of the target editor is that the picker
    # arrives via ha-selector's dynamic import, so it is not there yet.
    dialog.locator("shabbat-target-editor ha-selector").wait_for(timeout=15_000)
    picker = dialog.locator(TARGET_PICKER)
    picker.wait_for(timeout=15_000)
    _choose(picker, "ha-generic-picker ha-button", query, *narrow)


def _set_time(dialog, hh_mm_ss):
    """Fill the rule dialog's time field, `<ha-selector class="time"
    .selector=${{time:{}}}>`.

    Verified against the real dev container (HA 2026.8.2), not guessed:
    `ha-selector` -> `ha-selector-time` -> `ha-time-input` ->
    `ha-base-time-input`, which renders exactly three
    `input[type=number]` fields in hour/minute/second order (named
    `hours`/`minutes`/`seconds`) - the same `ha-base-time-input` shape the
    duration selector uses (see dev/README.md and
    test_replay_can_be_switched_on_with_a_window). Playwright locators
    pierce all of that shadow DOM, so a flat `input` descendant locator
    reaches all three directly.

    Each field only commits a `value-changed` on blur, using whatever the
    other two fields currently hold - so filling hour then minute can
    momentarily emit a stale combination built from the old, not-yet-typed
    third field. That is harmless here: by the time the third field is
    filled, the first two already hold their target values, and the
    dialog's own next click (Save, or moving to another field) blurs the
    last one and commits the correct HH:MM:SS.

    DO NOT pass hour 12 to this function. Diagnostic dumps (2026-08-28)
    against a real CI run of `test_editing_a_rule_redraws_the_timeline`
    (the only call site that ever used hour 12) showed the three
    `<input>` elements correctly holding ['12','15','00'] while the
    dialog's own bound `_form.time` - what `_onSave` actually reads - was
    already "00:15:00", consistently, and re-driving just the hour field
    up to four more times never once changed that reading. `hass.locale`
    on that run showed `time_format: 'language'` (English, which HA
    commonly renders as a 12-hour clock) - textbook "12 o'clock" AM/PM
    boundary behaviour, not a timing race: hour 11 and hour 21 (used
    elsewhere in this file) never showed this, only the one exact value
    where a 12-hour and a 24-hour reading of the same digits disagree.
    This widget is Home Assistant's own (`ha-base-time-input`), not this
    repo's to fix - avoiding the one ambiguous input is the practical
    answer, not fighting an upstream rendering choice from here.
    """
    if hh_mm_ss.startswith("12:"):
        raise ValueError("hour 12 hits a real AM/PM-boundary quirk in "
                          "ha-base-time-input - see this function's docstring")
    hour, minute, second = hh_mm_ss.split(":")
    inputs = dialog.locator("ha-selector.time input")
    inputs.nth(0).fill(hour)
    inputs.nth(1).fill(minute)
    inputs.nth(2).fill(second)


def test_the_card_renders_the_timeline(page, base_url):
    page.goto(f"{base_url}/{DASHBOARD_URL_PATH}/0")
    card = page.locator("shabbat-scheduler-card")
    card.wait_for(state="attached", timeout=30_000)

    groups = card.locator("shabbat-day-group")
    assert groups.count() == 2, "expected an erev group and a day-1 group"

    # The outer card element attaching does not mean its nested Lit
    # elements have completed their own first render yet - `subscribe`
    # resolves, then state propagates down through shabbat-day-group and
    # shabbat-rule-row on their own update cycles. Waiting for a leaf
    # that only exists once a rule row has actually rendered avoids
    # reading text before it is there.
    card.locator("shabbat-rule-row .time").first.wait_for(
        state="attached", timeout=30_000
    )

    # NOT card.inner_text(): shabbat-day-group and shabbat-rule-row each
    # own a separate shadow root, and native innerText/textContent never
    # composes across a shadow boundary belonging to a *descendant*
    # custom element - only Playwright's locators pierce shadow DOM to
    # find elements, not the browser's own text-reading APIs once one is
    # found. card.inner_text() reliably returns '' here even when the
    # card is rendering correctly, in a real browser, which is exactly
    # the "looked right, wasn't" trap this task exists to catch: it
    # would pass on a card that dropped every child by returning ''
    # against an expectation of '', so it asserts nothing. Reading the
    # specific elements the content lives in is the only way this
    # assertion means anything.
    dates = card.locator("shabbat-day-group .date").all_inner_texts()
    assert "2026-08-15" in dates

    markers = card.locator("shabbat-day-group .marker").all_inner_texts()
    assert any("Havdalah" in marker for marker in markers)


def test_the_card_shows_its_rules_in_time_order(page, base_url):
    """Each day group is sorted by time - see format.ts's buildGroups.

    The card deliberately groups by day before it sorts by time (erev's
    late rules render before day 1's early ones, chronologically
    correct for a block that spans midnight), so a flat string-sort of
    every `.time` on the card is not the right check - it would fail
    against exactly the ordering the card is supposed to have. Checking
    within each shabbat-day-group is what "in time order" actually
    means here.
    """
    page.goto(f"{base_url}/{DASHBOARD_URL_PATH}/0")
    card = page.locator("shabbat-scheduler-card")
    card.wait_for(state="attached", timeout=30_000)
    card.locator("shabbat-rule-row .time").first.wait_for(
        state="attached", timeout=30_000
    )

    groups = card.locator("shabbat-day-group")
    for index in range(groups.count()):
        times = groups.nth(index).locator("shabbat-rule-row .time").all_inner_texts()
        assert times == sorted(times), f"group {index} not in time order: {times}"


def test_the_card_lays_out_right_to_left_in_hebrew(page, base_url):
    """Hebrew is the language this household actually uses. A card that
    only works in English is a card that does not work.

    Setting the language via `frontend/set_user_data` (as HA's own docs
    suggest) persists correctly server-side - `frontend/get_user_data`
    confirms it - but on this HA release `hass.language` is decided
    before that value round-trips back on the next page load, so the
    card still rendered English. The frontend's own language store
    reads a `selectedLanguage` localStorage key first and only falls
    back to the server value if that key is absent (found by grepping
    the shipped frontend bundle for it - a second confirmed instance of
    this task's whole premise, that only a real browser session shows
    what actually decides rendering). Setting it directly, the same way
    this suite already injects the auth token, is what actually works.
    """
    page.context.add_init_script(
        "localStorage.setItem('selectedLanguage', JSON.stringify('he'));"
    )
    page.goto(f"{base_url}/{DASHBOARD_URL_PATH}/0")
    card = page.locator("shabbat-scheduler-card")
    card.wait_for(state="attached", timeout=30_000)

    direction = card.evaluate("el => getComputedStyle(el).direction")
    assert direction == "rtl"


def _card(page, base_url):
    page.goto(f"{base_url}/shabbat-scheduler/0")
    card = page.locator("shabbat-scheduler-card")
    card.wait_for(state="attached", timeout=30_000)
    card.locator("shabbat-rule-row .time").first.wait_for(timeout=30_000)
    return card


def test_editing_a_rule_redraws_the_timeline(page, base_url):
    """The whole loop this card exists for: change a time, and see it.

    happy-dom cannot prove this - it has no layout, no real focus, and a
    forgiving event model. Only a browser does.

    The undo is in a `finally`. This test mutates the shared dev fixture,
    and an assertion that fails halfway leaves the rule at 10:15 - so the
    next run starts from a different fixture than this one did and the
    suite stops being repeatable, which is precisely the property e2e is
    here to provide.
    """
    card = _card(page, base_url)
    dialog = card.locator("shabbat-rule-dialog")
    before = card.locator("shabbat-rule-row .time").all_inner_texts()
    assert "11:00" in before

    try:
        card.locator("shabbat-rule-row").filter(has_text="11:00").first.click()
        dialog.wait_for(state="attached", timeout=10_000)

        _set_time(dialog, "10:15:00")
        dialog.locator("button.save").click()

        # No optimistic update: the redraw only happens once the server has
        # accepted and pushed the new state back over the SIGNAL_RULES_CHANGED
        # subscription. 10:15, deliberately not noon - see _set_time's
        # docstring for the real, found cause of this test's long-standing
        # CI failure: hour 12 hits an upstream AM/PM-boundary quirk in
        # ha-base-time-input that has nothing to do with this wait.
        card.locator("shabbat-rule-row .time").filter(has_text="10:15").first.wait_for(
            timeout=15_000
        )
        after = card.locator("shabbat-rule-row .time").all_inner_texts()
        assert "10:15" in after
        assert "11:00" not in after
    finally:
        # Put it back, so the fixture is unchanged for the next run. A
        # fresh `_card()` first, deliberately, not the same `card`/`dialog`
        # captured above: the time widget is a single reused element bound
        # to whichever rule is open, and reverting through the SAME live
        # widget instance that just handled the 10:15 edit is exactly the
        # shape of bug this test exists to catch elsewhere in this file
        # (a value carried over from one edit into the next) - a real
        # navigation forces the widget to rebuild from the server's own
        # current value instead of whatever state it was last left in.
        card = _card(page, base_url)
        dialog = card.locator("shabbat-rule-dialog")
        if card.locator("shabbat-rule-row").filter(has_text="10:15").count():
            card.locator("shabbat-rule-row").filter(has_text="10:15").first.click()
            dialog.wait_for(state="attached", timeout=10_000)
            _set_time(dialog, "11:00:00")
            dialog.locator("button.save").click()
            card.locator("shabbat-rule-row .time").filter(
                has_text="11:00"
            ).first.wait_for(timeout=30_000)


def test_the_add_button_creates_a_rule_on_its_own_day(page, base_url):
    """The rule must land on the day whose button was pressed.

    Two things make this an actual guard rather than a name.

    1. It drives **day 1's** button, not erev's. Erev is what every
       fallback in the chain falls back TO - `EMPTY_FORM.day`, and the
       `?? 'erev'` in card.ts - so a create authored on erev passes
       whether or not the target day is honoured at all. Day 1 is the
       only choice that can tell the two apart.
    2. Every assertion is scoped to a day group, never to the card. A
       card-wide locator passes for a rule created on ANY day - proven by
       driving the day-1 button and running the old card-wide assertion,
       which passed while the erev group held zero matching rows.

    Break either the card's `.day` binding or the dialog's `day` stamp and
    every rule added from every day's button is created on erev - an air
    conditioner acting on the wrong day of a three-day Chag - while a
    card-wide assertion on erev's own button stays green through all of it.

    Since v2 the create also has to author an ACTION and a TARGET through
    Home Assistant's own elements, because `rule_schema._action` requires
    'domain.service' and an empty action is refused by the server. That is
    why this test failed on the v2 dialog: it filled only the time.
    """
    card = _card(page, base_url)
    erev = card.locator("shabbat-day-group").first
    day_one = card.locator("shabbat-day-group").nth(1)
    dialog = card.locator("shabbat-rule-dialog")

    try:
        day_one.locator("button.add").click()
        dialog.wait_for(state="attached", timeout=10_000)
        _set_time(dialog, "21:00:00")

        # The action, through HA's own service control...
        _set_action(dialog, "switch.turn_on", "turn_on", "switch")
        # ...and the target, through ha-selector's dynamically imported
        # ha-target-picker.
        _set_target_entity(dialog, "dev_pump", "switch")

        dialog.locator("button.save").click()

        # In the day-1 group...
        day_one.locator("shabbat-rule-row .time").filter(
            has_text="21:00"
        ).first.wait_for(timeout=15_000)
        assert day_one.locator("shabbat-rule-row .time").filter(
            has_text="21:00"
        ).count() == 1
        # ...and nowhere else. Without this line the assertion above is
        # satisfied by a rule that also exists on erev, and with a
        # card-wide locator it is satisfied by one that exists ONLY there.
        assert erev.locator("shabbat-rule-row .time").filter(
            has_text="21:00"
        ).count() == 0
        assert card.locator("shabbat-rule-row .time").filter(
            has_text="21:00"
        ).count() == 1

        # And what was authored is what came back. The rule row's `.brief`
        # is rendered from the SERVER's copy of the rule (there is no
        # optimistic update - see the edit test), so this is the line that
        # notices if the pickers were driven but their values never
        # reached the payload: drop `service-changed`'s action or
        # `target-changed`'s value and the save is refused or the brief
        # comes back naming something else, while all three day-scoped
        # counts above stay green.
        brief = day_one.locator("shabbat-rule-row").filter(
            has_text="21:00"
        ).locator(".brief").inner_text()
        assert "switch.turn_on" in brief, brief
        assert "switch.dev_pump" in brief, brief
    finally:
        # Remove it again so the fixture is unchanged.
        if card.locator("shabbat-rule-row").filter(has_text="21:00").count():
            card.locator("shabbat-rule-row").filter(has_text="21:00").first.click()
            dialog.wait_for(state="attached", timeout=10_000)
            dialog.locator("button.delete").click()
            card.locator("shabbat-rule-row .time").filter(
                has_text="21:00"
            ).wait_for(state="detached", timeout=15_000)


def test_a_preview_profile_shows_no_dates(page, base_url):
    """Selecting a profile that isn't the active block's own length is a
    PREVIEW - see format.ts's isPreview - and the card must not claim real
    calendar dates for it.

    Two things this test must NOT do, both of which it did before:

    1. Read `card.inner_text()`. shabbat-block-header's `.preview` banner
       sits behind its own shadow root (as shabbat-day-group's `.date`
       does - see test_the_card_renders_the_timeline above), so native
       innerText never composes across it. `card.inner_text()` reliably
       returns '' here even when the banner is rendering correctly, which
       would let this assertion pass against a card that dropped the
       banner entirely. Locating `.preview` directly, the way Playwright's
       locators pierce shadow DOM, is the only way the assertion means
       anything.
    2. Assert `all(... for date in dates)` without first pinning how many
       dates there should be. `all()` over an empty list is True, so a
       selector that matched nothing would pass this exact assertion while
       checking nothing at all.
    """
    card = _card(page, base_url)

    # Baseline, proven first: the default 1-day profile is the active
    # block's own length, so it is NOT a preview. If the assertions below
    # were vacuous - matching zero elements either way - this baseline
    # would pass right alongside the preview case and the pair would prove
    # nothing. Pinning both the group count and that a real date is shown
    # here is what makes the preview-mode assertions below mean something.
    assert card.locator(".preview").count() == 0
    baseline_groups = card.locator("shabbat-day-group")
    assert baseline_groups.count() == 2, "expected an erev group and a day-1 group"
    baseline_dates = card.locator("shabbat-day-group .date").all_inner_texts()
    assert len(baseline_dates) == 2
    assert any(date.strip() for date in baseline_dates), baseline_dates

    # Switch to the 3-day profile. The active block is 1 day, so this is a
    # preview: erev + 3 days is 4 groups, none of which may carry a date.
    card.locator("shabbat-block-header button.chip").nth(2).click()

    preview = card.locator(".preview")
    preview.wait_for(state="attached", timeout=10_000)
    assert preview.count() == 1
    preview_text = preview.inner_text()
    assert "Preview" in preview_text or "תצוגה" in preview_text, preview_text

    groups = card.locator("shabbat-day-group")
    assert groups.count() == 4, "3-day profile: erev + 3 days"

    dates = card.locator("shabbat-day-group .date").all_inner_texts()
    assert len(dates) == 4
    assert all(date.strip() == "" for date in dates), dates


# The Cancel button is the only one in `.actions` with no class of its own
# (see rule-dialog.ts); the others are .delete, .duplicate and .save, and
# which of them are rendered depends on whether the dialog is a create or
# an edit. Locating Cancel positionally - `.actions button` first - is
# therefore right for a create and wrong for an edit.
CANCEL = ".actions button:not([class])"


def _open_rule(card, time_text):
    """Click a rule row by its displayed time; return the open dialog."""
    card.locator("shabbat-rule-row").filter(has_text=time_text).first.click()
    dialog = card.locator("shabbat-rule-dialog")
    dialog.wait_for(state="attached", timeout=10_000)
    return dialog


def _open_create(card, group=0):
    dialog = card.locator("shabbat-rule-dialog")
    card.locator("shabbat-day-group").nth(group).locator("button.add").click()
    dialog.wait_for(state="attached", timeout=10_000)
    return dialog


def test_the_service_control_renders_a_real_service_schema(page, base_url):
    """The point of v2 on the frontend: the form comes from HA's schema.

    A hand-written form would show the same fields for every service.
    Choosing a service that HA says takes data must produce a field that
    a service HA says takes none does not.

    WHAT IS ASSERTED, AND WHY IT IS NOT `temperature`. The brief asks for
    a temperature field. `climate.set_temperature` declares `temperature`
    behind a `supported_features` filter, and `ha-service-control` only
    renders a filtered field once its OWN internal target selector names
    an entity with that feature. This card deliberately does not pass a
    target down to `ha-service-control` (see service-editor.ts: its
    target UI depends on `ha-target-picker`, which is not pre-registered
    on a dashboard, so the card owns the target separately), so
    `temperature` never appears here and asserting on it would assert on
    a field this card can never show. `hvac_mode` is the unfiltered field
    of the same service and carries exactly the same proof: it is present
    for `climate.set_temperature`, absent for `switch.turn_on`, and only
    Home Assistant's schema knows the difference.

    The difference is asserted in BOTH directions - the field appears,
    then goes away again when the action changes back. A one-way check
    passes against a form that renders every field it has ever seen.

    Nothing is saved: the whole test lives inside an unsaved create
    dialog and ends on Cancel, so it cannot leave the fixture dirty.
    """
    card = _card(page, base_url)
    dialog = _open_create(card)
    fields = dialog.locator(SERVICE_FIELDS)

    # switch.turn_on takes no data at all.
    _set_action(dialog, "switch.turn_on", "turn_on", "switch")
    expect(fields).to_have_count(0)

    # climate.set_temperature does, and HA's schema is what says so.
    _set_action(dialog, "climate.set_temperature", "set_temperature", "climate")
    expect(fields).to_have_count(1)
    expect(fields).to_contain_text("hvac_mode")
    # And it arrives as a TYPED selector, not as a text box this card
    # wrote: ha-service-control hands the field's `state` selector to an
    # `ha-selector`, which is something only HA's own schema can supply.
    expect(fields.locator("ha-selector")).to_have_count(1)

    # Back again: the field is gone, and `hvac_mode` is gone with it.
    _set_action(dialog, "switch.turn_on", "turn_on", "switch")
    expect(fields).to_have_count(0)
    expect(dialog.locator("shabbat-service-editor")).not_to_contain_text("hvac_mode")

    dialog.locator(CANCEL).click()
    dialog.wait_for(state="detached", timeout=10_000)


def test_the_target_selector_causes_ha_target_picker_to_be_defined(page, base_url):
    """ha-selector's dynamic import is the whole reason we use it.

    `ha-target-picker` is NOT pre-registered on a dashboard - this test
    proves that first rather than assuming it. Handing `ha-selector` a
    `{target: {}}` selector makes it become defined. If this ever stops
    being true, the target editor renders nothing and this is the test
    that says so.

    A CREATE dialog on purpose. In an EDIT dialog the rule already has an
    action, so `ha-service-control` renders its own internal
    `ha-selector.target-selector` and imports `ha-target-picker` by
    itself - which would make this test pass with the card's own target
    editor deleted outright. With an empty action there is exactly one
    `ha-target-picker` in the dialog and it is the card's, which is what
    the count below pins down.

    Registration alone is also not enough to assert: a class registered
    but never upgraded would satisfy `customElements.get` while the
    target editor showed an empty box. So the picker's own rendered
    trigger is checked too.
    """
    card = _card(page, base_url)

    defined = "() => customElements.get('ha-target-picker') !== undefined"
    assert page.evaluate(defined) is False, (
        "ha-target-picker was already registered before the dialog opened, "
        "so this test can no longer prove ha-selector imported it"
    )

    dialog = _open_create(card)
    picker = dialog.locator(TARGET_PICKER)
    picker.wait_for(timeout=15_000)

    assert page.evaluate(defined) is True
    # Exactly one, and it is the card's own - see the docstring.
    assert picker.count() == 1
    assert dialog.locator("ha-target-picker").count() == 1
    # It really upgraded and rendered: "Add target" is ha-target-picker's
    # own trigger, inside its own shadow root.
    expect(picker.locator("ha-generic-picker ha-button")).to_have_count(1)

    dialog.locator(CANCEL).click()
    dialog.wait_for(state="detached", timeout=10_000)


# Deliberately NOT the editor's own default. "Add condition" inserts
# `{condition: state}` (condition-editor.ts's NEW_CONDITION), and a
# fixture equal to the code's default round-trips identically whether or
# not the text is ever read, so it would prove nothing about the body
# being carried. `input_boolean.kids` exists on the dev instance, so HA's
# own condition schema accepts this.
CONDITION_YAML = 'condition: state\nentity_id: input_boolean.kids\nstate: "on"'


def test_a_condition_can_be_added_and_survives_a_save(page, base_url):
    """Authored conditions must round-trip through the server.

    The reload is what makes this a round trip rather than a re-read of
    the dialog's own state: a full `goto` discards every bit of frontend
    state, so what comes back came from `.storage` through
    `rules/list`.

    Uses the day-1 18:00 rule, which no other test in this file touches.
    Every mutating test here picks a different rule on purpose - the edit
    test drives 11:00, the add test creates 21:00, replay drives erev's
    23:00. Each already undoes itself in a `finally`, but two tests
    editing ONE rule would still interleave badly the moment anything ran
    them out of file order or in parallel (pytest-xdist is installed), and
    a suite whose result depends on its own ordering is not one to trust a
    card on.
    """
    card = _card(page, base_url)
    try:
        dialog = _open_rule(card, "18:00")
        editor = dialog.locator("shabbat-condition-editor")
        editor.wait_for(timeout=10_000)
        # Baseline, proven rather than assumed: this rule has no condition
        # yet (dev/seed.py seeds `condition: []`), so nothing below can be
        # satisfied by one that was already there.
        expect(editor.locator("textarea")).to_have_count(0)

        editor.locator("button.add-condition").click()
        textarea = editor.locator("textarea")
        expect(textarea).to_have_count(1)
        expect(textarea).to_have_value("condition: state")
        textarea.fill(CONDITION_YAML)

        dialog.locator("button.save").click()
        # The dialog closes only on a save the SERVER accepted (card.ts's
        # `_onSave`: `if (ok) this._closeDialogs()`), so this is the
        # acceptance check. A rejected condition leaves it open.
        dialog.wait_for(state="detached", timeout=15_000)

        card = _card(page, base_url)
        dialog = _open_rule(card, "18:00")
        textarea = dialog.locator("shabbat-condition-editor textarea")
        expect(textarea).to_have_count(1)
        text = textarea.input_value()
        # The BODY came back, not just a condition-shaped placeholder.
        assert "entity_id: input_boolean.kids" in text, text
        assert "condition: state" in text, text
        assert "on" in text.split("state:")[-1], text
        # Stated as an absence too: had the server or the card kept only
        # the default that "Add condition" inserted, every assertion
        # above except the entity_id one would still hold.
        assert text.strip() != "condition: state", text
        dialog.locator(CANCEL).click()
    finally:
        # Put the rule back, so the fixture is unchanged for the next run.
        card = _card(page, base_url)
        dialog = _open_rule(card, "18:00")
        if dialog.locator("shabbat-condition-editor textarea").count():
            dialog.locator("button.remove-condition").first.click()
            expect(dialog.locator("shabbat-condition-editor textarea")).to_have_count(0)
            dialog.locator("button.save").click()
            dialog.wait_for(state="detached", timeout=15_000)


def test_replay_can_be_switched_on_with_a_window(page, base_url):
    """And must come back switched on, with its window, after a reload.

    The window is set to something that is NOT replay-editor.ts's
    DEFAULT_WITHIN of '01:00:00'. That default is what the editor offers
    the moment replay is enabled, so a test that saved it could not tell
    "the window round-tripped" apart from "the editor re-offered its own
    default on reload" - the two produce the same screen.

    Uses the erev 23:00 rule, which no other test in this file touches.

    Verified against the real dev container (HA 2026.8.2). Three DOM/
    behaviour facts that are NOT how they would naively be guessed:

    - `ha-selector`'s boolean selector renders `ha-selector-boolean` ->
      `ha-formfield` -> a slotted `<ha-switch>`, whose own internal
      `<input type="checkbox" role="switch">` reflects the checked state
      for assertions - but CLICKING that inner input directly does
      nothing; only a click on `ha-switch` itself fires its toggle
      handler and the selector's `value-changed`.
    - `ha-selector`'s duration selector renders exactly one
      `ha-base-time-input` with three `input[type=number]` fields in
      hour/minute/second order (named `hours`/`minutes`/`seconds`).
      Minutes and seconds are always zero-padded to two digits
      ("00", "30"), but hours are NOT padded - `{hours: 1, ...}` renders
      as literal "1", not "01" (and `{hours: 36, ...}` renders as "36",
      unclamped, confirming replay-editor.ts's DurationValue comment).
    - The duration widget has NO clear affordance (no X button anywhere
      in it) and blanking all three fields by hand, then blurring, does
      NOT clear the value to "no bound" - it converges to an explicit
      00:00:00, which round-trips as a real (if unusual) `within` rather
      than dropping the key. See replay-editor.ts's `DurationValue` and
      `_onWithin` comments; this test's second block below exercises
      exactly that path for real, not mocked.
    """
    card = _card(page, base_url)
    try:
        dialog = _open_rule(card, "23:00")
        replay = dialog.locator("shabbat-replay-editor")
        replay.wait_for(timeout=10_000)
        enabled = replay.locator("ha-selector.replay-enabled")
        enabled_switch = enabled.locator("ha-switch")
        # Baseline: replay is off, and the window field does not exist
        # while it is. Replay being OFF by default is this integration's
        # defining behaviour, so it is worth pinning here too.
        expect(enabled_switch.locator("input")).not_to_be_checked()
        expect(replay.locator("ha-selector.replay-within")).to_have_count(0)

        enabled_switch.click()
        within = replay.locator("ha-selector.replay-within")
        within.wait_for(timeout=10_000)
        hour = within.locator("ha-base-time-input input").nth(0)
        minute = within.locator("ha-base-time-input input").nth(1)
        expect(hour).to_have_value("1")  # the offered default, 01:00:00
        expect(minute).to_have_value("00")
        hour.fill("02")
        minute.fill("30")

        dialog.locator("button.save").click()
        dialog.wait_for(state="detached", timeout=15_000)

        card = _card(page, base_url)
        dialog = _open_rule(card, "23:00")
        replay = dialog.locator("shabbat-replay-editor")
        expect(
            replay.locator("ha-selector.replay-enabled ha-switch input")
        ).to_be_checked()
        within = replay.locator("ha-selector.replay-within")
        within.wait_for(timeout=10_000)
        expect(within.locator("ha-base-time-input input").nth(0)).to_have_value("2")
        expect(within.locator("ha-base-time-input input").nth(1)).to_have_value("30")

        # Now the real clear path: blank every field of the real widget,
        # rather than mocking a `value-changed` with `undefined` (a unit
        # test covers that defensive branch; nothing before this commit
        # exercised what the real widget actually sends). It has no
        # clear/X affordance at all, and this must converge to an
        # explicit 00:00:00 - a real, saved `within` - NOT to the window
        # disappearing or replay silently reverting to unbounded. Each
        # `fill("")` already fires the field's own value-changed before
        # the next field is touched (confirmed directly against a bare
        # `<ha-selector>` outside the dialog, where blanking hours then
        # minutes then seconds emitted value-changed progressively:
        # {0,30,5} -> {0,0,5} -> {0,0,0}) - so what matters is what gets
        # SAVED, not each field's mid-edit display text, which can lag
        # behind the last field's own blur this deep inside three nested
        # shadow roots (card -> dialog -> replay-editor -> the widget's
        # own internals).
        hour = within.locator("ha-base-time-input input").nth(0)
        minute = within.locator("ha-base-time-input input").nth(1)
        second = within.locator("ha-base-time-input input").nth(2)
        hour.fill("")
        minute.fill("")
        second.fill("")

        dialog.locator("button.save").click()
        dialog.wait_for(state="detached", timeout=15_000)

        card = _card(page, base_url)
        dialog = _open_rule(card, "23:00")
        replay = dialog.locator("shabbat-replay-editor")
        # Replay is still ON - clearing the window did not turn it off,
        # and did not fall back to "no bound" (which would render with no
        # ha-selector.replay-within at all; see the baseline assertion at
        # the top of this test).
        expect(
            replay.locator("ha-selector.replay-enabled ha-switch input")
        ).to_be_checked()
        within = replay.locator("ha-selector.replay-within")
        within.wait_for(timeout=10_000)
        expect(within.locator("ha-base-time-input input").nth(0)).to_have_value("0")
        expect(within.locator("ha-base-time-input input").nth(1)).to_have_value("00")
        expect(within.locator("ha-base-time-input input").nth(2)).to_have_value("00")
        dialog.locator(CANCEL).click()
    finally:
        card = _card(page, base_url)
        dialog = _open_rule(card, "23:00")
        enabled_switch = dialog.locator(
            "shabbat-replay-editor ha-selector.replay-enabled ha-switch"
        )
        enabled_switch.wait_for(timeout=10_000)
        if enabled_switch.locator("input").is_checked():
            enabled_switch.click()
            dialog.locator("button.save").click()
            dialog.wait_for(state="detached", timeout=15_000)


def _visible_target_pickers(scope):
    """How many target pickers a user can actually see and click.

    Counting `ha-target-picker` elements is not the question - HA's own
    row is present in the DOM and merely hidden, deliberately (see
    service-editor.ts). What must be true is that exactly one is
    VISIBLE, because a second visible one is a picker whose value is
    thrown away on save.
    """
    pickers = scope.locator("ha-target-picker")
    return sum(
        1 for index in range(pickers.count()) if pickers.nth(index).is_visible()
    )


def test_only_one_target_picker_is_visible_in_the_rule_dialog(page, base_url):
    """HA's `ha-service-control` renders a target row of its own, and the
    card discards its value - so a user could set a target there, see it
    accepted, save, and lose it. service-editor.ts hides that row; this is
    the test that says so if it ever stops working.

    It has to be an EDIT, or a create with the action set: HA renders the
    row only once the chosen service's schema has a `target` key, so a
    create dialog with an empty action has nothing to hide and would pass
    this test with the suppression deleted outright. The seeded 11:00 rule
    has `input_boolean.turn_on`, whose schema does have a target.

    Both halves matter. The first pins that HA's row really is there to be
    hidden - delete the suppression and the count is 2. The second pins
    that the card's OWN picker is the one left standing, and is usable:
    hiding both would satisfy a bare count of 1 while leaving the dialog
    with no way to set a target at all.
    """
    card = _card(page, base_url)
    dialog = _open_rule(card, "11:00")
    # Wait for HA's row to have had every chance to render before counting
    # an absence: `shabbat-target-editor`'s picker arriving is what makes
    # ha-target-picker defined in the first place, so HA's row cannot
    # appear before this does.
    dialog.locator(TARGET_PICKER).wait_for(timeout=15_000)
    expect(dialog.locator("shabbat-service-editor ha-service-control ha-selector")).to_have_count(
        1, timeout=15_000
    )

    assert _visible_target_pickers(dialog) == 1, (
        "expected exactly one visible target picker; HA's own row inside "
        "ha-service-control is supposed to be suppressed"
    )
    # ...and the visible one is the card's, and it works.
    assert dialog.locator(TARGET_PICKER).is_visible()
    expect(dialog.locator(f"{TARGET_PICKER} ha-generic-picker ha-button")).to_have_count(1)
    # The suppression found something rather than silently matching
    # nothing - "we looked and found none" is a different state from "we
    # hid the row", and only one of them is correct here.
    expect(dialog.locator("shabbat-service-editor")).to_have_attribute(
        "data-target-rows-suppressed", "1"
    )

    dialog.locator(CANCEL).click()
    dialog.wait_for(state="detached", timeout=10_000)


def test_only_one_target_picker_is_visible_in_the_defaults_dialog(page, base_url):
    """The defaults dialog had the same duplicate, and worse.

    Its `<shabbat-service-editor>` exists only to shape the DATA form -
    defaults carry no action, and `_action` is never saved - so HA's
    target row appeared inside a section headed "Data", and anything set
    in it was dropped on save twice over: once by service-editor, and
    again by the dialog, which reads only `event.detail.data`.

    The action has to be chosen here, because the defaults dialog opens
    with `_action = ''` and HA renders no target row until a service is
    picked. That is exactly the sequence a user follows to fill in the
    data form, so it is the sequence that produced the bug.

    Nothing is saved: this ends on Cancel.
    """
    card = _card(page, base_url)
    dialog = card.locator("shabbat-defaults-dialog")
    card.locator("shabbat-block-header button.gear").click()
    dialog.wait_for(state="attached", timeout=10_000)
    dialog.locator(TARGET_PICKER).wait_for(timeout=15_000)

    # Baseline: with no action there is no row of HA's to hide, so the
    # count below cannot be satisfied by an empty dialog.
    assert _visible_target_pickers(dialog) == 1
    expect(dialog.locator("shabbat-service-editor")).to_have_attribute(
        "data-target-rows-suppressed", "0"
    )

    # Now pick a service, the way a user reaches the data form.
    _set_action(dialog, "climate.set_temperature", "set_temperature", "climate")
    expect(dialog.locator("shabbat-service-editor")).to_have_attribute(
        "data-target-rows-suppressed", "1", timeout=15_000
    )
    assert _visible_target_pickers(dialog) == 1, (
        "picking a service in the defaults dialog brought back a second "
        "visible target picker, under the 'Data' heading"
    )
    assert dialog.locator(TARGET_PICKER).is_visible()
    # The schema-derived form is still there - the suppression must hide
    # the target row and nothing else.
    expect(dialog.locator(SERVICE_FIELDS)).to_have_count(1)
    expect(dialog.locator(SERVICE_FIELDS)).to_contain_text("hvac_mode")
    # And VISIBLE, not merely present in the DOM. A suppression whose
    # filter matched every `ha-selector` instead of only the target row
    # would hide the entire schema-derived form - deleting the whole point
    # of v2 on the frontend - while still leaving exactly one visible
    # picker and one settings row for every assertion above to find.
    # `to_contain_text` reads the DOM, not what a user can see, so it
    # cannot notice this on its own.
    assert dialog.locator(f"{SERVICE_FIELDS} ha-selector").is_visible(), (
        "the schema-derived form was hidden along with the target row"
    )

    dialog.locator(".actions button").first.click()
    dialog.wait_for(state="detached", timeout=10_000)


def _rest_state(base_url, token, entity_id):
    request = urllib.request.Request(
        f"{base_url}/api/states/{entity_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read())["state"]


def test_run_day_for_real_actually_calls_the_real_services(page, base_url, token):
    """The exact code path a real fire uses, triggered manually.

    Profile 1 day '1' (dev/seed.py) has two real rules against
    `input_boolean.salon`: ON at 11:00 ("Shabbat morning"), then OFF at
    18:00. Run for real, in resolve_rules' own order, they leave the
    entity OFF regardless of its state before this test - so no starting
    state has to be pinned or restored.
    """
    card = _card(page, base_url)

    card.locator("shabbat-block-header button.simulate-open").click()
    dialog = card.locator("shabbat-simulate-dialog")
    dialog.wait_for(state="attached", timeout=10_000)

    dialog.locator("select.profile").select_option("1")
    dialog.locator("select.day").select_option("1")
    # "Run this day for real" now opens an inline confirm first, mirroring
    # the single-rule Run Now dialog - it does not fire on the first click.
    dialog.locator("button.run-real").click()
    dialog.locator("button.run-real-confirmed").click()

    dialog.locator(".results .row").first.wait_for(timeout=15_000)
    results_text = dialog.locator(".results").inner_text()
    assert "Fired" in results_text or "fired" in results_text.lower(), results_text

    assert _rest_state(base_url, token, "input_boolean.salon") == "off"

    dialog.locator("button:has-text('Cancel')").click()


def test_cloning_a_day_lands_a_new_rule_and_leaves_the_source_untouched(
    page, base_url
):
    """Erev (profile 1, 2 real rules) cloned onto profile 2's erev - a
    genuinely empty day, since dev/seed.py never seeds profile 2 or 3.
    """
    card = _card(page, base_url)
    source_rows_before = card.locator("shabbat-day-group").first.locator(
        "shabbat-rule-row"
    )
    assert source_rows_before.count() == 2
    source_times_before = source_rows_before.locator(".time").all_inner_texts()

    try:
        card.locator("shabbat-day-group").first.locator("button.clone-menu").click()
        dialog = card.locator("shabbat-clone-dialog")
        dialog.wait_for(state="attached", timeout=10_000)

        dialog.locator("select.target-profile").select_option("2")
        dialog.locator("select.target-day").select_option("erev")
        dialog.locator("button.mode.extend").click()
        dialog.locator("button.confirm").click()
        dialog.wait_for(state="detached", timeout=15_000)

        # Switch to the 2d profile and find the clone.
        card.locator("shabbat-block-header button.chip").nth(1).click()
        target_group = card.locator("shabbat-day-group").first
        target_group.locator("shabbat-rule-row").first.wait_for(timeout=15_000)
        assert target_group.locator("shabbat-rule-row").count() == 2
        target_times = target_group.locator(".time").all_inner_texts()
        assert sorted(target_times) == sorted(source_times_before)

        # The source (profile 1) is untouched.
        card.locator("shabbat-block-header button.chip").nth(0).click()
        source_rows_after = card.locator("shabbat-day-group").first.locator(
            "shabbat-rule-row"
        )
        assert source_rows_after.count() == 2
        assert sorted(source_rows_after.locator(".time").all_inner_texts()) == \
            sorted(source_times_before)
    finally:
        # Delete whatever landed on profile 2's erev day, so the dev
        # fixture is unchanged for the next run.
        card.locator("shabbat-block-header button.chip").nth(1).click()
        target_group = card.locator("shabbat-day-group").first
        while target_group.locator("shabbat-rule-row").count() > 0:
            target_group.locator("shabbat-rule-row").first.click()
            dialog = card.locator("shabbat-rule-dialog")
            dialog.wait_for(state="attached", timeout=10_000)
            dialog.locator("button.delete").click()
            dialog.wait_for(state="detached", timeout=15_000)


def test_overwrite_cloning_a_day_onto_itself_preserves_its_own_rules(page, base_url):
    """CRITICAL regression, against a real Home Assistant.

    `_cloneRules` (card.ts) used to delete the target day's rules FIRST
    and only THEN re-read `_state.rules` to find the source rules to clone
    from. When the target IS the source day - the clone dialog's own
    DEFAULT target, reached with zero picker interaction - the delete
    step removed the very rules being cloned from, the server's websocket
    push for that delete landed before the delete's own reply, and the
    create loop found nothing left to clone: a clean-looking success that
    silently deleted the source and replaced it with nothing.

    This is the exact zero-picker-interaction path the bug shipped with:
    open the clone menu on erev (profile 1, 2 real rules), switch to
    Overwrite, confirm - target profile and target day are left at their
    seeded defaults, which are erev's own.
    """
    card = _card(page, base_url)
    source_rows_before = card.locator("shabbat-day-group").first.locator(
        "shabbat-rule-row"
    )
    assert source_rows_before.count() == 2
    times_before = sorted(source_rows_before.locator(".time").all_inner_texts())

    try:
        card.locator("shabbat-day-group").first.locator("button.clone-menu").click()
        dialog = card.locator("shabbat-clone-dialog")
        dialog.wait_for(state="attached", timeout=10_000)

        dialog.locator("button.mode.overwrite").click()
        dialog.locator("button.confirm").click()
        dialog.wait_for(state="detached", timeout=15_000)

        rows_after = card.locator("shabbat-day-group").first.locator(
            "shabbat-rule-row"
        )
        rows_after.first.wait_for(timeout=15_000)
        assert rows_after.count() == 2
        assert sorted(rows_after.locator(".time").all_inner_texts()) == times_before
    finally:
        # However many rules erev ends up with, leave it with exactly the
        # two the fixture started with (their ids legitimately changed -
        # overwrite mode deletes and recreates - so this cannot just
        # assert; it has to actually restore the fixture for the next run).
        rows = card.locator("shabbat-day-group").first.locator("shabbat-rule-row")
        while rows.count() > 2:
            rows.first.click()
            rule_dialog = card.locator("shabbat-rule-dialog")
            rule_dialog.wait_for(state="attached", timeout=10_000)
            rule_dialog.locator("button.delete").click()
            rule_dialog.wait_for(state="detached", timeout=15_000)
