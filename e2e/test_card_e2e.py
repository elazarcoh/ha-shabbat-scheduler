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
    """
    card = _card(page, base_url)
    before = card.locator("shabbat-rule-row .time").all_inner_texts()
    assert "11:00" in before

    card.locator("shabbat-rule-row").filter(has_text="11:00").first.click()
    dialog = card.locator("shabbat-rule-dialog")
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

    # Put it back, so the fixture is unchanged for the next run.
    card.locator("shabbat-rule-row").filter(has_text="12:15").first.click()
    dialog.wait_for(state="attached", timeout=10_000)
    dialog.locator("input.time").fill("11:00:00")
    dialog.locator("button.save").click()
    card.locator("shabbat-rule-row .time").filter(has_text="11:00").first.wait_for(
        timeout=15_000
    )


def test_the_add_button_creates_a_rule_on_its_own_day(page, base_url):
    card = _card(page, base_url)
    erev = card.locator("shabbat-day-group").first

    erev.locator("button.add").click()
    dialog = card.locator("shabbat-rule-dialog")
    dialog.wait_for(state="attached", timeout=10_000)
    dialog.locator("input.time").fill("21:00:00")
    dialog.locator("button.save").click()

    card.locator("shabbat-rule-row .time").filter(has_text="21:00").first.wait_for(
        timeout=15_000
    )

    # Remove it again so the fixture is unchanged.
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
