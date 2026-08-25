# Shabbat Scheduler v2 Card Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the card real authoring for a v2 rule — action, target, condition and replay — on Home Assistant's own form elements, and close the three gaps Plan 1 carried forward.

**Architecture:** Four small Lit elements, each wrapping one Home Assistant element and owning one slice of the rule. `<ha-service-control>` supplies action + data; `<ha-selector>` supplies the target; two hand-written editors cover condition and replay. `rule-dialog.ts` composes them and its read-only block is deleted. No validation moves to the client — the Python side stays the only authority.

**Tech Stack:** TypeScript, Lit 3, rollup, vitest + happy-dom, Playwright, Python 3.14 + `pytest-homeassistant-custom-component`.

## Global Constraints

Copied from `docs/superpowers/specs/2026-08-22-shabbat-scheduler-v2-alpha-design.md`. Every task's requirements implicitly include these.

- **The integration owns *when*; Home Assistant owns *what*.** Any domain knowledge in this codebase must justify itself as a compatibility shim, be documented as one, and be narrow.
- **Fire once, never re-assert.** Unchanged and non-negotiable.
- **A rule that does not fire must say why.** Blocked by a condition, skipped as too stale to replay, or failed — each is visible in the logbook and on the card. A rule that silently does nothing is the failure this project exists to prevent.
- **Conflicts are warned, never resolved.**
- **No client-side revalidation.** The Python side owns validation.
- The pure modules (`models.py`, `block.py`, `device_ops.py`, `const.py`, `rule_schema.py`, `yaml_io.py`, `migration.py`) continue to import zero Home Assistant. `tests/test_packaging.py` enforces this.
- Storage must migrate, not break. An alpha user's rules survive upgrades.
- Home Assistant 2026.8.2 or later.
- **Reach for `<ha-selector>` with the selector you want, never for a specific picker element.** Availability differs element-by-element on a dashboard. `ha-entity-picker`, `ha-area-picker`, `ha-label-picker`, `ha-form` and `ha-icon-picker` are present; `ha-device-picker`, `ha-floor-picker`, `ha-target-picker` and `ha-textfield` are **not**. That list is not something to depend on.

## Project Context

Read this before Task 1. It is the state you are starting from, and several
items are counter-intuitive.

**The card cannot currently create a rule at all.** Plan 1 replaced v1's
`action`/`devices`/`settings` model with `action`/`target`/`data`, deleted the
bespoke climate form (`device-settings.ts` is gone), and left `rule-dialog.ts`
showing `target`, `data`, `condition` and `replay` in a **read-only block**. A
create therefore sends `target: {}` with whatever raw string was typed into the
`action` text input, and the server refuses it. This is deliberate and
documented — Plan 1 chose an honest read-only view over a form that would save a
v1-shaped payload — and undoing it is this plan's first job.

**The defaults dialog is read-only and its save button was deleted.** Its old
form wrote `{devices, settings}`, which `validate_defaults` now refuses, so
every press could only ever have failed.

**Verified baseline** (2026-08-25, on a freshly reset dev instance):

- 432 Python tests pass, 155 frontend tests pass.
- e2e: **5 passed, 2 failed**. Both failures are real drift this plan owns:
  - `test_the_settings_form_offers_only_what_every_selected_device_supports`
    drives `shabbat-device-settings`, which no longer exists.
  - `test_the_add_button_creates_a_rule_on_its_own_day` fills only `input.time`
    and saves, which cannot work now that a create needs a valid action and a
    target.
- e2e **skips silently** when `HA_DEV_TOKEN` is unset, which is how it stayed
  red unnoticed. Always run it with a token: mint one and export it, see
  `dev/README.md`.

**How to test an element Home Assistant has not defined.** `ha-service-control`
and `ha-selector` are not registered under happy-dom. This was probed
empirically, not assumed — all three of these hold:

- an undefined `<ha-service-control>` still renders, as a plain `HTMLElement`;
- `.hass=${...}` / `.value=${...}` property bindings land on it as JS
  properties and are readable in a test;
- a `value-changed` event dispatched from it reaches a listener bound in the
  parent's template.

So a unit test can drive **our whole side of the contract**: assert the
properties we pass down, dispatch the event HA would emit, and assert the form
state that results. It cannot test HA's rendering — that is Playwright's job,
and every new editor gets an e2e test here.

**Two pitfalls that have each cost real time in this repo:**

1. **A lit-html template whose root holds several top-level expressions renders
   NONE of them** under this repo's pinned lit-html + happy-dom. Wrap groups in
   a container element. `rule-dialog.ts` (`.advanced { display: contents; }`)
   and `day-group.ts` both document this. Do not unwrap those.
2. **`hass` is reassigned on every state change in the whole system.** Never
   re-seed form state from props on every update — `rule-dialog.ts`'s
   `willUpdate` seeds once per opened rule via a `_seeded` key, and that
   pattern must survive. Re-seeding on every update throws away what the user
   is typing.

**Where `hass` is today:** `card.ts` holds it in a private `_hass` with a
setter (line 108) and passes it to **no child element**. Task 1 fixes that.

---

## File Structure

**New frontend elements** — one Home Assistant element each, one slice of the
rule each, so a reviewer can reject one without touching its neighbours:

- `frontend/src/service-editor.ts` — wraps `<ha-service-control>`; owns
  `action` + `data` as one unit, because that is the shape HA's element speaks.
- `frontend/src/target-editor.ts` — wraps `<ha-selector>` with a `{target: {}}`
  selector; owns `target`. Also renders the inherited-from-defaults note that
  `rule-dialog.ts` renders today.
- `frontend/src/condition-editor.ts` — owns `condition`, a list of opaque HA
  condition configs.
- `frontend/src/replay-editor.ts` — owns `replay` (`enabled` + `within`).

**Modified:**

- `frontend/src/card.ts` — pass `hass` to both dialogs.
- `frontend/src/rule-dialog.ts` — compose the four editors; delete the
  read-only block and the `action` text input.
- `frontend/src/defaults-dialog.ts` — restore authoring using the target and
  service-data editors; restore its save button.
- `frontend/src/strings.ts` — new `en`/`he` keys.
- `frontend/src/types.ts` — a `Hass` interface for what we actually read.
- `custom_components/shabbat_scheduler/engine.py` — Gap B, and the durable
  per-rule outcome.
- `custom_components/shabbat_scheduler/store.py`,
  `websocket_api.py` — persist and expose that outcome.
- `dev/seed.py`, `dev/config/configuration.yaml` — entities for the
  multi-domain execution tests the spec requires.
- `e2e/test_card_e2e.py` — repair the two failures, add coverage for each
  editor.

**New tests:**

- `frontend/test/service-editor.test.ts`, `target-editor.test.ts`,
  `condition-editor.test.ts`, `replay-editor.test.ts`
- `frontend/test/payload-contract.test.ts` — Gap A.
- `frontend/test/fixtures/state-payload.json` — generated, committed.
- `tests/test_frontend_fixture.py` — Gap A's other half: regenerates that
  JSON from a real `_state_payload` and fails if the committed copy is stale.
- `tests/test_execution_domains.py` — the spec's multi-domain requirement.

---

## Task 1: Plumb `hass` into both dialogs

Nothing below can work without this, and it is worth its own commit because it
is the one change that touches the card's update path.

**Files:**
- Modify: `frontend/src/card.ts:457-483`
- Modify: `frontend/src/types.ts`
- Test: `frontend/test/card.test.ts`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: a `Hass` interface exported from `types.ts`; both
  `<shabbat-rule-dialog>` and `<shabbat-defaults-dialog>` receive `.hass`.

- [ ] **Step 1: Write the failing test**

Append to `frontend/test/card.test.ts`. Match the file's existing render
helper — read it first and reuse it rather than writing a second one.

```ts
it('passes hass down to the rule dialog, so HA elements can render', async () => {
  const el = await renderCard();           // existing helper in this file
  el.shadowRoot!.querySelector('shabbat-day-group')!
    .dispatchEvent(new CustomEvent('rule-add', {
      detail: { day: 'erev' }, bubbles: true, composed: true,
    }));
  await el.updateComplete;
  const dialog = el.shadowRoot!.querySelector('shabbat-rule-dialog') as any;
  expect(dialog).not.toBeNull();
  expect(dialog.hass).toBe(el.hass);
});

it('passes hass down to the defaults dialog', async () => {
  const el = await renderCard();
  (el as any)._defaultsOpen = true;
  await el.updateComplete;
  const dialog = el.shadowRoot!.querySelector('shabbat-defaults-dialog') as any;
  expect(dialog.hass).toBe(el.hass);
});
```

If `renderCard` is named differently or the add event is named differently,
use what the file actually uses. Do not change existing tests to suit these.

- [ ] **Step 2: Run the tests and watch them fail**

```bash
npm --prefix frontend test -- test/card.test.ts
```

Expected: both new tests FAIL with `dialog.hass` being `undefined`.

- [ ] **Step 3: Add the `Hass` interface**

In `frontend/src/types.ts`, after the `HassEntity` interface:

```ts
/**
 * As much of Home Assistant's `hass` object as this card reads, plus the
 * fields the HA elements we embed require to be present. It is passed
 * straight through to `<ha-service-control>` and `<ha-selector>`, which
 * read far more of it than this - so this is a *lower bound*, not a
 * description, and it must never be used to construct a hass object.
 */
export interface Hass {
  states: Record<string, HassEntity>;
  locale?: { language?: string };
  user?: { is_admin?: boolean };
  /**
   * The user's own advanced-mode preference. Passed to
   * `<ha-service-control>` so this card shows advanced service fields
   * exactly when Home Assistant itself would - hard-coding it on would
   * override a preference the user set deliberately.
   */
  userData?: { showAdvanced?: boolean };
  connection: unknown;
  callWS: (message: Record<string, unknown>) => Promise<unknown>;
  callService: (
    domain: string, service: string, data?: Record<string, unknown>,
  ) => Promise<unknown>;
  [key: string]: unknown;
}
```

- [ ] **Step 4: Pass it down**

In `frontend/src/card.ts`, add `.hass=${this._hass}` to both dialog
templates, as the first binding on each:

```ts
          ? html`<shabbat-rule-dialog
              .hass=${this._hass}
              .rule=${this._editing}
```

```ts
          ? html`<shabbat-defaults-dialog
              .hass=${this._hass}
              .defaults=${this._state.defaults}
```

- [ ] **Step 5: Accept it in both dialogs**

In `frontend/src/rule-dialog.ts`, add to the property block (after `rule` and
`seed`):

```ts
  /**
   * Passed straight to the Home Assistant elements the editors embed.
   * Reassigned on every state change in the whole system, so nothing may
   * key form-seeding off it - see `willUpdate`.
   */
  @property({ attribute: false }) hass: Hass | null = null;
```

Add `Hass` to the existing `import type { Defaults, RuleData, RuleFormState }
from './types';` line. Do the same in `frontend/src/defaults-dialog.ts`.

- [ ] **Step 6: Run the tests and watch them pass**

```bash
npm --prefix frontend test -- test/card.test.ts
npm --prefix frontend run typecheck
```

Expected: PASS, and no new typecheck errors.

- [ ] **Step 7: Run the whole frontend suite**

```bash
npm --prefix frontend test
```

Expected: 155 existing + 2 new = 157 passing.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/card.ts frontend/src/types.ts \
        frontend/src/rule-dialog.ts frontend/src/defaults-dialog.ts \
        frontend/test/card.test.ts
git commit -m "feat: pass hass into both dialogs, so HA's own elements can render"
```

---

## Task 2: The target editor

Restores the ability to say *what a rule acts on*, which the card has not had
since Plan 1.

**Files:**
- Create: `frontend/src/target-editor.ts`
- Create: `frontend/test/target-editor.test.ts`
- Modify: `frontend/src/strings.ts`

**Interfaces:**
- Consumes: `Hass` from `types.ts` (Task 1).
- Produces: `<shabbat-target-editor>` with properties
  `hass: Hass | null`, `value: Record<string, unknown>`,
  `inherited: Record<string, unknown>`, `disabled: boolean`,
  `language: string`. Emits `target-changed` with
  `detail: { value: Record<string, unknown> }`.

- [ ] **Step 1: Write the failing tests**

Create `frontend/test/target-editor.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import '../src/target-editor';

async function render(props: Record<string, unknown> = {}) {
  const el = document.createElement('shabbat-target-editor') as HTMLElement &
    Record<string, any>;
  Object.assign(el, {
    hass: { states: {} }, value: {}, inherited: {},
    disabled: false, language: 'en', ...props,
  });
  document.body.appendChild(el);
  await el.updateComplete;
  return el;
}

function selector(el: any) {
  return el.shadowRoot.querySelector('ha-selector');
}

describe('shabbat-target-editor', () => {
  it('hands ha-selector a target selector and the current value', async () => {
    const el = await render({ value: { entity_id: ['switch.a'] } });
    const sel = selector(el);
    expect(sel).not.toBeNull();
    expect(sel.selector).toEqual({ target: {} });
    expect(sel.value).toEqual({ entity_id: ['switch.a'] });
    expect(sel.hass).toBe(el.hass);
  });

  it('re-emits ha-selector value-changed as target-changed', async () => {
    const el = await render();
    const seen: unknown[] = [];
    el.addEventListener('target-changed', (e: Event) => {
      seen.push((e as CustomEvent).detail.value);
    });
    selector(el).dispatchEvent(new CustomEvent('value-changed', {
      detail: { value: { area_id: ['salon'] } },
    }));
    expect(seen).toEqual([{ area_id: ['salon'] }]);
  });

  it('normalises a cleared target to an empty object, never undefined', async () => {
    const el = await render({ value: { entity_id: ['switch.a'] } });
    const seen: unknown[] = [];
    el.addEventListener('target-changed', (e: Event) => {
      seen.push((e as CustomEvent).detail.value);
    });
    selector(el).dispatchEvent(new CustomEvent('value-changed', {
      detail: { value: undefined },
    }));
    expect(seen).toEqual([{}]);
  });

  it('says the target is inherited when it has none of its own', async () => {
    const el = await render({
      value: {}, inherited: { entity_id: ['switch.shared'] },
    });
    expect(el.shadowRoot.textContent).toContain('switch.shared');
  });

  it('does not mention inheritance once the rule has its own target', async () => {
    const el = await render({
      value: { entity_id: ['switch.a'] },
      inherited: { entity_id: ['switch.shared'] },
    });
    expect(el.shadowRoot.textContent).not.toContain('switch.shared');
  });

  it('disables the selector when the user cannot write', async () => {
    const el = await render({ disabled: true });
    expect(selector(el).disabled).toBe(true);
  });
});
```

- [ ] **Step 2: Run them and watch them fail**

```bash
npm --prefix frontend test -- test/target-editor.test.ts
```

Expected: FAIL — the element is not defined, so `selector(el)` is null.

- [ ] **Step 3: Add the strings**

In `frontend/src/strings.ts`, add to the `en` block:

```ts
    inherits_target_from_defaults: 'Inherited from the shared defaults:',
    target_none: 'No target — this rule will not reach anything.',
```

and to the `he` block:

```ts
    inherits_target_from_defaults: 'נורש מברירת המחדל המשותפת:',
    target_none: 'ללא יעד — הכלל לא יפעל על שום דבר.',
```

- [ ] **Step 4: Write the element**

Create `frontend/src/target-editor.ts`:

```ts
import { LitElement, css, html, nothing } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { describeTarget } from './format';
import { t } from './strings';
import type { Hass } from './types';

/**
 * The rule's target, on Home Assistant's own target selector.
 *
 * Deliberately `<ha-selector>` with `{target: {}}` rather than
 * `<ha-target-picker>`: on a dashboard the picker is NOT pre-registered,
 * while `ha-selector` always is and dynamically imports whatever
 * sub-selector it is handed. See the spec's "Frontend availability"
 * section - this was verified in real Chromium, not assumed.
 */
@customElement('shabbat-target-editor')
export class ShabbatTargetEditor extends LitElement {
  @property({ attribute: false }) hass: Hass | null = null;
  @property({ attribute: false }) value: Record<string, unknown> = {};
  /** The shared defaults' target, used only for the note. */
  @property({ attribute: false }) inherited: Record<string, unknown> = {};
  @property({ type: Boolean }) disabled = false;
  @property() language = 'en';

  static override styles = css`
    .note {
      color: var(--secondary-text-color, #666);
      font-size: 0.85em;
      margin-block-start: 4px;
      overflow-wrap: anywhere;
    }
  `;

  override render() {
    const own = describeTarget(this.value);
    const inheritedText = describeTarget(this.inherited);
    const inherits = own === '' && inheritedText !== '';
    return html`
      <div class="wrap">
        <ha-selector
          .hass=${this.hass}
          .selector=${{ target: {} }}
          .value=${this.value}
          .disabled=${this.disabled}
          @value-changed=${this._onChange}
        ></ha-selector>
        ${inherits
          ? html`<div class="note inherited">
              ${t(this.language, 'inherits_target_from_defaults')}
              ${inheritedText}
            </div>`
          : own === ''
            ? html`<div class="note empty">${t(this.language, 'target_none')}</div>`
            : nothing}
      </div>
    `;
  }

  private _onChange = (event: CustomEvent) => {
    // `ha-selector` emits `undefined` when the last target is removed. The
    // rest of this card, and rule_schema.py, expect an object - so
    // normalise here rather than letting undefined reach the form state
    // and become a missing key in the websocket payload.
    const value = (event.detail?.value ?? {}) as Record<string, unknown>;
    this.dispatchEvent(
      new CustomEvent('target-changed', { detail: { value } }),
    );
  };
}
```

- [ ] **Step 5: Run the tests and watch them pass**

```bash
npm --prefix frontend test -- test/target-editor.test.ts
npm --prefix frontend run typecheck
```

Expected: 6 passing, no typecheck errors.

If `describeTarget` is not exported from `format.ts`, export it — it is
already used by `rule-dialog.ts`, so it exists; check the import there.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/target-editor.ts frontend/src/strings.ts \
        frontend/test/target-editor.test.ts
git commit -m "feat: a target editor on ha-selector, not on a picker that may not exist"
```

---

## Task 3: The action and data editor

**Files:**
- Create: `frontend/src/service-editor.ts`
- Create: `frontend/test/service-editor.test.ts`

**Interfaces:**
- Consumes: `Hass` from `types.ts` (Task 1).
- Produces: `<shabbat-service-editor>` with properties
  `hass: Hass | null`, `action: string`, `data: Record<string, unknown>`,
  `disabled: boolean`. Emits `service-changed` with
  `detail: { action: string, data: Record<string, unknown> }`.

Note it takes `action` and `data` as **two** properties but emits them
together, because `<ha-service-control>` speaks a single
`{action, target, data}` value object and changing the action rewrites the
data.

- [ ] **Step 1: Write the failing tests**

Create `frontend/test/service-editor.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import '../src/service-editor';

async function render(props: Record<string, unknown> = {}) {
  const el = document.createElement('shabbat-service-editor') as HTMLElement &
    Record<string, any>;
  Object.assign(el, {
    hass: { states: {} }, action: '', data: {},
    disabled: false, language: 'en', ...props,
  });
  document.body.appendChild(el);
  await el.updateComplete;
  return el;
}

function control(el: any) {
  return el.shadowRoot.querySelector('ha-service-control');
}

describe('shabbat-service-editor', () => {
  it('hands ha-service-control the action and data as one value', async () => {
    const el = await render({
      action: 'climate.set_temperature', data: { temperature: 26 },
    });
    expect(control(el).value).toEqual({
      action: 'climate.set_temperature', data: { temperature: 26 },
    });
    expect(control(el).hass).toBe(el.hass);
  });

  it('never hands it a target, which this card owns separately', async () => {
    const el = await render({ action: 'switch.turn_on' });
    expect(control(el).value.target).toBeUndefined();
  });

  it('splits value-changed back into action and data', async () => {
    const el = await render();
    const seen: any[] = [];
    el.addEventListener('service-changed', (e: Event) => {
      seen.push((e as CustomEvent).detail);
    });
    control(el).dispatchEvent(new CustomEvent('value-changed', {
      detail: { value: {
        action: 'climate.set_temperature', data: { temperature: 24 },
      } },
    }));
    expect(seen).toEqual([{
      action: 'climate.set_temperature', data: { temperature: 24 },
    }]);
  });

  it('drops any target ha-service-control emits', async () => {
    const el = await render();
    const seen: any[] = [];
    el.addEventListener('service-changed', (e: Event) => {
      seen.push((e as CustomEvent).detail);
    });
    control(el).dispatchEvent(new CustomEvent('value-changed', {
      detail: { value: {
        action: 'switch.turn_on',
        target: { entity_id: ['switch.stray'] },
        data: {},
      } },
    }));
    expect(seen).toEqual([{ action: 'switch.turn_on', data: {} }]);
  });

  it('normalises a missing action or data rather than emitting undefined', async () => {
    const el = await render();
    const seen: any[] = [];
    el.addEventListener('service-changed', (e: Event) => {
      seen.push((e as CustomEvent).detail);
    });
    control(el).dispatchEvent(new CustomEvent('value-changed', {
      detail: { value: {} },
    }));
    expect(seen).toEqual([{ action: '', data: {} }]);
  });

  it('disables the control when the user cannot write', async () => {
    const el = await render({ disabled: true });
    expect(control(el).disabled).toBe(true);
  });
});
```

- [ ] **Step 2: Run them and watch them fail**

```bash
npm --prefix frontend test -- test/service-editor.test.ts
```

Expected: FAIL — element not defined.

- [ ] **Step 3: Write the element**

Create `frontend/src/service-editor.ts`:

```ts
import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import type { Hass } from './types';

/**
 * The rule's action and its data, on Home Assistant's own service control.
 *
 * This is the whole point of v2 on the frontend: the form for every
 * service comes from Home Assistant's own schema for that service, so
 * this card carries no per-domain form code and gains support for new
 * services without changing.
 *
 * `<ha-service-control>` speaks a single `{action, target, data}` value,
 * and it HAS internal target logic - but on a dashboard its target UI
 * depends on `ha-target-picker`, which is not pre-registered outside the
 * automation editor. So this card owns the target separately (see
 * `target-editor.ts`) and this element neither passes a target down nor
 * lets one back up. Dropping it on the way out is not defensive coding:
 * without it, a stray target from HA's element would silently overwrite
 * what the user chose in the target editor.
 */
@customElement('shabbat-service-editor')
export class ShabbatServiceEditor extends LitElement {
  @property({ attribute: false }) hass: Hass | null = null;
  @property() action = '';
  @property({ attribute: false }) data: Record<string, unknown> = {};
  @property({ type: Boolean }) disabled = false;

  static override styles = css`
    :host { display: block; }
  `;

  override render() {
    return html`
      <div class="wrap">
        <ha-service-control
          .hass=${this.hass}
          .value=${{ action: this.action, data: this.data }}
          .disabled=${this.disabled}
          .showAdvanced=${this.hass?.userData?.showAdvanced === true}
          @value-changed=${this._onChange}
        ></ha-service-control>
      </div>
    `;
  }

  private _onChange = (event: CustomEvent) => {
    const value = (event.detail?.value ?? {}) as Record<string, unknown>;
    this.dispatchEvent(new CustomEvent('service-changed', {
      detail: {
        action: typeof value.action === 'string' ? value.action : '',
        data: (value.data ?? {}) as Record<string, unknown>,
      },
    }));
  };
}
```

- [ ] **Step 4: Run the tests and watch them pass**

```bash
npm --prefix frontend test -- test/service-editor.test.ts
npm --prefix frontend run typecheck
```

Expected: 6 passing, no typecheck errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/service-editor.ts frontend/test/service-editor.test.ts
git commit -m "feat: an action and data editor on ha-service-control

The form for every service now comes from Home Assistant's own schema,
so this card carries no per-domain form code."
```

---

## Task 4: The replay editor

Smaller than the condition editor, and independent of it, so it comes first.

**Files:**
- Create: `frontend/src/replay-editor.ts`
- Create: `frontend/test/replay-editor.test.ts`
- Modify: `frontend/src/strings.ts`

**Interfaces:**
- Consumes: `ReplayData` from `types.ts` (`{ enabled: boolean; within?: string }`).
- Produces: `<shabbat-replay-editor>` with properties
  `value: ReplayData`, `disabled: boolean`, `language: string`. Emits
  `replay-changed` with `detail: { value: ReplayData }`.

- [ ] **Step 1: Write the failing tests**

Create `frontend/test/replay-editor.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import '../src/replay-editor';

async function render(props: Record<string, unknown> = {}) {
  const el = document.createElement('shabbat-replay-editor') as HTMLElement &
    Record<string, any>;
  Object.assign(el, {
    value: { enabled: false }, disabled: false, language: 'en', ...props,
  });
  document.body.appendChild(el);
  await el.updateComplete;
  return el;
}

const enabledBox = (el: any) =>
  el.shadowRoot.querySelector('input.replay-enabled') as HTMLInputElement;
const withinBox = (el: any) =>
  el.shadowRoot.querySelector('input.replay-within') as HTMLInputElement | null;

describe('shabbat-replay-editor', () => {
  it('is off by default and hides the window', async () => {
    const el = await render();
    expect(enabledBox(el).checked).toBe(false);
    expect(withinBox(el)).toBeNull();
  });

  it('emits enabled with a default window when switched on', async () => {
    const el = await render();
    const seen: any[] = [];
    el.addEventListener('replay-changed', (e: Event) => {
      seen.push((e as CustomEvent).detail.value);
    });
    enabledBox(el).checked = true;
    enabledBox(el).dispatchEvent(new Event('change'));
    expect(seen).toEqual([{ enabled: true, within: '01:00:00' }]);
  });

  it('shows the window once enabled', async () => {
    const el = await render({ value: { enabled: true, within: '02:30:00' } });
    expect(withinBox(el)!.value).toBe('02:30:00');
  });

  it('emits a changed window', async () => {
    const el = await render({ value: { enabled: true, within: '01:00:00' } });
    const seen: any[] = [];
    el.addEventListener('replay-changed', (e: Event) => {
      seen.push((e as CustomEvent).detail.value);
    });
    withinBox(el)!.value = '00:45:00';
    withinBox(el)!.dispatchEvent(new Event('change'));
    expect(seen).toEqual([{ enabled: true, within: '00:45:00' }]);
  });

  it('treats a cleared window as no bound, dropping the key', async () => {
    const el = await render({ value: { enabled: true, within: '01:00:00' } });
    const seen: any[] = [];
    el.addEventListener('replay-changed', (e: Event) => {
      seen.push((e as CustomEvent).detail.value);
    });
    withinBox(el)!.value = '';
    withinBox(el)!.dispatchEvent(new Event('change'));
    expect(seen).toEqual([{ enabled: true }]);
  });

  it('forgets the window when switched off, so off means off', async () => {
    const el = await render({ value: { enabled: true, within: '01:00:00' } });
    const seen: any[] = [];
    el.addEventListener('replay-changed', (e: Event) => {
      seen.push((e as CustomEvent).detail.value);
    });
    enabledBox(el).checked = false;
    enabledBox(el).dispatchEvent(new Event('change'));
    expect(seen).toEqual([{ enabled: false }]);
  });
});
```

- [ ] **Step 2: Run them and watch them fail**

```bash
npm --prefix frontend test -- test/replay-editor.test.ts
```

Expected: FAIL — element not defined.

- [ ] **Step 3: Add the strings**

In `frontend/src/strings.ts`, add to `en`:

```ts
    replay_after_restart: 'Replay after a restart',
    replay_within_label: 'Only if less than',
    replay_help: 'Off by default: after a restart, nothing that already passed is re-run.',
```

and to `he`:

```ts
    replay_after_restart: 'הפעלה חוזרת לאחר אתחול',
    replay_within_label: 'רק אם עברו פחות מ־',
    replay_help: 'כברירת מחדל כבוי: לאחר אתחול, מה שכבר עבר לא יופעל שוב.',
```

- [ ] **Step 4: Write the element**

Create `frontend/src/replay-editor.ts`:

```ts
import { LitElement, css, html, nothing } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { t } from './strings';
import type { ReplayData } from './types';

/** Offered when replay is first switched on. One hour, in HH:MM:SS. */
const DEFAULT_WITHIN = '01:00:00';

/**
 * Whether, and how late, a rule may be re-run after a restart.
 *
 * Replay is OFF by default, and that is a deliberate product decision
 * rather than a conservative default: this integration's defining
 * property is fire-once-never-re-assert, and the owner chose the
 * strictest reading - after a restart, nothing unexpected ever fires.
 * See docs/known-behaviours.md.
 *
 * Note `within` is dropped rather than set to null when cleared. An
 * absent `within` means "no bound" to rule_schema.py, and a plain
 * `<input type="text">` is used rather than a duration selector because
 * `ha-textfield` is NOT pre-registered on a dashboard.
 */
@customElement('shabbat-replay-editor')
export class ShabbatReplayEditor extends LitElement {
  @property({ attribute: false }) value: ReplayData = { enabled: false };
  @property({ type: Boolean }) disabled = false;
  @property() language = 'en';

  static override styles = css`
    .field { display: flex; align-items: center; gap: 12px; margin-block: 8px; }
    .field label { min-inline-size: 9em; }
    input[type='text'] {
      font: inherit;
      padding-block: 4px;
      padding-inline: 6px;
      flex: 1;
      min-inline-size: 0;
    }
    .help { color: var(--secondary-text-color, #666); font-size: 0.85em; }
  `;

  override render() {
    return html`
      <div class="wrap">
        <div class="field">
          <label for="replay-enabled">
            ${t(this.language, 'replay_after_restart')}
          </label>
          <input
            id="replay-enabled"
            class="replay-enabled"
            type="checkbox"
            .checked=${this.value.enabled}
            ?disabled=${this.disabled}
            @change=${this._onEnabled}
          />
        </div>
        ${this.value.enabled
          ? html`<div class="field">
              <label for="replay-within">
                ${t(this.language, 'replay_within_label')}
              </label>
              <input
                id="replay-within"
                class="replay-within"
                type="text"
                placeholder="HH:MM:SS"
                .value=${this.value.within ?? ''}
                ?disabled=${this.disabled}
                @change=${this._onWithin}
              />
            </div>`
          : html`<div class="help">${t(this.language, 'replay_help')}</div>`}
      </div>
    `;
  }

  private _emit(value: ReplayData) {
    this.dispatchEvent(new CustomEvent('replay-changed', { detail: { value } }));
  }

  private _onEnabled = (event: Event) => {
    const enabled = (event.target as HTMLInputElement).checked;
    // Switching off drops the window entirely: a remembered window on a
    // disabled replay is state the user cannot see, and it would come
    // back if they toggled twice.
    this._emit(
      enabled
        ? { enabled: true, within: this.value.within ?? DEFAULT_WITHIN }
        : { enabled: false },
    );
  };

  private _onWithin = (event: Event) => {
    const within = (event.target as HTMLInputElement).value.trim();
    // No validation here - rule_schema.py owns that, and a half-typed
    // "01:" must not be silently rewritten under the user's cursor.
    this._emit(within === '' ? { enabled: true } : { enabled: true, within });
  };
}
```

- [ ] **Step 5: Run the tests and watch them pass**

```bash
npm --prefix frontend test -- test/replay-editor.test.ts
npm --prefix frontend run typecheck
```

Expected: 6 passing, no typecheck errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/replay-editor.ts frontend/src/strings.ts \
        frontend/test/replay-editor.test.ts
git commit -m "feat: a replay editor, off by default and saying so"
```

---

## Task 5: The condition editor

A condition is an arbitrary Home Assistant condition config — an opaque nested
dict this card has no business parsing. So this editor is a **list manager over
YAML text**, not a structured builder: it owns adding, removing and reordering
entries, and each entry's body is edited as text.

That is a deliberate scope choice, and the reason is worth stating: HA's own
structured condition editor is not available as a dashboard-safe element, and a
hand-written one would be a large surface that duplicates HA's schemas — exactly
what this plan exists to stop doing. Text is honest about what it is.

**Files:**
- Create: `frontend/src/condition-editor.ts`
- Create: `frontend/test/condition-editor.test.ts`
- Modify: `frontend/src/strings.ts`
- Modify: `frontend/package.json` (add `js-yaml`)

**Interfaces:**
- Consumes: nothing from earlier tasks beyond `strings.ts`.
- Produces: `<shabbat-condition-editor>` with properties
  `value: Record<string, unknown>[]`, `disabled: boolean`,
  `language: string`. Emits `condition-changed` with
  `detail: { value: Record<string, unknown>[] }`. Emits it **only for
  parseable text**, and exposes `hasError: boolean` for the dialog to read.

- [ ] **Step 1: Add the YAML dependency**

```bash
npm --prefix frontend install --save-exact js-yaml@4.1.0
npm --prefix frontend install --save-exact --save-dev @types/js-yaml@4.0.9
```

`js-yaml` is what Home Assistant's own frontend uses for this, and YAML is the
form every HA user already reads conditions in. Confirm it appears in
`frontend/package.json` dependencies before continuing.

- [ ] **Step 2: Write the failing tests**

Create `frontend/test/condition-editor.test.ts`:

```ts
import { describe, expect, it } from 'vitest';
import '../src/condition-editor';

async function render(props: Record<string, unknown> = {}) {
  const el = document.createElement('shabbat-condition-editor') as HTMLElement &
    Record<string, any>;
  Object.assign(el, {
    value: [], disabled: false, language: 'en', ...props,
  });
  document.body.appendChild(el);
  await el.updateComplete;
  return el;
}

const rows = (el: any) => el.shadowRoot.querySelectorAll('.condition-row');
const areaFor = (el: any, i: number) =>
  rows(el)[i].querySelector('textarea') as HTMLTextAreaElement;

const stateCondition = { condition: 'state', entity_id: 'input_boolean.a', state: 'on' };

describe('shabbat-condition-editor', () => {
  it('shows nothing but an add button when there are no conditions', async () => {
    const el = await render();
    expect(rows(el).length).toBe(0);
    expect(el.shadowRoot.querySelector('button.add-condition')).not.toBeNull();
  });

  it('renders one row per condition, as YAML', async () => {
    const el = await render({ value: [stateCondition] });
    expect(rows(el).length).toBe(1);
    expect(areaFor(el, 0).value).toContain('condition: state');
    expect(areaFor(el, 0).value).toContain('input_boolean.a');
  });

  it('emits the parsed condition when a row is edited', async () => {
    const el = await render({ value: [stateCondition] });
    const seen: any[] = [];
    el.addEventListener('condition-changed', (e: Event) => {
      seen.push((e as CustomEvent).detail.value);
    });
    const area = areaFor(el, 0);
    area.value = 'condition: state\nentity_id: input_boolean.b\nstate: "off"';
    area.dispatchEvent(new Event('change'));
    expect(seen).toEqual([[
      { condition: 'state', entity_id: 'input_boolean.b', state: 'off' },
    ]]);
  });

  it('does not emit while the YAML is unparseable, and says so', async () => {
    const el = await render({ value: [stateCondition] });
    const seen: any[] = [];
    el.addEventListener('condition-changed', (e: Event) => {
      seen.push((e as CustomEvent).detail.value);
    });
    const area = areaFor(el, 0);
    area.value = 'condition: [state';
    area.dispatchEvent(new Event('change'));
    await el.updateComplete;
    expect(seen).toEqual([]);
    expect(el.hasError).toBe(true);
    expect(rows(el)[0].querySelector('.row-error')).not.toBeNull();
  });

  it('clears the error once the YAML parses again', async () => {
    const el = await render({ value: [stateCondition] });
    const area = areaFor(el, 0);
    area.value = 'condition: [state';
    area.dispatchEvent(new Event('change'));
    await el.updateComplete;
    expect(el.hasError).toBe(true);
    area.value = 'condition: state\nentity_id: input_boolean.a\nstate: "on"';
    area.dispatchEvent(new Event('change'));
    await el.updateComplete;
    expect(el.hasError).toBe(false);
  });

  it('rejects YAML that is valid but is not a mapping', async () => {
    const el = await render({ value: [stateCondition] });
    const seen: any[] = [];
    el.addEventListener('condition-changed', (e: Event) => {
      seen.push((e as CustomEvent).detail.value);
    });
    const area = areaFor(el, 0);
    area.value = '- one\n- two';
    area.dispatchEvent(new Event('change'));
    await el.updateComplete;
    expect(seen).toEqual([]);
    expect(el.hasError).toBe(true);
  });

  it('adds an empty condition row', async () => {
    const el = await render();
    const seen: any[] = [];
    el.addEventListener('condition-changed', (e: Event) => {
      seen.push((e as CustomEvent).detail.value);
    });
    el.shadowRoot.querySelector('button.add-condition').click();
    expect(seen).toEqual([[{ condition: 'state' }]]);
  });

  it('removes the row that was pressed, not the first', async () => {
    const second = { condition: 'time', after: '20:00:00' };
    const el = await render({ value: [stateCondition, second] });
    const seen: any[] = [];
    el.addEventListener('condition-changed', (e: Event) => {
      seen.push((e as CustomEvent).detail.value);
    });
    rows(el)[1].querySelector('button.remove-condition').click();
    expect(seen).toEqual([[stateCondition]]);
  });

  it('disables every control when the user cannot write', async () => {
    const el = await render({ value: [stateCondition], disabled: true });
    expect(areaFor(el, 0).disabled).toBe(true);
    expect(
      el.shadowRoot.querySelector('button.add-condition').disabled,
    ).toBe(true);
  });
});
```

- [ ] **Step 3: Run them and watch them fail**

```bash
npm --prefix frontend test -- test/condition-editor.test.ts
```

Expected: FAIL — element not defined.

- [ ] **Step 4: Add the strings**

In `frontend/src/strings.ts`, add to `en`:

```ts
    conditions: 'Conditions',
    conditions_help: 'All conditions must pass, or the rule does not run and says why.',
    add_condition: 'Add condition',
    remove_condition: 'Remove',
    condition_unparseable: 'Not valid YAML — this condition is not being saved.',
    condition_not_a_mapping: 'A condition must be a mapping, like `condition: state`.',
```

and to `he`:

```ts
    conditions: 'תנאים',
    conditions_help: 'כל התנאים חייבים להתקיים, אחרת הכלל לא ירוץ ויציין זאת.',
    add_condition: 'הוספת תנאי',
    remove_condition: 'הסרה',
    condition_unparseable: 'YAML לא תקין — התנאי הזה לא נשמר.',
    condition_not_a_mapping: 'תנאי חייב להיות מפה, כמו `condition: state`.',
```

- [ ] **Step 5: Write the element**

Create `frontend/src/condition-editor.ts`:

```ts
import { LitElement, css, html, nothing } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { dump, load } from 'js-yaml';
import { t } from './strings';

/** What "Add condition" inserts: the shortest thing that is still a condition. */
const NEW_CONDITION = { condition: 'state' };

/**
 * The rule's conditions, as a list of YAML documents.
 *
 * A Home Assistant condition config is an arbitrary nested mapping, and
 * this card has no business knowing their schemas - the whole point of v2
 * is that Home Assistant owns *what*. There is no dashboard-safe
 * structured condition editor to embed (see the spec's frontend
 * availability findings), and hand-writing one would mean duplicating
 * HA's condition schemas here, which is exactly what this plan removes
 * elsewhere. So this element owns the LIST - add, remove, per-row errors -
 * and each entry's body is text.
 *
 * A `<textarea>` rather than `ha-code-editor` for the same reason the
 * replay editor uses a plain input: element availability on a dashboard
 * is not something to depend on.
 *
 * UNPARSEABLE TEXT IS NEVER EMITTED. The alternative - emitting a partial
 * parse - would silently save a condition the user did not write, and a
 * condition that does not mean what it says is worse than one that is
 * visibly broken. `hasError` lets the dialog refuse to save.
 */
@customElement('shabbat-condition-editor')
export class ShabbatConditionEditor extends LitElement {
  @property({ attribute: false }) value: Record<string, unknown>[] = [];
  @property({ type: Boolean }) disabled = false;
  @property() language = 'en';

  /** Per-row parse errors, keyed by index. Read by the dialog via `hasError`. */
  @state() private _errors: Record<number, string> = {};

  get hasError(): boolean {
    return Object.keys(this._errors).length > 0;
  }

  static override styles = css`
    .condition-row {
      display: flex;
      gap: 8px;
      align-items: flex-start;
      margin-block: 8px;
    }
    textarea {
      font-family: var(--code-font-family, monospace);
      font-size: 0.85em;
      flex: 1;
      min-inline-size: 0;
      min-block-size: 4.5em;
      padding: 6px;
    }
    .row-error {
      color: var(--error-color, #d64545);
      font-size: 0.8em;
      margin-block-start: 2px;
    }
    .body { flex: 1; min-inline-size: 0; }
    .help { color: var(--secondary-text-color, #666); font-size: 0.85em; }
    button {
      font: inherit;
      padding-block: 4px;
      padding-inline: 8px;
      border-radius: 6px;
      border: 1px solid var(--divider-color, #e0e0e0);
      background: var(--card-background-color, #fff);
      color: inherit;
      cursor: pointer;
    }
    button[disabled] { opacity: 0.5; cursor: not-allowed; }
  `;

  override render() {
    return html`
      <div class="wrap">
        <div class="help">${t(this.language, 'conditions_help')}</div>
        ${this.value.map((item, index) => this._row(item, index))}
        <button
          class="add-condition"
          ?disabled=${this.disabled}
          @click=${this._onAdd}
        >
          ${t(this.language, 'add_condition')}
        </button>
      </div>
    `;
  }

  private _row(item: Record<string, unknown>, index: number) {
    const error = this._errors[index];
    return html`
      <div class="condition-row">
        <div class="body">
          <textarea
            .value=${dump(item).trimEnd()}
            ?disabled=${this.disabled}
            @change=${(event: Event) => this._onEdit(event, index)}
          ></textarea>
          ${error
            ? html`<div class="row-error">${error}</div>`
            : nothing}
        </div>
        <button
          class="remove-condition"
          ?disabled=${this.disabled}
          @click=${() => this._onRemove(index)}
        >
          ${t(this.language, 'remove_condition')}
        </button>
      </div>
    `;
  }

  private _emit(value: Record<string, unknown>[]) {
    this.dispatchEvent(
      new CustomEvent('condition-changed', { detail: { value } }),
    );
  }

  private _setError(index: number, message: string | null) {
    const errors = { ...this._errors };
    if (message === null) delete errors[index];
    else errors[index] = message;
    this._errors = errors;
  }

  private _onEdit(event: Event, index: number) {
    const text = (event.target as HTMLTextAreaElement).value;
    let parsed: unknown;
    try {
      parsed = load(text);
    } catch {
      this._setError(index, t(this.language, 'condition_unparseable'));
      return;
    }
    // A condition is a mapping. A list or a bare scalar parses fine and
    // would be accepted by `load` while being meaningless as a condition,
    // so it is rejected here rather than sent to the server to fail.
    if (
      parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)
    ) {
      this._setError(index, t(this.language, 'condition_not_a_mapping'));
      return;
    }
    this._setError(index, null);
    const next = [...this.value];
    next[index] = parsed as Record<string, unknown>;
    this._emit(next);
  }

  private _onAdd = () => {
    this._emit([...this.value, { ...NEW_CONDITION }]);
  };

  private _onRemove(index: number) {
    // Errors are keyed by index, so removing a row would leave every later
    // error pointing at the wrong row. Clearing them is correct rather than
    // lazy: the rows all re-render from `value` immediately after this.
    this._errors = {};
    this._emit(this.value.filter((_, i) => i !== index));
  }
}
```

- [ ] **Step 6: Run the tests and watch them pass**

```bash
npm --prefix frontend test -- test/condition-editor.test.ts
npm --prefix frontend run typecheck
```

Expected: 10 passing, no typecheck errors.

- [ ] **Step 7: Verify the bundle still builds and did not balloon**

```bash
npm --prefix frontend run build
ls -l custom_components/shabbat_scheduler/www/
```

`js-yaml` is now bundled. Record the size in your report. If the bundle has
grown by more than ~100 KB, say so — it is committed to the repo for HACS.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/condition-editor.ts frontend/src/strings.ts \
        frontend/test/condition-editor.test.ts \
        frontend/package.json frontend/package-lock.json \
        custom_components/shabbat_scheduler/www/
git commit -m "feat: a condition editor that owns the list and leaves the schema to HA

Unparseable text is never emitted: a condition that does not mean what it
says is worse than one that is visibly broken."
```

---

## Task 6: Compose the editors into the rule dialog

The task that actually restores authoring. Deletes the read-only block and the
raw `action` text input.

**Files:**
- Modify: `frontend/src/rule-dialog.ts`
- Modify: `frontend/test/rule-dialog.test.ts`
- Modify: `frontend/src/strings.ts` (remove now-unused keys)

**Interfaces:**
- Consumes: `<shabbat-target-editor>` (`target-changed`),
  `<shabbat-service-editor>` (`service-changed`),
  `<shabbat-condition-editor>` (`condition-changed`, `hasError`),
  `<shabbat-replay-editor>` (`replay-changed`); `Hass` from Task 1.
- Produces: a `shabbat-rule-dialog` whose `dialog-save` detail carries a
  complete, authored `RuleFormState`.

- [ ] **Step 1: Write the failing tests**

Add to `frontend/test/rule-dialog.test.ts`. Reuse the file's existing `render`
helper; add `hass: { states: {} }` to its default props.

```ts
const editors = (el: any) => ({
  target: el.shadowRoot.querySelector('shabbat-target-editor'),
  service: el.shadowRoot.querySelector('shabbat-service-editor'),
  condition: el.shadowRoot.querySelector('shabbat-condition-editor'),
  replay: el.shadowRoot.querySelector('shabbat-replay-editor'),
});

it('offers all four editors instead of a read-only block', async () => {
  const el = await render();
  const found = editors(el);
  expect(found.target).not.toBeNull();
  expect(found.service).not.toBeNull();
  expect(found.condition).not.toBeNull();
  expect(found.replay).not.toBeNull();
  expect(el.shadowRoot.querySelector('.readonly')).toBeNull();
  expect(el.shadowRoot.querySelector('input.action')).toBeNull();
});

it('seeds every editor from the rule being edited', async () => {
  const el = await render();
  const found = editors(el);
  expect(found.service.action).toBe('climate.set_temperature');
  expect(found.service.data).toEqual({ temperature: 26 });
  expect(found.target.value).toEqual({ entity_id: ['climate.salon'] });
  expect(found.replay.value).toEqual({ enabled: false });
});

it('passes hass to the editors that need it', async () => {
  const el = await render();
  const found = editors(el);
  expect(found.service.hass).toBe(el.hass);
  expect(found.target.hass).toBe(el.hass);
});

it('gives the target editor the shared defaults to report inheritance', async () => {
  const el = await render({
    defaults: { target: { entity_id: ['switch.shared'] } },
  });
  expect(editors(el).target.inherited).toEqual({
    entity_id: ['switch.shared'],
  });
});

it('saves an action and data changed through the service editor', async () => {
  const el = await render();
  const saved: any[] = [];
  el.addEventListener('dialog-save', (e: Event) => {
    saved.push((e as CustomEvent).detail.form);
  });
  editors(el).service.dispatchEvent(new CustomEvent('service-changed', {
    detail: { action: 'switch.turn_on', data: {} },
  }));
  await el.updateComplete;
  el.shadowRoot.querySelector('button.save').click();
  expect(saved[0].action).toBe('switch.turn_on');
  expect(saved[0].data).toEqual({});
});

it('saves a target changed through the target editor', async () => {
  const el = await render();
  const saved: any[] = [];
  el.addEventListener('dialog-save', (e: Event) => {
    saved.push((e as CustomEvent).detail.form);
  });
  editors(el).target.dispatchEvent(new CustomEvent('target-changed', {
    detail: { value: { area_id: ['salon'] } },
  }));
  await el.updateComplete;
  el.shadowRoot.querySelector('button.save').click();
  expect(saved[0].target).toEqual({ area_id: ['salon'] });
});

it('saves conditions and replay changed through their editors', async () => {
  const el = await render();
  const saved: any[] = [];
  el.addEventListener('dialog-save', (e: Event) => {
    saved.push((e as CustomEvent).detail.form);
  });
  editors(el).condition.dispatchEvent(new CustomEvent('condition-changed', {
    detail: { value: [{ condition: 'state', entity_id: 'x', state: 'on' }] },
  }));
  editors(el).replay.dispatchEvent(new CustomEvent('replay-changed', {
    detail: { value: { enabled: true, within: '00:30:00' } },
  }));
  await el.updateComplete;
  el.shadowRoot.querySelector('button.save').click();
  expect(saved[0].condition).toEqual([
    { condition: 'state', entity_id: 'x', state: 'on' },
  ]);
  expect(saved[0].replay).toEqual({ enabled: true, within: '00:30:00' });
});

it('refuses to save while a condition is unparseable', async () => {
  const el = await render();
  const saved: any[] = [];
  el.addEventListener('dialog-save', () => { saved.push(true); });
  const condition = editors(el).condition as any;
  const area = condition.shadowRoot.querySelector('textarea');
  // The dialog must ask the editor, not re-parse the text itself.
  condition.value = [{ condition: 'state' }];
  await condition.updateComplete;
  const box = condition.shadowRoot.querySelector('textarea') as HTMLTextAreaElement;
  box.value = 'condition: [state';
  box.dispatchEvent(new Event('change'));
  await condition.updateComplete;
  await el.updateComplete;
  el.shadowRoot.querySelector('button.save').click();
  expect(saved).toEqual([]);
  expect(el.shadowRoot.querySelector('.error')).not.toBeNull();
  expect(area).not.toBeNull();
});

it('does not re-seed the form when hass is reassigned', async () => {
  const el = await render();
  editors(el).service.dispatchEvent(new CustomEvent('service-changed', {
    detail: { action: 'switch.turn_on', data: {} },
  }));
  await el.updateComplete;
  el.hass = { states: {}, changed: true };   // HA does this constantly
  await el.updateComplete;
  expect(editors(el).service.action).toBe('switch.turn_on');
});
```

- [ ] **Step 2: Run them and watch them fail**

```bash
npm --prefix frontend test -- test/rule-dialog.test.ts
```

Expected: the new tests FAIL. Existing tests that assert on `.readonly`,
`.ro-target`, `.ro-data`, `.ro-condition`, `.ro-replay` or `input.action` will
also fail — that is correct, they described the read-only stopgap. Delete
exactly those, and **list every test you delete in your report with one line
on what property it asserted**, so a reviewer can confirm nothing else went
with them.

- [ ] **Step 3: Import the editors and add the save guard**

In `frontend/src/rule-dialog.ts`, add the imports:

```ts
import './condition-editor';
import './replay-editor';
import './service-editor';
import './target-editor';
```

Add a state field and a query for the condition editor:

```ts
  @state() private _conditionError = false;
```

- [ ] **Step 4: Replace the read-only block with the editors**

Delete the whole `<div class="readonly">…</div>` block, the
`${this._text('action', …)}` line, and the now-unused `_describeData`,
`_describeConditions` and `_describeReplay` methods. Remove `'action'` from
`_text`'s key union. In its place, inside the `.form` div and after the
`enabled` field:

```ts
            <shabbat-service-editor
              .hass=${this.hass}
              .action=${this._form.action}
              .data=${this._form.data}
              .disabled=${!this.canWrite}
              @service-changed=${(event: CustomEvent) =>
                this._patch({
                  action: event.detail.action, data: event.detail.data,
                })}
            ></shabbat-service-editor>

            <shabbat-target-editor
              .hass=${this.hass}
              .value=${this._form.target}
              .inherited=${this.defaults.target ?? {}}
              .disabled=${!this.canWrite}
              .language=${this.language}
              @target-changed=${(event: CustomEvent) =>
                this._patch({ target: event.detail.value })}
            ></shabbat-target-editor>

            <shabbat-condition-editor
              .value=${this._form.condition}
              .disabled=${!this.canWrite}
              .language=${this.language}
              @condition-changed=${(event: CustomEvent) => {
                this._conditionError = false;
                this._patch({ condition: event.detail.value });
              }}
            ></shabbat-condition-editor>

            <shabbat-replay-editor
              .value=${this._form.replay}
              .disabled=${!this.canWrite}
              .language=${this.language}
              @replay-changed=${(event: CustomEvent) =>
                this._patch({ replay: event.detail.value })}
            ></shabbat-replay-editor>
```

- [ ] **Step 5: Make save consult the condition editor**

Replace the save button's handler so it refuses while a condition is
unparseable. Add this method:

```ts
  /**
   * Save, unless a condition is currently unparseable.
   *
   * The editor is ASKED (`hasError`) rather than the text re-parsed here:
   * one parser, one answer. Re-parsing would be a second implementation of
   * the same rule, and the two would drift.
   *
   * This is not client-side revalidation of the rule - the Python side
   * still owns whether a condition is *valid*. It is refusing to send
   * something that is not even a condition yet.
   */
  private _onSave() {
    const editor = this.shadowRoot?.querySelector(
      'shabbat-condition-editor',
    ) as (HTMLElement & { hasError?: boolean }) | null;
    if (editor?.hasError) {
      this._conditionError = true;
      return;
    }
    this._conditionError = false;
    this._emit('dialog-save');
  }
```

and point the button at it:

```ts
                  @click=${() => this._onSave()}
```

Render the message. Put it next to the existing `error` block, and note the
existing block is `${this.error !== null ? … : nothing}` — add a sibling
rather than nesting a second expression at the template root:

```ts
          ${this._conditionError
            ? html`<div class="error condition-blocked">
                ${t(this.language, 'condition_unparseable')}
              </div>`
            : nothing}
```

- [ ] **Step 6: Remove the strings the read-only block used**

Delete `read_only_fields`, `none_set`, `inherits_target`, `replay_no`,
`replay_yes`, `replay_within`, `data` and `replay` from both `en` and `he` in
`frontend/src/strings.ts` — **but only those with no remaining reference.**
Check each one first:

```bash
grep -rn "read_only_fields\|none_set\|inherits_target\|replay_no\|replay_yes\|replay_within" frontend/src frontend/test
```

Leave any key that is still used. `target` and `condition` are likely still
used as labels — check before deleting.

- [ ] **Step 7: Run the tests and watch them pass**

```bash
npm --prefix frontend test -- test/rule-dialog.test.ts
npm --prefix frontend run typecheck
npm --prefix frontend test
```

Expected: all pass. Report the new total.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/rule-dialog.ts frontend/src/strings.ts \
        frontend/test/rule-dialog.test.ts
git commit -m "feat: the rule dialog authors a v2 rule again

Replaces Plan 1's honest-but-read-only block. A rule could not be created
from the card at all between the two."
```

---

## Task 7: Restore authoring in the defaults dialog

**Files:**
- Modify: `frontend/src/defaults-dialog.ts`
- Modify: `frontend/test/defaults-dialog.test.ts`
- Modify: `frontend/src/card.ts`

**Interfaces:**
- Consumes: `<shabbat-target-editor>` (Task 2),
  `<shabbat-service-editor>` (Task 3), `Hass` (Task 1).
- Produces: `<shabbat-defaults-dialog>` emits `dialog-save` with
  `detail: { defaults: Defaults }`; `card.ts` gains `_onDefaultsSave`.

Note `card.ts:375` currently carries a comment saying there is deliberately no
`_onDefaultsSave`. Replace that comment; do not leave it contradicting the
code.

- [ ] **Step 1: Write the failing tests**

Add to `frontend/test/defaults-dialog.test.ts`, reusing its render helper and
adding `hass: { states: {} }` to the defaults:

```ts
it('offers a target editor and a data editor', async () => {
  const el = await render({ canWrite: true });
  expect(el.shadowRoot.querySelector('shabbat-target-editor')).not.toBeNull();
  expect(el.shadowRoot.querySelector('shabbat-service-editor')).not.toBeNull();
});

it('seeds them from the current defaults', async () => {
  const el = await render({
    canWrite: true,
    defaults: { target: { entity_id: ['switch.a'] }, data: { temperature: 20 } },
  });
  expect(
    (el.shadowRoot.querySelector('shabbat-target-editor') as any).value,
  ).toEqual({ entity_id: ['switch.a'] });
  expect(
    (el.shadowRoot.querySelector('shabbat-service-editor') as any).data,
  ).toEqual({ temperature: 20 });
});

it('has a save button again, and emits what was edited', async () => {
  const el = await render({ canWrite: true, defaults: {} });
  const saved: any[] = [];
  el.addEventListener('dialog-save', (e: Event) => {
    saved.push((e as CustomEvent).detail.defaults);
  });
  el.shadowRoot.querySelector('shabbat-target-editor')!
    .dispatchEvent(new CustomEvent('target-changed', {
      detail: { value: { area_id: ['salon'] } },
    }));
  await el.updateComplete;
  const save = el.shadowRoot.querySelector('button.save') as HTMLButtonElement;
  expect(save).not.toBeNull();
  save.click();
  expect(saved).toEqual([{ target: { area_id: ['salon'] }, data: {} }]);
});

it('offers no save button to a user who cannot write', async () => {
  const el = await render({ canWrite: false });
  expect(el.shadowRoot.querySelector('button.save')).toBeNull();
});

it('sends only the data half of the service editor, never an action', async () => {
  const el = await render({ canWrite: true, defaults: {} });
  const saved: any[] = [];
  el.addEventListener('dialog-save', (e: Event) => {
    saved.push((e as CustomEvent).detail.defaults);
  });
  el.shadowRoot.querySelector('shabbat-service-editor')!
    .dispatchEvent(new CustomEvent('service-changed', {
      detail: { action: 'climate.set_temperature', data: { temperature: 22 } },
    }));
  await el.updateComplete;
  (el.shadowRoot.querySelector('button.save') as HTMLButtonElement).click();
  expect(saved[0].data).toEqual({ temperature: 22 });
  expect('action' in saved[0]).toBe(false);
});
```

- [ ] **Step 2: Run them and watch them fail**

```bash
npm --prefix frontend test -- test/defaults-dialog.test.ts
```

Expected: FAIL — no editors, no save button.

- [ ] **Step 3: Rebuild the dialog body**

In `frontend/src/defaults-dialog.ts`: import `./service-editor` and
`./target-editor`, add the `hass` property (Task 1 already added it), hold a
`@state() private _draft: Defaults` seeded once per open with the same
`_seeded`-key discipline `rule-dialog.ts` uses, render the two editors, and
restore the save button behind `canWrite`.

`validate_defaults` accepts exactly two keys, `target` and `data`. The service
editor emits an `action` too — **drop it**, as
`{target, data}` is the whole of what the defaults are.

Emit on save:

```ts
    this.dispatchEvent(new CustomEvent('dialog-save', {
      detail: { defaults: { target: this._draft.target ?? {},
                            data: this._draft.data ?? {} } },
    }));
```

- [ ] **Step 4: Wire `card.ts`**

Replace the `// NOTE: there is no _onDefaultsSave` comment near line 375 with
the handler, following the same shape as `_onSave` in that file (read it and
match its busy/error handling and its websocket command name — check
`websocket_api.py` for the exact `type`):

```ts
  private async _onDefaultsSave(event: CustomEvent) {
    await this._command({
      type: 'shabbat_scheduler/defaults/update',
      defaults: event.detail.defaults,
    });
  }
```

Use whatever `_command`-equivalent helper the file already has, and add
`@dialog-save=${this._onDefaultsSave}` to the `<shabbat-defaults-dialog>`
template.

- [ ] **Step 5: Confirm the command name against the server**

```bash
grep -n "defaults/" custom_components/shabbat_scheduler/websocket_api.py
```

`shabbat_scheduler/defaults/update` is what the server registers at
`websocket_api.py:241`, and what the snippet above uses. Confirm it rather than
trusting this plan, and check the payload key the handler expects — if the
names disagree, the server is right.

- [ ] **Step 6: Run the tests and watch them pass**

```bash
npm --prefix frontend test
npm --prefix frontend run typecheck
```

Expected: all pass.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/defaults-dialog.ts frontend/src/card.ts \
        frontend/test/defaults-dialog.test.ts
git commit -m "feat: the defaults dialog can save again

Its old form wrote {devices, settings}, which validate_defaults refuses,
so every press could only ever have failed."
```

---

## Task 8: Gap A — validate the frontend fixtures against a real payload

Carried from Plan 1, numbered so it cannot be dropped. The frontend suite was
**168/168 green for the whole period in which the card rendered every conflict
as an empty string**: every fixture was hand-written and used a `device` key
the backend had stopped sending. The tests agreed with each other and with
nothing else.

The fix is a generated fixture. Python writes a real `_state_payload` to JSON;
the frontend suite renders the card from that JSON; a Python test fails if the
committed JSON is stale.

**Files:**
- Create: `tests/test_frontend_fixture.py`
- Create: `frontend/test/fixtures/state-payload.json` (generated, committed)
- Create: `frontend/test/payload-contract.test.ts`

**Interfaces:**
- Consumes: `_state_payload` from `custom_components/shabbat_scheduler/websocket_api.py`.
- Produces: `frontend/test/fixtures/state-payload.json`, regenerated by
  `REGEN_FRONTEND_FIXTURE=1 uv run pytest tests/test_frontend_fixture.py`.

- [ ] **Step 1: Read how the payload is built**

```bash
grep -n "_state_payload" -A 40 custom_components/shabbat_scheduler/websocket_api.py
grep -n "conflict_warnings" -A 25 custom_components/shabbat_scheduler/block.py
```

You need a real payload containing **at least one conflict**, because that is
the field the silent bug lived in. Two enabled rules in the same profile and
day, at the same time, with overlapping targets.

- [ ] **Step 2: Write the failing test**

Create `tests/test_frontend_fixture.py`. Follow the existing conventions in
`tests/` for setting up a config entry — read `tests/test_websocket_api.py`
and reuse its fixtures rather than inventing a new setup.

```python
"""Keeps the card's test fixtures honest.

The frontend suite was 168/168 green through the entire period in which
the card rendered every conflict as an empty string: its fixtures were
hand-written and used a `device` key the backend had stopped sending, so
the tests agreed with each other and with nothing else. This test is the
only thing that makes a frontend fixture answerable to the server.

Regenerate with:

    REGEN_FRONTEND_FIXTURE=1 uv run pytest tests/test_frontend_fixture.py
"""

import json
import os
from pathlib import Path

FIXTURE = (
    Path(__file__).parent.parent
    / "frontend" / "test" / "fixtures" / "state-payload.json"
)


async def test_the_committed_frontend_fixture_matches_a_real_payload(
    hass, setup_integration,        # use this repo's real fixture names
):
    """The card's fixture is the server's payload, or the suite is lying."""
    # ... seed two rules that conflict, via the same path the websocket
    # API uses, then build the payload the card would receive.
    payload = await build_state_payload(hass)

    assert payload["warnings"], (
        "this fixture is only worth having if it carries a conflict - that "
        "is the field the silent bug lived in"
    )

    current = json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n"

    if os.environ.get("REGEN_FRONTEND_FIXTURE"):
        FIXTURE.parent.mkdir(parents=True, exist_ok=True)
        FIXTURE.write_text(current)

    assert FIXTURE.exists(), (
        f"{FIXTURE} is missing; regenerate with "
        f"REGEN_FRONTEND_FIXTURE=1 uv run pytest {__file__}"
    )
    assert FIXTURE.read_text() == current, (
        "the card's committed fixture no longer matches what the server "
        "sends. The frontend suite is now testing a payload shape that does "
        "not exist. Regenerate with REGEN_FRONTEND_FIXTURE=1 uv run pytest "
        f"{__file__} and fix whatever in the card broke."
    )
```

Replace `build_state_payload` with the real call — either `_state_payload`
directly or a round trip through the websocket command, whichever the existing
tests already do. **Prefer the websocket round trip**: it proves the wire
shape, which is what the card actually receives.

- [ ] **Step 3: Run it and watch it fail**

```bash
uv run pytest tests/test_frontend_fixture.py -v
```

Expected: FAIL — the fixture file does not exist.

- [ ] **Step 4: Generate the fixture**

```bash
REGEN_FRONTEND_FIXTURE=1 uv run pytest tests/test_frontend_fixture.py -v
uv run pytest tests/test_frontend_fixture.py -v
```

Expected: the first run writes the file, the second passes. Open the JSON and
confirm it has a non-empty `warnings` array with a `targets` key.

- [ ] **Step 5: Write the frontend contract test**

Create `frontend/test/payload-contract.test.ts`:

```ts
/**
 * The card, rendered from a payload the SERVER produced.
 *
 * Every other fixture in this suite is hand-written, which is how the
 * card once rendered every conflict as an empty string while this suite
 * was entirely green. `state-payload.json` is generated by
 * tests/test_frontend_fixture.py and a Python test fails if it drifts.
 */
import { describe, expect, it } from 'vitest';
import '../src/card';
import payload from './fixtures/state-payload.json';

describe('the card, against a real server payload', () => {
  it('renders a conflict warning as visible text', async () => {
    // Render the card with this payload as its state, using the same
    // mechanism the other card tests use.
    const el = await renderCardWithState(payload as any);
    const warnings = el.shadowRoot!.querySelector('shabbat-warnings');
    expect(warnings).not.toBeNull();
    const text = warnings!.shadowRoot!.textContent!.trim();
    expect(text.length).toBeGreaterThan(0);
    // The bug was an EMPTY string where an entity id belonged. Assert the
    // entity ids from the payload actually appear.
    const targets = (payload as any).warnings[0].targets as string[];
    expect(targets.length).toBeGreaterThan(0);
    for (const target of targets) expect(text).toContain(target);
  });

  it('renders every rule in the payload', async () => {
    const el = await renderCardWithState(payload as any);
    const rows = el.shadowRoot!.querySelectorAll('shabbat-rule-row');
    expect(rows.length).toBe((payload as any).rules.length);
  });

  it('renders each rule with a non-empty time and action', async () => {
    const el = await renderCardWithState(payload as any);
    for (const row of el.shadowRoot!.querySelectorAll('shabbat-rule-row')) {
      const text = (row as HTMLElement).shadowRoot!.textContent!.trim();
      expect(text.length).toBeGreaterThan(0);
    }
  });
});
```

Write `renderCardWithState` by reading `frontend/test/card.test.ts` and using
the same mechanism it uses to put the card into a subscribed state. Do not
invent a second one — if that mechanism is a local helper, export it or move
it to a shared `frontend/test/helpers.ts` and have both files use it.

- [ ] **Step 6: Enable JSON imports if needed**

```bash
npm --prefix frontend test -- test/payload-contract.test.ts
```

If the JSON import fails to typecheck, add `"resolveJsonModule": true` to
`frontend/tsconfig.json`'s `compilerOptions`.

- [ ] **Step 7: Run everything and watch it pass**

```bash
npm --prefix frontend test
npm --prefix frontend run typecheck
uv run pytest tests/test_frontend_fixture.py -v
```

- [ ] **Step 8: Prove the guard bites**

Ablate it — this is the point of the task, so do it and report the result:

1. Change one key name in `frontend/test/fixtures/state-payload.json` (e.g.
   `targets` to `device`) and confirm `tests/test_frontend_fixture.py` fails.
2. Restore it, then make `warnings.ts` render an empty string for a conflict
   and confirm `payload-contract.test.ts` fails.
3. Restore both.

Report exactly what failed in each case. If either ablation passes, the test
is decoration and must be fixed.

- [ ] **Step 9: Commit**

```bash
git add tests/test_frontend_fixture.py \
        frontend/test/fixtures/state-payload.json \
        frontend/test/payload-contract.test.ts \
        frontend/tsconfig.json frontend/test/helpers.ts
git commit -m "test: close Gap A - make a frontend fixture answerable to the server

The frontend suite was 168/168 green through the whole period in which the
card rendered every conflict as an empty string, because every fixture was
hand-written against a key the backend had stopped sending."
```

---

## Task 9: Gap B — a misspelt entity id must not report success

Carried from Plan 1, numbered. `async_call_from_config` accepts a target
naming an entity that does not exist, so a typo'd rule reports outcome
`"called"` — the quiet-failure shape this project exists to prevent.

There is already a **characterisation test** pinning today's wrong behaviour:
`tests/test_engine.py::test_a_target_entity_that_does_not_exist_is_still_reported_as_called`.
It will fail when you fix this. That is the design — **update it to assert the
new behaviour, and say so in your report.** Do not delete it.

**Files:**
- Modify: `custom_components/shabbat_scheduler/engine.py`
- Modify: `tests/test_engine.py`

**Interfaces:**
- Consumes: `homeassistant.helpers.target.async_extract_referenced_entity_ids`.
- Produces: a `_call` result dict that may carry
  `unknown_targets: list[str]`, and `outcome: "failed"` when **every**
  referenced entity is unknown.

**The design, and why:**

Check only **explicitly named** entity ids. `async_extract_referenced_entity_ids`
returns a `SelectedEntities` with `referenced` and `indirectly_referenced`.
Only `referenced` holds ids the user typed; `indirectly_referenced` was
expanded from an area, device or label via the registries, so those exist by
construction. Checking both would produce false positives.

Partial failure is reported, not fatal: if a rule targets three entities and
one is a typo, the call still helps the other two, so make the call and report
the unknown one. But if **every** referenced entity is unknown, nothing can
have happened, so the outcome is `failed` — reporting `called` there is the
lie this task removes.

An empty target (`notify.persistent_notification` and friends) has no
referenced entities and is therefore never affected.

- [ ] **Step 1: Read the existing characterisation test and `_call`**

```bash
grep -n "does_not_exist" -B 10 -A 30 tests/test_engine.py
grep -n "async def _call" -A 30 custom_components/shabbat_scheduler/engine.py
```

- [ ] **Step 2: Write the failing tests**

Add to `tests/test_engine.py`, matching its existing fixtures and style:

These use the real names already in `tests/test_engine.py`: the `engine`
fixture (line 27), the module-level `_rule(action=, entities=, **kwargs)`
helper (line 34) and `engine.async_apply_rule(rule)`. There is no
`make_rule` fixture and no `engine.apply` — do not introduce either.

```python
async def test_a_target_naming_only_unknown_entities_is_reported_as_failed(
    hass, engine
):
    """A typo must not look like a rule that fired.

    Home Assistant's service layer accepts a target naming an entity that
    does not exist without raising, so the engine has nothing to report
    but success unless it looks first.
    """
    rule = _rule(
        action="input_boolean.turn_on",
        entities=("input_boolean.doe_not_exist",),
    )
    [result] = await engine.async_apply_rule(rule)
    assert result["outcome"] == "failed"
    assert result["unknown_targets"] == ["input_boolean.doe_not_exist"]


async def test_a_partly_wrong_target_still_calls_and_still_reports_the_typo(
    hass, engine
):
    """One typo among three must not suppress the other two."""
    hass.states.async_set("input_boolean.real_one", "off")
    hass.states.async_set("input_boolean.real_two", "off")
    rule = _rule(
        action="input_boolean.turn_on",
        entities=(
            "input_boolean.real_one",
            "input_boolean.nope",
            "input_boolean.real_two",
        ),
    )
    [result] = await engine.async_apply_rule(rule)
    assert result["outcome"] == "called"
    assert result["unknown_targets"] == ["input_boolean.nope"]


async def test_an_area_target_is_not_checked_entity_by_entity(hass, engine):
    """Only ids the USER typed are checked.

    Entities reached through an area, device or label come out of the
    registries, so they exist by construction; checking them would report
    a typo that is not there.

    `_rule`'s `entities` argument builds an entity_id target, so this one
    constructs the Rule directly to get an area target.
    """
    rule = _rule(action="input_boolean.turn_on", entities=())
    rule = replace(rule, target={"area_id": ["nowhere"]})
    [result] = await engine.async_apply_rule(rule)
    assert "unknown_targets" not in result


async def test_a_rule_with_no_target_is_unaffected(hass, engine):
    """notify.* and friends carry no entity at all."""
    rule = _rule(action="notify.persistent_notification", entities=())
    [result] = await engine.async_apply_rule(rule)
    assert "unknown_targets" not in result


async def test_a_dry_run_still_reports_an_unknown_target(hass, engine):
    """A dry run is where you WANT to find the typo."""
    engine.store.dry_run = True      # match how other tests in this file set it
    rule = _rule(
        action="input_boolean.turn_on", entities=("input_boolean.nope",),
    )
    [result] = await engine.async_apply_rule(rule)
    assert result["outcome"] == "would_call"
    assert result["unknown_targets"] == ["input_boolean.nope"]
```

`replace` is `dataclasses.replace` — `Rule` is a frozen dataclass. Add the
import if the file does not already have it. Check how other tests in the file
set `dry_run`; if they go through the store's own setter, do that instead.

- [ ] **Step 3: Run them and watch them fail**

```bash
uv run pytest tests/test_engine.py -k "unknown or does_not_exist or typo or no_target" -v
```

Expected: the new tests FAIL; the existing characterisation test still passes.

- [ ] **Step 4: Implement the check**

In `custom_components/shabbat_scheduler/engine.py`, add the import:

```python
from homeassistant.helpers import target as target_helper
```

and a helper:

```python
    def _unknown_targets(self, target: dict) -> list[str]:
        """Entity ids this target NAMES that do not exist.

        Only explicitly named ids. `async_extract_referenced_entity_ids`
        also returns `indirectly_referenced` - entities reached through an
        area, device or label - but those come out of the registries, so
        they exist by construction and checking them would invent typos.

        Home Assistant's service layer accepts a target naming a
        nonexistent entity without raising, so without this a typo'd rule
        reports "called" and looks exactly like a rule that fired.
        """
        if not target:
            return []
        try:
            selected = target_helper.async_extract_referenced_entity_ids(
                self.hass, target_helper.TargetSelection(target),
            )
        except Exception:  # noqa: BLE001 - a bad target must not stop the call
            _LOGGER.debug("could not resolve target %s", target, exc_info=True)
            return []
        return sorted(
            entity_id for entity_id in selected.referenced
            if self.hass.states.get(entity_id) is None
        )
```

Then in `_call`, after `result` is built and **before** the `dry_run` early
return, so a dry run reports the typo too:

```python
        unknown = self._unknown_targets(target)
        if unknown:
            result["unknown_targets"] = unknown
            _LOGGER.warning(
                "rule '%s' targets %s, which do not exist",
                rule.name or rule.id, ", ".join(unknown),
            )
```

and where the outcome is set on success, downgrade the total-miss case:

```python
            # Every named entity was unknown, so nothing can have happened.
            # Reporting "called" here is the quiet failure this integration
            # exists to prevent.
            referenced = _named_entity_ids(target)
            if unknown and referenced and len(unknown) == len(referenced):
                result["outcome"] = "failed"
                result["error"] = f"no such entity: {', '.join(unknown)}"
            else:
                result["outcome"] = "called"
```

Write `_named_entity_ids` as a small module-level helper that reads
`target.get("entity_id")` and normalises a bare string to a one-element list —
`target` may carry `entity_id` as either.

Check `async_extract_referenced_entity_ids`'s real signature before writing
this; `TargetSelection` may take the dict directly or by keyword:

```bash
grep -n "def async_extract_referenced_entity_ids" -A 15 \
  .venv/lib/python3.14/site-packages/homeassistant/helpers/target.py
grep -n "class TargetSelection" -A 20 \
  .venv/lib/python3.14/site-packages/homeassistant/helpers/target.py
```

- [ ] **Step 5: Update the characterisation test**

`test_a_target_entity_that_does_not_exist_is_still_reported_as_called` now
asserts behaviour that is gone. Rewrite it to assert the new behaviour and
rename it, keeping a note that it was the characterisation test for the gap:

```python
async def test_a_target_entity_that_does_not_exist_is_reported_as_failed(
    hass, engine
):
    """Was the characterisation test for Plan-2 Gap B.

    It used to assert outcome "called", pinning the wrong behaviour so
    that whoever fixed the gap would be told by this test failing. That
    happened; this is the corrected assertion.
    """
```

- [ ] **Step 6: Run the tests and watch them pass**

```bash
uv run pytest tests/test_engine.py -v
uv run pytest
```

Expected: all pass. Report the new total.

- [ ] **Step 7: Surface it in the logbook**

A result the user cannot see does not satisfy "a rule that does not fire must
say why". Check `logbook.py` and make the fired/failed row mention
`unknown_targets` when present. Add a test asserting the described text names
the missing entity — `tests/test_logbook.py` has the pattern.

- [ ] **Step 8: Commit**

```bash
git add custom_components/shabbat_scheduler/engine.py \
        custom_components/shabbat_scheduler/logbook.py \
        tests/test_engine.py tests/test_logbook.py
git commit -m "fix: close Gap B - a misspelt entity id no longer reports success

HA's service layer accepts a target naming a nonexistent entity without
raising, so a typo'd rule reported 'called' and looked exactly like a rule
that fired. Only explicitly named ids are checked: entities reached through
an area or label come from the registries and exist by construction."
```

---

## Task 10: Prove the executor is generic across domains

The spec requires this and it does not exist: *"Execution tests across several
domains — at minimum `climate`, `switch`, `scene`, `script` and `notify` —
proving the executor is genuinely generic and not climate-shaped. The dev
fixture needs entities for these; it currently has only booleans and two
thermostats."*

**Files:**
- Create: `tests/test_execution_domains.py`
- Modify: `dev/config/configuration.yaml`
- Modify: `dev/seed.py`

**Interfaces:**
- Consumes: the engine's `apply` and `device_ops.expand_action`.
- Produces: dev entities `scene.dev_evening`, `script.dev_beep`,
  `switch.dev_pump`, plus the existing `input_boolean.*` and `climate.dev_*`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_execution_domains.py`. Use the same fixtures
`tests/test_engine.py` uses, and assert on **calls actually made**, via the
`async_mock_service` helper that file already uses.

```python
"""The executor must be generic, not climate-shaped.

v1 understood five domains and hard-coded them. v2's whole claim is that a
rule is any Home Assistant service call, and the only domain knowledge
left is one documented shim for climate.set_temperature. These tests are
what makes that claim answerable.
"""

import pytest


@pytest.mark.parametrize(
    ("action", "target", "data", "expected_domain", "expected_service"),
    [
        ("switch.turn_on", {"entity_id": ["switch.pump"]}, {},
         "switch", "turn_on"),
        ("scene.turn_on", {"entity_id": ["scene.evening"]}, {},
         "scene", "turn_on"),
        ("script.turn_on", {"entity_id": ["script.beep"]}, {},
         "script", "turn_on"),
        ("notify.persistent_notification", {}, {"message": "shalom"},
         "notify", "persistent_notification"),
        ("input_boolean.turn_off", {"entity_id": ["input_boolean.a"]}, {},
         "input_boolean", "turn_off"),
        ("lock.lock", {"entity_id": ["lock.front"]}, {},
         "lock", "lock"),
        ("cover.close_cover", {"entity_id": ["cover.blind"]}, {},
         "cover", "close_cover"),
    ],
)
async def test_the_engine_calls_any_domain_untouched(
    hass, engine, action, target, data,
    expected_domain, expected_service,
):
    """No shim, no rewriting - exactly one call, exactly as authored."""
    for entity_id in target.get("entity_id", []):
        hass.states.async_set(entity_id, "off")
    calls = async_mock_service(hass, expected_domain, expected_service)
    rule = _rule(action=action, entities=target.get("entity_id", ()), data=data)

    [result] = await engine.async_apply_rule(rule)

    assert result["outcome"] == "called"
    assert len(calls) == 1
    assert calls[0].domain == expected_domain
    assert calls[0].service == expected_service
    for key, value in data.items():
        assert calls[0].data[key] == value


async def test_climate_set_temperature_is_the_one_documented_exception(
    hass, engine
):
    """The single shim, and it must stay single.

    device_ops.expand_action splits this into ordered calls because
    Home Assistant's SET_TEMPERATURE_SCHEMA is PREVENT_EXTRA and refuses
    hvac_mode/fan_mode alongside a temperature.
    """
    hass.states.async_set("climate.salon", "off")
    hvac = async_mock_service(hass, "climate", "set_hvac_mode")
    temp = async_mock_service(hass, "climate", "set_temperature")
    fan = async_mock_service(hass, "climate", "set_fan_mode")

    rule = _rule(
        action="climate.set_temperature",
        entities=("climate.salon",),
        data={"hvac_mode": "cool", "temperature": 24, "fan_mode": "high"},
    )
    results = await engine.async_apply_rule(rule)

    assert [r["outcome"] for r in results] == ["called"] * 3
    assert len(hvac) == 1 and len(temp) == 1 and len(fan) == 1
    assert hvac[0].data["hvac_mode"] == "cool"
    assert temp[0].data["temperature"] == 24
    assert "hvac_mode" not in temp[0].data
    assert fan[0].data["fan_mode"] == "high"


async def test_no_domain_other_than_climate_is_rewritten():
    """The guard on the shim staying narrow.

    If a second domain ever grows special handling, this fails - which is
    the point. Domain knowledge here must justify itself as a shim.
    """
    from custom_components.shabbat_scheduler.device_ops import expand_action

    for action in (
        "switch.turn_on", "light.turn_on", "climate.set_hvac_mode",
        "scene.turn_on", "script.turn_on", "notify.notify",
        "lock.lock", "cover.open_cover", "media_player.play_media",
    ):
        data = {"anything": 1}
        assert expand_action(action, dict(data)) == [(action, data)], action
```

Import `async_mock_service` the way `tests/test_engine.py:9` does
(`from pytest_homeassistant_custom_component.common import async_mock_service`),
and import the `engine` fixture and `_rule` helper — the cleanest route is to
move `_rule` into `tests/conftest.py` as a shared helper and import it in both
files, rather than copying it. If you move it, update `tests/test_engine.py`'s
import in the same commit and say so in your report.

Note `tests/test_engine.py:1037` already covers `cover.close_cover`. Check for
other existing per-domain coverage before writing this file and say what you
found — if a case is already tested elsewhere, cite it rather than duplicating
it.

- [ ] **Step 2: Run it and watch it fail, or explain why it passes**

```bash
uv run pytest tests/test_execution_domains.py -v
```

Some of these may pass immediately — the executor is *supposed* to be generic
already, so this task is partly a proof rather than a fix. **That is fine and
expected**, but you must say which passed first time and which did not. Any
that fails is a real bug in the genericity claim; fix it.

- [ ] **Step 3: Add the dev entities**

In `dev/config/configuration.yaml`, add entities for the domains the e2e and
manual testing need. Keep the existing `input_boolean` and `generic_thermostat`
blocks untouched:

```yaml
# Entities for the multi-domain execution work. The point is that the
# executor is not climate-shaped, and that cannot be demonstrated on an
# instance that only has booleans and two thermostats.
switch:
  - platform: template
    switches:
      dev_pump:
        friendly_name: Dev pump
        value_template: "{{ is_state('input_boolean.salon', 'on') }}"
        turn_on:
          service: input_boolean.turn_on
          target: { entity_id: input_boolean.salon }
        turn_off:
          service: input_boolean.turn_off
          target: { entity_id: input_boolean.salon }

scene:
  - name: Dev evening
    entities:
      input_boolean.salon: on
      input_boolean.kids: off

script:
  dev_beep:
    alias: Dev beep
    sequence:
      - service: persistent_notification.create
        data:
          title: Dev beep
          message: "The script ran."
```

- [ ] **Step 4: Verify they exist on the dev instance**

```bash
docker restart shabbat-scheduler-dev
# wait for http://127.0.0.1:8124 to answer, then mint a token per dev/README.md
for e in switch.dev_pump scene.dev_evening script.dev_beep; do
  curl -sS "http://127.0.0.1:8124/api/states/$e" \
    -H "Authorization: Bearer $TOKEN" | head -c 200; echo
done
```

Every one must return a state, not a 404. If a platform was removed or renamed
in 2026.8.2, use whatever that release actually provides and say what you
changed.

- [ ] **Step 5: Run the tests and watch them pass**

```bash
uv run pytest tests/test_execution_domains.py -v
uv run pytest
```

- [ ] **Step 6: Commit**

```bash
git add tests/test_execution_domains.py dev/config/configuration.yaml dev/seed.py
git commit -m "test: prove the executor is generic across domains, not climate-shaped

Seven domains called untouched, the one climate shim asserted to be the
only exception, and dev entities so this is demonstrable on the instance
as well as in the suite."
```

---

## Task 11: A durable per-rule outcome, on the card

The last carried item. `last_run` is a single transient value overwritten by
the next rule, so the card cannot say why *this* rule did not fire — blocked,
skipped as stale, or failed. The Global Constraint requires it be visible "in
the logbook **and on the card**", and only the logbook half holds today.

**Files:**
- Modify: `custom_components/shabbat_scheduler/store.py`
- Modify: `custom_components/shabbat_scheduler/engine.py`
- Modify: `custom_components/shabbat_scheduler/websocket_api.py`
- Modify: `frontend/src/types.ts`, `frontend/src/rule-row.ts`,
  `frontend/src/strings.ts`
- Test: `tests/test_store.py`, `tests/test_engine.py`,
  `frontend/test/rule-row.test.ts`

**Interfaces:**
- Produces: a per-rule `last_outcome` dict
  `{outcome: str, at: str, detail: str | None}` persisted in the store,
  present on each rule in `_state_payload`, and rendered on the row.
  `outcome` is one of `called`, `would_call`, `failed`, `blocked`,
  `skipped_stale`.

- [ ] **Step 1: Read how the store persists and how the payload is built**

```bash
grep -n "async_save\|_data\|STORAGE_VERSION" custom_components/shabbat_scheduler/store.py | head -30
grep -n "last_run\|_state_payload" custom_components/shabbat_scheduler/websocket_api.py
```

`STORAGE_VERSION` is 2. Adding a key that is **absent on old data and defaults
to None** does not need a version bump — but confirm the loader tolerates its
absence, and add a test that a store written before this change still loads.
That is the constraint "storage must migrate, not break".

- [ ] **Step 2: Write the failing tests**

In `tests/test_store.py`. That file has **no `store` fixture** — it constructs
`RuleStore(hass)` and awaits `async_load()` inline, and reads/writes
`hass_storage` directly for on-disk shapes. Follow that, and read a nearby
persistence test first to copy its exact setup.

```python
async def test_a_rules_last_outcome_survives_a_reload(hass):
    """Transient state cannot answer "why did this not fire?" tomorrow."""
    store = RuleStore(hass)
    await store.async_load()
    await store.async_record_outcome(
        "r1", {"outcome": "blocked", "at": "2026-08-25T18:00:00+00:00",
               "detail": "condition 1 of 1 (state on input_boolean.kids) not met"},
    )

    reloaded = RuleStore(hass)
    await reloaded.async_load()
    assert reloaded.last_outcome("r1")["outcome"] == "blocked"
    assert "input_boolean.kids" in reloaded.last_outcome("r1")["detail"]


async def test_a_store_written_before_last_outcome_still_loads(hass, hass_storage):
    """An alpha user's rules survive upgrades.

    Write a version-2 store with no last_outcome key at all - the shape
    every existing install has on disk right now - load it, and assert the
    rules come back with last_outcome None rather than the load failing.
    Copy the hass_storage shape from an existing test in this file.
    """


async def test_one_rules_outcome_does_not_overwrite_another(hass):
    """The bug this replaces: last_run held ONE result for the whole
    integration, so the next rule to fire erased the previous rule's."""
    store = RuleStore(hass)
    await store.async_load()
    await store.async_record_outcome("r1", {"outcome": "failed", "at": "x",
                                            "detail": "boom"})
    await store.async_record_outcome("r2", {"outcome": "called", "at": "y",
                                            "detail": None})
    assert store.last_outcome("r1")["outcome"] == "failed"
    assert store.last_outcome("r2")["outcome"] == "called"
```

In `tests/test_engine.py`, assert the engine records for all four
non-firing shapes: `called`, `failed`, `blocked`, `skipped_stale`.

In `frontend/test/rule-row.test.ts`. That file already has a `rule(over)`
factory and a `render(props)` helper — use them; there is no `base` const.
Add `last_outcome: null` to the factory's defaults so every existing test
keeps a complete `RuleData`.

```ts
it('says a rule was blocked, and why', async () => {
  const el = await render({ rule: rule({ last_outcome: {
    outcome: 'blocked', at: '2026-08-25T18:00:00+00:00',
    detail: 'condition 1 of 1 (state on input_boolean.kids) not met',
  } }) });
  expect(el.shadowRoot!.textContent).toContain('input_boolean.kids');
});

it('says a rule was skipped as too stale to replay', async () => {
  const el = await render({ rule: rule({ last_outcome: {
    outcome: 'skipped_stale', at: '2026-08-25T18:00:00+00:00',
    detail: '6:00:43 late, window 1:00:00',
  } }) });
  expect(el.shadowRoot!.textContent).toContain('1:00:00');
});

it('says nothing at all for a rule that has never run', async () => {
  const el = await render({ rule: rule({ last_outcome: null }) });
  expect(el.shadowRoot!.querySelector('.last-outcome')).toBeNull();
});
```

- [ ] **Step 3: Run them and watch them fail**

```bash
uv run pytest tests/test_store.py tests/test_engine.py -v
npm --prefix frontend test -- test/rule-row.test.ts
```

- [ ] **Step 4: Implement, in this order**

1. `store.py` — a `last_outcome` map keyed by rule id, `async_record_outcome`,
   `last_outcome(rule_id)`, persisted, tolerant of absence on load. Prune
   entries for deleted rules on save so the map cannot grow without bound.
2. `engine.py` — record at each of the four points that already produce a
   verdict: after `_call` (its `outcome` and `error`), at the condition gate
   (reusing `_condition_block_reason`, which already produces the text the
   logbook shows), and at the stale-replay skip.
3. `websocket_api.py` — add `last_outcome` to each rule in `_state_payload`.
   **Task 8's fixture will now be stale** — regenerate it and commit the new
   JSON, which is the mechanism working as designed.
4. `types.ts` — add `last_outcome: LastOutcome | null` to `RuleData`, and the
   `LastOutcome` interface.
5. `rule-row.ts` + `strings.ts` — render it, `en` and `he`.

Reuse the existing text. `_condition_block_reason` already produces "condition
1 of 1 (state on input_boolean.kids) not met" for the logbook; the card showing
the same words is a feature, not duplication.

- [ ] **Step 5: Run everything**

```bash
uv run pytest
REGEN_FRONTEND_FIXTURE=1 uv run pytest tests/test_frontend_fixture.py
uv run pytest tests/test_frontend_fixture.py
npm --prefix frontend test
npm --prefix frontend run typecheck
```

- [ ] **Step 6: Commit**

```bash
git add custom_components/shabbat_scheduler/ frontend/src/ frontend/test/ tests/
git commit -m "feat: a durable per-rule outcome, so the card can say why a rule did not fire

last_run held one result for the whole integration and the next rule to
fire erased it, so 'blocked' and 'skipped as stale' were durable only in
the logbook. The constraint asks for both."
```

---

## Task 12: Repair and extend the e2e suite

The last task, because it proves the whole plan in a real browser — the only
place `ha-service-control` and `ha-selector` actually render.

**Files:**
- Modify: `e2e/test_card_e2e.py`
- Modify: `e2e/conftest.py`
- Modify: `dev/README.md`

**Interfaces:**
- Consumes: everything above.

- [ ] **Step 1: Establish the baseline**

```bash
# Reset and seed per dev/README.md, then:
export HA_DEV_TOKEN=<a fresh token>
uv run pytest e2e/ -v
```

The recorded baseline before this plan was **5 passed, 2 failed**. Report what
you actually see. If more than 2 fail, the tasks above broke something — find
out what before continuing.

- [ ] **Step 2: Delete the obsolete test**

`test_the_settings_form_offers_only_what_every_selected_device_supports` drives
`shabbat-device-settings`, an element deleted in Plan 1. It tested v1's
capability-intersecting climate form, a feature that no longer exists — HA's
own service control now supplies the form.

Delete it. Do not try to salvage it: there is nothing left for it to assert.
Note the deletion in your report.

- [ ] **Step 3: Repair the add-button test**

`test_the_add_button_creates_a_rule_on_its_own_day` fills only `input.time`.
It must now also author an action and a target. Read the docstring first — it
explains at length why the test drives **day 1** and why every assertion is
scoped to a day group. **Preserve both properties**; they are what make it a
guard rather than a name.

Drive the real elements:

```python
        day_one.locator("button.add").click()
        dialog.wait_for(state="attached", timeout=10_000)
        dialog.locator("input.time").fill("21:00:00")

        # The action, through HA's own service control.
        service = dialog.locator("shabbat-service-editor ha-service-control")
        service.wait_for(timeout=15_000)
        # Find how this HA version exposes the action field and fill it.
        # It is a combo box, not a plain input - inspect it rather than
        # guessing at a selector.

        # The target, through ha-selector.
        target = dialog.locator("shabbat-target-editor ha-selector")
        target.wait_for(timeout=15_000)
```

You will have to discover the real internal structure of both elements. Do it
by inspection against the running instance, not by guessing:

```bash
# With the dev instance up, open the card, open a rule dialog, and dump
# the shadow DOM of the two editors.
```

Write a short throwaway Playwright script to print
`document.querySelector(...).shadowRoot.innerHTML` for each editor, read it,
then write selectors against what is actually there. **Put what you find in
`dev/README.md`** — the next person needs it, and it is the kind of thing that
costs an hour twice.

If either element proves undrivable from Playwright, say so explicitly and
assert what you can (that it rendered, that a rule saved with a target set via
the websocket API appears correctly). Do not leave a test that passes without
asserting anything.

- [ ] **Step 4: Add e2e coverage for the editors**

At minimum, and each scoped to the dialog:

```python
def test_the_service_control_renders_a_real_service_schema(page, base_url):
    """The point of v2 on the frontend: the form comes from HA's schema.

    A hand-written form would show the same fields for every service.
    Choosing climate.set_temperature must produce a temperature field that
    switch.turn_on does not.
    """


def test_the_target_selector_causes_ha_target_picker_to_be_defined(page, base_url):
    """ha-selector's dynamic import is the whole reason we use it.

    ha-target-picker is NOT pre-registered on a dashboard. Handing
    ha-selector a {target: {}} selector makes it become defined. If this
    ever stops being true, the target editor renders nothing and this is
    the test that says so.
    """
    # assert customElements.get('ha-target-picker') is undefined before
    # the dialog opens, and defined after.


def test_a_condition_can_be_added_and_survives_a_save(page, base_url):
    """Authored conditions must round-trip through the server."""


def test_replay_can_be_switched_on_with_a_window(page, base_url):
    """And must come back switched on after a reload."""
```

- [ ] **Step 5: Make a skipped e2e run visible**

The suite skipping silently is how it stayed red unnoticed. In
`e2e/conftest.py`, keep the skip — it is correct — but make the reason loud
at session level, e.g. a `pytest_sessionfinish` hook that prints a clear
banner when every e2e test skipped. A one-line summary is enough:

```
e2e: ALL TESTS SKIPPED - no HA_DEV_TOKEN. Nothing about the card was verified.
```

- [ ] **Step 6: Run the whole suite green**

```bash
export HA_DEV_TOKEN=<fresh token>
uv run pytest e2e/ -v
```

Expected: all pass. Tokens last 30 minutes — if a run dies part-way with
timeouts, mint a fresh one before assuming a real failure.

- [ ] **Step 7: Run absolutely everything**

```bash
uv run pytest
npm --prefix frontend test
npm --prefix frontend run typecheck
npm --prefix frontend run build
export HA_DEV_TOKEN=<fresh token>
uv run pytest e2e/ -v
git status --short
```

The built bundle under `custom_components/shabbat_scheduler/www/` must be
committed — a HACS install has no Node.

- [ ] **Step 8: Commit**

```bash
git add e2e/ dev/README.md custom_components/shabbat_scheduler/www/
git commit -m "test: repair the e2e suite and cover the four editors

The suite had been silently skipping without a token, which is how it
stayed red through Plan 1. A skipped run now says what it did not verify."
```

---

## Self-Review

Run against the spec's `## The card`, `## Alpha readiness` and `## Testing`
sections, plus the Plan 1 ledger's carried items.

**1. Spec coverage**

| Spec requirement | Task |
|---|---|
| Action editor on `<ha-service-control>` | 3, composed in 6 |
| Target picker as `<ha-selector>` with `{target: {}}` | 2, composed in 6 |
| Condition editor | 5, composed in 6 |
| Replay editor (`enabled` + `within`) | 4, composed in 6 |
| The bespoke climate form is deleted | Already done in Plan 1; its dead e2e test goes in 12 |
| Reach for `ha-selector`, never a specific picker | 2, 4, 5 all follow it; asserted in 12 |
| Everything else the card does is unchanged | Guarded by the existing suite, plus 8 |
| Migration tests with real v1 payloads | Done in Plan 1 (40-shape sweep) |
| Execution tests across several domains | 10 |
| Dev fixture needs entities for those domains | 10 |
| A rule that does not fire must say why, on the card | 11 |
| Plan-1 Gap A (frontend fixtures unvalidated) | 8 |
| Plan-1 Gap B (misspelt entity id reports called) | 9 |
| Plan-1 note: defaults dialog cannot save | 7 |

The spec's `## Alpha readiness` list (README, HACS metadata, brands,
diagnostics, translations, upgrade notes) is **Plan 3** and deliberately absent
here.

**2. Placeholder scan** — no TBDs. Two places deliberately require discovery
rather than prescribing code, and both say so explicitly and demand the
findings be written down: Task 12's Playwright selectors for HA's internal
shadow DOM, and Task 8's reuse of the existing card-render helper. Prescribing
either would be guessing at another codebase's internals.

**3. Type consistency**

- `Hass` — defined Task 1, used 1, 2, 3, 6, 7.
- `ReplayData` `{enabled, within?}` — existing `types.ts`, used 4, 6.
- `Defaults` `{target?, data?}` — existing, used 7.
- Event names, each emitted by exactly one element and consumed in Task 6 or 7:
  `target-changed`, `service-changed`, `condition-changed`, `replay-changed`.
- `hasError` — Task 5 produces, Task 6 consumes.
- `last_outcome` / `LastOutcome` — Task 11 only.
- `unknown_targets` — Task 9 only.
- `REGEN_FRONTEND_FIXTURE` — Task 8 defines, Task 11 uses.

**4. Ordering** — Task 1 unblocks 2, 3, 6, 7. Tasks 2–5 are independent of each
other. 6 needs 2–5; 7 needs 2, 3. 8–11 are backend-leaning and independent of
2–7, except that 11 invalidates 8's fixture (called out in 11's steps). 12
needs everything.

**One known cross-task interaction, stated rather than left to be discovered:**
Task 11 adds `last_outcome` to `_state_payload`, which makes Task 8's committed
fixture stale and Task 8's Python test fail. That is the guard working. Task 11
Step 5 regenerates it.
