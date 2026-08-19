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
