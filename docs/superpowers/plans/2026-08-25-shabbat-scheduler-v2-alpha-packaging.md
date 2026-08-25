# Shabbat Scheduler Alpha Packaging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make this integration ready for someone who has never seen it to install, understand and trust — CI that actually runs the suites (including e2e), a README that reads as a guide rather than a reference page, a diagnostics platform, upgrade notes, and the four code items Plan 2's final review triaged into this plan rather than dropping.

**Architecture:** No new subsystem. This is packaging work layered onto a feature-complete integration: a GitHub Actions workflow, one new HA platform (`diagnostics.py`), a handful of docs, brand image assets, and small consolidations in existing modules.

**Tech Stack:** GitHub Actions, Python 3.14 + `pytest-homeassistant-custom-component`, TypeScript + Lit 3 + rollup + vitest, Playwright, Docker (the existing `dev/` throwaway HA instance).

## Global Constraints

Copied from `docs/superpowers/specs/2026-08-22-shabbat-scheduler-v2-alpha-design.md`. Every task's requirements implicitly include these.

- **Fire once, never re-assert.** Non-negotiable; no task in this plan touches firing behaviour.
- **Conflicts are warned, never resolved.**
- **No client-side revalidation.** The Python side owns validation.
- The pure modules — `models.py`, `block.py`, `device_ops.py`, `const.py`, `rule_schema.py`, `yaml_io.py`, `migration.py` — import **zero** Home Assistant; `tests/test_packaging.py` enforces it.
- **Storage must migrate, not break.** An alpha user's rules survive upgrades.
- Home Assistant **2026.8.2** or later; Python **`>=3.14.2`** (`pyproject.toml`).
- Every `frontend/src/strings.ts` key exists in **both** `en` and `he`; `custom_components/shabbat_scheduler/translations/{en,he}.json` and the top-level `strings.json` stay in parity (currently 29/29, `strings.json` byte-identical to `translations/en.json`).
- The built card bundle at `custom_components/shabbat_scheduler/www/shabbat-scheduler-card.js` is committed (a HACS install has no Node); `frontend/bundle-manifest.json` must match it — `tests/test_frontend.py::test_the_committed_bundle_matches_the_committed_sources` enforces this.
- `CARD_VERSION` lives in **both** `frontend/src/version.ts` and `custom_components/shabbat_scheduler/frontend.py`, currently `0.5.0`; `tests/test_frontend.py::test_the_bundle_version_matches_the_url_stamp` forces the two to move together. Bump both if `frontend/src` changes; leave both alone otherwise.
- Never point anything in `dev/` or `e2e/` — or a CI workflow — at `192.168.1.14`. That is the owner's live production instance and this integration is deliberately not installed there.
- **Stage explicit paths when committing, not `git add -A`.**

---

## Project Context

**Current state (2026-08-25):** 507 Python tests + 12 Playwright e2e tests + 238 frontend tests, all green. The card authors a full v2 rule. Repair issues, HACS metadata (`hacs.json`, `manifest.json`) and translation parity are already done — this plan does not re-touch them. What is missing is everything a stranger needs to trust and install this, plus the code the final review found and triaged.

**Nothing runs the suites except a human remembering to.** e2e skipped silently for the entire previous plan and nobody noticed until the final review went looking. Task 1 exists to make that permanently impossible.

**The dev instance.** `dev/docker-compose.yml` runs Home Assistant `2026.8.2` on port **8124**, `0.0.0.0`-bound, login `dev`/`devdevdev` (dev-only, plaintext is fine per elazar). `dev/seed.py` onboards (or logs in, if already onboarded — it is fully re-runnable), points the integration at fabricated `sensor.jewish_calendar_upcoming_{candle_lighting,havdalah}` states, **clears every existing rule then re-seeds four**, creates the dashboard (or reuses it), and prints an access token as its last line of stdout. Tokens last 30 minutes. `dev/README.md` documents the reset recipe and the two elements' real shadow DOM. **If e2e shows more failures than you expect, count the rules before touching anything** — `seed.py` used to append without clearing and once stacked an instance to twenty.

**Test fixture names actually used in this repo** (a prior plan's briefs got these wrong more than once — use the real ones):
- `tests/conftest.py`: `engine` fixture, `setup_scheduler` fixture (an async closure `setup_scheduler(rules=(), defaults=None, enabled=False, dry_run=False)` returning a `MockConfigEntry`), `jerusalem`, `test_booleans`, the module-level `_rule(action=, entities=, **kwargs)` helper, and the single source of `ZMANIM`.
- `engine.async_apply_rule(rule)` is the method; there is no `engine.apply`.
- `RuleStore.dry_run` is a **read-only property** — set it via `await store.async_set_dry_run(True)`.
- `frontend/test/helpers.ts` holds the shared card-render helpers (`mount`, `fakeHass`, `renderCardWithState`, `dayGroups`, `ruleRows`).

**Testing standards** — each learned by a review in the previous plan catching a test that could not fail, and still binding:
- Assert key **absence** explicitly (`"k" not in d`, `'k' in o === false`, `toStrictEqual`), never by comparing whole dicts/objects.
- A fixture equal to the code's own default proves nothing — seed non-default values.
- Drive a replace-vs-merge property in the direction where replace and merge **differ**.
- Assume a reviewer will individually revert each behaviour you add and check whether a test notices. Write the test that would notice.

---

## File Structure

**New:**
- `.github/workflows/ci.yml` — the unit/frontend/purity job.
- `.github/workflows/e2e.yml` — the Playwright-against-a-real-HA job.
- `custom_components/shabbat_scheduler/diagnostics.py` — the diagnostics platform.
- `tests/test_diagnostics.py`
- `docs/upgrading-from-v1.md`
- `brands/icon.png`, `brands/icon@2x.png`, `brands/logo.png`, `brands/logo@2x.png`, `brands/README.md`
- `dev/screenshot.py`
- `docs/images/card-screenshot.png`

**Modified:**
- `custom_components/shabbat_scheduler/const.py` — `MIN_PROFILE`, `MAX_PROFILE`.
- `custom_components/shabbat_scheduler/migration.py`, `rule_schema.py`, `websocket_api.py`, `__init__.py`, `models.py` — read the two constants instead of six independent literals.
- `tests/test_websocket.py` — its local `_setup` deleted, every call site repointed at the shared `setup_scheduler` fixture.
- `tests/test_engine.py` — one new test.
- `frontend/rollup.config.mjs`, `frontend/package.json` — a minifier.
- `README.md` — rewritten as a guide.
- `custom_components/shabbat_scheduler/const.py` — a version constant for the upgrade-notes cross-reference (only if needed; see Task 9).

---

## Task 1: CI — unit, frontend and purity

The suites that do not need a live Home Assistant instance, run on every push and pull request.

**Files:**
- Create: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: nothing.
- Produces: a `ci` workflow other tasks' commits will run under from this point on.

- [ ] **Step 1: Write the workflow**

```yaml
name: ci

on:
  push:
    branches: [master]
  pull_request:

jobs:
  python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true
      - name: Install Python 3.14
        run: uv python install 3.14
      - name: Install dependencies
        run: uv sync --all-groups
      - name: Run the Python suite (excluding e2e)
        run: uv run pytest tests

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install Node
        uses: actions/setup-node@v4
        with:
          node-version: "22"
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - name: Install dependencies
        working-directory: frontend
        run: npm ci
      - name: Typecheck
        working-directory: frontend
        run: npm run typecheck
      - name: Test
        working-directory: frontend
        run: npm test
      - name: Build, and fail if the committed bundle would change
        working-directory: frontend
        run: |
          npm run build
          git diff --exit-code -- ../custom_components/shabbat_scheduler/www/ bundle-manifest.json
```

The last step is deliberate and worth explaining in a comment in the file
itself: `tests/test_frontend.py::test_the_committed_bundle_matches_the_committed_sources`
already catches a source edited without a rebuild, from the Python side.
This step catches the same class of mistake from the git side — a
contributor who ran `npm run build` locally, forgot to `git add` the
result, and committed only the source — as a clean, readable diff rather
than a cryptic Python assertion failure.

```yaml
      - name: Run the workflow above
```

Write that build-and-diff step as an actual step in the YAML (not a
placeholder comment) with a comment above it in the file explaining the
reasoning in the paragraph above, trimmed to 2-3 lines.

- [ ] **Step 2: Push to a branch and confirm both jobs run**

```bash
git checkout -b ci/add-unit-workflow
git add .github/workflows/ci.yml
git commit -m "ci: run the Python and frontend suites on every push and PR"
git push -u origin ci/add-unit-workflow
gh pr create --fill
```

Wait for the checks to appear (`gh pr checks --watch`), or open the PR's
Checks tab. Both `python` and `frontend` must go green. If `frontend`
fails on the build-diff step, that means the committed bundle is
genuinely stale — rebuild it (`npm run build` inside `frontend/`),
commit the result, and push again; do not weaken the check.

- [ ] **Step 3: Merge**

```bash
gh pr merge --squash --delete-branch
git checkout master
git pull
```

- [ ] **Step 4: Confirm master is green**

```bash
gh run list --branch master --limit 3
```

Both jobs should show `success` for the merge commit.

---

## Task 2: CI — end-to-end, against a real Home Assistant

The suite that proves the card's four editors actually render in a
browser. This is the only guard on the target-row suppression in
`service-editor.ts`, which is the most version-fragile code in this
codebase — it matches HA's internal shadow DOM by the *shape* of a
selector, and a Home Assistant frontend update could change that shape
with no warning from anywhere else.

**Files:**
- Create: `.github/workflows/e2e.yml`

**Interfaces:**
- Consumes: `dev/docker-compose.yml`, `dev/seed.py`'s printed token, `e2e/`'s existing suite (12 tests).
- Produces: an `e2e` workflow.

- [ ] **Step 1: Write the workflow**

```yaml
name: e2e

on:
  push:
    branches: [master]
  pull_request:

jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true
      - name: Install Python 3.14
        run: uv python install 3.14
      - name: Install dependencies
        run: uv sync --all-groups
      - name: Install Playwright's Chromium
        run: uv run playwright install --with-deps chromium

      - name: Start the throwaway Home Assistant
        run: docker compose -f dev/docker-compose.yml up -d

      - name: Wait for Home Assistant to answer
        run: |
          for _ in $(seq 1 60); do
            code=$(curl -sS -o /dev/null -w "%{http_code}" http://127.0.0.1:8124/ || true)
            [ "$code" = "200" ] && exit 0
            sleep 5
          done
          echo "Home Assistant never answered on :8124" >&2
          docker compose -f dev/docker-compose.yml logs
          exit 1

      - name: Seed and capture a token
        run: |
          token=$(uv run python dev/seed.py | tail -1)
          echo "HA_DEV_TOKEN=$token" >> "$GITHUB_ENV"

      - name: Run the e2e suite
        run: uv run pytest e2e -v

      - name: Home Assistant logs (always, for post-mortem)
        if: always()
        run: docker compose -f dev/docker-compose.yml logs
```

Note the `dev/docker-compose.yml` port binding is `0.0.0.0:8124:8123` —
on a GitHub-hosted runner this is a throwaway, network-isolated VM with no
inbound access from anywhere else, so the same binding that needs a
comment of caution on a developer's own machine is inert here. Do not
change the binding for CI; a divergent compose file for CI vs. local
would itself become a thing to keep in sync.

Do not add a step that builds the frontend bundle. The committed
`custom_components/shabbat_scheduler/www/` is what a real install runs,
and `dev/docker-compose.yml` mounts `custom_components/shabbat_scheduler`
read-only into the container — this job must prove that *committed*
artifact renders, the same one HACS ships, not a freshly rebuilt one.

- [ ] **Step 2: Push and watch it actually run against a container**

```bash
git checkout -b ci/add-e2e-workflow
git add .github/workflows/e2e.yml
git commit -m "ci: run the e2e suite against a real throwaway Home Assistant

The suite that proves the card's editors render in a browser, silently
skipped for a whole previous plan because nothing ran it automatically.
This is the only guard on the target-row suppression in
service-editor.ts, which matches HA's internal shadow DOM by selector
shape and could break with the next HA frontend release with no other
warning."
git push -u origin ci/add-e2e-workflow
gh pr create --fill
gh pr checks --watch
```

If the "Wait for Home Assistant to answer" step times out, the most
likely cause is the image pull taking longer than the 60×5s budget on a
cold runner — raise the loop count rather than the sleep, and check the
printed `docker compose logs` in the job output for the real reason
before assuming that.

- [ ] **Step 3: Merge**

```bash
gh pr merge --squash --delete-branch
git checkout master
git pull
```

---

## Task 3: One shared bound for a v2 rule's `profile`

Carried from Plan 2's final review: the integer range 1..3 (a block is at
most three calendar days — Shabbat plus a two-day Chag) is spelled out
independently in six places. Six independently-spelled copies is six
places to forget when this ever changes.

**Files:**
- Modify: `custom_components/shabbat_scheduler/const.py`
- Modify: `custom_components/shabbat_scheduler/migration.py:86,90-102,106-132,347,353`
- Modify: `custom_components/shabbat_scheduler/rule_schema.py:106-117`
- Modify: `custom_components/shabbat_scheduler/websocket_api.py:129`
- Modify: `custom_components/shabbat_scheduler/__init__.py:275`
- Modify: `custom_components/shabbat_scheduler/models.py:31`
- Test: `tests/test_migration.py`, `tests/test_rule_schema.py`

**Interfaces:**
- Produces: `MIN_PROFILE = 1`, `MAX_PROFILE = 3` in `const.py`, importable
  from every pure module (`const.py` imports zero Home Assistant, so this
  does not touch the purity boundary).

- [ ] **Step 1: Add the constants**

In `custom_components/shabbat_scheduler/const.py`, near the top:

```python
# A block spans at most three calendar days - a two-day Chag adjacent to
# Shabbat. This is the one place that bound is spelled out; everywhere
# else (migration.py, rule_schema.py, websocket_api.py, __init__.py)
# imports it. It used to be six independently-typed literal "1..3"s -
# carried forward from Plan 2's final review as the kind of duplication
# that is fine right up until someone changes one copy and not the rest.
MIN_PROFILE = 1
MAX_PROFILE = 3
```

- [ ] **Step 2: Write the failing tests**

Add to `tests/test_migration.py`:

```python
from custom_components.shabbat_scheduler.const import MAX_PROFILE, MIN_PROFILE


def test_the_profile_bound_is_read_from_the_shared_constant():
    """Not a behaviour test - a guard against the bound drifting back
    into six independent literals. If MAX_PROFILE ever changes, this
    module must move with it without being separately edited."""
    from custom_components.shabbat_scheduler.migration import _parses_as_profile

    assert _parses_as_profile(MAX_PROFILE) is True
    assert _parses_as_profile(MAX_PROFILE + 1) is False
    assert _parses_as_profile(MIN_PROFILE) is True
    assert _parses_as_profile(MIN_PROFILE - 1) is False
```

Add to `tests/test_rule_schema.py`:

```python
from custom_components.shabbat_scheduler.const import MAX_PROFILE, MIN_PROFILE


def test_the_profile_bound_matches_the_shared_constant():
    from custom_components.shabbat_scheduler.rule_schema import _profile

    assert _profile(MAX_PROFILE) == MAX_PROFILE
    with pytest.raises(RuleValidationError):
        _profile(MAX_PROFILE + 1)
    with pytest.raises(RuleValidationError):
        _profile(MIN_PROFILE - 1)
```

Check the top of `tests/test_rule_schema.py` for how `RuleValidationError`
and `pytest` are already imported there and match that, rather than
adding a second import style.

- [ ] **Step 3: Run the tests and watch them fail or pass by coincidence**

```bash
uv run pytest tests/test_migration.py tests/test_rule_schema.py -v
```

Expected: these two pass already (the literals happen to agree with the
constants you just added, since nobody has changed the bound). That is
fine — they are guards against future drift, not proof of a bug today.
The point is Step 4 changing every site to import the constant, after
which these tests are exercising the real code path rather than a
coincidence.

- [ ] **Step 4: Point every site at the constant**

In `custom_components/shabbat_scheduler/migration.py`, delete the local
`_MAX_PROFILE = 3` and its comment, add `from .const import MAX_PROFILE,
MIN_PROFILE` to the imports, and replace every `_MAX_PROFILE` with
`MAX_PROFILE`, and every bare `1 <=` with `MIN_PROFILE <=` in
`_parses_as_profile` and `_parses_as_day`. Update the two f-string
messages at lines 347 and 353 to interpolate `MIN_PROFILE`/`MAX_PROFILE`
rather than the literal `1`/`3`.

In `custom_components/shabbat_scheduler/rule_schema.py`, add `from .const
import MAX_PROFILE, MIN_PROFILE` and rewrite `_profile`:

```python
def _profile(value) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise RuleValidationError(
            f"profile must be an integer {MIN_PROFILE}..{MAX_PROFILE}, got {value!r}"
        )
    if not MIN_PROFILE <= value <= MAX_PROFILE:
        raise RuleValidationError(
            f"profile must be an integer {MIN_PROFILE}..{MAX_PROFILE}, got {value!r}"
        )
    return value
```

And the `day` check just above it, which encodes the same 1..3 bound as
a tuple of strings — derive it from the constants instead of a hand-typed
tuple:

```python
_VALID_DAYS = tuple(str(n) for n in range(MIN_PROFILE, MAX_PROFILE + 1))
```

and use `text in _VALID_DAYS` in place of `text in ("1", "2", "3")`,
updating the error message's `f"day must be {EREV!r} or '1'..'3', got
{value!r}"` to interpolate `MIN_PROFILE`/`MAX_PROFILE` too.

In `custom_components/shabbat_scheduler/websocket_api.py`, add the import
and change `vol.Range(1, 3)` to `vol.Range(MIN_PROFILE, MAX_PROFILE)`.

In `custom_components/shabbat_scheduler/__init__.py`, same import and
same change to the `simulate` service's schema at line 275.

In `custom_components/shabbat_scheduler/models.py`, reword the comment at
line 31 from `# block length this rule belongs to (1, 2 or 3)` to `# block
length this rule belongs to - see MIN_PROFILE/MAX_PROFILE in const.py`,
so the comment cannot go stale independently of the bound it describes.

- [ ] **Step 5: Run the tests and the whole suite**

```bash
uv run pytest tests/test_migration.py tests/test_rule_schema.py -v
uv run pytest
uv run pytest tests/test_packaging.py
```

Expected: all pass. `test_packaging.py` confirms `const.py` staying pure
did not regress — it already imports zero Home Assistant, and this task
adds two plain integers, so it should not need to change, but run it to
be sure.

- [ ] **Step 6: Commit**

```bash
git add custom_components/shabbat_scheduler/const.py \
        custom_components/shabbat_scheduler/migration.py \
        custom_components/shabbat_scheduler/rule_schema.py \
        custom_components/shabbat_scheduler/websocket_api.py \
        custom_components/shabbat_scheduler/__init__.py \
        custom_components/shabbat_scheduler/models.py \
        tests/test_migration.py tests/test_rule_schema.py
git commit -m "refactor: one shared MIN_PROFILE/MAX_PROFILE, not six literal 1..3s

Carried from Plan 2's final review. All six sites (migration.py,
rule_schema.py x2, websocket_api.py, __init__.py, a comment in
models.py) now read the same two constants in const.py."
```

---

## Task 4: One `setup_scheduler` fixture, not two nearly-identical helpers

Carried from Plan 2's final review. `tests/test_websocket.py` has its own
local `_setup(hass, rules=(), defaults=None, enabled=False)` helper,
almost byte-identical to the shared `setup_scheduler` fixture in
`tests/conftest.py` that `tests/test_execution_domains.py` and others
already use — except `setup_scheduler` also supports `dry_run`. Two
independently-maintained copies of the same setup path is exactly the
kind of duplication the shared fixture's own docstring argues against.

**Files:**
- Modify: `tests/test_websocket.py` (51 call sites of `_setup(hass, ...)`)

**Interfaces:**
- Consumes: `setup_scheduler` fixture, signature
  `setup_scheduler(rules=(), defaults=None, enabled=False, dry_run=False) -> MockConfigEntry`
  (already in `tests/conftest.py`, unchanged by this task).

- [ ] **Step 1: Confirm the two helpers really are equivalent**

```bash
grep -n "^async def _setup" -A 15 tests/test_websocket.py
grep -n "def setup_scheduler" -A 25 tests/conftest.py
```

Read both. They should differ only in: `setup_scheduler` is a fixture
returning a closure rather than a free function taking `hass` as its
first argument, and it additionally supports `dry_run`. If you find any
other difference (a different `MockConfigEntry` title, a different
sensor-population order, anything `test_websocket.py`'s version does that
`setup_scheduler` does not), **stop and report it** rather than deleting
the difference silently — it may be load-bearing for a test you have not
looked at yet.

- [ ] **Step 2: Establish the baseline**

```bash
uv run pytest tests/test_websocket.py -v 2>&1 | tail -5
```

Record the pass count. It must be identical after this task.

- [ ] **Step 3: Delete the local helper and repoint every call site**

Delete the `_setup` function definition (lines ~25-39) from
`tests/test_websocket.py`. Every test function in the file currently
takes `hass` (and often other fixtures) and calls `await _setup(hass,
...)`. Change each test's parameter list to also request `setup_scheduler`,
and change each call from `await _setup(hass, rules, defaults=...,
enabled=...)` to `await setup_scheduler(rules, defaults=..., enabled=...)`
— dropping the `hass` positional argument, since the fixture already
closes over it.

This is mechanical across all 51 sites, but **read each one rather than
running a blind sed** — a handful may pass `rules` as a keyword rather
than positionally, and the parameter name inside the closure is still
`rules` either way, so a keyword call needs no change beyond dropping
`hass,`.

- [ ] **Step 4: Run the tests and confirm the same count passes**

```bash
uv run pytest tests/test_websocket.py -v 2>&1 | tail -5
```

Expected: the exact same number of tests pass as Step 2's baseline, and
none newly fail. If the count differs, find out why before proceeding —
do not adjust a test's assertions to make the count match again.

- [ ] **Step 5: Run the whole suite**

```bash
uv run pytest
```

- [ ] **Step 6: Commit**

```bash
git add tests/test_websocket.py
git commit -m "test: use the shared setup_scheduler fixture, not a second copy

Carried from Plan 2's final review. test_websocket.py's local _setup was
almost byte-identical to conftest.py's setup_scheduler fixture, minus
dry_run support. One setup path now, not two to keep in sync."
```

---

## Task 5: `would_call` composing with `no_live_targets`

Carried from Plan 2's final review: the dry-run path is already tested
composing with `unknown_targets`
(`test_a_dry_run_still_reports_an_unknown_target` in `tests/test_engine.py`),
but nothing proves the sibling diagnostic — a target that resolves to
nothing live — survives a dry run the same way.

**Files:**
- Modify: `tests/test_engine.py`

**Interfaces:**
- Consumes: `engine`, `_rule` (both already in `tests/conftest.py`).

- [ ] **Step 1: Read the sibling test first**

```bash
grep -n "test_a_dry_run_still_reports_an_unknown_target" -A 15 tests/test_engine.py
```

Match its structure and style for the new test.

- [ ] **Step 2: Write the failing test**

Add near the existing `no_live_targets` tests in `tests/test_engine.py`
(search for `test_a_call_that_reached_nothing_says_so_rather_than_nothing`
to find them):

```python
async def test_a_dry_run_still_reports_reaching_nothing_live(hass, engine):
    """The sibling of test_a_dry_run_still_reports_an_unknown_target.

    A target that resolves to nothing live (every member of an existing
    group unavailable, say) must still carry the diagnostic under a dry
    run, exactly as an unknown target already does - a dry run is where
    you WANT to find out a rule would not have done anything real.
    """
    await hass.async_block_till_done()
    hass.states.async_set("group.g", "unknown", {"entity_id": ["input_boolean.member"]})
    engine.store  # noqa: B018 - documents that dry_run is set on the store below
    await engine.store.async_set_dry_run(True)
    rule = _rule(action="input_boolean.turn_on", entities=("group.g",))

    [result] = await engine.async_apply_rule(rule)

    assert result["outcome"] == "would_call"
    assert result["no_live_targets"] is True
    assert "unknown_targets" not in result
```

Delete the `engine.store  # noqa` line above — it was left in by mistake
while drafting; the real code needs only the `async_set_dry_run` call. If
`group.g`'s member being merely `unknown` rather than absent does not
reproduce `no_live_targets: True`, read
`test_a_call_that_reached_nothing_says_so_rather_than_nothing` for the
exact state shape that does, and match it.

- [ ] **Step 3: Run it and watch it fail or pass**

```bash
uv run pytest tests/test_engine.py -k reports_reaching_nothing_live -v
```

Expected: **PASS**, immediately — this task is proof, not a fix, exactly
like Plan 2's Task 10 was for domain genericity. `_inspect_target` and
`_call` already compute the diagnostic before the dry-run early return
(that ordering is precisely what the previous plan's ledger recorded as
verified-by-reading but not tested). If it fails instead, that is a real
defect: the diagnostic is being computed after the dry-run return rather
than before it, and this task becomes a fix, not just a test. Say so
explicitly in your report either way.

- [ ] **Step 4: Run the whole suite**

```bash
uv run pytest
```

- [ ] **Step 5: Commit**

```bash
git add tests/test_engine.py
git commit -m "test: prove would_call composes with no_live_targets

Carried from Plan 2's final review. The dry-run path already had
coverage for unknown_targets; this closes the same gap for the sibling
diagnostic."
```

---

## Task 6: Minify the card bundle

Carried from Plan 2's final review, numbered as "Gap C." The rollup build
has no minification step at all. `js-yaml` alone (needed for the
condition editor's YAML text) added roughly 105 KB unminified, and the
committed bundle is roughly 223 KB — one step benefits the whole bundle,
not just that one dependency.

**Files:**
- Modify: `frontend/package.json`, `frontend/rollup.config.mjs`
- Test: `tests/test_frontend.py` (existing; no new test needed — this
  task's correctness is proven by the existing bundle-integrity tests)

**Interfaces:**
- Produces: a smaller committed `custom_components/shabbat_scheduler/www/shabbat-scheduler-card.js`, functionally identical.

- [ ] **Step 1: Record the current size**

```bash
ls -l custom_components/shabbat_scheduler/www/shabbat-scheduler-card.js
```

Note the byte count for your report.

- [ ] **Step 2: Add the minifier**

```bash
cd frontend
npm install --save-dev @rollup/plugin-terser
```

Confirm it landed as a `devDependency` in `frontend/package.json` (not a
runtime `dependency` — it only runs at build time, never shipped).

- [ ] **Step 3: Wire it into the build**

In `frontend/rollup.config.mjs`, add the import:

```js
import terser from '@rollup/plugin-terser';
```

and add it as the **last** plugin in the `plugins` array, after
`bundleManifest`'s call but appearing after `typescript(...)` in source
order (the manifest plugin runs its own hook regardless of plugin order,
so this is about readability, not correctness — but check
`bundle-manifest.mjs`'s own comment for whether it assumes it sees the
pre- or post-minification bytes, and place `terser()` so the manifest's
`bundle` hash is computed from the **final**, minified file, which is
what actually ships):

```js
  plugins: [
    resolve(),
    typescript({ tsconfig: './tsconfig.json' }),
    terser(),
    bundleManifest({
      srcDir: path.join(here, 'src'),
      outFile,
      manifestDir: here,
    }),
  ],
```

Use **terser's default options**. Do not enable `mangle.properties` —
Lit's `@property()` names and this card's cross-module property access
(`.hass`, `.action`, `.target`, and so on) are accessed by name from
outside the class, and property mangling would rename them inconsistently
between call sites. Default terser only mangles local variable and
function names, which is safe.

- [ ] **Step 4: Build and check nothing broke**

```bash
npm run build
ls -l ../custom_components/shabbat_scheduler/www/shabbat-scheduler-card.js
npm test
npm run typecheck
```

Compare the new size against Step 1's — it should be meaningfully
smaller. Report both numbers.

- [ ] **Step 5: Run the Python bundle-integrity tests**

```bash
cd ..
uv run pytest tests/test_frontend.py -v
```

`test_the_bundle_defines_the_card_element` in particular must still pass
— it is the check that the string `shabbat-scheduler-card` (the custom
element tag name) still appears literally in the minified output.
Terser's default settings never touch string literals, so this should
pass without any special configuration, but confirm rather than assume.

- [ ] **Step 6: Confirm the whole suite, and e2e**

```bash
uv run pytest
```

Then, with the dev instance up and a fresh token (`uv run python
dev/seed.py`), run:

```bash
HA_DEV_TOKEN=<token> uv run pytest e2e -v
```

The minified bundle is what the dev container actually serves (it mounts
`custom_components/shabbat_scheduler` read-only), so this is the real
proof that minification did not silently break the card in a browser —
the Python bundle tests only check the bundle's *text*, not that it
executes correctly.

- [ ] **Step 7: Commit**

```bash
git add frontend/package.json frontend/package-lock.json \
        frontend/rollup.config.mjs \
        custom_components/shabbat_scheduler/www/shabbat-scheduler-card.js \
        frontend/bundle-manifest.json
git commit -m "build: minify the card bundle

Carried from Plan 2's final review as Gap C. The build had no
minification step at all; js-yaml alone added ~105 KB unminified.
Default @rollup/plugin-terser settings - no property mangling, since
Lit properties and this card's cross-module property access are
name-sensitive."
```

---

## Task 7: A diagnostics platform

Config entry, rule count, resolved block, last run — the standard HA
"Download diagnostics" button on the integration's page, with nothing
sensitive to redact (the config entry holds only two zmanim sensor entity
ids; nothing here is a credential).

**Files:**
- Create: `custom_components/shabbat_scheduler/diagnostics.py`
- Create: `tests/test_diagnostics.py`

**Interfaces:**
- Consumes: `hass.data[DOMAIN][entry.entry_id]` — a dict with keys
  `"store"` (a `RuleStore`) and `"engine"` (a `ShabbatEngine`), set in
  `custom_components/shabbat_scheduler/__init__.py:178-182`.
  `RuleStore.rules -> list[Rule]`, `.defaults -> dict`, `.enabled -> bool`,
  `.dry_run -> bool`, `.migration_failures -> list[str]`,
  `.last_outcome(rule_id: str) -> dict | None`.
  `ShabbatEngine.current_block -> Block | None`,
  `.upcoming() -> list[ResolvedRule]`.
  `Block` (`models.py`) has `candle_lighting: datetime`, `havdalah:
  datetime`, `length: int`, `erev_date: date`, `day_dates: tuple[date, ...]`.
  `Rule` has `id, profile, day, time, action, target, data, condition,
  replay, name, icon, enabled, color, migration_error, migration_source`.
- Produces: `async_get_config_entry_diagnostics(hass, config_entry) -> dict[str, Any]`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_diagnostics.py`. Follow this repo's existing
conventions: use `setup_scheduler` from `conftest.py`, and the
`get_diagnostics_for_config_entry` helper this test dependency chain
provides.

```python
"""The diagnostics platform - what 'Download diagnostics' actually sends."""

from datetime import time

import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
)

from custom_components.shabbat_scheduler.models import Rule


async def test_diagnostics_report_the_rule_count_and_engine_state(
    hass, hass_client, setup_scheduler, jerusalem
):
    from pytest_homeassistant_custom_component.components.diagnostics import (
        get_diagnostics_for_config_entry,
    )

    entry = await setup_scheduler(
        rules=[
            Rule(id="r1", profile=1, day="1", time=time(11, 0),
                 action="input_boolean.turn_on",
                 target={"entity_id": ["input_boolean.t"]}),
        ],
        enabled=True,
    )
    await hass.async_block_till_done()

    result = await get_diagnostics_for_config_entry(hass, hass_client, entry)

    assert result["rule_count"] == 1
    assert result["enabled"] is True
    assert result["dry_run"] is False
    assert "migration_failures" in result
    assert result["migration_failures"] == []


async def test_diagnostics_do_not_include_rule_targets_or_data(
    hass, hass_client, setup_scheduler, jerusalem
):
    """The config entry holds no credentials, so nothing here is redacted -
    but a rule's own target/data is still someone's home layout, and
    diagnostics attached to a support request should not casually spell
    out every entity id in a person's house. Report SHAPE, not content."""
    from pytest_homeassistant_custom_component.components.diagnostics import (
        get_diagnostics_for_config_entry,
    )

    entry = await setup_scheduler(
        rules=[
            Rule(id="r1", profile=1, day="1", time=time(11, 0),
                 action="climate.set_temperature",
                 target={"entity_id": ["climate.master_bedroom"]},
                 data={"temperature": 22}),
        ],
        enabled=True,
    )
    await hass.async_block_till_done()

    result = await get_diagnostics_for_config_entry(hass, hass_client, entry)

    dumped = str(result)
    assert "master_bedroom" not in dumped
    assert "temperature" not in dumped or "22" not in dumped


async def test_diagnostics_report_no_block_gracefully(
    hass, hass_client, setup_scheduler
):
    """No Jewish Calendar sensors published yet - the engine has no
    block, and diagnostics must say that plainly rather than raising."""
    from pytest_homeassistant_custom_component.components.diagnostics import (
        get_diagnostics_for_config_entry,
    )

    entry = await setup_scheduler()
    await hass.async_block_till_done()

    result = await get_diagnostics_for_config_entry(hass, hass_client, entry)

    assert result["current_block"] is None
```

If `setup_scheduler` (without the `jerusalem` fixture) does not publish
zmanim sensors and the third test's "no block" premise does not actually
hold without it, that is fine — the point of that test is "no block
resolves to `None`, not an exception," and it will still exercise that
whether or not a block happens to resolve. Adjust the assertion to
`assert result["current_block"] is None or isinstance(result["current_block"], dict)`
only if you find the fixture does publish zmanim by default; check by
reading `setup_scheduler`'s body before changing the test to match
whatever you find, rather than guessing.

- [ ] **Step 2: Run it and watch it fail**

```bash
uv run pytest tests/test_diagnostics.py -v
```

Expected: FAIL — `diagnostics.py` does not exist, `async_setup_component(hass, "diagnostics", {})` inside the helper will not find a platform to call.

- [ ] **Step 3: Write the platform**

Create `custom_components/shabbat_scheduler/diagnostics.py`:

```python
"""What 'Download diagnostics' sends for this integration.

Nothing here is a credential - the config entry holds only the two zmanim
sensor entity ids the engine reads a block from - so there is no
async_redact_data call. But a rule's own target and data are still
someone's home layout (device names, room names), and diagnostics
attached to a support request should not spell that out by default. So
this reports SHAPES (counts, kinds, whether a field is set) rather than
CONTENTS wherever the two diverge.
"""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .models import Block, Rule


def _rule_shape(rule: Rule) -> dict[str, Any]:
    """A rule's shape, not its content: what kind of thing it is, not
    which entities or rooms it names."""
    return {
        "id": rule.id,
        "profile": rule.profile,
        "day": rule.day,
        "action": rule.action,
        "has_target": bool(rule.target),
        "data_keys": sorted(rule.data.keys()),
        "condition_count": len(rule.condition),
        "replay_enabled": rule.replay.enabled,
        "enabled": rule.enabled,
        "migration_error": rule.migration_error,
    }


def _block_shape(block: Block | None) -> dict[str, Any] | None:
    if block is None:
        return None
    return {
        "length": block.length,
        "candle_lighting": block.candle_lighting.isoformat(),
        "havdalah": block.havdalah.isoformat(),
        "erev_date": block.erev_date.isoformat(),
        "day_dates": [d.isoformat() for d in block.day_dates],
    }


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> dict[str, Any]:
    """Config entry, rule count, resolved block, last run - and nothing
    that identifies a person's home beyond a service name."""
    entry_data = hass.data[DOMAIN][config_entry.entry_id]
    store = entry_data["store"]
    engine = entry_data["engine"]

    return {
        "config_entry": {
            "data_keys": sorted(config_entry.data.keys()),
            "options_keys": sorted(config_entry.options.keys()),
        },
        "enabled": store.enabled,
        "dry_run": store.dry_run,
        "rule_count": len(store.rules),
        "migration_failures": store.migration_failures,
        "current_block": _block_shape(engine.current_block),
        "upcoming_count": len(engine.upcoming()),
        "rules": [_rule_shape(rule) for rule in store.rules],
    }
```

Verify `ConfigEntry.data` and `.options` are the real attribute names by
checking one existing use in `custom_components/shabbat_scheduler/config_flow.py`
or `__init__.py` before trusting this snippet — if either differs, the
installed Home Assistant is right.

- [ ] **Step 4: Run the tests**

```bash
uv run pytest tests/test_diagnostics.py -v
```

Expected: PASS. If the second test's assertion about `data_keys`/content
leakage fails because `data` legitimately needs to appear somewhere (e.g.
`data_keys` reporting `["temperature"]` is fine — that is a KEY, not the
VALUE `22` or an entity id), re-read the test: it checks for the specific
strings `"master_bedroom"` and the co-occurrence of `"temperature"` with
`"22"`, not for the word `"temperature"` alone. `_rule_shape`'s
`data_keys` reporting the key name `"temperature"` is intended and
correct; only the *value* and *targets* must not appear.

- [ ] **Step 5: Verify manually against the dev instance**

With the dev instance up and seeded (`uv run python dev/seed.py`),
confirm the diagnostics download actually works end to end — this is the
one thing the unit test cannot prove, since it goes through HA's real
diagnostics HTTP view rather than the test helper's shortcut:

```bash
TOKEN=$(uv run python dev/seed.py | tail -1)
ENTRY_ID=$(curl -sS "http://127.0.0.1:8124/api/config/config_entries/entry" \
  -H "Authorization: Bearer $TOKEN" \
  | python3 -c "import json,sys; print([e['entry_id'] for e in json.load(sys.stdin) if e['domain']=='shabbat_scheduler'][0])")
curl -sS "http://127.0.0.1:8124/api/diagnostics/config_entry/$ENTRY_ID" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

Confirm the output looks like the shape above and contains no error.

- [ ] **Step 6: Run the whole suite**

```bash
uv run pytest
```

- [ ] **Step 7: Commit**

```bash
git add custom_components/shabbat_scheduler/diagnostics.py tests/test_diagnostics.py
git commit -m "feat: a diagnostics platform

Config entry (shape only), rule count, migration failures, the resolved
block, and each rule's shape. Nothing that identifies a person's home
beyond a service name and a data key - a rule's actual target entities
and data values are omitted, since diagnostics attached to a support
request should not spell out someone's house."
```

---

## Task 8: Brand assets for `home-assistant/brands`

`home-assistant/brands` is a **separate GitHub repository** whose
inclusion is a pull request reviewed by Home Assistant's own brand team —
outside this repo, and outside what this plan can complete on its own.
This task prepares the four required image files and documents the
submission step; it does not open that PR.

**Files:**
- Create: `brands/icon.png`, `brands/icon@2x.png`, `brands/logo.png`, `brands/logo@2x.png`
- Create: `brands/README.md`

**Interfaces:**
- Consumes: nothing.
- Produces: image assets ready to hand to a `home-assistant/brands` PR.

- [ ] **Step 1: Confirm the current size/format requirements**

`home-assistant/brands`' own contribution guidelines are the source of
truth and can change. If you have `WebFetch` available, fetch
`https://github.com/home-assistant/brands/blob/master/CONTRIBUTING.md`
and use whatever it currently specifies. If you do not, or the fetch
fails, use these as of 2026: `icon.png` 256×256, `icon@2x.png` 512×512,
`logo.png` and `logo@2x.png` no fixed width but a maximum height (256px
for `logo.png`, 512px for `logo@2x.png`), all PNG, transparent background
permitted. **State in your report which source you used** — the live
guidelines or this fallback — so a reviewer knows whether to double-check
before the real submission.

- [ ] **Step 2: Generate the assets**

There is no existing brand mark for this integration and no reason to
borrow anyone else's. Draw an original, simple geometric mark: two
candles with flames (Shabbat candles are the one visual element that
identifies what this integration is about, unambiguously and without
depicting any religious symbol more specific than that). Use Pillow via
`uv run --with pillow python <script>` so this stays a one-off tool
rather than a permanent dependency of the project:

```bash
uv run --with pillow python3 - <<'PY'
from PIL import Image, ImageDraw

def candles(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    unit = size / 8
    colour = (0xF5, 0xC2, 0x42, 255)   # warm candlelight
    wax = (0xEE, 0xE6, 0xD8, 255)
    for cx in (size * 0.35, size * 0.65):
        top = size * 0.35
        draw.rectangle(
            [cx - unit * 0.5, top, cx + unit * 0.5, size * 0.85],
            fill=wax,
        )
        draw.polygon(
            [
                (cx, top - unit * 1.1),
                (cx - unit * 0.35, top - unit * 0.1),
                (cx + unit * 0.35, top - unit * 0.1),
            ],
            fill=colour,
        )
    return img

for name, size in (("icon", 256), ("icon@2x", 512)):
    candles(size).save(f"brands/{name}.png")
for name, size in (("logo", 256), ("logo@2x", 512)):
    candles(size).save(f"brands/{name}.png")
PY
```

This is a starting point, not a demand for pixel-perfect output — open
each generated file and confirm it actually looks like two lit candles at
a glance, not an abstract smear. If it does not read clearly at 256×256,
adjust the proportions (the flame polygon's height relative to `unit`,
the candle width) until it does, rather than shipping something
illegible at icon size.

- [ ] **Step 3: Verify the files**

```bash
python3 -c "
from PIL import Image
for name in ('icon', 'icon@2x', 'logo', 'logo@2x'):
    img = Image.open(f'brands/{name}.png')
    print(name, img.size, img.mode)
"
```

Confirm `icon.png` is exactly 256×256, `icon@2x.png` exactly 512×512, and
both logo files are RGBA PNGs.

- [ ] **Step 4: Write the submission instructions**

Create `brands/README.md`:

```markdown
# Brand assets

Prepared for submission to `home-assistant/brands`, which this repo
cannot submit to directly - it is reviewed by Home Assistant's own brand
team via a pull request against their repository, not this one.

To submit:

1. Fork `https://github.com/home-assistant/brands`.
2. Copy these four files to
   `custom_integrations/shabbat_scheduler/` in that fork
   (`icon.png`, `icon@2x.png`, `logo.png`, `logo@2x.png`).
3. Open a pull request against `home-assistant/brands`, following their
   `CONTRIBUTING.md`.
4. Once merged, the integration's icon appears automatically in Home
   Assistant's UI for anyone on a recent core version - no change needed
   in this repo.

Until that PR is merged, Home Assistant falls back to a generic
integration icon. That is expected and not a bug in this integration.
```

- [ ] **Step 5: Commit**

```bash
git add brands/
git commit -m "docs: prepare brand assets for home-assistant/brands

Original two-candles mark, generated rather than borrowed. The actual
submission is a PR against a separate repository reviewed by HA's own
brand team - this commit prepares the assets and documents the steps,
it does not open that PR."
```

---

## Task 9: Upgrade notes, v1 → v2

For the person who installed v1 and is about to update — what changed,
what the migration does automatically, and what to check afterwards.

**Files:**
- Create: `docs/upgrading-from-v1.md`

**Interfaces:**
- Consumes: the accepted-behaviour record already written during the v2
  migration work — read `docs/known-behaviours.md`'s migration-related
  entries and `custom_components/shabbat_scheduler/migration.py`'s module
  docstring before writing this, so the two documents agree rather than
  one silently contradicting the other.

- [ ] **Step 1: Read what the migration actually guarantees**

```bash
sed -n '1,40p' custom_components/shabbat_scheduler/migration.py
grep -n "^## " docs/known-behaviours.md | grep -i "migrat\|v1\|upgrade"
```

- [ ] **Step 2: Write the document**

Create `docs/upgrading-from-v1.md`:

```markdown
# Upgrading from v1

v1 rules were `on` / `off` / `custom` against a fixed list of devices,
with three hardcoded climate settings. v2 rules are any Home Assistant
service call: an `action` (`domain.service`), a `target` (Home
Assistant's own target selector), and `data` (that service's own
payload). The upgrade is automatic - **restarting Home Assistant with
this version installed migrates every existing rule** - but the shapes
are different enough that this page exists.

## What happens automatically

Every v1 rule is converted to the equivalent v2 shape on first start.
This is described in full, with every input shape that was checked, in
[`docs/known-behaviours.md`](known-behaviours.md) - the short version:

- `on`/`off`/`custom` become the matching `domain.service` call for that
  device's domain.
- A rule's `devices` becomes its `target.entity_id`.
- The three v1 climate settings (`hvac_mode`, `temperature`, `fan_mode`)
  become `data`, expanded by the one climate compatibility shim this
  integration keeps (see the "Rule format" section of the main
  [README](../README.md)).
- A rule that named more than one domain is **split** into one rule per
  domain, since a v2 rule is one action. Both halves keep the same
  schedule; only the id changes (suffixed, e.g. `mine` becomes
  `mine-climate` and `mine-switch`).

## What is NOT dropped

**A rule the migration cannot convert is kept, disabled, and reported -
never silently dropped.** You will see a repair issue in Settings →
System → Repairs naming which rules need attention, with the original v1
shape preserved so nothing is lost while you decide what to do. This was
the single hardest constraint on the migration: a schedule that goes
silently short is worse than one that visibly asks for help.

## What changed in behaviour, not just shape

- **Replay after a restart is now off by default**, for every migrated
  rule. v1's catch-up behaviour did not map cleanly onto what "replay"
  means in v2 (see `docs/known-behaviours.md`'s entry on this), and the
  safer default was chosen deliberately: nothing unexpected fires after a
  restart unless you opt a rule in.
- **Conflicts are detected differently.** v1 could only detect two rules
  disagreeing about a *climate* setting for one device. v2 detects any
  two enabled rules, in the same profile and day, at the same time, whose
  resolved targets overlap - broader, and no longer climate-specific.
- **The card can author anything now**, not just the four fields v1's
  form understood. If you used YAML export/import to work around v1's
  form limitations, you likely do not need to any more - the card's rule
  dialog now has real editors for action, target, condition and replay.

## After upgrading

1. Restart Home Assistant.
2. Check Settings → System → Repairs for any migration issues.
3. Open the card and confirm your schedule still reads as you expect -
   the migration preserves rule ids, so each rule keeps its switch entity,
   history and any dashboard customisation you had.
4. If you relied on v1's automatic catch-up after a restart, review which
   rules you now want to opt into replay (the gear icon → a rule → the
   replay section), since that is off by default post-migration.
```

- [ ] **Step 3: Cross-check against the actual migration code**

For every specific claim above (the split-id suffix format, the repair
issue's exact wording, replay's default), grep the real source and
correct anything you find stated wrongly rather than trusting the draft:

```bash
grep -n "suffix\|-climate\|-switch" custom_components/shabbat_scheduler/migration.py | head -10
grep -n "async_create_unmigrated_rules_issue\|async_create_split_rules_issue" -A 5 custom_components/shabbat_scheduler/repairs.py
```

- [ ] **Step 4: Link it from the README**

This is done as part of Task 10, not here — do not add the link yet if
Task 10 has not run, to avoid a dangling cross-reference in an
intermediate commit. If Task 10 has already landed when you reach this
task, add the link now instead and say so in your report.

- [ ] **Step 5: Commit**

```bash
git add docs/upgrading-from-v1.md
git commit -m "docs: upgrade notes for v1 -> v2

What the automatic migration does, what it guarantees is never silently
dropped, and the three behaviour changes (replay default, conflict
detection, the card's editors) someone upgrading in place should know
about before they trust the result."
```

---

## Task 10: The README, rewritten as a guide

The last task. Everything before it — CI, the diagnostics platform, the
upgrade notes, the brand assets — is either referenced from here or makes
what this page claims actually true.

**Files:**
- Create: `dev/screenshot.py`
- Create: `docs/images/card-screenshot.png`
- Modify: `README.md` (full rewrite)

**Interfaces:**
- Consumes: the running dev instance (`dev/docker-compose.yml`,
  `dev/seed.py`), the same Playwright login pattern `e2e/conftest.py`
  already uses.

- [ ] **Step 1: Get the dev instance into a state worth screenshotting**

```bash
docker compose -f dev/docker-compose.yml up -d
# wait for http://127.0.0.1:8124 to answer
uv run python dev/seed.py
```

The default seed (four rules across erev and day 1) is a reasonable
screenshot — a timeline with more than one row, a named rule, and at
least one that is not simply "on". If it looks sparse once you actually
look at it in Step 3, use the websocket API to add one or two more varied
rules first (a `scene.turn_on`, a rule with a `name`) rather than
screenshotting something that undersells what the card does.

- [ ] **Step 2: Write the screenshot script**

Create `dev/screenshot.py`, following `e2e/conftest.py`'s existing
pattern for getting a token into the page before any script runs:

```python
"""Screenshot the card, for the README.

Not a test - a one-shot tool. Uses the same login-flow pattern
e2e/conftest.py uses to get a working token into the page before any
frontend script runs, because injecting it after a `goto()` is too late.
"""

import json
import sys
import urllib.request

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8124"


def _post(path: str, payload) -> dict:
    request = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(payload).encode() if isinstance(payload, dict)
        else payload.encode(),
        headers={"Content-Type": "application/json" if isinstance(payload, dict)
                  else "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode())


def mint_token() -> str:
    flow = _post("/auth/login_flow", {
        "client_id": BASE, "handler": ["homeassistant", None],
        "redirect_uri": BASE, "type": "authorize",
    })
    step = _post(f"/auth/login_flow/{flow['flow_id']}", {
        "client_id": BASE, "username": "dev", "password": "devdevdev",
    })
    token = _post(
        "/auth/token",
        f"grant_type=authorization_code&code={step['result']}&client_id={BASE}",
    )
    return token["access_token"]


def main() -> None:
    token = mint_token()
    out_path = sys.argv[1] if len(sys.argv) > 1 else "docs/images/card-screenshot.png"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport={"width": 900, "height": 700})
        context.add_init_script(f"""
            window.localStorage.setItem('hassTokens', JSON.stringify({{
                access_token: {json.dumps(token)},
                token_type: 'Bearer',
                expires_in: 1800,
            }}));
        """)
        page = context.new_page()
        page.goto(f"{BASE}/shabbat-scheduler/0")
        page.wait_for_selector("shabbat-scheduler-card", timeout=15_000)
        page.wait_for_timeout(1_000)  # let the day groups finish rendering
        page.locator("shabbat-scheduler-card").screenshot(path=out_path)
        browser.close()

    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
```

If `hassTokens`' exact shape does not work (Home Assistant's frontend
auth storage format can differ from what a raw `localStorage.setItem`
expects), check how `e2e/conftest.py`'s `page` fixture actually injects
its token — read that file's `context.add_init_script` call in full and
match its exact shape rather than guessing a second one.

- [ ] **Step 3: Run it and look at the result**

```bash
mkdir -p docs/images
uv run python dev/screenshot.py docs/images/card-screenshot.png
```

Open the resulting PNG and actually look at it. It must show: the day
timeline with real dates, at least two rules, the candle-lighting or
havdalah marker, and the header with the master switch. If the master
switch reads as off (grey, unlit) and that reads as "broken" or
"nothing is happening" at a glance, consider turning it on for the
screenshot only (`shabbat_scheduler.set_dry_run` with `enabled: true`, or
via the card's own toggle) — a screenshot's job is to show what the card
looks like in active use, not to preserve the master-off safe default
that a fresh install actually starts in. State in your report which state
you chose and why.

- [ ] **Step 4: Write the guide**

Replace `README.md` entirely. Keep every fact from the current version —
it is accurate — but reorder and rewrite so a stranger can follow it top
to bottom without needing to know the vocabulary in advance. Structure:

1. **One paragraph: what this is, for whom.** Not "a block is a
   contiguous period..." — start with "schedules Home Assistant to do
   anything, at specific times across Shabbat and Chag, without you
   touching a switch," then who needs this (someone who currently uses
   plain time-based automations or does it by hand and wants both safety
   guarantees — fire-once, no silent auto-resolution of conflicts — that
   an ordinary automation does not give them).
2. **The screenshot**, immediately after, before any more prose:
   `![The card showing a resolved Shabbat block](docs/images/card-screenshot.png)`
3. **Quick start** — a numbered list a newcomer can follow with nothing
   else open:
   1. Install via HACS (the existing Installation section's instructions,
      verbatim or close to it).
   2. Add the integration; it offers the Jewish Calendar's sensors by
      default if that integration is installed.
   3. The master switch starts **off** — nothing can happen yet. Say this
      explicitly and say why it matters (safe by default).
   4. Open the card (it registers itself, nothing to configure), tap
      **+** under a day, and author one rule — walk through picking an
      action and a target for the simplest possible example
      (`input_boolean.turn_on` against one entity is a safe first rule to
      try, since nothing about it is dangerous to get wrong).
   5. Turn the master switch on when ready.
4. **Then** the existing reference material, kept close to its current
   wording: Design commitments, Entities, The card (drop the "read-mostly
   … until Plan 2" sentence entirely — Plan 2 is done, the card authors
   everything), Services, Rule format (keep the existing worked YAML
   example, it is real non-climate material), Known behaviours.
5. **A new "Upgrading" section**, one paragraph, linking
   `docs/upgrading-from-v1.md` from Task 9 — only add this if that file
   exists by the time you write this section; if Task 9 has not run yet,
   skip it and note the gap in your report rather than linking a file
   that does not exist.
6. **A status line near the top**, right under the title, honest about
   where this stands: *"Alpha. [N] tests passing (Python + frontend +
   end-to-end), not yet installed on the maintainer's own production
   instance."* Get the real current count by running
   `uv run pytest --collect-only -q | tail -1` and
   `npm --prefix frontend test -- --run 2>&1 | grep -E 'Tests +[0-9]'`
   rather than copying a number from this plan, which will be stale by
   the time you run it.

Do not add a badge referencing CI unless Tasks 1 and 2 have actually
merged and you can confirm the workflow files exist at
`.github/workflows/` — a badge pointing at a workflow that does not exist
renders as broken or misleadingly "no runs yet" forever.

- [ ] **Step 5: Read it once, cold**

After writing it, read the whole file start to finish as if you have
never seen this project, and fix anything that uses a term (`block`,
`profile`, `replay`, `dry run`) before it is defined, or that assumes
knowledge the quick start has not yet given the reader.

- [ ] **Step 6: Commit**

```bash
git add README.md dev/screenshot.py docs/images/card-screenshot.png
git commit -m "docs: rewrite the README as a guide

Screenshot, quick start, terminology defined before use, and the
'read-mostly ... until Plan 2' line removed now that Plan 2 shipped the
real editors. The existing reference material is kept, reordered below
the guide rather than rewritten - it was accurate, just written for
someone who already knew what this was."
```

- [ ] **Step 7: If Task 9 had not linked back, close the loop**

If Task 9's Step 4 was skipped because this task had not run yet, add the
link from `docs/upgrading-from-v1.md` back to the README's new "Upgrading"
section anchor now, in a small follow-up commit, so navigation works in
both directions.

---

## Self-Review

**1. Spec coverage.** Checked against `docs/superpowers/specs/2026-08-22-shabbat-scheduler-v2-alpha-design.md`'s "Alpha readiness" section (2026-08-25 revision):

| Requirement | Task |
|---|---|
| CI | 1, 2 |
| README as a guide, screenshot, quick start | 10 |
| HACS brands entry (assets prepared) | 8 |
| Diagnostics platform | 7 |
| Upgrade notes | 9 |
| Repair issues, translation parity, HACS metadata | already done (Plan 1/2), not re-scoped |
| The `1..3` bound | 3 |
| `test_websocket.py::_setup` duplication | 4 |
| `would_call` + `no_live_targets` | 5 |
| Bundle minification | 6 |

**2. Placeholder scan.** No TBDs. Two places deliberately ask the
implementer to verify a live external source (brand asset dimensions in
Task 8, the exact `hassTokens` shape in Task 10) rather than hard-coding
something that might already be stale by execution time, and both say
explicitly what to fall back to and what to report if verification is not
possible.

**3. Type/interface consistency.** `diagnostics.py`'s
`async_get_config_entry_diagnostics` reads `hass.data[DOMAIN][entry.entry_id]["store"]`
/`["engine"]`, matching `__init__.py:178-182` exactly. `setup_scheduler`'s
signature in Task 4/5/7 matches `tests/conftest.py`'s actual definition
(`rules=(), defaults=None, enabled=False, dry_run=False`). `MIN_PROFILE`/
`MAX_PROFILE` are introduced once in Task 3 and consumed nowhere else in
this plan.

**4. Ordering.** Task 1 and 2 (CI) are independent of everything else and
placed first so every later commit in this plan runs under them. Tasks
3-6 are independent of each other and of 7-10. Task 9 and 10 have one soft
dependency (the README's "Upgrading" link), handled explicitly in both
tasks' final steps regardless of execution order.
