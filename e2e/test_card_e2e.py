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

# Must match dev/seed.py's DASHBOARD_URL_PATH - that script creates the
# dashboard this test navigates to.
DASHBOARD_URL_PATH = "shabbat-scheduler"


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
    and an assertion that fails halfway leaves the rule at 12:15 - so the
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

        time_input = dialog.locator("input.time")
        time_input.fill("12:15:00")
        dialog.locator("button.save").click()

        # No optimistic update: the redraw only happens once the server has
        # accepted and pushed the new state back.
        card.locator("shabbat-rule-row .time").filter(has_text="12:15").first.wait_for(
            timeout=15_000
        )
        after = card.locator("shabbat-rule-row .time").all_inner_texts()
        assert "12:15" in after
        assert "11:00" not in after
    finally:
        # Put it back, so the fixture is unchanged for the next run.
        if card.locator("shabbat-rule-row").filter(has_text="12:15").count():
            card.locator("shabbat-rule-row").filter(has_text="12:15").first.click()
            dialog.wait_for(state="attached", timeout=10_000)
            dialog.locator("input.time").fill("11:00:00")
            dialog.locator("button.save").click()
            card.locator("shabbat-rule-row .time").filter(
                has_text="11:00"
            ).first.wait_for(timeout=15_000)


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
    """
    card = _card(page, base_url)
    erev = card.locator("shabbat-day-group").first
    day_one = card.locator("shabbat-day-group").nth(1)
    dialog = card.locator("shabbat-rule-dialog")

    try:
        day_one.locator("button.add").click()
        dialog.wait_for(state="attached", timeout=10_000)
        dialog.locator("input.time").fill("21:00:00")
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
    finally:
        # Remove it again so the fixture is unchanged.
        if card.locator("shabbat-rule-row").filter(has_text="21:00").count():
            card.locator("shabbat-rule-row").filter(has_text="21:00").first.click()
            dialog.wait_for(state="attached", timeout=10_000)
            dialog.locator("button.delete").click()
            card.locator("shabbat-rule-row .time").filter(
                has_text="21:00"
            ).wait_for(state="detached", timeout=15_000)


def test_the_settings_form_offers_only_what_every_selected_device_supports(
    page, base_url
):
    """The device-aware form, in a real browser, against real climates.

    This is the branch's headline feature and until now it had zero
    real-browser coverage: the dev fixture held only input_boolean and
    switch entities, so every e2e test ran with `options.climate ==
    False` and the intersection / narrowest-bounds / orphan logic was
    exercised only under happy-dom - the same emulator the plan documents
    as mis-rendering exactly these nested templates.

    `dev/config/configuration.yaml` seeds two generic_thermostats chosen
    so no two of the three possible selections agree:

        climate.dev_salon   hvac ['heat','off']   16.0 .. 32.0
        climate.dev_kids    hvac ['cool','off']   14.0 .. 31.0
        both                hvac ['off']          16.0 .. 31.0

    Nothing here is saved: the whole test lives inside an unsaved create
    dialog and ends on Cancel, so it cannot leave the fixture dirty.
    """
    from playwright.sync_api import expect

    card = _card(page, base_url)
    card.locator("shabbat-day-group").first.locator("button.add").click()
    dialog = card.locator("shabbat-rule-dialog")
    dialog.wait_for(state="attached", timeout=10_000)

    settings = dialog.locator("shabbat-device-settings")
    devices = settings.locator("select.devices")
    hvac = settings.locator("select.hvac")
    temperature = settings.locator("input.temperature")

    # --- one device: exactly its own modes and its own bounds ---
    devices.select_option(["climate.dev_salon"])
    expect(hvac.locator("option[value='heat']")).to_have_count(1)
    expect(temperature).to_have_attribute("min", "16")
    expect(temperature).to_have_attribute("max", "32")
    # Nothing is being intersected yet, and nothing is orphaned.
    expect(settings).not_to_contain_text("every selected device")
    expect(settings).not_to_contain_text("does not list it")

    hvac.select_option("heat")
    expect(hvac).to_have_value("heat")

    # --- both devices: the intersection, and the narrowest range ---
    devices.select_option(["climate.dev_salon", "climate.dev_kids"])

    # 'heat' is not a mode the kids' unit accepts, so it is no longer
    # offered - but the value the rule already holds is KEPT and flagged,
    # never silently dropped. A dropped setting is a rule that quietly
    # stops doing what it says.
    expect(settings).to_contain_text("every selected device")
    expect(settings).to_contain_text("does not list it")
    expect(hvac).to_have_value("heat")

    # min from the salon (16, the higher floor), max from the kids (31,
    # the lower ceiling). Sending 14 to the salon or 32 to the kids is a
    # value the device rejects - discovered at 11:00 on Shabbat morning.
    expect(temperature).to_have_attribute("min", "16")
    expect(temperature).to_have_attribute("max", "31")

    # --- and back down to one: the narrowing is not one-way ---
    devices.select_option(["climate.dev_kids"])
    expect(temperature).to_have_attribute("min", "14")
    expect(temperature).to_have_attribute("max", "31")
    expect(hvac.locator("option[value='cool']")).to_have_count(1)
    expect(hvac.locator("option[value='heat']")).to_have_count(1)  # still the orphan
    expect(settings).not_to_contain_text("every selected device")

    # Cancel: nothing was ever sent, so the fixture is untouched.
    dialog.locator(".actions button").first.click()
    dialog.wait_for(state="detached", timeout=10_000)


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
