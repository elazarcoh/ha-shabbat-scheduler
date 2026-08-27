# Clone Rules + Rule-Testing Rework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Two independent-but-related additions. (1) Let an author copy an
already-authored day's or profile's rules onto another day/profile, with
extend or overwrite semantics. (2) Replace the global, persistent `dry_run`
flag with an on-demand way to prove a rule, and a whole day's schedule,
actually fire correctly — reusing the exact code path a real fire uses,
triggered manually, any day of the week. Folded in as early, independent
tasks: a mobile CSS pass, a sweep of remaining plain HTML form elements onto
`<ha-selector>` (plus one deliberate native `<input type="color">`), a
master-switch styling fix, and a per-row quick enable/disable toggle.

**Architecture:** Both headline features are thin orchestration on top of
machinery that already exists and is already tested: `rules/create` +
`rules/delete` (clone), and `resolve_rules()` + `async_apply_rule()` (the
verification story). No new domain knowledge, no new persisted state for
verification, no change to how or when the real scheduler sets real timers.
The four bounded UI items are independent, low-risk, and establish/extend the
`<ha-selector>` pattern this plan uses repeatedly later.

**Tech stack:** No new dependencies. Backend: `websocket_api.py`,
`engine.py`, `block.py`, `store.py`, `__init__.py`, `diagnostics.py`.
Frontend: `card.ts`, `block-header.ts`, `rule-row.ts`, `rule-dialog.ts`,
`replay-editor.ts`, `day-group.ts`, plus new files `clone-dialog.ts` and
`simulate-dialog.ts`.

**Spec:** `docs/superpowers/specs/2026-08-27-clone-and-verification-design.md`
(Part 1 clone, Part 2 verification). The four bounded UI items (mobile CSS,
native-component sweep, master-switch fix, row toggle) are approved
separately and have no separate spec file; their requirements are captured
verbatim in this plan's task descriptions below.

## Global Constraints

- `custom_components/shabbat_scheduler/{models,block,device_ops,const,
  rule_schema,yaml_io,migration}.py` import zero Home Assistant
  (`tests/test_packaging.py` enforces this) — nothing in this plan adds an HA
  import to those files. (None of this plan's tasks touch those six files.)
- The climate shim (`device_ops.expand_action`) stays the only domain-aware
  code. Neither feature in this plan adds a second one.
- No feature here changes when or whether a REAL scheduled timer fires. The
  master switch (`store.enabled`) and the real schedule (`async_refresh`,
  `_make_callback`) are untouched by this plan.
- Every websocket write command in this plan follows the existing pattern in
  `websocket_api.py`: `@websocket_api.require_admin`, a `vol.Schema`, a
  `not_set_up` guard via `_entry_data`, `RuleValidationError` ->
  `connection.send_error`.
- Card writes stay non-optimistic: a control reflects only what the server
  pushed back, matching every existing write in `card.ts` (`_send`, `_call`).
- Both `en` and `he` entries are required for every new string in
  `frontend/src/strings.ts`.
- `<ha-selector>` with the selector type wanted, never a specific picker
  element (`ha-switch`, `ha-textfield`, `ha-code-editor`) — dashboard
  availability differs picker-by-picker; `ha-selector` itself is always
  registered. See `frontend/src/target-editor.ts`'s existing comment for why.
  Exception, stated explicitly by the bounded UI scope: the rule dialog's
  `color` field goes to a plain native `<input type="color">`, never
  `ha-selector` — it is a browser-built-in element, not an HA custom
  element, so it carries none of the dashboard-availability risk this rule
  exists to guard against.
- `frontend/src/condition-editor.ts`'s `<textarea>` is deliberately not a
  native HA element (`ha-code-editor` isn't guaranteed pre-registered on a
  dashboard) and stays exactly as it is. No task in this plan touches it.
- Mobile CSS is a pure styling pass — no JS/template changes — and must not
  alter the existing tablet layout (≥600px).

---

### Task 1: Mobile responsive CSS pass

**Files:**
- Modify: `frontend/src/block-header.ts:17-63` (styles), `88-138` (render)
- Modify: `frontend/src/rule-row.ts:22-66` (styles)
- Test: `frontend/test/block-header.test.ts`, `frontend/test/rule-row.test.ts`

**Interfaces:**
- Consumes: nothing new.
- Produces: nothing new (pure CSS). Later tasks (2–5) add markup inside
  `block-header.ts`/`rule-row.ts`; they must keep the class names this task
  targets (`.header`, `.label`, `.chips`, `.gear`, `.master`, `.row`,
  `.body`, `.title`, `.brief`, `.last-outcome`, `.conflict-detail`, `.tag`,
  `.conflict`) so this task's media queries keep applying.

This codebase's frontend suite (vitest + happy-dom) has no viewport/visual
testing. The only thing a unit test can honestly pin for pure CSS is that
the expected rule text is present in the component's compiled stylesheet
(Lit's `css` tagged template exposes `.cssText`). Real visual confirmation
happens by hand against the dev container (`dev/`) at a narrow viewport —
add that as a manual verification note in the PR, not as an automated step
this plan can write.

- [ ] **Step 1: Write the failing test for block-header.ts**

```ts
// frontend/test/block-header.test.ts — add to the top-level describe list
import { ShabbatBlockHeader } from '../src/block-header';

describe('shabbat-block-header mobile layout', () => {
  it('wraps header controls onto their own row under 600px with 44px tap targets', () => {
    const cssText = (ShabbatBlockHeader.styles as unknown as { cssText: string }).cssText;
    expect(cssText).toContain('@media (max-width: 599px)');
    expect(cssText).toContain('min-block-size: 44px');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- block-header.test.ts`
Expected: FAIL — `cssText` does not contain `@media (max-width: 599px)`.

- [ ] **Step 3: Add the media query to block-header.ts's styles**

Append inside the existing `static override styles = css\`...\`` template
literal in `frontend/src/block-header.ts`, right after the closing `.gear`
rule (currently the last rule, ending the template):

```css
    @media (max-width: 599px) {
      .header { flex-wrap: wrap; }
      .label { flex-basis: 100%; }
      .chips, .gear, .master, button {
        min-block-size: 44px;
      }
      .chip { min-block-size: 44px; display: inline-flex; align-items: center; }
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- block-header.test.ts`
Expected: PASS.

- [ ] **Step 5: Write the failing test for rule-row.ts**

```ts
// frontend/test/rule-row.test.ts — add to the top-level describe list
import { ShabbatRuleRow } from '../src/rule-row';

describe('shabbat-rule-row mobile layout', () => {
  it('drops to two lines under 600px: time+dot+title on line 1, the rest stacked', () => {
    const cssText = (ShabbatRuleRow.styles as unknown as { cssText: string }).cssText;
    expect(cssText).toContain('@media (max-width: 599px)');
    expect(cssText).toContain('display: contents');
  });
});
```

- [ ] **Step 6: Run test to verify it fails**

Run: `cd frontend && npm test -- rule-row.test.ts`
Expected: FAIL.

- [ ] **Step 7: Add the media query to rule-row.ts's styles**

Append inside `frontend/src/rule-row.ts`'s `static override styles = css\`...\``,
after the existing `.row:focus-visible` rule (currently the last rule):

```css
    /* Below 600px, `.body`'s children (title, brief, last-outcome,
       conflict-detail) become direct flex items of `.row` via
       `display: contents` - the same unwrap trick `rule-dialog.ts`'s
       `.advanced` class already uses, for the same reason: only that lets
       `.title` stay on the row's first line, next to the dot and time,
       while `.brief`/`.last-outcome`/`.conflict-detail` wrap onto their
       own full-width lines below. `.body` itself has no visual box (no
       padding/border/background), so nothing is lost by unwrapping it. */
    @media (max-width: 599px) {
      .row { flex-wrap: wrap; row-gap: 4px; }
      .body { display: contents; }
      .brief, .last-outcome, .conflict-detail { flex-basis: 100%; }
    }
```

- [ ] **Step 8: Run test to verify it passes**

Run: `cd frontend && npm test -- rule-row.test.ts`
Expected: PASS.

- [ ] **Step 9: Manually verify against the dev container**

Run: `cd dev && ./run.sh` (or this repo's documented dev-container command —
see `dev/README.md`), open the card in Chromium's device toolbar at a
375px-wide viewport, and confirm the header wraps and rows show two lines
without a horizontal scrollbar. Confirm the tablet layout (≥600px,
e.g. 800px wide) is pixel-identical to before this task. This step has no
automated assertion; note the result in the PR description.

- [ ] **Step 10: Commit**

```bash
git add frontend/src/block-header.ts frontend/src/rule-row.ts \
  frontend/test/block-header.test.ts frontend/test/rule-row.test.ts
git commit -m "style: mobile responsive layout for header and rule rows"
```

---

### Task 2: Master switch styling fix (block-header.ts)

**Files:**
- Modify: `frontend/src/block-header.ts` (whole file — properties, styles, render)
- Modify: `frontend/src/card.ts:436-450` (pass `.hass` to `<shabbat-block-header>`)
- Test: `frontend/test/block-header.test.ts`

**Interfaces:**
- Consumes: `Hass` type from `frontend/src/types.ts` (already exported).
- Produces: `ShabbatBlockHeader` gains a `@property({ attribute: false }) hass: Hass | null = null;`
  property. Later tasks that touch `block-header.ts` (Task 9b's dry-run
  removal, Task 14's clone-menu button) must keep this property and keep
  `card.ts` passing `.hass=${this._hass}` to `<shabbat-block-header>`.
- The `shabbat-master-toggle` event name and its `{ enabled: boolean }`
  detail shape are UNCHANGED — `card.ts`'s existing `_onMaster` handler
  (`frontend/src/card.ts:230-237`) needs no change.

Today the `master` button is a plain `<button>` sharing the same
`.active` blue-pill CSS class as the 1d/2d/3d profile chips
(`frontend/src/block-header.ts:39-43,122-128`). It becomes an
`<ha-selector>` with a `{boolean: {}}` selector, paired with its own text
label. The 1d/2d/3d chips are NOT touched — they are a legitimate
single-select group, not a toggle.

- [ ] **Step 1: Write the failing test**

Replace the existing `'fires an event rather than mutating its own state'`
and `'disables both controls for a read-only user'` /
`'disables the master control when the entity is unknown'` tests in
`frontend/test/block-header.test.ts`'s first `describe('shabbat-block-header', ...)`
block with:

```ts
function master(el: any) {
  return el.shadowRoot.querySelector('ha-selector.master');
}

describe('shabbat-block-header', () => {
  it('shows the block length and its dates', async () => {
    const el = await render({});
    const text = el.shadowRoot!.textContent!;
    expect(text).toContain('2026-08-15');
  });

  it('orders the dates erev-first, not by object key enumeration', async () => {
    const el = await render({});
    const text = el.shadowRoot!.textContent!;
    expect(text).toContain('2026-08-14 → 2026-08-15');
  });

  it('says so when there is no block instead of rendering an empty header', async () => {
    const el = await render({ block: null });
    expect(el.shadowRoot!.textContent).toContain('No upcoming Shabbat');
  });

  it('hands the master ha-selector a boolean selector and the current value', async () => {
    const el = await render({ enabled: true });
    const sel = master(el);
    expect(sel).not.toBeNull();
    expect(sel.selector).toEqual({ boolean: {} });
    expect(sel.value).toBe(true);
    expect(sel.hass).toBe(el.hass);
  });

  it('fires an event rather than mutating its own state', async () => {
    const el = await render({ enabled: false });
    const listener = vi.fn();
    el.addEventListener('shabbat-master-toggle', listener);

    master(el).dispatchEvent(
      new CustomEvent('value-changed', { detail: { value: true } }),
    );

    expect(listener).toHaveBeenCalledOnce();
    expect((listener.mock.calls[0][0] as CustomEvent).detail).toEqual({
      enabled: true,
    });
    // No optimistic update: the control still reads the pushed state.
    expect((el as unknown as { enabled: boolean }).enabled).toBe(false);
  });

  it('disables the master control for a read-only user', async () => {
    const el = await render({ canWrite: false });
    expect(master(el).disabled).toBe(true);
  });

  it('disables the master control when the entity is unknown', async () => {
    const el = await render({ masterEntityId: null });
    expect(master(el).disabled).toBe(true);
  });
});
```

Also add `hass: {}` to the `render()` helper's default props at the top of
the file (`Object.assign(el, { block, enabled: false, ..., hass: {}, ...props })`).

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- block-header.test.ts`
Expected: FAIL — `ha-selector.master` not found (still a `<button class="master">`).

- [ ] **Step 3: Implement**

In `frontend/src/block-header.ts`:

```ts
import { LitElement, css, html, nothing } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { orderedDates } from './format';
import { t } from './strings';
import type { BlockData, Hass } from './types';

@customElement('shabbat-block-header')
export class ShabbatBlockHeader extends LitElement {
  @property({ attribute: false }) hass: Hass | null = null;
  @property({ attribute: false }) block: BlockData | null = null;
  @property({ type: Boolean }) enabled = false;
  @property({ type: Boolean }) dryRun = false;
  @property({ type: Boolean }) canWrite = false;
  @property() masterEntityId: string | null = null;
  @property() language = 'en';
  @property({ type: Number }) selectedProfile = 1;

  static override styles = css`
    .header {
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
      padding-block-end: 8px;
      border-block-end: 1px solid var(--divider-color, #e0e0e0);
    }
    .label { flex: 1; min-inline-size: 0; font-weight: 600; }
    .dates { color: var(--secondary-text-color, #666); font-weight: 400; }
    button {
      font: inherit;
      padding-block: 4px;
      padding-inline: 10px;
      border-radius: 14px;
      border: 1px solid var(--divider-color, #e0e0e0);
      background: var(--card-background-color, #fff);
      color: inherit;
      cursor: pointer;
    }
    button[disabled] { opacity: 0.5; cursor: not-allowed; }
    button.active {
      background: var(--primary-color, #03a9f4);
      color: var(--text-primary-color, #fff);
      border-color: transparent;
    }
    .none { color: var(--secondary-text-color, #666); }
    .chips { display: flex; gap: 4px; }
    .chip {
      font: inherit;
      font-size: 0.85em;
      padding-block: 2px;
      padding-inline: 8px;
      border-radius: 10px;
      border: 1px solid var(--divider-color, #e0e0e0);
      background: var(--card-background-color, #fff);
      color: inherit;
      cursor: pointer;
    }
    .chip.active {
      background: var(--primary-color, #03a9f4);
      color: var(--text-primary-color, #fff);
      border-color: transparent;
    }
    .gear { border: none; background: none; cursor: pointer; font-size: 1.1em; }
    .master-wrap { display: flex; align-items: center; gap: 6px; }
    .master-label { font-size: 0.9em; }
    @media (max-width: 599px) {
      .header { flex-wrap: wrap; }
      .label { flex-basis: 100%; }
      .chips, .gear, .master, button {
        min-block-size: 44px;
      }
      .chip { min-block-size: 44px; display: inline-flex; align-items: center; }
    }
  `;

  private _dates(): string {
    if (this.block === null) return '';
    return orderedDates(this.block).join(' → ');
  }

  // No optimistic update anywhere here: the control reports intent and
  // keeps rendering the pushed state until the server confirms.
  private _onMasterChanged = (event: CustomEvent) => {
    this.dispatchEvent(
      new CustomEvent('shabbat-master-toggle', {
        detail: { enabled: Boolean(event.detail?.value) },
      }),
    );
  };

  private _toggleDryRun() {
    this.dispatchEvent(
      new CustomEvent('shabbat-dry-run-toggle', {
        detail: { dryRun: !this.dryRun },
      }),
    );
  }

  override render() {
    return html`
      <div class="header">
        <div class="label">
          ${this.block === null
            ? html`<span class="none">${t(this.language, 'no_block')}</span>`
            : html`
                <span>${t(this.language, 'day')} ×${this.block.length}</span>
                <span class="dates">${this._dates()}</span>
              `}
        </div>
        <div class="chips">
          ${[1, 2, 3].map(
            (profile) => html`
              <button
                class="chip ${this.selectedProfile === profile ? 'active' : ''}"
                @click=${() =>
                  this.dispatchEvent(
                    new CustomEvent('profile-selected', { detail: { profile } }),
                  )}
              >
                ${profile}d
              </button>
            `,
          )}
        </div>
        ${this.canWrite
          ? html`<button
              class="gear"
              @click=${() => this.dispatchEvent(new CustomEvent('defaults-open'))}
            >
              ⚙
            </button>`
          : nothing}
        <div class="master-wrap">
          <span class="master-label">${t(this.language, 'master')}</span>
          <ha-selector
            class="master"
            .hass=${this.hass}
            .selector=${{ boolean: {} }}
            .value=${this.enabled}
            .disabled=${!this.canWrite || this.masterEntityId === null}
            @value-changed=${this._onMasterChanged}
          ></ha-selector>
        </div>
        <button
          class="dry-run ${this.dryRun ? 'active' : ''}"
          ?disabled=${!this.canWrite}
          @click=${this._toggleDryRun}
        >
          ${t(this.language, 'dry_run')}
        </button>
      </div>
    `;
  }
}
```

(The `dry-run` button and `dryRun` property stay for now — Task 9b removes
them. `master`'s own text label uses the existing `master` string key
unchanged.)

- [ ] **Step 4: Pass `hass` down from card.ts**

In `frontend/src/card.ts`, in the `<shabbat-block-header>` tag
(around line 436), add `.hass=${this._hass}` alongside the existing
`.block=${this._state.block}` binding:

```ts
        <shabbat-block-header
          .hass=${this._hass}
          .block=${this._state.block}
          .enabled=${this._state.enabled}
          .dryRun=${this._state.dry_run}
          .canWrite=${this._canWrite}
          .masterEntityId=${this._state.master_entity_id}
          .selectedProfile=${this._profile}
          .language=${this._language}
          @shabbat-master-toggle=${this._onMaster}
          @shabbat-dry-run-toggle=${this._onDryRun}
          @profile-selected=${(event: Event) => {
            this._selectedProfile = (event as CustomEvent).detail.profile;
          }}
          @defaults-open=${() => { this._defaultsOpen = true; }}
        ></shabbat-block-header>
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd frontend && npm test -- block-header.test.ts`
Expected: PASS.

- [ ] **Step 6: Typecheck and full frontend suite**

Run: `cd frontend && npm run typecheck && npm test`
Expected: PASS (card.test.ts continues to assert `header.enabled`/
`header.masterEntityId` the same way — those bindings are unchanged).

- [ ] **Step 7: Commit**

```bash
git add frontend/src/block-header.ts frontend/src/card.ts frontend/test/block-header.test.ts
git commit -m "fix: master switch uses ha-selector boolean instead of a shared chip class"
```

---

### Task 3: rule-dialog.ts native-component sweep (time, enabled, icon, color)

**Files:**
- Modify: `frontend/src/rule-dialog.ts` (whole file)
- Test: `frontend/test/rule-dialog.test.ts`

**Interfaces:**
- Consumes: nothing new (uses `this.hass`, already a property).
- Produces: no new events, no new props — `_form.time`/`_form.enabled`/
  `_form.icon`/`_form.color` keep their existing types (`string`, `boolean`,
  `string | null`, `string | null`) so `format.ts`'s `formToChanges`/
  `formToCreate`/`ruleToForm` need no change.

Four fields move off plain HTML: `time` (`<input>` → `<ha-selector
{time:{}}>`), `enabled` (`<input type="checkbox">` → `<ha-selector
{boolean:{}}>`), `icon` (plain text via `_text()` → `<ha-selector
{icon:{}}>`), `color` (plain text via `_text()` → native
`<input type="color">`, per the Global Constraints exception — NOT
`ha-selector`). `name` stays on `_text()` unchanged; `_text()`'s type
signature narrows to `'name'` only since it is the only remaining caller.

HA's `{time: {}}`, `{boolean: {}}` and `{icon: {}}` selector values are
plain strings/booleans matching this form's existing field types 1:1 — no
conversion helpers needed (unlike `replay-editor.ts`'s `duration` selector
in Task 4). A native `<input type="color">` has no "empty" state — once a
colour is set it can no longer be cleared back to `null` through this UI.
This is an accepted, spec-mandated trade-off of using the native element
here rather than a workaround.

- [ ] **Step 1: Write the failing test**

Replace `frontend/test/rule-dialog.test.ts`'s
`'opens an existing rule with its values filled in'`,
`'reports a save with the edited form, not the original rule'`, and
`'disables everything and hides the actions for a read-only user'` tests,
and the `'shows the advanced fields only once asked for'` test, with:

```ts
function timeSelector(el: any) {
  return el.shadowRoot.querySelector('ha-selector.time');
}
function enabledSelector(el: any) {
  return el.shadowRoot.querySelector('ha-selector.enabled');
}
function iconSelector(el: any) {
  return el.shadowRoot.querySelector('ha-selector.icon');
}
function colorInput(el: any) {
  return el.shadowRoot.querySelector('input.color') as HTMLInputElement | null;
}

describe('shabbat-rule-dialog', () => {
  it('opens an existing rule with its values filled in', async () => {
    const el = await render();
    expect(timeSelector(el).value).toBe('11:00:00');
    expect(enabledSelector(el).value).toBe(true);
    expect((el.shadowRoot!.querySelector('.name') as HTMLInputElement).value)
      .toBe('Morning');
    expect(el.shadowRoot!.textContent).toContain('Edit rule');
  });

  it('opens empty for a new rule, and offers no delete', async () => {
    const el = await render({ rule: null });
    expect(el.shadowRoot!.textContent).toContain('Add rule');
    expect(el.shadowRoot!.querySelector('.delete')).toBeNull();
    expect(el.shadowRoot!.querySelector('.duplicate')).toBeNull();
  });

  it('reports a save with the edited form, not the original rule', async () => {
    const el = await render();
    const listener = vi.fn();
    el.addEventListener('dialog-save', listener);

    timeSelector(el).dispatchEvent(
      new CustomEvent('value-changed', { detail: { value: '12:30:00' } }),
    );
    (el.shadowRoot!.querySelector('.save') as HTMLElement).click();

    const detail = (listener.mock.calls[0][0] as CustomEvent).detail;
    expect(detail.form.time).toBe('12:30:00');
    expect(detail.rule.id).toBe('r1');
  });

  it('flips enabled through the boolean selector', async () => {
    const el = await render();
    const listener = vi.fn();
    el.addEventListener('dialog-save', listener);

    enabledSelector(el).dispatchEvent(
      new CustomEvent('value-changed', { detail: { value: false } }),
    );
    (el.shadowRoot!.querySelector('.save') as HTMLElement).click();

    expect((listener.mock.calls[0][0] as CustomEvent).detail.form.enabled).toBe(false);
  });

  it('shows the server error and stays open, keeping the input', async () => {
    const el = await render({ error: 'time is not a valid clock time' });
    expect(el.shadowRoot!.textContent).toContain('not a valid clock time');
    expect(el.shadowRoot!.querySelector('.form')).not.toBeNull();
  });

  it('disables everything and hides the actions for a read-only user', async () => {
    const el = await render({ canWrite: false });
    expect(el.shadowRoot!.textContent).toContain('do not have permission');
    expect(el.shadowRoot!.querySelector('.save')).toBeNull();
    expect(el.shadowRoot!.querySelector('.delete')).toBeNull();
    expect(timeSelector(el).disabled).toBe(true);
    expect(enabledSelector(el).disabled).toBe(true);
  });

  it('disables the actions while a command is in flight', async () => {
    const el = await render({ busy: true });
    expect((el.shadowRoot!.querySelector('.save') as HTMLButtonElement).disabled)
      .toBe(true);
  });

  it('shows the advanced fields only once asked for, icon and colour among them', async () => {
    const el = await render();
    expect(iconSelector(el)).toBeNull();
    expect(colorInput(el)).toBeNull();
    (el.shadowRoot!.querySelector('.advanced-toggle') as HTMLElement).click();
    await el.updateComplete;
    expect(iconSelector(el)).not.toBeNull();
    expect(iconSelector(el).selector).toEqual({ icon: {} });
    expect(colorInput(el)!.type).toBe('color');
  });

  it('edits icon through ha-selector and colour through a native color input', async () => {
    const el = await render();
    (el.shadowRoot!.querySelector('.advanced-toggle') as HTMLElement).click();
    await el.updateComplete;
    const listener = vi.fn();
    el.addEventListener('dialog-save', listener);

    iconSelector(el).dispatchEvent(
      new CustomEvent('value-changed', { detail: { value: 'mdi:white-balance-sunny' } }),
    );
    colorInput(el)!.value = '#ff8800';
    colorInput(el)!.dispatchEvent(new Event('change'));
    (el.shadowRoot!.querySelector('.save') as HTMLElement).click();

    const detail = (listener.mock.calls[0][0] as CustomEvent).detail;
    expect(detail.form.icon).toBe('mdi:white-balance-sunny');
    expect(detail.form.color).toBe('#ff8800');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- rule-dialog.test.ts`
Expected: FAIL — `ha-selector.time`/`.enabled`/`.icon` not found, `input.color` not found.

- [ ] **Step 3: Implement**

In `frontend/src/rule-dialog.ts`, narrow `_text`'s key union and add the
four new field renderers. Replace the `_text` method (lines 155–174) with:

```ts
  private _text(key: 'name', label: string) {
    return html`
      <div class="field">
        <label for=${key}>${label}</label>
        <input
          id=${key}
          class=${key}
          .value=${String(this._form[key] ?? '')}
          ?disabled=${!this.canWrite}
          @change=${(event: Event) => {
            const value = (event.target as HTMLInputElement).value;
            this._patch({ [key]: value === '' ? null : value } as Partial<RuleFormState>);
          }}
        />
      </div>
    `;
  }

  private _timeField() {
    return html`
      <div class="field">
        <label for="time">${t(this.language, 'time')}</label>
        <ha-selector
          id="time"
          class="time"
          .hass=${this.hass}
          .selector=${{ time: {} }}
          .value=${this._form.time || null}
          .disabled=${!this.canWrite}
          @value-changed=${(event: CustomEvent) =>
            this._patch({ time: (event.detail?.value as string) ?? '' })}
        ></ha-selector>
      </div>
    `;
  }

  private _enabledField() {
    return html`
      <div class="field">
        <label for="enabled">${t(this.language, 'enabled')}</label>
        <ha-selector
          id="enabled"
          class="enabled"
          .hass=${this.hass}
          .selector=${{ boolean: {} }}
          .value=${this._form.enabled}
          .disabled=${!this.canWrite}
          @value-changed=${(event: CustomEvent) =>
            this._patch({ enabled: Boolean(event.detail?.value) })}
        ></ha-selector>
      </div>
    `;
  }

  private _iconField() {
    return html`
      <div class="field">
        <label for="icon">${t(this.language, 'icon')}</label>
        <ha-selector
          id="icon"
          class="icon"
          .hass=${this.hass}
          .selector=${{ icon: {} }}
          .value=${this._form.icon ?? ''}
          .disabled=${!this.canWrite}
          @value-changed=${(event: CustomEvent) => {
            const value = (event.detail?.value as string) ?? '';
            this._patch({ icon: value === '' ? null : value });
          }}
        ></ha-selector>
      </div>
    `;
  }

  private _colorField() {
    return html`
      <div class="field">
        <label for="color">${t(this.language, 'colour')}</label>
        <input
          id="color"
          class="color"
          type="color"
          .value=${this._form.color || '#000000'}
          ?disabled=${!this.canWrite}
          @change=${(event: Event) => {
            this._patch({ color: (event.target as HTMLInputElement).value });
          }}
        />
      </div>
    `;
  }
```

Then in `render()` (lines 227–312), replace the `.form` block's contents:

```ts
          <div class="form">
            ${this._timeField()}
            ${this._text('name', t(this.language, 'name'))}

            ${this._enabledField()}

            <!-- \`data: … ?? {}\` below is on purpose ... (comment unchanged) -->
            <shabbat-service-editor
              .hass=${this.hass}
              .action=${this._form.action}
              .data=${this._form.data}
              .disabled=${!this.canWrite}
              @service-changed=${(event: CustomEvent) =>
                this._patch({
                  action: event.detail.action, data: event.detail.data ?? {},
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
                const editor = event.target as HTMLElement & { hasError?: boolean };
                this._conditionError = editor.hasError === true;
                this._patch({ condition: event.detail.value });
              }}
            ></shabbat-condition-editor>

            <shabbat-replay-editor
              .hass=${this.hass}
              .value=${this._form.replay}
              .disabled=${!this.canWrite}
              .language=${this.language}
              @replay-changed=${(event: CustomEvent) =>
                this._patch({ replay: event.detail.value })}
            ></shabbat-replay-editor>

            <button
              class="advanced-toggle"
              @click=${() => { this._advanced = !this._advanced; }}
            >
              ${t(this.language, 'advanced')}
            </button>
            ${this._advanced
              ? html`
                  <div class="advanced">
                    ${this._iconField()}
                    ${this._colorField()}
                  </div>
                `
              : nothing}
          </div>
```

(`.hass=${this.hass}` is added to `<shabbat-replay-editor>` here because
Task 4 gives that component an `hass` property too — see Task 4's own
step for the property declaration; adding the binding now is harmless
since Lit ignores an unknown property set on a not-yet-upgraded element,
and avoids a second edit to this exact line later.)

Add `.time`/`.enabled`/`.icon` styling is unnecessary — `ha-selector`
lays itself out; the surrounding `.field` flex rules already apply.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- rule-dialog.test.ts`
Expected: PASS.

- [ ] **Step 5: Typecheck**

Run: `cd frontend && npm run typecheck`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/rule-dialog.ts frontend/test/rule-dialog.test.ts
git commit -m "refactor: rule dialog time/enabled/icon use ha-selector, color uses native input"
```

---

### Task 4: replay-editor.ts native-component sweep + duration conversion helpers

**Files:**
- Modify: `frontend/src/replay-editor.ts` (whole file)
- Modify: `frontend/test/replay-editor.test.ts` (whole file)
- Modify: `e2e/test_card_e2e.py:567-606` (`test_replay_can_be_switched_on_with_a_window`)
- Test: `frontend/test/replay-editor.test.ts`

**Interfaces:**
- Consumes: `Hass` type from `types.ts`; `ReplayData` type (unchanged shape:
  `{enabled: boolean; within?: string}`, `within` still `'HH:MM:SS'` on the
  wire — `rule_schema.py` and `ReplayData.within` are NOT changing shape).
- Produces: `durationObjectToString(value: DurationValue | undefined): string`
  and `durationStringToObject(value: string | undefined): DurationValue | undefined`,
  both exported from `frontend/src/replay-editor.ts`. No other task in this
  plan calls them, but they must keep these exact names/signatures if any
  later task (none currently planned) needs duration conversion.
- `ShabbatReplayEditor` gains a `@property({ attribute: false }) hass: Hass | null = null;`
  property (already wired from `rule-dialog.ts` in Task 3's step 3).

HA's `{duration: {}}` selector's value shape is **assumed**, not verified
against this repo (no file here uses `duration` yet): a partial
`{hours?: number; minutes?: number; seconds?: number}` object, missing keys
meaning zero, values not clamped to 24 hours. This assumption is stated in
a code comment and MUST be checked against the real dev container before
this is trusted in production (Step 8 below).

- [ ] **Step 1: Write the failing unit tests for the conversion helpers**

Create/replace `frontend/test/replay-editor.test.ts` in full:

```ts
import { describe, expect, it, vi } from 'vitest';
import '../src/replay-editor';
import {
  durationObjectToString, durationStringToObject,
} from '../src/replay-editor';

async function render(props: Record<string, unknown> = {}) {
  const el = document.createElement('shabbat-replay-editor') as HTMLElement &
    Record<string, any>;
  Object.assign(el, {
    hass: {}, value: { enabled: false }, disabled: false, language: 'en', ...props,
  });
  document.body.appendChild(el);
  await el.updateComplete;
  return el;
}

const enabledSel = (el: any) =>
  el.shadowRoot!.querySelector('ha-selector.replay-enabled');
const withinSel = (el: any) =>
  el.shadowRoot!.querySelector('ha-selector.replay-within') as any | null;

describe('duration conversion', () => {
  it('converts a full object to HH:MM:SS', () => {
    expect(durationObjectToString({ hours: 2, minutes: 30, seconds: 5 })).toBe('02:30:05');
  });

  it('treats missing fields as zero', () => {
    expect(durationObjectToString({ hours: 1 })).toBe('01:00:00');
    expect(durationObjectToString({})).toBe('00:00:00');
    expect(durationObjectToString(undefined)).toBe('00:00:00');
  });

  it('does not clamp hours at 24', () => {
    expect(durationObjectToString({ hours: 36, minutes: 15, seconds: 0 })).toBe('36:15:00');
  });

  it('converts HH:MM:SS back to an object', () => {
    expect(durationStringToObject('02:30:05')).toEqual({ hours: 2, minutes: 30, seconds: 5 });
  });

  it('round-trips a value with hours over 24', () => {
    expect(durationStringToObject('36:15:00')).toEqual({ hours: 36, minutes: 15, seconds: 0 });
  });

  it('treats an undefined string as an undefined object, not zeroed', () => {
    expect(durationStringToObject(undefined)).toBeUndefined();
  });

  it('rejects a malformed string rather than guessing', () => {
    expect(durationStringToObject('not-a-duration')).toBeUndefined();
    expect(durationStringToObject('01:02')).toBeUndefined();
  });
});

describe('shabbat-replay-editor', () => {
  it('is off by default and hides the window', async () => {
    const el = await render();
    expect(enabledSel(el).value).toBe(false);
    expect(withinSel(el)).toBeNull();
  });

  it('emits enabled with a default window when switched on', async () => {
    const el = await render();
    const seen: any[] = [];
    el.addEventListener('replay-changed', (e: Event) => {
      seen.push((e as CustomEvent).detail.value);
    });
    enabledSel(el).dispatchEvent(
      new CustomEvent('value-changed', { detail: { value: true } }),
    );
    expect(seen).toEqual([{ enabled: true, within: '01:00:00' }]);
  });

  it('shows the window as an {hours,minutes,seconds} object once enabled', async () => {
    const el = await render({ value: { enabled: true, within: '02:30:00' } });
    expect(withinSel(el)!.value).toEqual({ hours: 2, minutes: 30, seconds: 0 });
  });

  it('emits a changed window, converted back to HH:MM:SS', async () => {
    const el = await render({ value: { enabled: true, within: '01:00:00' } });
    const seen: any[] = [];
    el.addEventListener('replay-changed', (e: Event) => {
      seen.push((e as CustomEvent).detail.value);
    });
    withinSel(el)!.dispatchEvent(
      new CustomEvent('value-changed', { detail: { value: { hours: 0, minutes: 45, seconds: 0 } } }),
    );
    expect(seen).toEqual([{ enabled: true, within: '00:45:00' }]);
  });

  it('treats a cleared window as no bound, dropping the key', async () => {
    const el = await render({ value: { enabled: true, within: '01:00:00' } });
    const seen: any[] = [];
    el.addEventListener('replay-changed', (e: Event) => {
      seen.push((e as CustomEvent).detail.value);
    });
    withinSel(el)!.dispatchEvent(
      new CustomEvent('value-changed', { detail: { value: undefined } }),
    );
    expect(seen).toStrictEqual([{ enabled: true }]);
    expect('within' in seen[0]).toBe(false);
  });

  it('forgets the window when switched off, so off means off', async () => {
    const el = await render({ value: { enabled: true, within: '01:00:00' } });
    const seen: any[] = [];
    el.addEventListener('replay-changed', (e: Event) => {
      seen.push((e as CustomEvent).detail.value);
    });
    enabledSel(el).dispatchEvent(
      new CustomEvent('value-changed', { detail: { value: false } }),
    );
    expect(seen).toStrictEqual([{ enabled: false }]);
    expect('within' in seen[0]).toBe(false);
  });

  it('hands both selectors the current hass', async () => {
    const hass = { fake: true };
    const el = await render({ hass, value: { enabled: true, within: '01:00:00' } });
    expect(enabledSel(el).hass).toBe(hass);
    expect(withinSel(el)!.hass).toBe(hass);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- replay-editor.test.ts`
Expected: FAIL — `durationObjectToString`/`durationStringToObject` are not exported; `ha-selector.replay-enabled` not found.

- [ ] **Step 3: Implement**

Replace `frontend/src/replay-editor.ts` in full:

```ts
import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { t } from './strings';
import type { Hass, ReplayData } from './types';

/** Offered when replay is first switched on. One hour, in HH:MM:SS. */
const DEFAULT_WITHIN = '01:00:00';

/**
 * HA's duration selector value shape. ASSUMED, not yet confirmed against a
 * real running dev container - no other file in this repo uses a
 * `{duration: {}}` selector yet. Verify against `dev/` before trusting
 * this in production; if the real shape differs (e.g. it always sends
 * every key rather than omitting zeros, or nests under a `days` key),
 * adjust `durationObjectToString`/`durationStringToObject` below - nothing
 * else in this file needs to change, since they are the only place this
 * shape is read or written.
 */
interface DurationValue {
  hours?: number;
  minutes?: number;
  seconds?: number;
}

/**
 * {hours, minutes, seconds} -> 'HH:MM:SS', the shape `rule_schema.py`'s
 * `_duration` (and so every API client) accepts. Missing fields are 0;
 * hours are zero-padded to at least two digits but never clamped - a
 * duration selector allows values of 24 hours or more and `_duration`'s
 * `timedelta(hours=...)` does not care either.
 */
export function durationObjectToString(value: DurationValue | undefined): string {
  const hours = value?.hours ?? 0;
  const minutes = value?.minutes ?? 0;
  const seconds = value?.seconds ?? 0;
  return [hours, minutes, seconds].map((n) => String(n).padStart(2, '0')).join(':');
}

/**
 * 'HH:MM:SS' -> {hours, minutes, seconds}, the shape `ha-selector`'s
 * duration selector expects. `undefined` input (no window set) becomes
 * `undefined`, not a zeroed object, so the selector renders as genuinely
 * empty rather than "00:00:00". A malformed string also becomes
 * `undefined` rather than guessed at - `rule_schema.py` is the only owner
 * of what counts as a valid duration.
 */
export function durationStringToObject(value: string | undefined): DurationValue | undefined {
  if (value === undefined) return undefined;
  const parts = value.split(':');
  if (parts.length !== 3) return undefined;
  const [hours, minutes, seconds] = parts.map((p) => Number(p));
  if ([hours, minutes, seconds].some((n) => Number.isNaN(n))) return undefined;
  return { hours, minutes, seconds };
}

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
 * absent `within` means "no bound" to rule_schema.py.
 *
 * `within` is edited through `<ha-selector>` with a `{duration: {}}`
 * selector, per this project's own rule (see target-editor.ts): a
 * specific picker element's dashboard availability varies picker by
 * picker, `ha-selector` itself is always registered. This is NOT the
 * `ha-textfield` availability risk an earlier version of this comment
 * cited - that risk was about a plain `<input>` standing in for a
 * not-always-registered picker, and it does not apply to `ha-selector`,
 * so it was never a reason to avoid the selector here. What IS specific
 * to `duration`: HA's duration selector value is an
 * `{hours, minutes, seconds}` object, not the 'HH:MM:SS' string
 * `rule_schema.py` (and so every other API client) expects -
 * `durationObjectToString`/`durationStringToObject` above convert
 * between the two on every read and write.
 */
@customElement('shabbat-replay-editor')
export class ShabbatReplayEditor extends LitElement {
  @property({ attribute: false }) hass: Hass | null = null;
  @property({ attribute: false }) value: ReplayData = { enabled: false };
  @property({ type: Boolean }) disabled = false;
  @property() language = 'en';

  static override styles = css`
    .field { display: flex; align-items: center; gap: 12px; margin-block: 8px; }
    .field label { min-inline-size: 9em; }
    .help { color: var(--secondary-text-color, #666); font-size: 0.85em; }
  `;

  override render() {
    return html`
      <div class="wrap">
        <div class="field">
          <label for="replay-enabled">
            ${t(this.language, 'replay_after_restart')}
          </label>
          <ha-selector
            id="replay-enabled"
            class="replay-enabled"
            .hass=${this.hass}
            .selector=${{ boolean: {} }}
            .value=${this.value.enabled}
            .disabled=${this.disabled}
            @value-changed=${this._onEnabled}
          ></ha-selector>
        </div>
        ${this.value.enabled
          ? html`<div class="field">
              <label for="replay-within">
                ${t(this.language, 'replay_within_label')}
              </label>
              <ha-selector
                id="replay-within"
                class="replay-within"
                .hass=${this.hass}
                .selector=${{ duration: {} }}
                .value=${durationStringToObject(this.value.within)}
                .disabled=${this.disabled}
                @value-changed=${this._onWithin}
              ></ha-selector>
            </div>`
          : html`<div class="help">${t(this.language, 'replay_help')}</div>`}
      </div>
    `;
  }

  private _emit(value: ReplayData) {
    this.dispatchEvent(new CustomEvent('replay-changed', { detail: { value } }));
  }

  private _onEnabled = (event: CustomEvent) => {
    const enabled = Boolean(event.detail?.value);
    this._emit(
      enabled
        ? { enabled: true, within: this.value.within ?? DEFAULT_WITHIN }
        : { enabled: false },
    );
  };

  private _onWithin = (event: CustomEvent) => {
    const raw = event.detail?.value as DurationValue | undefined;
    // No validation here - rule_schema.py owns that, same as the plain
    // <input> this replaced.
    this._emit(
      raw === undefined
        ? { enabled: true }
        : { enabled: true, within: durationObjectToString(raw) },
    );
  };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- replay-editor.test.ts`
Expected: PASS.

- [ ] **Step 5: Typecheck the whole frontend**

Run: `cd frontend && npm run typecheck`
Expected: PASS (Task 3 already added `.hass=${this.hass}` to
`<shabbat-replay-editor>` in `rule-dialog.ts`).

- [ ] **Step 6: Update the e2e test that drives the old plain `<input>`**

`e2e/test_card_e2e.py`'s `test_replay_can_be_switched_on_with_a_window`
(lines 567–606) currently fills `input.replay-within` directly. Replace it
with a version driving `ha-selector.replay-within`'s internal duration
inputs. **The exact DOM `ha-selector`'s duration selector renders is not
verified here** — this is written from HA's documented `ha-duration-selector`
shape (a nested `ha-base-time-input` with separate hour/minute/second
number inputs) and MUST be checked against the real dev container in
Step 8; adjust the locators if the real structure differs.

```python
def test_replay_can_be_switched_on_with_a_window(page, base_url):
    """And must come back switched on, with its window, after a reload.

    Uses the erev 23:00 rule, which no other test in this file touches.

    UNVERIFIED against a real dev container as of this test's authoring -
    see this plan's Task 4, Step 6/8. The locators below assume
    `ha-duration-selector` renders three `ha-base-time-input input`
    elements in hour/minute/second order; adjust if the real DOM differs.
    """
    card = _card(page, base_url)
    try:
        dialog = _open_rule(card, "23:00")
        replay = dialog.locator("shabbat-replay-editor")
        replay.wait_for(timeout=10_000)
        enabled = replay.locator("ha-selector.replay-enabled")
        within = replay.locator("ha-selector.replay-within")
        expect(within).to_have_count(0)

        enabled.locator("ha-switch, ha-checkbox").first.click()
        within.wait_for(timeout=10_000)
        hour = within.locator("ha-base-time-input input").nth(0)
        minute = within.locator("ha-base-time-input input").nth(1)
        expect(hour).to_have_value("01")  # the offered default, 01:00:00
        hour.fill("02")
        minute.fill("30")

        dialog.locator("button.save").click()
        dialog.wait_for(state="detached", timeout=15_000)

        card = _card(page, base_url)
        dialog = _open_rule(card, "23:00")
        replay = dialog.locator("shabbat-replay-editor")
        within = replay.locator("ha-selector.replay-within")
        within.wait_for(timeout=10_000)
        expect(within.locator("ha-base-time-input input").nth(0)).to_have_value("02")
        expect(within.locator("ha-base-time-input input").nth(1)).to_have_value("30")
        dialog.locator(CANCEL).click()
    finally:
        card = _card(page, base_url)
        dialog = _open_rule(card, "23:00")
        enabled = dialog.locator("shabbat-replay-editor ha-selector.replay-enabled")
        switch = enabled.locator("ha-switch, ha-checkbox").first
        if switch.is_checked():
            switch.click()
            dialog.locator("button.save").click()
            dialog.wait_for(state="detached", timeout=15_000)
```

- [ ] **Step 7: Run the frontend and Python suites (e2e excluded — needs the dev container)**

Run: `cd frontend && npm test && npm run typecheck`
Run: `uv run pytest tests/`
Expected: both PASS. `e2e/` is not run here — it needs the dev container
(Step 8).

- [ ] **Step 8: Verify against the real dev container**

Run: `cd dev && ./run.sh` (see `dev/README.md` for the exact command), then
`uv run pytest e2e/test_card_e2e.py -k test_replay_can_be_switched_on_with_a_window`.
If the duration selector's real DOM does not match Step 6's assumed
locators, fix them here — this step is the verification the earlier steps
call for, not a formality.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/replay-editor.ts frontend/test/replay-editor.test.ts e2e/test_card_e2e.py
git commit -m "refactor: replay editor uses ha-selector for enabled and duration"
```

---

### Task 5: Row-level quick enable/disable toggle

**Files:**
- Modify: `frontend/src/rule-row.ts` (whole file)
- Modify: `frontend/src/day-group.ts` (whole file)
- Modify: `frontend/src/card.ts` (new state, handler, template bindings)
- Test: `frontend/test/rule-row.test.ts`, `frontend/test/day-group.test.ts`, `frontend/test/card.test.ts`

**Interfaces:**
- Consumes: nothing new from earlier tasks.
- Produces: `rule-row.ts` dispatches a new event `rule-toggle-enabled`
  (`bubbles: true, composed: true`, `detail: { rule: RuleData }`) — reaches
  `card.ts` directly at the `<ha-card>` level, the same way `rule-open`
  already does; `day-group.ts` needs no listener for it. `rule-row.ts`
  gains `@property({ type: Boolean }) canWrite = false;` and
  `@property() toggleError: string | null = null;`. `day-group.ts` gains
  `@property({ attribute: false }) toggleErrors: Record<string, string> = {};`
  and passes `.canWrite=${this.canWrite}` (already a `day-group.ts`
  property) and `.toggleError=${this.toggleErrors[rule.id] ?? null}` to
  each `<shabbat-rule-row>`. `card.ts` gains
  `@state() private _toggleErrors: Record<string, string> = {};` and a
  private `_toggleRuleEnabled(rule: RuleData): Promise<void>` method — no
  other task calls it directly.

The row's `@click`/`role="button"`/keydown handlers already open the rule
dialog on any click (`frontend/src/rule-row.ts:104-114`). The new toggle's
click handler MUST call `event.stopPropagation()`, and the keydown path
needs the same guard, or every tap both flips the switch and opens the
dialog. This toggle only renders `canWrite`, mirroring every other write
control in this codebase (`day-group.ts`'s add button, `block-header.ts`'s
gear/master, `rule-dialog.ts`'s save/delete) — a control certain to fail
for a read-only user is worse than not offering it. The write goes through
a NEW method, not `card.ts`'s existing `_send`/`_dialogError`: those are
dialog-scoped (`_dialogError` renders only inside `<shabbat-rule-dialog>`),
and a row-toggle failure has to be visible on the row that failed, with no
dialog open at all.

- [ ] **Step 1: Write the failing test for rule-row.ts**

Add to `frontend/test/rule-row.test.ts`:

```ts
describe('the row-level enable/disable toggle', () => {
  it('renders a compact boolean selector for a writer', async () => {
    const el = await render({ rule: rule({}), canWrite: true });
    const sel = el.shadowRoot!.querySelector('ha-selector.row-toggle') as any;
    expect(sel).not.toBeNull();
    expect(sel.selector).toEqual({ boolean: {} });
    expect(sel.value).toBe(true);
  });

  it('offers no toggle to a read-only user', async () => {
    const el = await render({ rule: rule({}), canWrite: false });
    expect(el.shadowRoot!.querySelector('ha-selector.row-toggle')).toBeNull();
  });

  it('fires rule-toggle-enabled naming the whole rule, not just its id', async () => {
    const el = await render({ rule: rule({ id: 'a', enabled: true }), canWrite: true });
    let detail: any = null;
    el.addEventListener('rule-toggle-enabled', (e: Event) => {
      detail = (e as CustomEvent).detail;
    });
    const sel = el.shadowRoot!.querySelector('ha-selector.row-toggle') as any;
    sel.dispatchEvent(new CustomEvent('value-changed', { detail: { value: false } }));
    expect(detail.rule.id).toBe('a');
  });

  it('does not open the dialog when the toggle is used', async () => {
    const el = await render({ rule: rule({ id: 'a' }), canWrite: true });
    let opened = false;
    el.addEventListener('rule-open', () => { opened = true; });
    const sel = el.shadowRoot!.querySelector('ha-selector.row-toggle') as any;
    sel.dispatchEvent(new CustomEvent('click', { bubbles: true, composed: true }));
    expect(opened).toBe(false);
  });

  it('shows a per-row error when the toggle write is rejected', async () => {
    const el = await render({
      rule: rule({}), canWrite: true, toggleError: 'That did not go through.',
    });
    expect(el.shadowRoot!.textContent).toContain('That did not go through.');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- rule-row.test.ts`
Expected: FAIL — `canWrite`/`toggleError` are not properties yet, no `.row-toggle`.

- [ ] **Step 3: Implement rule-row.ts**

Add two properties and the toggle markup to `frontend/src/rule-row.ts`:

```ts
  @property({ attribute: false }) rule!: RuleData;
  @property({ attribute: false }) defaults: Defaults = {};
  @property({ attribute: false }) warnings: WarningData[] = [];
  @property({ type: Boolean }) canWrite = false;
  @property() toggleError: string | null = null;
  @property() language = 'en';
```

Add a `.row-error` style rule alongside the existing ones (after
`.tag { ... }`):

```css
    .row-toggle { flex: none; }
    .row-error {
      color: var(--error-color, #c62828);
      font-size: 0.85em;
      overflow-wrap: anywhere;
      margin-block-start: 2px;
    }
```

In `render()`, add the toggle as the first child of `.row` (before `.dot`)
and the error line inside `.body`:

```ts
      <div
        class="row ${this.rule.enabled ? '' : 'disabled'}"
        tabindex="0"
        role="button"
        @click=${() => this._open()}
        @keydown=${(event: KeyboardEvent) => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            this._open();
          }
        }}
      >
        ${this.canWrite
          ? html`<ha-selector
              class="row-toggle"
              .selector=${{ boolean: {} }}
              .value=${this.rule.enabled}
              @click=${(event: Event) => event.stopPropagation()}
              @keydown=${(event: Event) => event.stopPropagation()}
              @value-changed=${(event: CustomEvent) => {
                this.dispatchEvent(
                  new CustomEvent('rule-toggle-enabled', {
                    detail: { rule: this.rule },
                    bubbles: true, composed: true,
                  }),
                );
              }}
            ></ha-selector>`
          : nothing}
        <span class="dot" style="background:${ruleColour(this.rule)}"></span>
        <span class="time">${this.rule.time.slice(0, 5)}</span>
        <div class="body">
          ${title ? html`<div class="title">${title}</div>` : nothing}
          <div class="brief">${ruleBrief(this.rule, this.defaults)}</div>
          ${this.toggleError !== null
            ? html`<div class="row-error">${this.toggleError}</div>`
            : nothing}
          ${outcome !== null
            ? html`<div class="last-outcome ${outcomeIsBad(outcome) ? 'bad' : ''}">
                <span>${formatOutcome(outcome, this.language)}</span>
                ${when ? html`<span class="last-outcome-at">${when}</span>` : nothing}
              </div>`
            : nothing}
          ${conflicts.length
            ? html`<div class="conflict-detail">
                ${conflicts.map(
                  (conflict) =>
                    html`<div>${formatWarning(conflict, this.language)}</div>`,
                )}
              </div>`
            : nothing}
        </div>
        ${this.rule.enabled
          ? nothing
          : html`<span class="tag">${t(this.language, 'disabled_rule')}</span>`}
        ${conflicts.length
          ? html`<span
              class="conflict"
              role="img"
              aria-label=${conflicts
                .map((conflict) => formatWarning(conflict, this.language))
                .join('; ')}
              title=${formatWarning(conflicts[0], this.language)}
              >⚠</span
            >`
          : nothing}
      </div>
```

Note the toggle's `@value-changed` handler ignores `event.detail.value` —
the dispatched `rule-toggle-enabled` always carries the CURRENT
`this.rule`, and it is `card.ts`'s `_toggleRuleEnabled` (Step 5) that
computes `!rule.enabled` when it builds the websocket write, so the row
never has to guess at the server's eventual value.

- [ ] **Step 4: Run rule-row.test.ts, then write+run the day-group.ts test**

Run: `cd frontend && npm test -- rule-row.test.ts`
Expected: PASS.

Add to `frontend/test/day-group.test.ts`:

```ts
  it('threads canWrite and the matching toggle error down to each row', async () => {
    const el = await render({
      group: group({
        rules: [
          { id: 'a', profile: 1, day: '1', time: '11:00:00',
            action: 'climate.turn_on', target: {}, data: {}, condition: [],
            replay: { enabled: false }, name: null, icon: null,
            enabled: true, color: null, last_outcome: null },
        ],
      }),
      canWrite: true,
      toggleErrors: { a: 'That did not go through.' },
    });
    const row = el.shadowRoot!.querySelector('shabbat-rule-row') as any;
    expect(row.canWrite).toBe(true);
    expect(row.toggleError).toBe('That did not go through.');
  });
```

Run: `cd frontend && npm test -- day-group.test.ts`
Expected: FAIL — `toggleErrors` not a property yet.

- [ ] **Step 5: Implement day-group.ts and card.ts**

In `frontend/src/day-group.ts`, add a property and thread it through:

```ts
  @property({ attribute: false }) toggleErrors: Record<string, string> = {};
```

In `render()`, change the row mapping:

```ts
        ${rules.length
          ? rules.map(
              (rule) => html`
                <shabbat-rule-row
                  .rule=${rule}
                  .defaults=${this.defaults}
                  .warnings=${this.warnings}
                  .language=${this.language}
                  .canWrite=${this.canWrite}
                  .toggleError=${this.toggleErrors[rule.id] ?? null}
                ></shabbat-rule-row>
              `,
            )
          : html`<div class="empty">${t(this.language, 'no_rules')}</div>`}
```

In `frontend/src/card.ts`, add state and a handler (near `_dialogError`'s
declaration):

```ts
  @state() private _toggleErrors: Record<string, string> = {};
```

```ts
  /**
   * Same websocket write path `_saveChanges` uses for the dialog's own
   * `enabled` field, scoped to one field on purpose - not a round trip
   * through `_send`/`_dialogError`, which are dialog-scoped and would
   * report a row's failure nowhere visible when no dialog is open.
   */
  private async _toggleRuleEnabled(rule: RuleData) {
    try {
      await this._hass.callWS({
        type: 'shabbat_scheduler/rules/update',
        rule_id: rule.id,
        changes: { enabled: !rule.enabled },
      });
      if (rule.id in this._toggleErrors) {
        const rest = { ...this._toggleErrors };
        delete rest[rule.id];
        this._toggleErrors = rest;
      }
    } catch (err) {
      const detail = err as { message?: string } | null;
      this._toggleErrors = {
        ...this._toggleErrors,
        [rule.id]: detail?.message ?? String(err),
      };
    }
  }

  private _onRuleToggleEnabled = (event: Event) => {
    const { rule } = (event as CustomEvent).detail as { rule: RuleData };
    void this._toggleRuleEnabled(rule);
  };
```

In `render()`, add the listener to `<ha-card>` and thread `_toggleErrors`
into each `<shabbat-day-group>`:

```ts
      <ha-card @rule-open=${this._onRuleOpen} @rule-toggle-enabled=${this._onRuleToggleEnabled}>
        ...
        ${groups.map(
          (group) => html`
            <shabbat-day-group
              .group=${group}
              .defaults=${this._state!.defaults}
              .warnings=${this._state!.warnings}
              .language=${this._language}
              .canWrite=${this._canWrite}
              .toggleErrors=${this._toggleErrors}
              @rule-add=${this._onRuleAdd}
            ></shabbat-day-group>
          `,
        )}
```

- [ ] **Step 6: Write and run the card.ts integration test**

Add to `frontend/test/card.test.ts`, INSIDE the existing
`describe('authoring', () => { ... })` block (starts at line 438) so the
`withRules()` helper (defined at line 439) is in scope:

```ts
  it('toggles a rule enabled/disabled from the row, non-optimistically', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(withRules());
    await el.updateComplete;

    const row = (await ruleRows(el))[0] as any;
    row.shadowRoot!.querySelector('ha-selector.row-toggle')!.dispatchEvent(
      new CustomEvent('value-changed', { detail: { value: false } }),
    );
    await flush();

    expect(hass.callWS).toHaveBeenCalledWith({
      type: 'shabbat_scheduler/rules/update',
      rule_id: withRules().rules[0].id,
      changes: { enabled: !withRules().rules[0].enabled },
    });
    // No optimistic update: the row still shows what the last push said.
    expect(row.rule.enabled).toBe(withRules().rules[0].enabled);
  });

  it('reports a rejected row toggle on the row, not the dialog', async () => {
    const { hass, send } = fakeHass();
    hass.callWS = vi.fn(async () => { throw { message: 'nope' }; });
    const el = await mount(hass);
    send(withRules());
    await el.updateComplete;

    const row = (await ruleRows(el))[0] as any;
    row.shadowRoot!.querySelector('ha-selector.row-toggle')!.dispatchEvent(
      new CustomEvent('value-changed', { detail: { value: false } }),
    );
    await flush();
    await el.updateComplete;

    const refreshedRow = (await ruleRows(el))[0] as any;
    expect(refreshedRow.toggleError).toBe('nope');
    expect(el.shadowRoot!.querySelector('shabbat-rule-dialog')).toBeNull();
  });
```

(This assumes `withRules()` already exists in `card.test.ts` and returns a
`CardState` with at least one rule — check the file; if the helper has a
different name, use it instead, matching this file's own convention.)

- [ ] **Step 7: Run the full frontend suite and typecheck**

Run: `cd frontend && npm test && npm run typecheck`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/rule-row.ts frontend/src/day-group.ts frontend/src/card.ts \
  frontend/test/rule-row.test.ts frontend/test/day-group.test.ts frontend/test/card.test.ts
git commit -m "feat: quick enable/disable toggle on each rule row"
```

---

### Task 6: `engine.async_apply_rule` gains `simulate`, `at`, `force_conditions`

**Files:**
- Modify: `custom_components/shabbat_scheduler/engine.py:281-441` (`async_apply_rule`, `_fire_completed`, `_condition_block_reason`, `_call`)
- Modify: `tests/test_engine.py` (port the four `dry_run`-driven tests; add new ones)
- Test: `tests/test_engine.py`

**Interfaces:**
- Consumes: nothing new from the frontend tasks (backend-only).
- Produces:
  `async def async_apply_rule(self, rule: Rule, *, simulate: bool = False, at: datetime | None = None, force_conditions: bool = False) -> list[dict]`
  — Task 7 (`ws_run_now`) and Task 8 (`ws_run_day`) call this exact
  signature. `_condition_block_reason(self, rule: Rule, at: datetime | None = None) -> str | None`
  and `_call(self, rule, action, target, data, context, *, simulate: bool) -> dict`
  and `_fire_completed(self, rule: Rule, results: list[dict], *, simulate: bool = False) -> None`
  are internal to this file; no other task calls them directly.

The old `force: bool = False` parameter on `async_apply_rule` is unused
dead code (verified: no caller in `custom_components/` or `tests/` ever
passes it) and is replaced outright, not kept alongside the new
keyword-only parameters.

**Judgment call — `at` for `sun`/`time` conditions.** The spec assumes HA's
own condition helpers accept an explicit "now" override for `sun`/`time`.
Verified against the installed 2026.8.2
(`homeassistant/helpers/condition.py`'s `time()` and
`homeassistant/components/sun/condition.py`'s `sun()`): **neither accepts
one** — both read `dt_util.now()`/`dt_util.utcnow()` directly with no
parameter to substitute. The mechanism below (`_check_at_scoped`)
temporarily reassigns `dt_util.now`/`dt_util.utcnow` for the duration of
one synchronous, non-`await`-ing checker call, restored in `finally` —
the same technique `freezegun` itself uses, done with plain attribute
reassignment rather than adding a test-only dependency (`freezegun` is not
in `manifest.json`'s `requirements`) to code Home Assistant loads at
runtime. This is safe from interleaving specifically because the
substituted call contains no `await`, so nothing else on the event loop
can run between the substitution and its restore.

**Judgment call — does `simulate` suppress outcome recording on the
*blocked* path too?** The spec's `simulate` paragraph says "does not call
`self._async_record_outcome`" without scoping that to the `_call`-level
`would_call` path specifically, and the Goal states unconditionally "a
simulated run is never recorded to `last_outcome`... never persisted." The
old `store.dry_run` flag never touched the blocked path's recording (it
only ever gated `_call`'s return value) — this is a genuine, deliberate
behaviour change from the old flag, not a straight port of it, and this
task implements the broader reading: `_async_record_outcome` (and so
`SIGNAL_RULES_CHANGED`, which it alone fires) is skipped whenever
`simulate` is true, on every path, blocked included.

- [ ] **Step 1: Write the failing tests**

In `tests/test_engine.py`, replace the four `dry_run`-driven tests
(`test_a_dry_run_still_reports_an_unknown_target`,
`test_dry_run_makes_no_service_calls`,
`test_a_dry_run_still_reports_reaching_nothing_live`,
`test_a_dry_run_records_that_it_would_have_run`) with `simulate=True`
versions, and add the new ablation/at-scoping tests:

```python
async def test_a_simulated_run_still_reports_an_unknown_target(
    hass, jerusalem, test_booleans, _rule
):
    """A simulated run is where you WANT to find the typo."""
    engine = ShabbatEngine(hass, RuleStore(hass))
    await engine.store.async_load()

    rule = _rule(action=_ON, entities=("input_boolean.nope",))
    [result] = await engine.async_apply_rule(rule, simulate=True)

    assert result["outcome"] == "would_call"
    assert result["unknown_targets"] == ["input_boolean.nope"]


async def test_simulate_makes_no_service_calls(hass, jerusalem, test_booleans, _rule):
    engine = ShabbatEngine(hass, RuleStore(hass))
    await engine.store.async_load()

    hass.states.async_set("input_boolean.t", "off")
    results = await engine.async_apply_rule(_rule(), simulate=True)
    await hass.async_block_till_done()

    assert hass.states.get("input_boolean.t").state == "off"
    assert results[0]["outcome"] == "would_call"


async def test_a_simulated_run_still_reports_reaching_nothing_live(hass, engine, _rule):
    await hass.async_block_till_done()
    hass.states.async_set("group.g", "unknown", {"entity_id": ["input_boolean.member"]})
    rule = _rule(action="input_boolean.turn_on", entities=("group.g",))

    [result] = await engine.async_apply_rule(rule, simulate=True)

    assert result["outcome"] == "would_call"
    assert result["no_live_targets"] is True
    assert "unknown_targets" not in result


async def test_simulate_never_records_a_durable_outcome(hass, engine, _rule):
    """`would_call` is not `called`, and it must never overwrite a real
    verdict, because the run it describes did not really happen."""
    hass.states.async_set("input_boolean.t", "off")
    rule = await _seeded(engine, _rule())

    await engine.async_apply_rule(rule, simulate=True)

    assert engine.store.last_outcome(rule.id) is None


async def test_simulate_does_not_record_even_when_the_rule_is_blocked(hass, engine, _rule):
    """Ablate this and a simulated but blocked rule leaves a real verdict
    behind - the exact thing 'never persisted' forbids."""
    hass.states.async_set("input_boolean.kids", "off")
    rule = await _seeded(engine, _rule(condition=(
        {"condition": "state", "entity_id": "input_boolean.kids", "state": "on"},
    )))

    results = await engine.async_apply_rule(rule, simulate=True)

    assert results[0]["outcome"] == "blocked"
    assert engine.store.last_outcome(rule.id) is None


async def test_simulate_does_not_signal_rules_changed(hass, engine, _rule):
    from custom_components.shabbat_scheduler.const import SIGNAL_RULES_CHANGED
    from homeassistant.helpers.dispatcher import async_dispatcher_connect

    hass.states.async_set("input_boolean.t", "off")
    rule = await _seeded(engine, _rule())
    calls = []
    async_dispatcher_connect(hass, SIGNAL_RULES_CHANGED, lambda: calls.append(1))

    await engine.async_apply_rule(rule, simulate=True)
    await hass.async_block_till_done()

    assert calls == []


async def test_a_real_run_still_records_and_signals(hass, engine, _rule):
    """The two tests above ablated: a REAL run (simulate defaults False)
    must still record and signal, or the guard above proves nothing."""
    from custom_components.shabbat_scheduler.const import SIGNAL_RULES_CHANGED
    from homeassistant.helpers.dispatcher import async_dispatcher_connect

    hass.states.async_set("input_boolean.t", "off")
    rule = await _seeded(engine, _rule())
    calls = []
    async_dispatcher_connect(hass, SIGNAL_RULES_CHANGED, lambda: calls.append(1))

    await engine.async_apply_rule(rule)
    await hass.async_block_till_done()

    assert engine.store.last_outcome(rule.id) is not None
    assert calls == [1]


async def test_force_conditions_skips_evaluation_entirely(hass, engine, _rule):
    hass.states.async_set("input_boolean.kids", "off")  # would normally block
    hass.states.async_set("input_boolean.t", "off")
    rule = await _seeded(engine, _rule(condition=(
        {"condition": "state", "entity_id": "input_boolean.kids", "state": "on"},
    )))

    results = await engine.async_apply_rule(rule, simulate=True, force_conditions=True)

    assert results[0]["outcome"] == "would_call"  # not "blocked"


async def test_at_evaluates_a_time_condition_against_a_hypothetical_moment(
    hass, jerusalem, engine, _rule
):
    from datetime import datetime

    hass.states.async_set("input_boolean.t", "off")
    # after 20:00 local - false right now (test runs at an arbitrary real
    # time), true at the `at` below.
    rule = await _seeded(engine, _rule(condition=(
        {"condition": "time", "after": "20:00:00"},
    )))

    at = datetime(2026, 8, 15, 21, 0, tzinfo=jerusalem.config.time_zone)
    results = await engine.async_apply_rule(rule, simulate=True, at=at)

    assert results[0]["outcome"] == "would_call"


async def test_at_does_not_affect_a_state_condition(hass, jerusalem, engine, _rule):
    """`at` is scoped to `sun`/`time` only - a `state` condition still
    reads the real state, not something keyed off `at`."""
    from datetime import datetime

    hass.states.async_set("input_boolean.kids", "off")
    hass.states.async_set("input_boolean.t", "off")
    rule = await _seeded(engine, _rule(condition=(
        {"condition": "state", "entity_id": "input_boolean.kids", "state": "on"},
    )))

    at = datetime(2026, 8, 15, 21, 0, tzinfo=jerusalem.config.time_zone)
    results = await engine.async_apply_rule(rule, simulate=True, at=at)

    assert results[0]["outcome"] == "blocked"
```

(`_seeded` is an existing helper in `tests/test_engine.py` — check its
definition near the top of the file and use it as-is; it is what the
existing `test_a_dry_run_records_that_it_would_have_run` test already
called.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_engine.py -k "simulate or force_conditions or at_evaluates or at_does_not" -v`
Expected: FAIL — `async_apply_rule()` does not accept `simulate=`/`at=`/`force_conditions=` yet.

- [ ] **Step 3: Implement**

In `custom_components/shabbat_scheduler/engine.py`, replace
`async_apply_rule` (lines 281–335):

```python
    async def async_apply_rule(
        self,
        rule: Rule,
        *,
        simulate: bool = False,
        at: datetime | None = None,
        force_conditions: bool = False,
    ) -> list[dict]:
        """Apply one rule, returning a per-attribute outcome report.

        The event is fired BEFORE the calls and carries everything needed to
        describe itself. The logbook renders historical events, so a describe
        function cannot look the rule up - it may have been renamed or deleted
        by then. Firing first is also what lets Home Assistant attribute each
        device's own change back to this rule, the same way automations do.

        `simulate`: behaves exactly as the old `store.dry_run` flag used to
        at the point of the real service call (`_call` returns `would_call`
        instead of calling) - but, unlike that flag, a simulated run never
        calls `_async_record_outcome` and never fires SIGNAL_RULES_CHANGED
        (the only place that signal fires from here), on every path
        including a blocked one: it did not really happen, and the rest of
        the system must not be told otherwise. The event bus still fires
        (EVENT_RULE_APPLIED / EVENT_RULE_COMPLETED), carrying the same
        `dry_run`-named key for backward compatibility with anything
        listening - renaming it would be a breaking change to an external
        contract this codebase does not control the readers of.

        `force_conditions`: when true, every condition is treated as passed
        and `_condition_block_reason` is not consulted at all. Its only
        effect; it does not interact with `at` - forcing pass is "ignore
        conditions", evaluating against `at` is "evaluate conditions
        honestly against a different moment", and a caller gets one or the
        other, or neither, never both combined into a third meaning.

        `at`: passed through to `_condition_block_reason` so a `sun`/`time`
        condition is evaluated as though `at` were now - see that method's
        docstring for the mechanism and its limits. Has no effect when
        `force_conditions` is true, since no condition is evaluated then.

        Both default to today's behaviour when omitted, so the two real
        call sites (`_make_callback`'s real callback and
        `async_catch_up`'s replay path) are unaffected and untested
        differently.
        """
        context = Context()
        self._our_contexts.append(context.id)

        self.hass.bus.async_fire(
            EVENT_RULE_APPLIED,
            {
                "rule_id": rule.id,
                "name": rule.name,
                "action": rule.action,
                "target": dict(rule.target),
                "dry_run": simulate,
            },
            context=context,
        )

        if rule.condition and not force_conditions:
            blocked_by = await self._condition_block_reason(rule, at)
            if blocked_by is not None:
                results = [{"outcome": "blocked", "reason": blocked_by}]
                self.last_run = results
                self.last_run_at = dt_util.utcnow()
                self._fire_completed(rule, results, simulate=simulate)
                if not simulate:
                    await self._async_record_outcome(
                        rule,
                        build_outcome("blocked", self.last_run_at, blocked_by),
                    )
                return results

        async with self._locks[rule.id]:
            results = []
            for action, data in expand_action(rule.action, dict(rule.data)):
                results.append(
                    await self._call(
                        rule, action, rule.target, data, context, simulate=simulate
                    )
                )

        self.last_run = results
        self.last_run_at = dt_util.utcnow()
        self._fire_completed(rule, results, simulate=simulate)
        if not simulate:
            await self._async_record_outcome(
                rule, outcome_from_results(results, self.last_run_at)
            )
        return results
```

Replace `_fire_completed` (lines 367–391):

```python
    def _fire_completed(
        self, rule: Rule, results: list[dict], *, simulate: bool = False
    ) -> None:
        """Announce the outcome, carrying enough to describe itself.

        Fired after the results exist, for consumers that need them.
        EVENT_RULE_APPLIED cannot carry them: it must precede the calls so
        Home Assistant can attribute each device's change back to this rule.

        It carries `name`/`action`/`target`/`dry_run` as well as the
        results, for the same reason EVENT_RULE_APPLIED does: the logbook
        renders HISTORICAL events, so its describer cannot look the rule up
        - it may have been renamed or deleted by then. Without these the
        outcome row could not say which rule or which device it was about,
        and an outcome nobody can attribute is barely an outcome.

        `dry_run` in the payload is `simulate`, not `self.store.dry_run` -
        the persisted flag is gone (see docs/known-behaviours.md); the key
        NAME stays `dry_run` for backward compatibility with anything
        listening on the event bus.
        """
        self.hass.bus.async_fire(
            EVENT_RULE_COMPLETED,
            {
                "rule_id": rule.id,
                "name": rule.name,
                "action": rule.action,
                "target": dict(rule.target),
                "dry_run": simulate,
                "results": results,
            },
        )
```

Replace `_condition_block_reason` (lines 393–440) and add
`_check_at_scoped` right after it:

```python
    # The only two condition types HA's own helpers read the clock for
    # without accepting any override argument at all - see
    # `_check_at_scoped`.
    _AT_SCOPED_CONDITIONS = frozenset({"sun", "time"})

    async def _condition_block_reason(
        self, rule: Rule, at: datetime | None = None
    ) -> str | None:
        """None if every condition passes, else WHY the rule is blocked.

        Every condition must pass. An error counts as not passing: erring
        towards NOT acting, because an unexpected error is not consent to
        drive an appliance on a day nobody can undo it.

        Returns a reason rather than a bool because this stops at the FIRST
        failing condition, so a rule carrying three of them would otherwise
        report a bare "condition not met" and leave the user no way at all
        to tell which one held it back - on the one day they cannot
        investigate. The index and the condition's own identifying fields
        are the difference between a report and a shrug.

        `async_from_config` builds its checker straight from the raw dict
        without normalising it first (e.g. a bare `entity_id: "a.b"` string
        is never turned into `["a.b"]"), so a config that skipped schema
        validation is silently misread rather than rejected -
        `cv.CONDITION_SCHEMA` + `async_validate_condition_config` is what
        does that normalising, same as `ha_validation.py` does at
        authoring time for the identical reason.

        `at`: when given, a condition of type `sun` or `time` is evaluated
        as though `at` were "now" - verified against the installed
        2026.8.2, `homeassistant.helpers.condition.time` and
        `homeassistant.components.sun.condition.sun` both call
        `dt_util.now()`/`dt_util.utcnow()` directly and accept no `now`
        parameter of their own. `at` for any OTHER condition type is a
        documented no-op, not silently pretended to work, since HA gives
        this module no hook to parameterise them at all. See
        `_check_at_scoped` for the substitution mechanism.
        """
        total = len(rule.condition)
        for index, item in enumerate(rule.condition, start=1):
            label = _condition_label(index, total, item)
            kind = item.get("condition") if isinstance(item, dict) else None
            try:
                validated = cv.CONDITION_SCHEMA(dict(item))
                validated = await condition.async_validate_condition_config(
                    self.hass, validated
                )
                checker = await condition.async_from_config(self.hass, validated)
                if at is not None and kind in self._AT_SCOPED_CONDITIONS:
                    passed = self._check_at_scoped(checker, at)
                else:
                    passed = checker(self.hass, {})
                if not passed:
                    return f"{label} not met"
            except Exception as err:  # noqa: BLE001 - a broken condition blocks
                _LOGGER.exception(
                    "Rule %s: %s could not be evaluated; not acting",
                    rule.id,
                    label,
                )
                detail = (
                    f"{type(err).__name__}: {err}" if str(err)
                    else type(err).__name__
                )
                return f"{label} could not be evaluated ({detail})"
        return None

    def _check_at_scoped(self, checker, at: datetime) -> bool:
        """Evaluate a sun/time condition checker as though `at` were now.

        HA's `time`/`sun` condition helpers read `dt_util.now()`/
        `dt_util.utcnow()` directly and accept no override parameter of
        their own (see `_condition_block_reason`'s docstring). The only
        honest way to evaluate one against a hypothetical moment is to
        substitute what "now" means for the duration of this one call -
        the same technique `freezegun` itself uses under the hood, done
        here with plain attribute reassignment rather than adding a
        test-only dependency (`freezegun` is not in `manifest.json`'s
        `requirements`; see pyproject.toml) to a component Home Assistant
        loads at runtime.

        Safe from interleaving: `checker(...)` for `sun`/`time` is
        synchronous and contains no `await`, so nothing else on the event
        loop can run between the substitution and its `finally` restore.
        """
        at_local = at.astimezone(self._tz())
        original_now, original_utcnow = dt_util.now, dt_util.utcnow
        dt_util.now = lambda time_zone=None: (
            at_local.astimezone(time_zone) if time_zone else at_local
        )
        dt_util.utcnow = lambda: at_local.astimezone(dt_util.UTC)
        try:
            return checker(self.hass, {})
        finally:
            dt_util.now = original_now
            dt_util.utcnow = original_utcnow
```

Replace `_call`'s signature and its `dry_run` check (lines 927–968, the
part up to and including `if self.store.dry_run:`):

```python
    async def _call(
        self,
        rule: Rule,
        action: str,
        target: dict,
        data: dict,
        context: Context,
        *,
        simulate: bool,
    ) -> dict:
        """One service call, retried, reported either way.

        Everything here is Home Assistant's own service machinery -
        `async_call_from_config` validates the config, resolves the target
        and makes the call. This integration's contribution is deciding
        that now is the moment.
        """
        result = {"action": action, "target": dict(target), "data": dict(data)}

        # Before the simulate return, deliberately: a simulated run is
        # exactly where you want to be told about a misspelt entity id, and
        # one that reported "would_call" for a target that cannot resolve
        # would be the same quiet failure one step earlier.
        unknown, nothing_real = self._inspect_target(target)
        if unknown:
            result["unknown_targets"] = unknown
            _LOGGER.warning(
                "rule '%s' targets %s, which do not exist",
                rule.name or rule.id, ", ".join(unknown),
            )
        elif nothing_real:
            result["no_live_targets"] = True
            _LOGGER.warning(
                "rule '%s' was called but its target %s %s - "
                "nothing can have changed",
                rule.name or rule.id, target or "none", NO_LIVE_TARGETS_NOTE,
            )

        if simulate:
            result["outcome"] = "would_call"
            return result
```

The remainder of `_call` (the `config = {...}` block through the end of
the method) is unchanged — leave it exactly as it is.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_engine.py -v`
Expected: PASS — every test in the file, including the ported and new ones.

- [ ] **Step 5: Full backend suite**

Run: `uv run pytest tests/`
Expected: PASS (`test_logbook.py`'s `dry_run` assertions are on the EVENT
PAYLOAD key, which is unchanged by this task — see the docstring above —
so they still pass unmodified).

- [ ] **Step 6: Commit**

```bash
git add custom_components/shabbat_scheduler/engine.py tests/test_engine.py
git commit -m "feat: async_apply_rule gains simulate, at, and force_conditions"
```

---

### Task 7: New websocket command `rules/run_now`

**Files:**
- Modify: `custom_components/shabbat_scheduler/websocket_api.py` (imports, new `ws_run_now`, `async_register`)
- Modify: `tests/test_websocket.py` (new tests; add to `MUTATIONS`)
- Test: `tests/test_websocket.py`

**Interfaces:**
- Consumes: `engine.async_apply_rule(rule, *, simulate, at, force_conditions)`
  from Task 6, called as `async_apply_rule(rule, simulate=msg["simulate"], at=at)`
  (no `force_conditions` — `run_now` never passes it, matching the spec's
  schema, which has no `force_conditions` field).
- Produces: registers `shabbat_scheduler/rules/run_now`. Task 10
  (`rule-dialog.ts`'s Run Now button) sends this exact command shape:
  `{type: 'shabbat_scheduler/rules/run_now', rule_id, simulate, at?}`,
  and reads back `{results: list[dict]}`.

**Judgment call — merging defaults before applying.** The spec's
description says only "looks the rule up in `store`" — but every REAL fire
path (`_make_callback`'s `_fire`, `async_catch_up`) applies
`engine._merged_rules()`'s output, i.e. the rule with the shared defaults
already merged into its `target`/`data`. A raw `store.rules` entry can have
an EMPTY `target`/`data` that only resolves once merged with
`store.defaults`. Without merging here, "Run Now" on such a rule would
silently behave differently from how it really fires — the exact kind of
gap this whole feature exists to close. This task merges defaults
(`merge_defaults(store.defaults, existing)`) before calling
`async_apply_rule`, mirroring `engine._merged_rules()`'s own pattern.

**Judgment call — malformed `at`.** The spec's schema is
`vol.Optional("at"): str` with no further validation. A value that fails
`dt_util.parse_datetime` is rejected with `invalid_rule` rather than
silently treated as "no `at`", since silently ignoring a malformed value
the caller explicitly supplied would misreport what was actually run
against.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_websocket.py`:

```python
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
```

Extend `MUTATIONS` (around line 827) with a `run_now` entry:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_websocket.py -k run_now -v`
Expected: FAIL — `unknown_command`, `run_now` is not registered yet.

- [ ] **Step 3: Implement**

In `custom_components/shabbat_scheduler/websocket_api.py`, extend the
imports (line 3 area — add `datetime`) and the `.block` import (line 18):

```python
from datetime import datetime
```

```python
from .block import block_payload, conflict_warnings, merge_defaults, preview_payload
```

Add `ws_run_now` after `ws_delete` (after line 253, before `ws_defaults`):

```python
@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "shabbat_scheduler/rules/run_now",
        vol.Required("rule_id"): str,
        vol.Optional("simulate", default=True): bool,
        vol.Optional("at"): str,
    }
)
@websocket_api.async_response
async def ws_run_now(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    """Apply one rule right now, through the exact path a real fire uses.

    `simulate` defaults to True so an accidental or malformed call from a
    future client version cannot silently make a real call.
    """
    data = _entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_set_up", "Integration is not set up")
        return
    store, engine = data["store"], data["engine"]

    existing = next((r for r in store.rules if r.id == msg["rule_id"]), None)
    if existing is None:
        connection.send_error(msg["id"], "not_found", f"No rule {msg['rule_id']}")
        return

    at: datetime | None = None
    if "at" in msg:
        at = dt_util.parse_datetime(msg["at"])
        if at is None:
            connection.send_error(
                msg["id"], "invalid_rule",
                f"at is not a valid ISO 8601 datetime: {msg['at']!r}",
            )
            return

    # Merged with the shared defaults first, exactly as every real fire
    # does (`engine._merged_rules()`) - a rule whose target/data come from
    # the defaults must run_now the same way it would really fire, not
    # against its own bare, possibly-empty target.
    rule = merge_defaults(store.defaults, existing)
    results = await engine.async_apply_rule(rule, simulate=msg["simulate"], at=at)
    connection.send_result(msg["id"], {"results": results})
```

Register it in `async_register` (after `ws_delete`, before `ws_defaults`):

```python
    websocket_api.async_register_command(hass, ws_run_now)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_websocket.py -k "run_now or read_only" -v`
Expected: PASS.

- [ ] **Step 5: Full backend suite**

Run: `uv run pytest tests/`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add custom_components/shabbat_scheduler/websocket_api.py tests/test_websocket.py
git commit -m "feat: websocket command shabbat_scheduler/rules/run_now"
```

---

### Task 8: New websocket command `rules/run_day`

**Files:**
- Modify: `custom_components/shabbat_scheduler/websocket_api.py` (imports, new `ws_run_day`, `async_register`)
- Modify: `tests/test_websocket.py` (new tests; add to `MUTATIONS`)
- Test: `tests/test_websocket.py`

**Interfaces:**
- Consumes: `engine.async_apply_rule` (Task 6), `engine._merged_rules()`,
  `engine._tz()`, `engine.current_block` (all pre-existing), `resolve_rules`
  and `compute_block` from `block.py` (pre-existing).
- Produces: registers `shabbat_scheduler/rules/run_day`. Task 11
  (`simulate-dialog.ts`) sends
  `{type: 'shabbat_scheduler/rules/run_day', profile, day, simulate, force_conditions}`
  and reads back `{results: [{rule_id, results: [...]}, ...]}`.

**Judgment call — no block known at all.** `engine.current_block` can be
`None` (unreadable zmanim). The spec's pseudocode has no guard for this;
without one there is no real candle-lighting instant to anchor a
hypothetical block on. This task returns an error, wording matched to
`preview_payload`'s own `no_block` message for the identical condition:
`connection.send_error(msg["id"], "no_block", "No block could be derived
from the Jewish Calendar sensors; nothing to run.")`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_websocket.py`:

```python
async def test_run_day_simulates_the_real_current_block_by_default(
    hass, hass_ws_client, setup_scheduler
):
    await setup_scheduler([
        Rule(id="r1", profile=1, day="1", time=time(11, 0),
             action="input_boolean.turn_on", target={"entity_id": ["input_boolean.t"]}),
        Rule(id="erev1", profile=1, day="erev", time=time(9, 0),
             action="input_boolean.turn_on", target={"entity_id": ["input_boolean.t"]}),
    ])
    hass.states.async_set("input_boolean.t", "off")
    client = await hass_ws_client(hass)

    await client.send_json({
        "id": 1, "type": "shabbat_scheduler/rules/run_day",
        "profile": 1, "day": "1",
    })
    msg = await client.receive_json()

    assert msg["success"]
    ids = [item["rule_id"] for item in msg["result"]["results"]]
    assert ids == ["r1"]  # only day '1', not 'erev'
    assert msg["result"]["results"][0]["results"][0]["outcome"] == "would_call"
    assert hass.states.get("input_boolean.t").state == "off"


async def test_run_day_preserves_resolve_rules_order(
    hass, hass_ws_client, setup_scheduler
):
    await setup_scheduler([
        Rule(id="late", profile=1, day="1", time=time(20, 0), action="input_boolean.turn_on"),
        Rule(id="early", profile=1, day="1", time=time(8, 0), action="input_boolean.turn_on"),
    ])
    client = await hass_ws_client(hass)

    await client.send_json({
        "id": 1, "type": "shabbat_scheduler/rules/run_day",
        "profile": 1, "day": "1",
    })
    msg = await client.receive_json()

    assert [item["rule_id"] for item in msg["result"]["results"]] == ["early", "late"]


async def test_run_day_can_simulate_a_hypothetical_profile(
    hass, hass_ws_client, setup_scheduler
):
    """profile=3 while the real block is 1 day: a hypothetical block,
    anchored on the real candle lighting - same construction preview_payload
    uses for block_length."""
    await setup_scheduler([
        Rule(id="p3", profile=3, day="2", time=time(11, 0), action="input_boolean.turn_on"),
    ])
    client = await hass_ws_client(hass)

    await client.send_json({
        "id": 1, "type": "shabbat_scheduler/rules/run_day",
        "profile": 3, "day": "2",
    })
    msg = await client.receive_json()

    assert msg["success"]
    assert [item["rule_id"] for item in msg["result"]["results"]] == ["p3"]


async def test_run_day_force_conditions_bypasses_a_blocking_condition(
    hass, hass_ws_client, setup_scheduler
):
    await setup_scheduler([
        Rule(id="r1", profile=1, day="1", time=time(11, 0),
             action="input_boolean.turn_on",
             condition=({"condition": "state", "entity_id": "input_boolean.kids", "state": "on"},)),
    ])
    hass.states.async_set("input_boolean.kids", "off")
    client = await hass_ws_client(hass)

    await client.send_json({
        "id": 1, "type": "shabbat_scheduler/rules/run_day",
        "profile": 1, "day": "1", "force_conditions": True,
    })
    msg = await client.receive_json()

    assert msg["result"]["results"][0]["results"][0]["outcome"] == "would_call"


async def test_run_day_without_force_conditions_still_blocks(
    hass, hass_ws_client, setup_scheduler
):
    await setup_scheduler([
        Rule(id="r1", profile=1, day="1", time=time(11, 0),
             action="input_boolean.turn_on",
             condition=({"condition": "state", "entity_id": "input_boolean.kids", "state": "on"},)),
    ])
    hass.states.async_set("input_boolean.kids", "off")
    client = await hass_ws_client(hass)

    await client.send_json({
        "id": 1, "type": "shabbat_scheduler/rules/run_day",
        "profile": 1, "day": "1",
    })
    msg = await client.receive_json()

    assert msg["result"]["results"][0]["results"][0]["outcome"] == "blocked"


async def test_run_day_errors_cleanly_with_no_known_block(hass, hass_ws_client):
    entry = MockConfigEntry(domain=DOMAIN, title="Shabbat Scheduler")
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    client = await hass_ws_client(hass)

    await client.send_json({
        "id": 1, "type": "shabbat_scheduler/rules/run_day",
        "profile": 1, "day": "1",
    })
    msg = await client.receive_json()

    assert not msg["success"]
    assert msg["error"]["code"] == "no_block"
```

Extend `MUTATIONS` further with a `run_day` entry:

```python
    {"type": "shabbat_scheduler/rules/run_day", "profile": 1, "day": "1"},
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_websocket.py -k run_day -v`
Expected: FAIL — `unknown_command`.

- [ ] **Step 3: Implement**

Extend the `.block` import further (from Task 7's edit) to also bring in
`compute_block` and `resolve_rules`:

```python
from .block import (
    block_payload,
    compute_block,
    conflict_warnings,
    merge_defaults,
    preview_payload,
    resolve_rules,
)
```

Add `from datetime import datetime, timedelta` (extends Task 7's `datetime`
import).

Add `ws_run_day` right after `ws_run_now`:

```python
@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        vol.Required("type"): "shabbat_scheduler/rules/run_day",
        vol.Required("profile"): int,
        vol.Required("day"): str,
        vol.Optional("simulate", default=True): bool,
        vol.Optional("force_conditions", default=False): bool,
    }
)
@websocket_api.async_response
async def ws_run_day(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    """Run a whole day's resolved schedule right now.

    This is `resolve_rules()` - the exact function `async_refresh` calls to
    build the real schedule - followed by a loop over `async_apply_rule()` -
    the exact function `_make_callback`'s real timer closure calls. No
    parallel implementation of either decision; the only thing this command
    owns is *when* to call `async_apply_rule`: a plain sequential loop,
    right now, instead of HA's real point-in-time timer waiting for the
    real clock.
    """
    data = _entry_data(hass)
    if data is None:
        connection.send_error(msg["id"], "not_set_up", "Integration is not set up")
        return
    store, engine = data["store"], data["engine"]

    current = engine.current_block
    if current is None:
        connection.send_error(
            msg["id"], "no_block",
            "No block could be derived from the Jewish Calendar sensors; "
            "nothing to run.",
        )
        return

    profile = msg["profile"]
    if current.length == profile:
        block = current
    else:
        # A hypothetical block of the requested length, anchored on the
        # real candle lighting - exactly preview_payload's own
        # `block_length` branch (block.py), reused rather than
        # reimplemented so the two can never disagree about what a
        # hypothetical block of a given length looks like.
        block = compute_block(
            current.candle_lighting,
            current.candle_lighting.replace(hour=20, minute=0)
            + timedelta(days=int(profile)),
        )

    merged = engine._merged_rules()  # same call async_refresh already makes
    resolved = resolve_rules(merged, block, engine._tz())
    day_items = [item for item in resolved if item.rule.day == msg["day"]]

    results = []
    for item in day_items:  # in resolve_rules' own order - unchanged
        result = await engine.async_apply_rule(
            item.rule, simulate=msg["simulate"], force_conditions=msg["force_conditions"],
        )
        results.append({"rule_id": item.rule.id, "results": result})
    connection.send_result(msg["id"], {"results": results})
```

Register it in `async_register`:

```python
    websocket_api.async_register_command(hass, ws_run_day)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_websocket.py -k "run_day or read_only" -v`
Expected: PASS.

- [ ] **Step 5: Full backend suite**

Run: `uv run pytest tests/`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add custom_components/shabbat_scheduler/websocket_api.py tests/test_websocket.py
git commit -m "feat: websocket command shabbat_scheduler/rules/run_day"
```

---

### Task 9a: Remove `store.dry_run` — backend

**Files:**
- Modify: `custom_components/shabbat_scheduler/store.py` (remove field, property, setter, persistence)
- Modify: `custom_components/shabbat_scheduler/websocket_api.py:93-94` (`_state_payload`)
- Modify: `custom_components/shabbat_scheduler/__init__.py` (remove `_set_dry_run` and its registration/unregistration)
- Modify: `custom_components/shabbat_scheduler/diagnostics.py:99` (drop the `dry_run` key)
- Modify: `custom_components/shabbat_scheduler/services.yaml` (remove `set_dry_run` block)
- Modify: `custom_components/shabbat_scheduler/strings.json`, `translations/en.json`, `translations/he.json` (remove the `set_dry_run` services entry)
- Modify: `tests/conftest.py:89-107` (`setup_scheduler`'s `dry_run` kwarg)
- Modify: `tests/test_store.py`, `tests/test_migration.py`, `tests/test_diagnostics.py`, `tests/test_services.py`, `tests/test_translations.py`, `tests/test_frontend_fixture.py`
- Test: `uv run pytest tests/`

**Interfaces:**
- Consumes: nothing (Task 6 already stopped `engine.py` reading
  `self.store.dry_run` — this task removes the property those reads no
  longer use).
- Produces: `RuleStore` no longer has `.dry_run`, `.async_set_dry_run()`.
  `_state_payload` no longer includes a `dry_run` key — Task 9b (frontend)
  depends on this landing first, since it removes the TypeScript side that
  reads that key.

The `would_call` outcome VALUE is unaffected — `build_outcome`,
`OUTCOME_PRECEDENCE`, and `logbook.py` (which reads the `dry_run` key on
the EVENT payload, not on the store) are unchanged and untouched by this
task.

- [ ] **Step 1: Write the failing tests**

In `tests/test_store.py`, remove `assert store.dry_run is False` from
`test_store_starts_empty_and_disabled` (line ~38); change
`test_a_store_without_an_active_block_keeps_its_old_shape`'s assertion
(line ~106) to:

```python
    assert set(_stored(hass_storage)) == {"rules", "defaults", "enabled"}
```

Add a new test confirming an old `dry_run` key is tolerated, not migrated:

```python
async def test_a_pre_upgrade_dry_run_key_is_ignored_not_migrated(hass, hass_storage):
    """The key carried no information worth preserving - it is simply
    absent from a freshly-loaded store, never read back out."""
    hass_storage[STORAGE_KEY] = {
        "version": STORAGE_VERSION,
        "key": STORAGE_KEY,
        "data": {
            "rules": [], "defaults": {}, "enabled": True, "dry_run": True,
        },
    }
    store = RuleStore(hass)
    await store.async_load()

    assert store.enabled is True
    assert not hasattr(store, "dry_run") or "dry_run" not in vars(store)
```

Remove `"dry_run": False,`/`"dry_run": True,` from every `hass_storage[...]`
fixture dict in `tests/test_store.py` that currently includes it (lines
~126, ~146, ~227, ~249) — the key is simply absent from the fixture now,
since a store written by THIS code never writes it, and the tolerance test
above is what proves an OLD store's key is still tolerated. Remove
`assert store.dry_run is True` (line ~236). In
`test_change_listener_fires_for_enabled_and_dry_run` (line ~391), rename it
to `test_change_listener_fires_for_enabled` and remove the
`await store.async_set_dry_run(True)` line and its `len(calls) == 2`
assertion, replacing with `len(calls) == 1`.

In `tests/test_migration.py`, change `test_the_other_store_keys_survive`
(line ~121) to drop `dry_run` entirely:

```python
def test_the_other_store_keys_survive():
    data = {"rules": [], "defaults": {}, "enabled": True,
            "active_block": {"candle_lighting": "x", "havdalah": "y"}}
    out, _ = migrate_v1(data)
    assert out["enabled"] is True
    assert out["active_block"] == {"candle_lighting": "x", "havdalah": "y"}
```

In `tests/test_diagnostics.py`, remove `assert result["dry_run"] is False`
(line ~37).

In `tests/test_services.py`, remove `test_set_dry_run` (lines ~86–93)
entirely, and remove `assert hass.services.has_service(DOMAIN, "set_dry_run") is False`
from `test_services_removed_on_unload` (line ~190).

In `tests/test_translations.py`, change `SERVICES` (line 5) to:

```python
SERVICES = ("simulate", "export_yaml", "import_yaml")
```

In `tests/conftest.py`'s `setup_scheduler` fixture (lines 89–107), drop the
`dry_run` parameter and its body:

```python
    async def _setup(rules=(), defaults=None, enabled=False):
        await hass.config.async_set_time_zone("Asia/Jerusalem")
        for entity_id, state in ZMANIM.items():
            hass.states.async_set(entity_id, state)
        store = RuleStore(hass)
        await store.async_load()
        await store.async_replace_all(defaults or {}, list(rules))
        if enabled:
            # Timers are only armed while the master switch is on.
            await store.async_set_enabled(True)
        entry = MockConfigEntry(domain=DOMAIN, title="Shabbat Scheduler")
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        return entry

    return _setup
```

In `tests/test_frontend_fixture.py`, remove `dry_run=True` from the
`setup_scheduler(RULES, defaults=DEFAULTS, enabled=True, dry_run=True)`
call (the RULES set's only replay-enabled rule, `erev-salon`, is
deliberately made `skipped_stale` — it never reaches `_call`'s real-service
path during catch-up, so `dry_run=True` was never load-bearing there; it
only ever fed the now-removed `payload["dry_run"]` pin). Remove
`assert payload["enabled"] is True and payload["dry_run"] is True` and
replace with `assert payload["enabled"] is True`. Update the file's
top-of-file WHY comment (the "`enabled=True, dry_run=True`" paragraph) to
say only `enabled=True`, and drop the sentence claiming this is why
catch-up "really runs" (catch-up runs whenever `enabled` and a block are
both true, regardless of `dry_run`/`simulate`).

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_store.py tests/test_migration.py tests/test_diagnostics.py tests/test_services.py tests/test_translations.py -v`
Expected: FAIL — `store.dry_run` etc. still exist/are still required at this point (implementation not yet changed).

Actually: since this step only EDITED tests to remove assertions that
depended on the (still-present) `dry_run`, most will currently PASS except
`test_a_pre_upgrade_dry_run_key_is_ignored_not_migrated` (new) and
`test_change_listener_fires_for_enabled` (renamed/changed assertion count,
still passes since `async_set_dry_run` is still callable — skip re-running
until Step 3 makes the removal real, then re-run in Step 4 to prove the
whole set together).

- [ ] **Step 3: Implement the removal**

In `custom_components/shabbat_scheduler/store.py`: remove
`self._dry_run: bool = False` (line 206); remove the `dry_run` property
(lines 228–230); remove `self._dry_run = data.get("dry_run", False)`
(line 312); remove `"dry_run": self._dry_run,` from `async_save`'s `data`
dict (line 325); remove `async_set_dry_run` (lines 362–365).

In `custom_components/shabbat_scheduler/websocket_api.py`'s
`_state_payload` (line 94), remove `"dry_run": store.dry_run,`.

In `custom_components/shabbat_scheduler/__init__.py`: remove the
`_set_dry_run` function (lines 240–241); remove the
`hass.services.async_register(DOMAIN, "set_dry_run", _set_dry_run, ...)`
block (lines 280–283); remove `"set_dry_run"` from the tuple in
`async_unload_entry` (line 314):

```python
        for service in ("simulate", "export_yaml", "import_yaml"):
            hass.services.async_remove(DOMAIN, service)
```

In `custom_components/shabbat_scheduler/diagnostics.py`, remove
`"dry_run": store.dry_run,` (line 99).

In `custom_components/shabbat_scheduler/services.yaml`, remove the whole
`set_dry_run:` block (lines 16–25).

In `custom_components/shabbat_scheduler/strings.json` and
`translations/en.json`, remove the `"set_dry_run": {...}` entry under
`"services"`. In `translations/he.json`, remove the matching
`"set_dry_run"` entry (same key, Hebrew values) so its key SHAPE still
matches `strings.json`'s (per `test_hebrew_translation_has_the_same_shape`).

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/`
Expected: PASS — the whole Python suite, including
`tests/test_frontend_fixture.py` (which regenerates
`frontend/test/fixtures/state-payload.json` only when
`REGEN_FRONTEND_FIXTURE=1` is set — run that regeneration now since the
payload shape changed:

```bash
REGEN_FRONTEND_FIXTURE=1 uv run pytest tests/test_frontend_fixture.py
```

This rewrites the committed fixture to no longer carry a `dry_run` key —
Task 9b's frontend removal depends on this landing first.)

- [ ] **Step 5: Commit**

```bash
git add custom_components/shabbat_scheduler/store.py \
  custom_components/shabbat_scheduler/websocket_api.py \
  custom_components/shabbat_scheduler/__init__.py \
  custom_components/shabbat_scheduler/diagnostics.py \
  custom_components/shabbat_scheduler/services.yaml \
  custom_components/shabbat_scheduler/strings.json \
  custom_components/shabbat_scheduler/translations/en.json \
  custom_components/shabbat_scheduler/translations/he.json \
  tests/conftest.py tests/test_store.py tests/test_migration.py \
  tests/test_diagnostics.py tests/test_services.py tests/test_translations.py \
  tests/test_frontend_fixture.py frontend/test/fixtures/state-payload.json
git commit -m "refactor: remove store.dry_run and the set_dry_run service"
```

---

### Task 9b: Remove `dry_run` — frontend

**Files:**
- Modify: `frontend/src/types.ts:161` (`CardState.dry_run`)
- Modify: `frontend/src/strings.ts` (remove `dry_run` key, both languages)
- Modify: `frontend/src/block-header.ts` (remove `dryRun` prop, `.dry-run` button, `_toggleDryRun`)
- Modify: `frontend/src/card.ts` (remove `_onDryRun`, `.dryRun=` binding, `@shabbat-dry-run-toggle=` listener)
- Modify: `frontend/test/block-header.test.ts`, `frontend/test/card.test.ts`, `frontend/test/format.test.ts`, `frontend/test/payload-contract.test.ts`
- Test: `cd frontend && npm test && npm run typecheck`

**Interfaces:**
- Consumes: Task 9a's backend removal must land first — `state-payload.json`
  (the fixture `payload-contract.test.ts` reads) no longer carries
  `dry_run` once Task 9a's fixture regeneration runs.
- Produces: `CardState` has no `dry_run` field; `ShabbatBlockHeader` has no
  `dryRun` property, no `.dry-run` element, no `shabbat-dry-run-toggle`
  event. `button.active` CSS rule in `block-header.ts` becomes dead (its
  only remaining user, `.dry-run`, is deleted in this task) and is removed
  too.

- [ ] **Step 1: Write the failing tests**

In `frontend/test/block-header.test.ts`, remove `'disables both controls
for a read-only user'`'s `.dry-run` half (replaced already in Task 2 with
`'disables the master control for a read-only user'`, which does not
reference `.dry-run` — confirm no other test in the file queries `.dry-run`
or sets `dryRun` in the `render()` helper's default props; remove
`dryRun: false,` from that default prop object).

In `frontend/test/card.test.ts`, remove `dry_run: false,` from the `state`
factory (line ~35). In `frontend/test/format.test.ts`, remove `dry_run:
false,` from its `CardState` fixture (line ~23). In
`frontend/test/payload-contract.test.ts`, remove
`expect(header.dryRun).toBe(state.dry_run);` (line ~220).

Add one guard test to `frontend/test/card.test.ts` confirming the wiring
is gone:

```ts
  it('no longer offers a dry-run control at all', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(state());
    await el.updateComplete;
    expect(el.shadowRoot!.querySelector('shabbat-block-header')!
      .shadowRoot).toBeTruthy(); // sanity: header rendered
    const header = el.shadowRoot!.querySelector('shabbat-block-header') as any;
    await header.updateComplete;
    expect(header.shadowRoot!.querySelector('.dry-run')).toBeNull();
    expect('dryRun' in header).toBe(false);
  });
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm run typecheck`
Expected: FAIL — `types.ts` still declares `dry_run` so removing it from
the test fixtures above does not yet fail typecheck, but the NEW test
(`'no longer offers a dry-run control at all'`) fails at runtime since
`.dry-run` and `dryRun` both still exist.

Run: `cd frontend && npm test -- card.test.ts`
Expected: FAIL on the new test.

- [ ] **Step 3: Implement**

In `frontend/src/types.ts`, remove `dry_run: boolean;` from `CardState`
(line 161).

In `frontend/src/strings.ts`, remove `dry_run: 'Dry run',` (line 10) and
`dry_run: 'הרצה יבשה',` (line 84).

In `frontend/src/block-header.ts`: remove
`@property({ type: Boolean }) dryRun = false;`; remove the `button.active`
CSS rule (its only user is deleted below); remove `_toggleDryRun()`; remove
the `.dry-run` `<button>` block from `render()` (the final element in the
`.header` div).

In `frontend/src/card.ts`: remove `_onDryRun` (lines 239–242); remove
`.dryRun=${this._state.dry_run}` and `@shabbat-dry-run-toggle=${this._onDryRun}`
from the `<shabbat-block-header>` tag.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npm test && npm run typecheck`
Expected: PASS — the whole frontend suite.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/types.ts frontend/src/strings.ts frontend/src/block-header.ts \
  frontend/src/card.ts frontend/test/block-header.test.ts frontend/test/card.test.ts \
  frontend/test/format.test.ts frontend/test/payload-contract.test.ts
git commit -m "refactor: remove the dry-run toggle from the card"
```

---

### Task 10: "Run Now" button in rule-dialog.ts

**Files:**
- Modify: `frontend/src/format.ts` (new `OUTCOME_PRECEDENCE`, `foldCallResults`)
- Modify: `frontend/src/rule-dialog.ts` (button, inline confirm, result rendering)
- Modify: `frontend/src/strings.ts` (new keys, both languages)
- Modify: `frontend/src/card.ts` (new state, handler, prop/event wiring)
- Test: `frontend/test/format.test.ts`, `frontend/test/rule-dialog.test.ts`, `frontend/test/card.test.ts`

**Interfaces:**
- Consumes: `LastOutcome` type (`types.ts`, unchanged), `formatOutcome`/
  `outcomeIsBad` (`format.ts`, unchanged signatures).
- Produces: `foldCallResults(results: Record<string, unknown>[], at: string): LastOutcome`,
  exported from `format.ts` — Task 11 (`simulate-dialog.ts`) calls this
  exact function, per rule, to render `rules/run_day`'s per-rule results
  the same way. `rule-dialog.ts` dispatches a new event `dialog-run-now`
  (`detail: { rule: RuleData; simulate: boolean }`); `card.ts`'s handler
  sends `{type: 'shabbat_scheduler/rules/run_now', rule_id, simulate}` via
  its existing `_hass.callWS` (NOT `_send` — this write is not a form save,
  has no dialog-blocking `_busy` semantics of its own, and must not clear
  `_dialogError`/close the dialog on success) and stores the result on
  `@state() private _runNowResult: { ruleId: string; results: unknown[]; at: string } | null`,
  passed to the dialog as `.runNowResult=`.

Visible only when editing an existing rule (`this.rule !== null`) and
`canWrite`. Clicking opens a small inline confirm — two buttons,
"Simulate" and "Run for real" — not a separate dialog, each sending
`rules/run_now` with `simulate` set accordingly.

- [ ] **Step 1: Write the failing test for `foldCallResults`**

Add to `frontend/test/format.test.ts`:

```ts
import { foldCallResults } from '../src/format';

describe('foldCallResults', () => {
  it('reports the single result verbatim', () => {
    const result = foldCallResults(
      [{ outcome: 'would_call' }], '2026-08-25T18:00:00Z',
    );
    expect(result).toEqual({ outcome: 'would_call', at: '2026-08-25T18:00:00Z', detail: null });
  });

  it('picks the worst outcome across multiple calls, precedence-ordered', () => {
    const result = foldCallResults(
      [{ outcome: 'called' }, { outcome: 'failed', error: 'boom' }],
      '2026-08-25T18:00:00Z',
    );
    expect(result.outcome).toBe('failed');
    expect(result.detail).toBe('boom');
  });

  it('unions unknown_targets across calls', () => {
    const result = foldCallResults(
      [
        { outcome: 'called', unknown_targets: ['a.x'] },
        { outcome: 'called', unknown_targets: ['a.y'] },
      ],
      '2026-08-25T18:00:00Z',
    );
    expect(result.unknown_targets).toEqual(['a.x', 'a.y']);
  });

  it('reports unknown for an empty results list rather than throwing', () => {
    expect(foldCallResults([], '2026-08-25T18:00:00Z').outcome).toBe('unknown');
  });

  it('reads reason as detail for a blocked result, which has no error key', () => {
    const result = foldCallResults(
      [{ outcome: 'blocked', reason: 'condition 1 of 1 not met' }],
      '2026-08-25T18:00:00Z',
    );
    expect(result.detail).toBe('condition 1 of 1 not met');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- format.test.ts`
Expected: FAIL — `foldCallResults` is not exported.

- [ ] **Step 3: Implement `foldCallResults` in format.ts**

Add near the bottom of `frontend/src/format.ts`, after `formatOutcomeAt`:

```ts
/**
 * Mirrors const.py's `OUTCOME_PRECEDENCE` - see that file for why this
 * exact order matters and why the two must never drift apart.
 */
const OUTCOME_PRECEDENCE = [
  'failed', 'blocked', 'skipped_stale', 'skipped_no_replay', 'would_call', 'called',
] as const;

/**
 * One rule's per-call results (from `rules/run_now`/`rules/run_day`, never
 * durable - these calls may have been simulated) folded into the single
 * verdict `formatOutcome`/`outcomeIsBad` expect, mirroring
 * `outcome_from_results` (engine.py) client-side for exactly this display
 * purpose. `at` is the moment this response arrived, not a server-recorded
 * timestamp - a simulated run is never durably recorded, so there is no
 * server `at` to read.
 */
export function foldCallResults(
  results: Record<string, unknown>[], at: string,
): LastOutcome {
  if (results.length === 0) {
    return { outcome: 'unknown', at, detail: null };
  }
  const outcomes = new Set(results.map((r) => String(r.outcome ?? '')));
  const outcome = OUTCOME_PRECEDENCE.find((candidate) => outcomes.has(candidate)) ?? 'unknown';
  const withDetail = results.find(
    (r) => r.outcome === outcome && (r.error || r.reason),
  );
  const unknownTargets = Array.from(new Set(
    results.flatMap((r) => (r.unknown_targets as string[] | undefined) ?? []),
  ));
  return {
    outcome,
    at,
    detail: (withDetail?.error ?? withDetail?.reason ?? null) as string | null,
    unknown_targets: unknownTargets.length ? unknownTargets : undefined,
    no_live_targets: results.some((r) => r.no_live_targets === true) || undefined,
  };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- format.test.ts`
Expected: PASS.

- [ ] **Step 5: Add strings**

In `frontend/src/strings.ts`, add to both `en` and `he`:

```ts
    run_now_button: 'Run now',
    run_now_simulate: 'Simulate',
    run_now_real: 'Run for real',
```
```ts
    run_now_button: 'הרצה עכשיו',
    run_now_simulate: 'סימולציה',
    run_now_real: 'הרצה אמיתית',
```

- [ ] **Step 6: Write the failing rule-dialog.ts test**

Add to `frontend/test/rule-dialog.test.ts`:

```ts
describe('Run Now', () => {
  it('offers Run Now only for an existing rule and a writer', async () => {
    expect((await render()).shadowRoot!.querySelector('.run-now')).not.toBeNull();
    expect((await render({ rule: null })).shadowRoot!.querySelector('.run-now')).toBeNull();
    expect((await render({ canWrite: false })).shadowRoot!.querySelector('.run-now')).toBeNull();
  });

  it('opens an inline confirm with Simulate and Run for real, not a dialog', async () => {
    const el = await render();
    (el.shadowRoot!.querySelector('.run-now') as HTMLElement).click();
    await el.updateComplete;
    expect(el.shadowRoot!.querySelector('.run-simulate')).not.toBeNull();
    expect(el.shadowRoot!.querySelector('.run-real')).not.toBeNull();
  });

  it('dispatches dialog-run-now with simulate true from Simulate', async () => {
    const el = await render();
    const listener = vi.fn();
    el.addEventListener('dialog-run-now', listener);
    (el.shadowRoot!.querySelector('.run-now') as HTMLElement).click();
    await el.updateComplete;
    (el.shadowRoot!.querySelector('.run-simulate') as HTMLElement).click();
    expect((listener.mock.calls[0][0] as CustomEvent).detail).toEqual({
      rule: existing, simulate: true,
    });
  });

  it('dispatches dialog-run-now with simulate false from Run for real', async () => {
    const el = await render();
    const listener = vi.fn();
    el.addEventListener('dialog-run-now', listener);
    (el.shadowRoot!.querySelector('.run-now') as HTMLElement).click();
    await el.updateComplete;
    (el.shadowRoot!.querySelector('.run-real') as HTMLElement).click();
    expect((listener.mock.calls[0][0] as CustomEvent).detail).toEqual({
      rule: existing, simulate: false,
    });
  });

  it('renders the result inline using formatOutcome', async () => {
    const el = await render({
      runNowResult: { ruleId: 'r1', results: [{ outcome: 'would_call' }], at: '2026-08-25T18:00:00Z' },
    });
    expect(el.shadowRoot!.textContent).toContain('Would have fired');
  });

  it('does not render a result belonging to a different rule', async () => {
    const el = await render({
      runNowResult: { ruleId: 'someone-else', results: [{ outcome: 'would_call' }], at: '2026-08-25T18:00:00Z' },
    });
    expect(el.shadowRoot!.textContent).not.toContain('Would have fired');
  });
});
```

- [ ] **Step 7: Run test to verify it fails**

Run: `cd frontend && npm test -- rule-dialog.test.ts`
Expected: FAIL — `.run-now` not found.

- [ ] **Step 8: Implement rule-dialog.ts**

Add imports and a new `@state`/property:

```ts
import { foldCallResults, formatOutcome, ruleToForm } from './format';
```

```ts
  @property({ attribute: false }) runNowResult:
    { ruleId: string; results: unknown[]; at: string } | null = null;
  @state() private _runConfirmOpen = false;
```

Reset `_runConfirmOpen` in `willUpdate`'s re-seed branch (inside the
existing `if (this._seeded !== key) { ... }` block, alongside
`this._advanced = false;`):

```ts
      this._advanced = false;
      this._runConfirmOpen = false;
```

Add a handler and render additions. In the `.actions` div, right after the
`.duplicate` button block:

```ts
            ${this.canWrite && editing
              ? html`<button
                  class="run-now"
                  ?disabled=${this.busy}
                  @click=${() => { this._runConfirmOpen = !this._runConfirmOpen; }}
                >
                  ▶ ${t(this.language, 'run_now_button')}
                </button>`
              : nothing}
```

And, as a new block right after the `.actions` div closes (still inside
`.panel`, after the `</div>` that closes `.actions`):

```ts
          ${this._runConfirmOpen
            ? html`<div class="run-confirm">
                <button
                  class="run-simulate"
                  @click=${() => this._emitRunNow(true)}
                >${t(this.language, 'run_now_simulate')}</button>
                <button
                  class="run-real"
                  @click=${() => this._emitRunNow(false)}
                >${t(this.language, 'run_now_real')}</button>
              </div>`
            : nothing}
          ${this.rule !== null && this.runNowResult?.ruleId === this.rule.id
            ? html`<div class="run-now-result">
                ${foldRunNowResults(this.runNowResult).map(
                  (line) => html`<div>${line}</div>`,
                )}
              </div>`
            : nothing}
```

Add the handler and a small local helper (module scope, above the class):

```ts
function foldRunNowResults(
  result: { results: unknown[]; at: string },
): string[] {
  const outcome = foldCallResults(result.results as Record<string, unknown>[], result.at);
  return [formatOutcome(outcome)];
}
```

```ts
  private _emitRunNow(simulate: boolean) {
    this._runConfirmOpen = false;
    this.dispatchEvent(
      new CustomEvent('dialog-run-now', { detail: { rule: this.rule, simulate } }),
    );
  }
```

(`formatOutcome` is called without a language argument in
`foldRunNowResults` purely for brevity here — pass `this.language` through
instead if the dialog needs a translated result; do this by changing
`foldRunNowResults(this.runNowResult)` to
`foldRunNowResults(this.runNowResult, this.language)` and threading a
second `language?: string` parameter into the helper, calling
`formatOutcome(outcome, language)`. Do this now, not as a follow-up — the
test in Step 6 asserts on the English string, but a Hebrew-locale dialog
must not silently stay in English.)

- [ ] **Step 9: Run test to verify it passes**

Run: `cd frontend && npm test -- rule-dialog.test.ts`
Expected: PASS.

- [ ] **Step 10: Wire card.ts**

Add state and a handler:

```ts
  @state() private _runNowResult: { ruleId: string; results: unknown[]; at: string } | null = null;
```

```ts
  /**
   * Not `_send`: this write has no dialog-blocking `_busy` semantics of
   * its own and must not close the dialog or clear `_dialogError` on
   * success - it is an inline result, not a form save.
   */
  private _onRunNow = async (event: Event) => {
    const { rule, simulate } = (event as CustomEvent).detail as {
      rule: RuleData; simulate: boolean;
    };
    try {
      const response = await this._hass.callWS({
        type: 'shabbat_scheduler/rules/run_now',
        rule_id: rule.id,
        simulate,
      }) as { results: unknown[] };
      this._runNowResult = {
        ruleId: rule.id, results: response.results, at: new Date().toISOString(),
      };
    } catch (err) {
      const detail = err as { message?: string } | null;
      this._dialogError = detail?.message ?? String(err);
    }
  };
```

Reset `_runNowResult` in `_closeDialogs` and `_onRuleOpen`/`_onRuleAdd`
(alongside the existing `_dialogError = null;` resets in each), and pass
the prop/listener on `<shabbat-rule-dialog>`:

```ts
              .runNowResult=${this._runNowResult}
              @dialog-run-now=${this._onRunNow}
```

- [ ] **Step 11: Write and run the card.ts integration test**

Add to `frontend/test/card.test.ts`, INSIDE the existing
`describe('authoring', () => { ... })` block so `withRules()` is in scope
(same placement note as Task 5, Step 6):

```ts
  it('sends run_now and shows the inline result, without closing the dialog', async () => {
    const { hass, send } = fakeHass();
    hass.callWS = vi.fn(async () => ({ results: [{ outcome: 'would_call' }] }));
    const el = await mount(hass);
    send(withRules());
    el._editing = withRules().rules[0];
    await el.updateComplete;

    el.shadowRoot!.querySelector('shabbat-rule-dialog')!.dispatchEvent(
      new CustomEvent('dialog-run-now', {
        detail: { rule: withRules().rules[0], simulate: true },
      }),
    );
    await flush();
    await el.updateComplete;

    expect(hass.callWS).toHaveBeenCalledWith({
      type: 'shabbat_scheduler/rules/run_now',
      rule_id: withRules().rules[0].id,
      simulate: true,
    });
    expect(el.shadowRoot!.querySelector('shabbat-rule-dialog')).not.toBeNull();
  });
```

- [ ] **Step 12: Run the full frontend suite and typecheck**

Run: `cd frontend && npm test && npm run typecheck`
Expected: PASS.

- [ ] **Step 13: Commit**

```bash
git add frontend/src/format.ts frontend/src/rule-dialog.ts frontend/src/strings.ts \
  frontend/src/card.ts frontend/test/format.test.ts frontend/test/rule-dialog.test.ts \
  frontend/test/card.test.ts
git commit -m "feat: Run Now button in the rule dialog"
```

---

### Task 11: New `simulate-dialog.ts`

**Files:**
- Create: `frontend/src/simulate-dialog.ts`
- Modify: `frontend/src/block-header.ts` (new icon next to the gear)
- Modify: `frontend/src/strings.ts` (new keys, both languages)
- Modify: `frontend/src/card.ts` (mount/wire the dialog)
- Test: `frontend/test/simulate-dialog.test.ts` (new), `frontend/test/block-header.test.ts`, `frontend/test/card.test.ts`

**Interfaces:**
- Consumes: `foldCallResults`/`formatOutcome` from `format.ts` (Task 10).
  Calls the pre-existing `shabbat_scheduler/preview` command (read-only,
  unchanged) and the new `shabbat_scheduler/rules/run_day` command
  (Task 8).
- Produces: `<shabbat-simulate-dialog>`, opened from `block-header.ts` via
  a new `simulate-open` event (`bubbles: true, composed: true`, no
  detail). No other task in this plan consumes anything from this file.

**Judgment call — day-filtering the preview list.** `preview`'s `when` is
an ISO datetime resolved against the whole chosen block; the mapping from
a specific `when` back to a day NAME ('erev' vs '1' vs '2'...) is
block.py's own logic and is not re-derived client-side to avoid a second,
possibly-drifting implementation of it. The preview panel therefore shows
**every rule in the previewed block, in schedule order** (still an honest
answer to "what would run"), while the separate day picker only selects
`run_day`'s own `day` argument for the Simulate/Run buttons below it.

**Judgment call — no shared sub-component with `clone-dialog.ts`.** The
spec allows but does not mandate sharing the profile/day picker as an
internal sub-component with `clone-dialog.ts` (Task 15). This task
implements its own plain `<select>` pair (matching `block-header.ts`'s
existing plain-button precedent for the 1d/2d/3d chips — a small fixed
local enumeration, not an HA domain concept needing `ha-selector`), kept
independent of Task 15 so the two tasks have no ordering dependency.

- [ ] **Step 1: Write the failing test**

Create `frontend/test/simulate-dialog.test.ts`:

```ts
import { describe, expect, it, vi } from 'vitest';
import '../src/simulate-dialog';

function fakeHass(previewResult: unknown, runResult: unknown) {
  const callWS = vi.fn(async (message: any) => {
    if (message.type === 'shabbat_scheduler/preview') return previewResult;
    return runResult;
  });
  return { callWS };
}

async function render(hass: unknown, props: Record<string, unknown> = {}) {
  const el = document.createElement('shabbat-simulate-dialog') as HTMLElement &
    Record<string, any>;
  Object.assign(el, { hass, language: 'en', ...props });
  document.body.appendChild(el);
  await el.updateComplete;
  await el.updateComplete; // second tick: the preview load is async
  return el;
}

describe('shabbat-simulate-dialog', () => {
  it('loads and renders the preview for the default 1-day profile on connect', async () => {
    const hass = fakeHass(
      { profile: 1, rules: [{ when: '2026-08-15T11:00:00+03:00', rule_id: 'r1', name: 'Morning', action: 'a.b', target: {}, data: {} }], conflicts: [], warnings: [] },
      { results: [] },
    );
    const el = await render(hass);
    expect(hass.callWS).toHaveBeenCalledWith({ type: 'shabbat_scheduler/preview', block_length: 1 });
    expect(el.shadowRoot!.textContent).toContain('Morning');
  });

  it('reloads the preview when the profile picker changes', async () => {
    const hass = fakeHass({ profile: 3, rules: [], conflicts: [], warnings: [] }, { results: [] });
    const el = await render(hass);
    const select = el.shadowRoot!.querySelector('select.profile') as HTMLSelectElement;
    select.value = '3';
    select.dispatchEvent(new Event('change'));
    await el.updateComplete;
    await el.updateComplete;
    expect(hass.callWS).toHaveBeenLastCalledWith({ type: 'shabbat_scheduler/preview', block_length: 3 });
  });

  it('offers a day picker scoped to the selected profile', async () => {
    const hass = fakeHass({ profile: 1, rules: [], conflicts: [], warnings: [] }, { results: [] });
    const el = await render(hass, {});
    const select = el.shadowRoot!.querySelector('select.profile') as HTMLSelectElement;
    select.value = '2';
    select.dispatchEvent(new Event('change'));
    await el.updateComplete;
    await el.updateComplete;
    const days = [...el.shadowRoot!.querySelectorAll('select.day option')].map(
      (o) => (o as HTMLOptionElement).value,
    );
    expect(days).toEqual(['erev', '1', '2']);
  });

  it('sends run_day with force_conditions from the toggle', async () => {
    const hass = fakeHass({ profile: 1, rules: [], conflicts: [], warnings: [] }, { results: [] });
    const el = await render(hass);
    (el.shadowRoot!.querySelector('ha-selector.force-conditions') as any).dispatchEvent(
      new CustomEvent('value-changed', { detail: { value: true } }),
    );
    (el.shadowRoot!.querySelector('button.run-simulate') as HTMLElement).click();
    await el.updateComplete;
    expect(hass.callWS).toHaveBeenCalledWith({
      type: 'shabbat_scheduler/rules/run_day',
      profile: 1, day: 'erev', simulate: true, force_conditions: true,
    });
  });

  it('renders one result row per rule, outcome formatted', async () => {
    const hass = fakeHass(
      { profile: 1, rules: [], conflicts: [], warnings: [] },
      { results: [{ rule_id: 'r1', results: [{ outcome: 'would_call' }] }] },
    );
    const el = await render(hass);
    (el.shadowRoot!.querySelector('button.run-simulate') as HTMLElement).click();
    await el.updateComplete;
    expect(el.shadowRoot!.textContent).toContain('Would have fired');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- simulate-dialog.test.ts`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Implement simulate-dialog.ts**

Create `frontend/src/simulate-dialog.ts`:

```ts
import { LitElement, css, html, nothing } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { foldCallResults, formatOutcome } from './format';
import { t } from './strings';
import type { Hass } from './types';

interface PreviewRule {
  when: string;
  rule_id: string;
  name: string | null;
  action: string;
  target: Record<string, unknown>;
  data: Record<string, unknown>;
}

interface PreviewResponse {
  profile: number | null;
  rules: PreviewRule[];
  conflicts: unknown[];
  warnings: { kind: string; message?: string }[];
}

function daysFor(length: number): string[] {
  const days = ['erev'];
  for (let i = 1; i <= length; i += 1) days.push(String(i));
  return days;
}

@customElement('shabbat-simulate-dialog')
export class ShabbatSimulateDialog extends LitElement {
  @property({ attribute: false }) hass: Hass | null = null;
  @property() language = 'en';

  @state() private _profile = 1;
  @state() private _day = 'erev';
  @state() private _forceConditions = false;
  @state() private _preview: PreviewResponse | null = null;
  @state() private _busy = false;
  @state() private _error: string | null = null;
  @state() private _results: { ruleId: string; results: unknown[] }[] | null = null;

  static override styles = css`
    .sheet {
      position: fixed; inset: 0; display: flex; align-items: center;
      justify-content: center; background: rgba(0, 0, 0, 0.4); z-index: 10;
    }
    .panel {
      background: var(--card-background-color, #fff);
      color: var(--primary-text-color, #111);
      border-radius: 12px; padding: 16px;
      inline-size: min(28rem, 92vw); max-block-size: 88vh; overflow: auto;
    }
    h2 { margin-block: 0 12px; font-size: 1.1em; }
    .field { display: flex; align-items: center; gap: 12px; margin-block: 8px; }
    .field label { min-inline-size: 9em; }
    select { font: inherit; padding-block: 4px; padding-inline: 6px; flex: 1; }
    .row {
      padding-block: 4px; font-size: 0.9em;
      border-block-end: 1px solid var(--divider-color, #e0e0e0);
    }
    .error { color: var(--error-color, #d64545); margin-block: 8px; font-size: 0.9em; }
    .actions {
      display: flex; gap: 8px; justify-content: flex-end;
      flex-wrap: wrap; margin-block-start: 16px;
    }
    button {
      font: inherit; padding-block: 6px; padding-inline: 12px;
      border-radius: 6px; border: 1px solid var(--divider-color, #e0e0e0);
      background: var(--card-background-color, #fff); color: inherit; cursor: pointer;
    }
    button[disabled] { opacity: 0.5; cursor: not-allowed; }
  `;

  override connectedCallback() {
    super.connectedCallback();
    void this._loadPreview();
  }

  private async _loadPreview() {
    if (this.hass === null) return;
    this._busy = true;
    try {
      this._preview = (await this.hass.callWS({
        type: 'shabbat_scheduler/preview', block_length: this._profile,
      })) as PreviewResponse;
    } catch (err) {
      const detail = err as { message?: string } | null;
      this._error = detail?.message ?? String(err);
    } finally {
      this._busy = false;
    }
  }

  /**
   * Every rule in the previewed block, in schedule order - NOT filtered to
   * the selected day. `preview`'s `when` is a resolved datetime; mapping it
   * back to a day NAME ('erev'/'1'/'2'...) is block.py's own logic, and is
   * not re-derived here to avoid a second, possibly-drifting
   * implementation of it. The separate day picker below only selects
   * `run_day`'s own `day` argument.
   */
  private _previewRules(): PreviewRule[] {
    return this._preview?.rules ?? [];
  }

  private async _run(simulate: boolean) {
    if (this.hass === null) return;
    this._busy = true;
    this._error = null;
    try {
      const response = (await this.hass.callWS({
        type: 'shabbat_scheduler/rules/run_day',
        profile: this._profile,
        day: this._day,
        simulate,
        force_conditions: this._forceConditions,
      })) as { results: { rule_id: string; results: unknown[] }[] };
      this._results = response.results.map(
        (r) => ({ ruleId: r.rule_id, results: r.results }),
      );
    } catch (err) {
      const detail = err as { message?: string } | null;
      this._error = detail?.message ?? String(err);
    } finally {
      this._busy = false;
    }
  }

  private _dayLabel(day: string): string {
    return day === 'erev' ? t(this.language, 'erev') : `${t(this.language, 'day')} ${day}`;
  }

  override render() {
    return html`
      <div class="sheet" @click=${(event: Event) => {
        if (event.target === event.currentTarget) {
          this.dispatchEvent(new CustomEvent('dialog-close'));
        }
      }}>
        <div class="panel">
          <h2>${t(this.language, 'simulate_title')}</h2>
          ${this._error !== null ? html`<div class="error">${this._error}</div>` : nothing}

          <div class="field">
            <label>${t(this.language, 'simulate_profile')}</label>
            <select
              class="profile"
              .value=${String(this._profile)}
              @change=${(event: Event) => {
                this._profile = Number((event.target as HTMLSelectElement).value);
                if (!daysFor(this._profile).includes(this._day)) this._day = 'erev';
                void this._loadPreview();
              }}
            >
              ${[1, 2, 3].map((p) => html`<option value=${p}>${p}d</option>`)}
            </select>
          </div>
          <div class="field">
            <label>${t(this.language, 'simulate_day')}</label>
            <select
              class="day"
              .value=${this._day}
              @change=${(event: Event) => {
                this._day = (event.target as HTMLSelectElement).value;
              }}
            >
              ${daysFor(this._profile).map(
                (day) => html`<option value=${day}>${this._dayLabel(day)}</option>`,
              )}
            </select>
          </div>
          <div class="field">
            <label>${t(this.language, 'simulate_force_conditions')}</label>
            <ha-selector
              class="force-conditions"
              .hass=${this.hass}
              .selector=${{ boolean: {} }}
              .value=${this._forceConditions}
              @value-changed=${(event: CustomEvent) => {
                this._forceConditions = Boolean(event.detail?.value);
              }}
            ></ha-selector>
          </div>

          ${this._preview !== null
            ? html`<div class="preview">
                ${this._previewRules().map(
                  (rule) => html`<div class="row">
                    ${rule.when.slice(11, 16)} — ${rule.name ?? rule.action}
                  </div>`,
                )}
              </div>`
            : nothing}

          ${this._results !== null
            ? html`<div class="results">
                ${this._results.map((r) => {
                  const outcome = foldCallResults(
                    r.results as Record<string, unknown>[], new Date().toISOString(),
                  );
                  return html`<div class="row">
                    ${r.ruleId}: ${formatOutcome(outcome, this.language)}
                  </div>`;
                })}
              </div>`
            : nothing}

          <div class="actions">
            <button @click=${() => this.dispatchEvent(new CustomEvent('dialog-close'))}>
              ${t(this.language, 'cancel')}
            </button>
            <button
              class="run-simulate"
              ?disabled=${this._busy}
              @click=${() => this._run(true)}
            >${t(this.language, 'simulate_this_day')}</button>
            <button
              class="run-real"
              ?disabled=${this._busy}
              @click=${() => this._run(false)}
            >${t(this.language, 'simulate_run_for_real')}</button>
          </div>
        </div>
      </div>
    `;
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- simulate-dialog.test.ts`
Expected: PASS.

- [ ] **Step 5: Add strings**

In `frontend/src/strings.ts`, add to both `en` and `he`:

```ts
    simulate_title: 'Test your schedule',
    simulate_profile: 'Block length',
    simulate_day: 'Day',
    simulate_force_conditions: 'Force conditions to pass',
    simulate_this_day: 'Simulate this day',
    simulate_run_for_real: 'Run this day for real',
```
```ts
    simulate_title: 'בדיקת הלוח',
    simulate_profile: 'אורך הבלוק',
    simulate_day: 'יום',
    simulate_force_conditions: 'לעקוף תנאים',
    simulate_this_day: 'סימולציה ליום זה',
    simulate_run_for_real: 'הרצה אמיתית ליום זה',
```

- [ ] **Step 6: Add the icon to block-header.ts and wire card.ts**

In `frontend/src/block-header.ts`, add a new icon button next to `.gear`
(inside the `this.canWrite ? html\`...\`` block, right after it):

```ts
        ${this.canWrite
          ? html`<button
              class="gear"
              @click=${() => this.dispatchEvent(new CustomEvent('defaults-open'))}
            >
              ⚙
            </button>`
          : nothing}
        ${this.canWrite
          ? html`<button
              class="simulate-open"
              aria-label=${t(this.language, 'simulate_title')}
              @click=${() =>
                this.dispatchEvent(
                  new CustomEvent('simulate-open', { bubbles: true, composed: true }),
                )}
            >
              ▶
            </button>`
          : nothing}
```

Reuse the `.gear` CSS rule for `.simulate-open` too (`.gear, .simulate-open { border: none; background: none; cursor: pointer; font-size: 1.1em; }`).

In `frontend/src/card.ts`, import the new element, add state, and wire it:

```ts
import './simulate-dialog';
```

```ts
  @state() private _simulateOpen = false;
```

Add `_simulateOpen = false;` to `_closeDialogs`, and add
`@simulate-open=${() => { this._simulateOpen = true; }}` to `<ha-card>`
(alongside `@rule-open`/`@rule-toggle-enabled` from earlier tasks). Add the
dialog to the render tree, alongside the other conditionally-mounted
dialogs:

```ts
        ${this._simulateOpen
          ? html`<shabbat-simulate-dialog
              .hass=${this._hass}
              .language=${this._language}
              @dialog-close=${() => { this._simulateOpen = false; }}
            ></shabbat-simulate-dialog>`
          : nothing}
```

- [ ] **Step 7: Write and run the block-header.ts/card.ts tests**

Add to `frontend/test/block-header.test.ts`:

```ts
  it('offers the simulate icon to a writer and not to a reader', async () => {
    expect((await render({ canWrite: true })).shadowRoot!.querySelector('.simulate-open'))
      .not.toBeNull();
    expect((await render({ canWrite: false })).shadowRoot!.querySelector('.simulate-open'))
      .toBeNull();
  });

  it('dispatches simulate-open when the icon is used', async () => {
    const el = await render({ canWrite: true });
    const listener = vi.fn();
    el.addEventListener('simulate-open', listener);
    (el.shadowRoot!.querySelector('.simulate-open') as HTMLElement).click();
    expect(listener).toHaveBeenCalledOnce();
  });
```

Add to `frontend/test/card.test.ts`:

```ts
  it('opens the simulate dialog from the header icon', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(state());
    await el.updateComplete;

    el.shadowRoot!.querySelector('shabbat-block-header')!.dispatchEvent(
      new CustomEvent('simulate-open', { bubbles: true, composed: true }),
    );
    await el.updateComplete;

    expect(el.shadowRoot!.querySelector('shabbat-simulate-dialog')).not.toBeNull();
  });
```

Run: `cd frontend && npm test && npm run typecheck`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/simulate-dialog.ts frontend/src/block-header.ts frontend/src/strings.ts \
  frontend/src/card.ts frontend/test/simulate-dialog.test.ts frontend/test/block-header.test.ts \
  frontend/test/card.test.ts
git commit -m "feat: simulate-dialog.ts for testing a whole day's schedule"
```

---

### Task 12: Docs — README and known-behaviours.md for Part 2

**Files:**
- Modify: `README.md:16-20` (screenshot caption), `84-91` (Design commitments), `103-120` (card description), `147-153` (Services)
- Modify: `docs/known-behaviours.md` (new entry, appended)
- Test: none (docs-only; `tests/test_translations.py`/packaging tests are
  unaffected since neither reads README or known-behaviours.md)

**Interfaces:** none — pure documentation, no code.

- [ ] **Step 1: Update the README**

Replace the screenshot caption (lines 16–20):

```markdown
![The card showing a real, resolved schedule](docs/images/card-screenshot.png)

*(The master switch itself starts off on every fresh install; see step 3
below for why.)*
```

Replace the "Safe by default" line's neighbour in "Design commitments"
(the bullet list at lines 71–91) — the dry-run bullet does not exist as
its own bullet (it was folded into "Reports what happened, honestly"),
so add a new bullet after "Replay is opt-in, off by default":

```markdown
- **Testable on demand, without waiting for Shabbat.** Every rule has a
  Run Now button (Simulate, or run for real); every day's whole resolved
  schedule can be run the same way from the header's ▶ icon. Both reuse
  the exact code path a real fire uses - `resolve_rules()` then
  `async_apply_rule()` - so what you see is what would really happen, not
  a separate approximation of it. A simulated run is never recorded or
  logged; it is a live-only answer to "would this actually work?".
```

In "The card" section (around line 118–120), replace:

```markdown
The card shows only the rules matching the coming block's length, because
rules are authored per profile - a 3-day chag's rules are not shown on a
plain Shabbat.
```

with (same paragraph, `master switch and the dry-run toggle` corrected):

```markdown
The header carries the master switch, the shared-defaults gear, and a ▶
icon that opens a dialog for testing a whole day's schedule at once - all
three are disabled for non-admin users, who can still read the whole
schedule.

The card shows only the rules matching the coming block's length, because
rules are authored per profile - a 3-day chag's rules are not shown on a
plain Shabbat.
```

Add a "Testing your rules" subsection under Quick Start, right after
step 5 (`## Quick start`'s numbered list ends around line 55, before
`## Terminology`):

```markdown
### Testing your rules

You do not have to wait for a real Shabbat to find out whether a rule
works. Open any rule and press **Run now** for an inline choice: Simulate
(reports what would happen, calls nothing) or Run for real. To test a
whole day's schedule at once - in order, exactly as it would really run -
use the ▶ icon in the header, which also lets you force every condition
to pass so you can see past a guard that is currently blocking. Neither
path changes any real timer: they run the exact same
`resolve_rules()` → `async_apply_rule()` path a real fire uses, on demand,
any day of the week.
```

In "Services" (lines 147–153), remove the `set_dry_run` bullet:

```markdown
## Services

- `shabbat_scheduler.simulate` - resolve a block with no side effects. Answers
  "what happens this Shabbat?" and "what happens on a 3-day chag?".
- `shabbat_scheduler.export_yaml` - dump the whole rule set.
- `shabbat_scheduler.import_yaml` - replace the whole rule set.
```

- [ ] **Step 2: Add the known-behaviours.md entry**

Append a new section to `docs/known-behaviours.md`, matching the file's
own established style (a heading, prose, references to the actual test
names and code):

```markdown
## Dry run is gone; verification is now on-demand

The persisted `store.dry_run` flag - a standing toggle that made every
REAL scheduled fire report `would_call` instead of calling - is removed.
Two reasons, both from actually trying to use it: it only ever exercised
a real Shabbat (there was no way to prove a rule worked except living
through one with the toggle on), and it produced no visible proof
anything had worked even then - just an absence of real side effects,
indistinguishable from a rule that silently did nothing at all.

In its place: `engine.async_apply_rule` takes an optional `simulate`
keyword (behaving exactly as the old flag did at the point of the real
service call), plus `at` (evaluate `sun`/`time` conditions as though a
given moment were now) and `force_conditions` (skip condition evaluation
entirely). Two new websocket commands - `rules/run_now` (one rule) and
`rules/run_day` (a whole day, in `resolve_rules()`'s own order) - expose
these on demand, from the rule dialog's Run Now button and the header's
new simulate dialog respectively. Both reuse the exact code path a real
fire uses; neither is a second, parallel implementation of "what would
this rule do".

The critical difference from the old flag: a simulated run is never
recorded to a rule's `last_outcome`, never pushed to the logbook, and
never fires `SIGNAL_RULES_CHANGED` - see
`test_simulate_never_records_a_durable_outcome` and
`test_simulate_does_not_signal_rules_changed` in `tests/test_engine.py`.
It did not really happen, and the rest of the system must not be told
otherwise. The `would_call` outcome VALUE itself, and everywhere it
renders (`format.ts`, `rule-row.ts`, the logbook), is unchanged - only
what TRIGGERS it changed, from a standing flag to an explicit per-call
choice.

`EVENT_RULE_APPLIED`/`EVENT_RULE_COMPLETED` still carry a `dry_run` key in
their payload, sourced from `simulate` rather than `self.store.dry_run` -
the key NAME is kept for backward compatibility with anything already
listening on the event bus, even though the internal flag it used to read
is gone.

`at`'s honest limit: HA's own `sun`/`time` condition helpers
(`homeassistant.helpers.condition.time`,
`homeassistant.components.sun.condition.sun`) read the real clock
directly and accept no override argument of their own - verified against
the installed 2026.8.2. `engine._check_at_scoped` works around this by
substituting `dt_util.now`/`dt_util.utcnow` for the duration of one
synchronous condition check, restored immediately after - the same
technique `freezegun` uses, without adding it as a runtime dependency.
Every OTHER condition type (`state`, `numeric_state`, `template`, ...)
still reads real state when `at` is given: `at` only ever affects
`sun`/`time`, and is a documented no-op for anything else, not a silent
pretence of universality.
```

- [ ] **Step 3: Verify no test depends on the removed README/known-behaviours text**

Run: `uv run pytest tests/test_translations.py tests/test_packaging.py`
Expected: PASS (neither file reads README.md or known-behaviours.md; this
step is a sanity check, not a real dependency).

- [ ] **Step 4: Commit**

```bash
git add README.md docs/known-behaviours.md
git commit -m "docs: replace dry-run docs with Run Now / Simulate"
```

---

### Task 13: `_cloneRules` composition in card.ts

**Files:**
- Modify: `frontend/src/card.ts` (new private method `_cloneRules`, new `CloneReport` type)
- Test: `frontend/test/clone.test.ts` (new)

**Interfaces:**
- Consumes: `card.ts`'s existing `_send` (`_hass.callWS` wrapper that sets
  `_busy`/`_dialogError`) and `this._state.rules`.
- Produces:
  `private async _cloneRules(sourceRuleIds: string[], targetProfile: number, targetDay: string, mode: 'extend' | 'overwrite'): Promise<CloneReport>`
  where `CloneReport = { landed: string[]; failed: string[]; error: string | null }`.
  Task 15 (`clone-dialog.ts` + card.ts wiring) calls this method — see the
  judgment call below for exactly how.

**Judgment call — `_cloneRules` is a single-day primitive; a profile-scope
clone calls it once per matching day.** The spec's literal signature
(`_cloneRules(sourceRuleIds, targetProfile, targetDay, mode)`) rewrites
EVERY source rule's `day` to the SAME `targetDay` — this only makes sense
for a day-to-day clone. The spec's own "Day-name matching (profile-to-
profile clone)" section, though, describes a DIFFERENT scheme: each source
rule keeps its OWN day name, matched day-by-day against the target
profile's valid days, skipping any day the target does not have. These two
parts of the spec are only consistent if `_cloneRules` is read as the
single-source-day-to-single-target-day primitive, and a profile-scope
clone is composed by calling it once per day name common to both
profiles — which is exactly what this task implements, and what Task 15's
orchestration (`_cloneTargetDays`) builds on top of it. This task's own
tests exercise `_cloneRules` only at the single-day granularity the spec's
literal signature describes; Task 15's tests cover the profile-scope
day-by-day composition.

- [ ] **Step 1: Write the failing tests**

Create `frontend/test/clone.test.ts`:

```ts
import { describe, expect, it, vi } from 'vitest';
import '../src/card';
import type { CardState, RuleData } from '../src/types';
import { fakeHass, mount } from './helpers';

const rule = (over: Partial<RuleData> = {}): RuleData => ({
  id: 'a', profile: 1, day: 'erev', time: '11:00:00',
  action: 'climate.turn_on', target: { entity_id: ['climate.a'] },
  data: {}, condition: [], replay: { enabled: false },
  name: null, icon: null, enabled: true, color: null,
  last_outcome: null, ...over,
});

const state = (over: Partial<CardState> = {}): CardState => ({
  defaults: {}, rules: [], enabled: false, warnings: [],
  master_entity_id: 'switch.master',
  block: {
    length: 1, candle_lighting: '2026-08-14T18:44:00+03:00',
    havdalah: '2026-08-15T20:01:00+03:00',
    dates: { erev: '2026-08-14', '1': '2026-08-15' },
  },
  ...over,
} as CardState);

describe('_cloneRules', () => {
  it('creates one rule per source id, day and profile rewritten to the target', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(state({ rules: [rule({ id: 'a' }), rule({ id: 'b', time: '12:00:00' })] }));
    await el.updateComplete;

    await (el as any)._cloneRules(['a', 'b'], 2, '1', 'extend');

    expect(hass.callWS).toHaveBeenCalledTimes(2);
    const calls = hass.callWS.mock.calls.map((c: any) => c[0]);
    expect(calls.every((c: any) => c.type === 'shabbat_scheduler/rules/create')).toBe(true);
    expect(calls[0].rule.day).toBe('1');
    expect(calls[0].rule.profile).toBe(2);
    expect(calls[1].rule.time).toBe('12:00:00');
  });

  it('deletes every rule on the target day first in overwrite mode, before creating', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(state({
      rules: [
        rule({ id: 'a' }), // source
        rule({ id: 'existing1', profile: 2, day: '1' }), // to be deleted
        rule({ id: 'existing2', profile: 2, day: '1' }), // to be deleted
      ],
    }));
    await el.updateComplete;

    await (el as any)._cloneRules(['a'], 2, '1', 'overwrite');

    const calls = hass.callWS.mock.calls.map((c: any) => c[0]);
    const deletes = calls.filter((c: any) => c.type === 'shabbat_scheduler/rules/delete');
    const creates = calls.filter((c: any) => c.type === 'shabbat_scheduler/rules/create');
    expect(deletes.map((d: any) => d.rule_id).sort()).toEqual(['existing1', 'existing2']);
    expect(creates).toHaveLength(1);
    // Deletes strictly before creates - never interleaved.
    const lastDeleteIndex = calls.lastIndexOf(deletes[deletes.length - 1]);
    const firstCreateIndex = calls.indexOf(creates[0]);
    expect(lastDeleteIndex).toBeLessThan(firstCreateIndex);
  });

  it('does not delete anything in extend mode, only creates', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(state({
      rules: [rule({ id: 'a' }), rule({ id: 'existing', profile: 2, day: '1' })],
    }));
    await el.updateComplete;

    await (el as any)._cloneRules(['a'], 2, '1', 'extend');

    const calls = hass.callWS.mock.calls.map((c: any) => c[0]);
    expect(calls.some((c: any) => c.type === 'shabbat_scheduler/rules/delete')).toBe(false);
  });

  it('stops issuing creates after the first rejection and reports exactly what landed', async () => {
    const { hass, send } = fakeHass();
    let call = 0;
    hass.callWS = vi.fn(async (message: any) => {
      call += 1;
      if (message.type === 'shabbat_scheduler/rules/create' && call === 2) {
        throw { message: 'rejected' };
      }
      return {};
    });
    const el = await mount(hass);
    send(state({ rules: [rule({ id: 'a' }), rule({ id: 'b' }), rule({ id: 'c' })] }));
    await el.updateComplete;

    const report = await (el as any)._cloneRules(['a', 'b', 'c'], 2, '1', 'extend');

    expect(report.landed).toEqual(['a']);
    expect(report.failed).toEqual(['b', 'c']);
    expect(report.error).toBe('rejected');
    // Only 2 creates attempted (a succeeded, b failed) - c never attempted.
    const creates = hass.callWS.mock.calls.filter(
      (c: any) => c[0].type === 'shabbat_scheduler/rules/create',
    );
    expect(creates).toHaveLength(2);
  });

  it('stops before any create when overwrite mode fails to clear the target', async () => {
    const { hass, send } = fakeHass();
    hass.callWS = vi.fn(async (message: any) => {
      if (message.type === 'shabbat_scheduler/rules/delete') throw { message: 'delete failed' };
      return {};
    });
    const el = await mount(hass);
    send(state({ rules: [rule({ id: 'a' }), rule({ id: 'existing', profile: 2, day: '1' })] }));
    await el.updateComplete;

    const report = await (el as any)._cloneRules(['a'], 2, '1', 'overwrite');

    expect(report.landed).toEqual([]);
    expect(report.failed).toEqual(['a']);
    const creates = hass.callWS.mock.calls.filter(
      (c: any) => c[0].type === 'shabbat_scheduler/rules/create',
    );
    expect(creates).toHaveLength(0);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- clone.test.ts`
Expected: FAIL — `_cloneRules` does not exist.

- [ ] **Step 3: Implement**

Add to `frontend/src/card.ts`, near `formToCreate`'s import (extend the
existing `import { buildGroups, formToChanges, formToCreate, isPreview } from './format';`
— no new import needed, `_cloneRules` builds its own payload inline since
it needs `day`/`profile` rewritten to the TARGET, unlike `formToCreate`
which stamps the CURRENT profile):

```ts
export interface CloneReport {
  landed: string[];
  failed: string[];
  error: string | null;
}
```

(Place this `export interface` at module scope, near `CardConfig`.)

Add the private method to the `ShabbatSchedulerCard` class, near
`_onDuplicate`:

```ts
  /** Every field `rules/create` accepts for a clone, everything but `id`. */
  private _cloneCreatePayload(
    rule: RuleData, targetProfile: number, targetDay: string,
  ): Record<string, unknown> {
    return {
      day: targetDay,
      profile: targetProfile,
      time: rule.time,
      action: rule.action,
      target: rule.target,
      data: rule.data,
      condition: rule.condition,
      replay: rule.replay,
      name: rule.name,
      icon: rule.icon,
      color: rule.color,
      enabled: rule.enabled,
    };
  }

  /**
   * Composes a clone of `sourceRuleIds` onto `{targetProfile, targetDay}`
   * from the existing `rules/create` + `rules/delete` commands - the
   * server already assigns a fresh id on create, so there is no
   * id-collision case to handle and no new backend command.
   *
   * This is a SINGLE-DAY primitive: every rule in `sourceRuleIds` lands on
   * the ONE `targetDay` given. A profile-scope clone (every day of one
   * profile onto every matching day of another) is composed by calling
   * this once per day name common to both profiles - see
   * `_cloneTargetDays`, which `_onCloneConfirm` uses.
   */
  private async _cloneRules(
    sourceRuleIds: string[],
    targetProfile: number,
    targetDay: string,
    mode: 'extend' | 'overwrite',
  ): Promise<CloneReport> {
    if (mode === 'overwrite') {
      const toDelete = (this._state?.rules ?? []).filter(
        (rule) => rule.profile === targetProfile && rule.day === targetDay,
      );
      for (const rule of toDelete) {
        const ok = await this._send({
          type: 'shabbat_scheduler/rules/delete', rule_id: rule.id,
        });
        if (!ok) {
          return {
            landed: [], failed: sourceRuleIds,
            error: this._dialogError ?? 'Could not clear the target day.',
          };
        }
      }
    }

    const sourceRules = this._state?.rules ?? [];
    const landed: string[] = [];
    for (const sourceId of sourceRuleIds) {
      const source = sourceRules.find((rule) => rule.id === sourceId);
      if (source === undefined) continue; // deleted since the dialog opened
      const ok = await this._send({
        type: 'shabbat_scheduler/rules/create',
        rule: this._cloneCreatePayload(source, targetProfile, targetDay),
      });
      if (!ok) {
        return {
          landed,
          failed: sourceRuleIds.slice(landed.length),
          error: this._dialogError,
        };
      }
      landed.push(sourceId);
    }
    return { landed, failed: [], error: null };
  }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- clone.test.ts`
Expected: PASS.

- [ ] **Step 5: Typecheck the whole frontend**

Run: `cd frontend && npm run typecheck`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/card.ts frontend/test/clone.test.ts
git commit -m "feat: _cloneRules composition (day-to-day clone primitive)"
```

---

### Task 14: `day-group.ts` + `block-header.ts` clone-menu buttons

**Files:**
- Modify: `frontend/src/day-group.ts` (new `profile` property, `⋮` button)
- Modify: `frontend/src/block-header.ts` (new `⋮` button next to the chips)
- Modify: `frontend/src/strings.ts` (new keys, both languages)
- Modify: `frontend/src/card.ts` (pass `.profile=` to `<shabbat-day-group>`)
- Test: `frontend/test/day-group.test.ts`, `frontend/test/block-header.test.ts`

**Interfaces:**
- Consumes: nothing new.
- Produces: both buttons dispatch `clone-open`
  (`bubbles: true, composed: true`) — day-group's detail is
  `{ scope: 'day', profile: number, day: string }`, block-header's is
  `{ scope: 'profile', profile: number }`. Task 15 defines
  `CloneOpenDetail` matching this exact union and adds the `<ha-card
  @clone-open=...>` listener that receives it — neither button needs a
  listener wired in THIS task, since the event is a valid, independently
  testable fact on its own (this mirrors `rule-open`'s existing
  bubble-to-`<ha-card>` pattern, where `day-group.ts` never relays it
  itself).
- `day-group.ts` gains `@property({ type: Number }) profile = 1;` — the
  block length the day BEING SHOWN belongs to. `card.ts`'s existing
  `<shabbat-day-group>` template (per group in `groups.map(...)`) passes
  `.profile=${this._profile}`, since every group `card.ts` renders shares
  the one currently-selected profile (`buildGroups` is called with exactly
  that profile — see `format.ts`).

- [ ] **Step 1: Write the failing tests**

Add to `frontend/test/day-group.test.ts`:

```ts
  it('offers a clone menu to a writer, naming this day and profile', async () => {
    const el = await render({ group: group({ day: '1' }), profile: 3, canWrite: true });
    const listener = vi.fn();
    el.addEventListener('clone-open', listener);

    (el.shadowRoot!.querySelector('.clone-menu') as HTMLElement).click();

    expect((listener.mock.calls[0][0] as CustomEvent).detail).toEqual({
      scope: 'day', profile: 3, day: '1',
    });
  });

  it('offers no clone menu to a read-only user', async () => {
    const el = await render({ canWrite: false });
    expect(el.shadowRoot!.querySelector('.clone-menu')).toBeNull();
  });
```

Add to `frontend/test/block-header.test.ts`:

```ts
  it('offers a clone menu to a writer, naming the selected profile', async () => {
    const el = await render({ canWrite: true, selectedProfile: 2 });
    const listener = vi.fn();
    el.addEventListener('clone-open', listener);

    (el.shadowRoot!.querySelector('.clone-menu') as HTMLElement).click();

    expect((listener.mock.calls[0][0] as CustomEvent).detail).toEqual({
      scope: 'profile', profile: 2,
    });
  });

  it('offers no clone menu to a read-only user', async () => {
    const el = await render({ canWrite: false });
    expect(el.shadowRoot!.querySelector('.clone-menu')).toBeNull();
  });
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm test -- day-group.test.ts block-header.test.ts`
Expected: FAIL — `.clone-menu` not found.

- [ ] **Step 3: Implement day-group.ts**

Add a property and the button, plus a string import already present.
In `frontend/src/day-group.ts`:

```ts
  @property({ type: Boolean }) canWrite = false;
  @property({ type: Number }) profile = 1;
```

In `render()`'s `.heading` div:

```ts
        <div class="heading">
          <span>${this.label()}</span>
          <span class="date">${this.group.date ?? ''}</span>
          ${this.canWrite
            ? html`<button
                class="clone-menu"
                aria-label=${t(this.language, 'clone_day_prefix')}
                @click=${() =>
                  this.dispatchEvent(
                    new CustomEvent('clone-open', {
                      detail: { scope: 'day', profile: this.profile, day: this.group.day },
                      bubbles: true, composed: true,
                    }),
                  )}
              >⋮</button>`
            : nothing}
        </div>
```

Add a CSS rule (near `.add`):

```css
    .clone-menu {
      font: inherit; background: none; border: none; cursor: pointer;
      font-size: 1.1em; margin-inline-start: auto; padding-inline: 4px;
    }
```

- [ ] **Step 4: Implement block-header.ts**

Add the button inside `.chips`, after the three chip buttons:

```ts
        <div class="chips">
          ${[1, 2, 3].map(
            (profile) => html`
              <button
                class="chip ${this.selectedProfile === profile ? 'active' : ''}"
                @click=${() =>
                  this.dispatchEvent(
                    new CustomEvent('profile-selected', { detail: { profile } }),
                  )}
              >
                ${profile}d
              </button>
            `,
          )}
          ${this.canWrite
            ? html`<button
                class="clone-menu"
                aria-label=${t(this.language, 'clone_profile_prefix')}
                @click=${() =>
                  this.dispatchEvent(
                    new CustomEvent('clone-open', {
                      detail: { scope: 'profile', profile: this.selectedProfile },
                      bubbles: true, composed: true,
                    }),
                  )}
              >⋮</button>`
            : nothing}
        </div>
```

Add the CSS rule (`.clone-menu { font: inherit; background: none; border: none; cursor: pointer; font-size: 1.1em; }` — no `margin-inline-start: auto` needed here, `.chips` is already its own flex group).

- [ ] **Step 5: Add strings**

In `frontend/src/strings.ts`, add to both `en` and `he`:

```ts
    clone_day_prefix: 'Clone day',
    clone_profile_prefix: 'Clone the',
    clone_profile_suffix: '-day profile',
```
```ts
    clone_day_prefix: 'שכפול יום',
    clone_profile_prefix: 'שכפול פרופיל בן',
    clone_profile_suffix: 'ימים',
```

- [ ] **Step 6: Pass `profile` from card.ts**

In `frontend/src/card.ts`'s `<shabbat-day-group>` template:

```ts
        ${groups.map(
          (group) => html`
            <shabbat-day-group
              .group=${group}
              .profile=${this._profile}
              .defaults=${this._state!.defaults}
              .warnings=${this._state!.warnings}
              .language=${this._language}
              .canWrite=${this._canWrite}
              .toggleErrors=${this._toggleErrors}
              @rule-add=${this._onRuleAdd}
            ></shabbat-day-group>
          `,
        )}
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd frontend && npm test -- day-group.test.ts block-header.test.ts && npm run typecheck`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/day-group.ts frontend/src/block-header.ts frontend/src/strings.ts \
  frontend/src/card.ts frontend/test/day-group.test.ts frontend/test/block-header.test.ts
git commit -m "feat: clone-menu buttons on day groups and the block header"
```

---

### Task 15: New `clone-dialog.ts` + card.ts wiring

**Files:**
- Create: `frontend/src/clone-dialog.ts`
- Modify: `frontend/src/strings.ts` (new keys, both languages)
- Modify: `frontend/src/card.ts` (state, `_onCloneOpen`/`_onCloneConfirm`/`_cloneTargetDays`, template)
- Test: `frontend/test/clone-dialog.test.ts` (new), `frontend/test/card.test.ts`

**Interfaces:**
- Consumes: `_cloneRules` (Task 13), the `clone-open` event shape (Task 14).
- Produces: `CloneOpenDetail = { scope: 'day' | 'profile'; profile: number; day?: string }`,
  exported from `clone-dialog.ts`. `<shabbat-clone-dialog>` dispatches
  `dialog-clone-confirm` with detail
  `{ sourceRuleIds: string[]; sourceScope: 'day' | 'profile'; sourceProfile: number; targetProfile: number; targetDay?: string; mode: 'extend' | 'overwrite' }`
  and `dialog-close` (no detail) — no other task consumes these.

`_cloneTargetDays` (card.ts) is the piece that connects Task 13's
single-day `_cloneRules` primitive to a profile-scope clone, per Task 13's
own judgment call: for `sourceScope: 'day'`, it is one `{day, ruleIds}`
pair; for `sourceScope: 'profile'`, it groups `sourceRuleIds` by each
rule's OWN day name, keeping only day names that are also valid on the
target profile — days the source profile has that the target does not are
silently skipped, per the spec's day-name-matching rule, in BOTH extend
and overwrite mode.

- [ ] **Step 1: Write the failing clone-dialog.ts test**

Create `frontend/test/clone-dialog.test.ts`:

```ts
import { describe, expect, it, vi } from 'vitest';
import '../src/clone-dialog';
import type { RuleData } from '../src/types';

const rule = (over: Partial<RuleData> = {}): RuleData => ({
  id: 'a', profile: 1, day: 'erev', time: '11:00:00',
  action: 'climate.turn_on', target: {}, data: {}, condition: [],
  replay: { enabled: false }, name: null, icon: null, enabled: true,
  color: null, last_outcome: null, ...over,
});

async function render(props: Record<string, unknown> = {}) {
  const el = document.createElement('shabbat-clone-dialog') as HTMLElement &
    Record<string, any>;
  Object.assign(el, {
    source: { scope: 'day', profile: 1, day: 'erev' },
    rules: [rule({ id: 'a' })],
    busy: false, error: null, landed: null, failed: null, language: 'en',
    ...props,
  });
  document.body.appendChild(el);
  await el.updateComplete;
  return el;
}

describe('shabbat-clone-dialog', () => {
  it('shows a day picker for a day-scope clone', async () => {
    const el = await render({ source: { scope: 'day', profile: 1, day: 'erev' } });
    expect(el.shadowRoot!.querySelector('select.target-day')).not.toBeNull();
  });

  it('shows no day picker for a profile-scope clone', async () => {
    const el = await render({ source: { scope: 'profile', profile: 1 } });
    expect(el.shadowRoot!.querySelector('select.target-day')).toBeNull();
  });

  it('disables confirm when the source has zero rules', async () => {
    const el = await render({ rules: [] });
    expect((el.shadowRoot!.querySelector('.confirm') as HTMLButtonElement).disabled).toBe(true);
  });

  it('enables confirm when the source has at least one rule', async () => {
    const el = await render();
    expect((el.shadowRoot!.querySelector('.confirm') as HTMLButtonElement).disabled).toBe(false);
  });

  it('defaults to extend mode, the non-destructive choice', async () => {
    const el = await render();
    expect(el.shadowRoot!.querySelector('.mode.extend')!.classList).toContain('active');
    expect(el.shadowRoot!.querySelector('.mode.overwrite')!.classList).not.toContain('active');
  });

  it('shows the existing-target-rules warning only when the target has rules', async () => {
    const el = await render({
      rules: [rule({ id: 'a', profile: 1, day: 'erev' }), rule({ id: 'b', profile: 2, day: 'erev' })],
    });
    (el as any)._targetProfile = 2;
    await el.updateComplete;
    expect(el.shadowRoot!.textContent).toContain('1');
  });

  it('says the same warning wording regardless of mode', async () => {
    const el = await render({
      rules: [rule({ id: 'a', profile: 1, day: 'erev' }), rule({ id: 'b', profile: 2, day: 'erev' })],
    });
    (el as any)._targetProfile = 2;
    (el as any)._mode = 'overwrite';
    await el.updateComplete;
    const overwriteText = el.shadowRoot!.querySelector('.warning')!.textContent;
    (el as any)._mode = 'extend';
    await el.updateComplete;
    expect(el.shadowRoot!.querySelector('.warning')!.textContent).toBe(overwriteText);
  });

  it('dispatches dialog-clone-confirm with the source rule ids, target and mode', async () => {
    const el = await render({
      source: { scope: 'day', profile: 1, day: 'erev' },
      rules: [rule({ id: 'a', profile: 1, day: 'erev' })],
    });
    const listener = vi.fn();
    el.addEventListener('dialog-clone-confirm', listener);
    (el.shadowRoot!.querySelector('.confirm') as HTMLElement).click();
    const detail = (listener.mock.calls[0][0] as CustomEvent).detail;
    expect(detail.sourceRuleIds).toEqual(['a']);
    expect(detail.sourceScope).toBe('day');
    expect(detail.mode).toBe('extend');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- clone-dialog.test.ts`
Expected: FAIL — module does not exist.

- [ ] **Step 3: Implement clone-dialog.ts**

Create `frontend/src/clone-dialog.ts`:

```ts
import { LitElement, css, html, nothing } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { t } from './strings';
import type { RuleData } from './types';

export interface CloneOpenDetail {
  scope: 'day' | 'profile';
  profile: number;
  day?: string;
}

function daysFor(length: number): string[] {
  const days = ['erev'];
  for (let i = 1; i <= length; i += 1) days.push(String(i));
  return days;
}

@customElement('shabbat-clone-dialog')
export class ShabbatCloneDialog extends LitElement {
  @property({ attribute: false }) source: CloneOpenDetail | null = null;
  @property({ attribute: false }) rules: RuleData[] = [];
  @property({ type: Boolean }) busy = false;
  @property() error: string | null = null;
  @property({ attribute: false }) landed: string[] | null = null;
  @property({ attribute: false }) failed: string[] | null = null;
  @property() language = 'en';

  @state() private _targetProfile = 1;
  @state() private _targetDay = 'erev';
  @state() private _mode: 'extend' | 'overwrite' = 'extend';
  private _seeded: string | null = null;

  static override styles = css`
    .sheet {
      position: fixed; inset: 0; display: flex; align-items: center;
      justify-content: center; background: rgba(0, 0, 0, 0.4); z-index: 10;
    }
    .panel {
      background: var(--card-background-color, #fff);
      color: var(--primary-text-color, #111);
      border-radius: 12px; padding: 16px;
      inline-size: min(28rem, 92vw); max-block-size: 88vh; overflow: auto;
    }
    h2 { margin-block: 0 12px; font-size: 1.1em; }
    .field { display: flex; align-items: center; gap: 12px; margin-block: 8px; }
    .field label { min-inline-size: 7em; }
    select { font: inherit; padding-block: 4px; padding-inline: 6px; flex: 1; }
    .warning { color: var(--warning-color, #d9822b); margin-block: 8px; font-size: 0.9em; }
    .error { color: var(--error-color, #d64545); margin-block: 8px; font-size: 0.9em; }
    .report { font-size: 0.85em; margin-block: 8px; }
    .actions {
      display: flex; gap: 8px; justify-content: flex-end;
      margin-block-start: 16px; flex-wrap: wrap;
    }
    button {
      font: inherit; padding-block: 6px; padding-inline: 12px;
      border-radius: 6px; border: 1px solid var(--divider-color, #e0e0e0);
      background: var(--card-background-color, #fff); color: inherit; cursor: pointer;
    }
    button[disabled] { opacity: 0.5; cursor: not-allowed; }
    button.mode.active {
      background: var(--primary-color, #03a9f4);
      color: var(--text-primary-color, #fff); border-color: transparent;
    }
  `;

  override willUpdate() {
    const key = this.source
      ? `${this.source.scope}:${this.source.profile}:${this.source.day ?? ''}`
      : null;
    if (key !== this._seeded) {
      this._seeded = key;
      this._targetProfile = this.source?.profile ?? 1;
      this._targetDay = this.source?.day ?? 'erev';
      this._mode = 'extend';
    }
  }

  private get _dayScope(): boolean {
    return this.source?.scope === 'day';
  }

  private _sourceRuleIds(): string[] {
    if (this.source === null) return [];
    if (this._dayScope) {
      return this.rules
        .filter((r) => r.profile === this.source!.profile && r.day === this.source!.day)
        .map((r) => r.id);
    }
    return this.rules.filter((r) => r.profile === this.source!.profile).map((r) => r.id);
  }

  private _targetRuleCount(): number {
    if (this._dayScope) {
      return this.rules.filter(
        (r) => r.profile === this._targetProfile && r.day === this._targetDay,
      ).length;
    }
    return this.rules.filter((r) => r.profile === this._targetProfile).length;
  }

  private _title(): string {
    if (this.source === null) return '';
    if (this._dayScope) {
      const label = this.source.day === 'erev'
        ? t(this.language, 'erev') : `${t(this.language, 'day')} ${this.source.day}`;
      return `${t(this.language, 'clone_day_prefix')} ${label}`;
    }
    return `${t(this.language, 'clone_profile_prefix')} ${this.source.profile}${t(this.language, 'clone_profile_suffix')}`;
  }

  private _onConfirm() {
    this.dispatchEvent(new CustomEvent('dialog-clone-confirm', {
      detail: {
        sourceRuleIds: this._sourceRuleIds(),
        sourceProfile: this.source?.profile,
        sourceScope: this.source?.scope,
        targetProfile: this._targetProfile,
        targetDay: this._dayScope ? this._targetDay : undefined,
        mode: this._mode,
      },
    }));
  }

  override render() {
    if (this.source === null) return nothing;
    const empty = this._sourceRuleIds().length === 0;
    const targetCount = this._targetRuleCount();
    return html`
      <div class="sheet" @click=${(event: Event) => {
        if (event.target === event.currentTarget) {
          this.dispatchEvent(new CustomEvent('dialog-close'));
        }
      }}>
        <div class="panel">
          <h2>${this._title()}</h2>
          ${this.error !== null ? html`<div class="error">${this.error}</div>` : nothing}
          ${this.landed !== null
            ? html`<div class="report">
                ${t(this.language, 'clone_landed')}: ${this.landed.join(', ') || t(this.language, 'clone_none')}
                ${this.failed && this.failed.length
                  ? html`<br />${t(this.language, 'clone_failed')}: ${this.failed.join(', ')}`
                  : nothing}
              </div>`
            : nothing}

          <div class="field">
            <label>${t(this.language, 'clone_target_profile')}</label>
            <select
              class="target-profile"
              .value=${String(this._targetProfile)}
              @change=${(event: Event) => {
                this._targetProfile = Number((event.target as HTMLSelectElement).value);
              }}
            >
              ${[1, 2, 3].map((p) => html`<option value=${p}>${p}d</option>`)}
            </select>
          </div>
          ${this._dayScope
            ? html`<div class="field">
                <label>${t(this.language, 'clone_target_day')}</label>
                <select
                  class="target-day"
                  .value=${this._targetDay}
                  @change=${(event: Event) => {
                    this._targetDay = (event.target as HTMLSelectElement).value;
                  }}
                >
                  ${daysFor(this._targetProfile).map(
                    (day) => html`<option value=${day}>
                      ${day === 'erev' ? t(this.language, 'erev') : `${t(this.language, 'day')} ${day}`}
                    </option>`,
                  )}
                </select>
              </div>`
            : nothing}

          <div class="field">
            <button
              class="mode extend ${this._mode === 'extend' ? 'active' : ''}"
              @click=${() => { this._mode = 'extend'; }}
            >${t(this.language, 'clone_extend')}</button>
            <button
              class="mode overwrite ${this._mode === 'overwrite' ? 'active' : ''}"
              @click=${() => { this._mode = 'overwrite'; }}
            >${t(this.language, 'clone_overwrite')}</button>
          </div>

          ${targetCount > 0
            ? html`<div class="warning">${t(this.language, 'clone_target_has_rules')} ${targetCount}</div>`
            : nothing}

          <div class="actions">
            <button @click=${() => this.dispatchEvent(new CustomEvent('dialog-close'))}>
              ${t(this.language, 'cancel')}
            </button>
            <button
              class="confirm"
              ?disabled=${this.busy || empty}
              @click=${() => this._onConfirm()}
            >${t(this.language, 'clone_confirm')}</button>
          </div>
        </div>
      </div>
    `;
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- clone-dialog.test.ts`
Expected: PASS.

- [ ] **Step 5: Add strings**

In `frontend/src/strings.ts`, add to both `en` and `he` (`clone_day_prefix`,
`clone_profile_prefix`, `clone_profile_suffix` already added in Task 14):

```ts
    clone_target_profile: 'Target block length',
    clone_target_day: 'Target day',
    clone_extend: 'Extend',
    clone_overwrite: 'Overwrite',
    clone_target_has_rules: 'The target has existing rule(s):',
    clone_confirm: 'Clone',
    clone_landed: 'Cloned',
    clone_failed: 'Not cloned',
    clone_none: 'none',
```
```ts
    clone_target_profile: 'אורך היעד',
    clone_target_day: 'יום היעד',
    clone_extend: 'הוספה',
    clone_overwrite: 'החלפה',
    clone_target_has_rules: 'ליעד כבר יש כללים:',
    clone_confirm: 'שכפול',
    clone_landed: 'שוכפלו',
    clone_failed: 'לא שוכפלו',
    clone_none: 'ללא',
```

(Wording note: the spec's exact copy is "The target has N existing
rule(s)." — this implementation renders the count as a trailing number
after `clone_target_has_rules`'s text rather than interpolating N into
the string, matching this codebase's existing convention of concatenating
dynamic values around a fixed string — e.g. `day-group.ts`'s
`\`${t(this.language,'day')} ${day}\``, `format.ts`'s day-label pattern —
rather than adding template-interpolation support to `t()`.)

- [ ] **Step 6: Wire card.ts**

Add imports, state, and handlers:

```ts
import './clone-dialog';
import type { CloneOpenDetail } from './clone-dialog';
```

```ts
  @state() private _cloneSource: CloneOpenDetail | null = null;
  @state() private _cloneLanded: string[] | null = null;
  @state() private _cloneFailed: string[] | null = null;
```

Add `_cloneSource = null; _cloneLanded = null; _cloneFailed = null;` to
`_closeDialogs`.

```ts
  private _onCloneOpen = (event: Event) => {
    this._cloneSource = (event as CustomEvent).detail as CloneOpenDetail;
    this._cloneLanded = null;
    this._cloneFailed = null;
    this._dialogError = null;
  };

  /**
   * One or more (day, sourceRuleIds) pairs to hand to `_cloneRules`, one
   * call per day - see Task 13's note on why a single `_cloneRules` call
   * only covers one target day.
   */
  private _cloneTargetDays(detail: {
    sourceRuleIds: string[];
    sourceScope: 'day' | 'profile';
    targetProfile: number;
    targetDay?: string;
  }): { day: string; ruleIds: string[] }[] {
    if (detail.sourceScope === 'day') {
      return [{ day: detail.targetDay!, ruleIds: detail.sourceRuleIds }];
    }
    // Profile scope: one call per day name common to both profiles.
    const targetDayNames = new Set<string>(['erev']);
    for (let i = 1; i <= detail.targetProfile; i += 1) targetDayNames.add(String(i));
    const rules = this._state?.rules ?? [];
    const byDay = new Map<string, string[]>();
    for (const id of detail.sourceRuleIds) {
      const rule = rules.find((r) => r.id === id);
      if (rule && targetDayNames.has(rule.day)) {
        byDay.set(rule.day, [...(byDay.get(rule.day) ?? []), id]);
      }
    }
    return [...byDay.entries()].map(([day, ruleIds]) => ({ day, ruleIds }));
  }

  private _onCloneConfirm = async (event: Event) => {
    const detail = (event as CustomEvent).detail as {
      sourceRuleIds: string[]; sourceScope: 'day' | 'profile'; sourceProfile: number;
      targetProfile: number; targetDay?: string; mode: 'extend' | 'overwrite';
    };
    const targets = this._cloneTargetDays(detail);
    const landed: string[] = [];
    const failed: string[] = [];
    for (const { day, ruleIds } of targets) {
      const report = await this._cloneRules(ruleIds, detail.targetProfile, day, detail.mode);
      landed.push(...report.landed);
      if (report.error !== null) {
        failed.push(...report.failed);
        break; // stop issuing further creates, per _cloneRules' own contract
      }
    }
    this._cloneLanded = landed;
    this._cloneFailed = failed;
    if (failed.length === 0 && this._dialogError === null) {
      this._cloneSource = null; // full success closes the dialog
    }
  };
```

Add the listener to `<ha-card>` and the dialog to the render tree:

```ts
      <ha-card
        @rule-open=${this._onRuleOpen}
        @rule-toggle-enabled=${this._onRuleToggleEnabled}
        @simulate-open=${() => { this._simulateOpen = true; }}
        @clone-open=${this._onCloneOpen}
      >
```

```ts
        ${this._cloneSource !== null
          ? html`<shabbat-clone-dialog
              .source=${this._cloneSource}
              .rules=${this._state.rules}
              .busy=${this._busy}
              .error=${this._dialogError}
              .landed=${this._cloneLanded}
              .failed=${this._cloneFailed}
              .language=${this._language}
              @dialog-clone-confirm=${this._onCloneConfirm}
              @dialog-close=${() => { this._cloneSource = null; }}
            ></shabbat-clone-dialog>`
          : nothing}
```

- [ ] **Step 7: Write and run the card.ts integration tests**

Add to `frontend/test/clone.test.ts` (created in Task 13):

```ts
describe('clone dialog wiring in card.ts', () => {
  it('opens the clone dialog on clone-open from a day group', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(state({ rules: [rule({ id: 'a' })] }));
    await el.updateComplete;

    el.shadowRoot!.querySelector('shabbat-day-group')!.dispatchEvent(
      new CustomEvent('clone-open', {
        detail: { scope: 'day', profile: 1, day: 'erev' },
        bubbles: true, composed: true,
      }),
    );
    await el.updateComplete;

    expect(el.shadowRoot!.querySelector('shabbat-clone-dialog')).not.toBeNull();
  });

  it('clones a whole profile day-by-day, skipping days the target does not have', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(state({
      rules: [
        rule({ id: 'erev-rule', profile: 3, day: 'erev' }),
        rule({ id: 'day1-rule', profile: 3, day: '1' }),
        rule({ id: 'day3-rule', profile: 3, day: '3' }), // target (1d) has no day '3'
      ],
    }));
    await el.updateComplete;

    el.shadowRoot!.querySelector('shabbat-block-header')!.dispatchEvent(
      new CustomEvent('clone-open', {
        detail: { scope: 'profile', profile: 3 }, bubbles: true, composed: true,
      }),
    );
    await el.updateComplete;

    const dialog = el.shadowRoot!.querySelector('shabbat-clone-dialog') as any;
    dialog._targetProfile = 1;
    dialog.dispatchEvent(new CustomEvent('dialog-clone-confirm', {
      detail: {
        sourceRuleIds: ['erev-rule', 'day1-rule', 'day3-rule'],
        sourceScope: 'profile', sourceProfile: 3,
        targetProfile: 1, mode: 'extend',
      },
    }));
    await flush();

    const creates = hass.callWS.mock.calls
      .map((c: any) => c[0])
      .filter((c: any) => c.type === 'shabbat_scheduler/rules/create');
    expect(creates).toHaveLength(2); // erev and day 1 only, day 3 skipped
    expect(creates.map((c: any) => c.rule.day).sort()).toEqual(['1', 'erev']);
  });
});
```

Run: `cd frontend && npm test -- clone.test.ts && npm run typecheck`
Expected: PASS.

- [ ] **Step 8: Full frontend suite**

Run: `cd frontend && npm test && npm run typecheck`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/clone-dialog.ts frontend/src/strings.ts frontend/src/card.ts \
  frontend/test/clone-dialog.test.ts frontend/test/clone.test.ts
git commit -m "feat: clone-dialog.ts and card.ts clone wiring"
```

---

### Task 16: e2e test — run a day's schedule for real

**Files:**
- Modify: `e2e/test_card_e2e.py` (new test, new small REST helper)
- Test: `e2e/test_card_e2e.py` (requires the dev container — see Step 3)

**Interfaces:**
- Consumes: `_card`, `CANCEL` (existing e2e helpers), the simulate-dialog
  UI built in Task 11 (`.simulate-open` icon, `select.profile`,
  `select.day`, `button.run-real`).
- Produces: nothing consumed by another task — this is a leaf test.

Uses `dev/seed.py`'s real fixture rules for profile 1, day '1':
`input_boolean.salon` turned ON at 11:00 ("Shabbat morning") then turned
OFF at 18:00 — resolved and run in that order by `run_day`, so the entity
ends up `off` regardless of its state when the test starts, giving a
deterministic assertion without needing to pin a starting state.

- [ ] **Step 1: Write the test**

Add to `e2e/test_card_e2e.py`, near the other REST-touching code (the file
does not yet import `urllib.request` at module scope for a test body — add
it alongside the existing `from playwright.sync_api import expect`):

```python
import urllib.request


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
    dialog.locator("button.run-real").click()

    dialog.locator(".results .row").first.wait_for(timeout=15_000)
    results_text = dialog.locator(".results").inner_text()
    assert "Fired" in results_text or "fired" in results_text.lower(), results_text

    assert _rest_state(base_url, token, "input_boolean.salon") == "off"

    dialog.locator("button:has-text('Cancel')").click()
```

(`import json` is already present at module scope in this file for other
tests — confirm before adding a second import.)

- [ ] **Step 2: This is TDD against a real system, not a unit — there is
  no "run to see it fail" against a stub.** Instead: run it BEFORE Task 11
  lands (or on a branch without Task 11's `simulate-dialog.ts`) against the
  dev container, and confirm it fails for the RIGHT reason.

Run: `cd dev && ./run.sh` (see `dev/README.md`), then
`HA_DEV_TOKEN=<token> uv run pytest e2e/test_card_e2e.py::test_run_day_for_real_actually_calls_the_real_services -v`
Expected (pre-Task-11 checkout): FAIL — `button.simulate-open` not found
(Playwright timeout).

- [ ] **Step 3: Run against the real dev container on this task's own branch**

Run: `HA_DEV_TOKEN=<token> uv run pytest e2e/test_card_e2e.py::test_run_day_for_real_actually_calls_the_real_services -v`
Expected: PASS. If `.results .row` never appears, or the REST assertion
reads a state other than `off`, this is real information about a bug in
Tasks 6/8/11 — fix the actual defect, not this test.

- [ ] **Step 4: Full e2e suite against the dev container**

Run: `HA_DEV_TOKEN=<token> uv run pytest e2e/`
Expected: PASS (every existing e2e test still passes; this task's test is
additive).

- [ ] **Step 5: Commit**

```bash
git add e2e/test_card_e2e.py
git commit -m "test(e2e): run a day's schedule for real via the dev container"
```

---

### Task 17: e2e test — clone a day

**Files:**
- Modify: `e2e/test_card_e2e.py` (new test)
- Test: `e2e/test_card_e2e.py` (requires the dev container — see Step 3)

**Interfaces:**
- Consumes: `_card`, `CANCEL` (existing e2e helpers), the clone-menu button
  and dialog built in Tasks 14–15 (`.clone-menu`, `select.target-profile`,
  `select.target-day`, `.mode.extend`, `.confirm`).
- Produces: nothing consumed by another task — this is a leaf test.

`dev/seed.py` only ever seeds profile 1 (erev + day '1'); profiles 2 and 3
are genuinely empty in the dev container, so profile 2's erev day is a
real "empty day" target with no pre-existing fixture to disturb. Cloned
rules are deleted again in a `finally`, matching this file's own
mutate-then-restore convention (see `test_editing_a_rule_redraws_the_timeline`).

- [ ] **Step 1: Write the test**

Add to `e2e/test_card_e2e.py`:

```python
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
```

- [ ] **Step 2: Confirm it fails for the right reason pre-Task-14/15**

Run: `HA_DEV_TOKEN=<token> uv run pytest e2e/test_card_e2e.py::test_cloning_a_day_lands_a_new_rule_and_leaves_the_source_untouched -v`
against a checkout without Tasks 14–15.
Expected: FAIL — `button.clone-menu` not found.

- [ ] **Step 3: Run against the real dev container on this task's own branch**

Run: `HA_DEV_TOKEN=<token> uv run pytest e2e/test_card_e2e.py::test_cloning_a_day_lands_a_new_rule_and_leaves_the_source_untouched -v`
Expected: PASS.

- [ ] **Step 4: Full e2e suite against the dev container**

Run: `HA_DEV_TOKEN=<token> uv run pytest e2e/`
Expected: PASS — every existing e2e test still passes, including Task 16's.

- [ ] **Step 5: Commit**

```bash
git add e2e/test_card_e2e.py
git commit -m "test(e2e): clone a day onto an empty day via the dev container"
```

---

## Self-review notes (fixed inline while writing this plan)

- **Spec coverage:** every named file in the spec's Part 1 and Part 2 has
  a task (`_cloneRules`/clone-dialog/day-group/block-header for Part 1;
  `async_apply_rule`/`ws_run_now`/`ws_run_day`/dry-run removal/Run
  Now/simulate-dialog/docs for Part 2). The four bounded UI items each
  have their own task (1–5). Both e2e tests from the spec's Testing
  sections are Tasks 16–17.
- **Placeholder scan:** no task contains "TBD"/"add appropriate error
  handling"/"similar to Task N" — every step shows the actual code, and
  every judgment call is named and resolved rather than left open.
- **Type/signature consistency across tasks:** `async_apply_rule`'s new
  keyword-only signature (Task 6) is used identically in `ws_run_now`
  (Task 7) and `ws_run_day` (Task 8). `foldCallResults` (Task 10) is
  called with the identical signature in `simulate-dialog.ts` (Task 11).
  `_cloneRules`'s signature (Task 13) is called identically by
  `_cloneTargetDays`/`_onCloneConfirm` (Task 15). `CloneOpenDetail`
  (defined in Task 15's `clone-dialog.ts`) matches the event detail shape
  dispatched by both buttons added in Task 14. `durationObjectToString`/
  `durationStringToObject` (Task 4) are not referenced by any other task,
  consistent with their scope.
