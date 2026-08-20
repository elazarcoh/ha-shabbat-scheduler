# Shabbat Scheduler Card — Authoring (2b-ii) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a Shabbat schedule be built and adjusted entirely from the card — create, edit, duplicate and delete rules, edit the shared defaults, and author the 2- and 3-day Chag profiles before a Chag arrives.

**Architecture:** Three new Lit elements (a rule dialog, a shared device-aware settings block, a defaults dialog) on top of the existing read view. All logic that can be decided without a DOM goes into `format.ts`, which stays the frontend's pure core. The card sends the Plan 2a websocket commands unchanged and re-renders only from the server's push.

**Tech Stack:** TypeScript, Lit 3, rollup, vitest + happy-dom; Home Assistant 2026.8.2; Docker + Playwright for end-to-end.

## Global Constraints

- **No new write API.** Use `shabbat_scheduler/rules/create`, `rules/update`, `rules/delete` and `defaults/update` exactly as Plan 2a shipped them.
- **No optimistic local state.** A dialog closes on the server's confirmation, and the following push redraws the card. A card showing a change the server did not accept is lying on the one day nobody can check.
- **No client-side revalidation.** `rule_schema.py` owns validation. Send the command and render whatever the server says.
- **Conflicts are warned, never blocking.** Saving a conflicting rule must succeed.
- `format.ts` stays pure: no DOM, no Lit import, no side effects.
- Every Lit element needs `static override styles` and `override render()` — `noImplicitOverride` is on.
- **Wrap every `render()` root in ONE element.** Under happy-dom 15.11.7 + lit-html 3.3.3 a template whose root has more than one top-level node fails to render either branch of a ternary. Reproduced under happy-dom only; a real browser is fine.
- RTL: logical CSS properties only (`padding-inline`, `margin-block`, `inline-size`). Never `left`, `right`, `width`, `height`.
- No new npm dependencies. `npm --prefix frontend run typecheck` clean under `strict` and `noUnusedLocals`.
- Every test for a new behaviour must be observed **failing** before the behaviour exists.
- Development and testing use the throwaway Docker instance on `127.0.0.1:8124`. **Nothing may address 192.168.1.14.**

## File Structure

| File | Responsibility |
|---|---|
| `frontend/src/format.ts` | +`deviceOptions`, `ruleToForm`, `formToCreate`, `formToChanges`, profile-aware `buildGroups`, `isPreview` |
| `frontend/src/types.ts` | +`DeviceOptions`, `RuleFormState`, `HassEntity` |
| `frontend/src/strings.ts` | +authoring strings, en and he |
| `frontend/src/device-settings.ts` | **new** — `<shabbat-device-settings>`, shared by both dialogs |
| `frontend/src/rule-dialog.ts` | **new** — `<shabbat-rule-dialog>` |
| `frontend/src/defaults-dialog.ts` | **new** — `<shabbat-defaults-dialog>` |
| `frontend/src/block-header.ts` | +profile chips, +defaults gear |
| `frontend/src/day-group.ts` | +per-day add button |
| `frontend/src/card.ts` | +`_callWS`, dialog hosting, selected profile, preview banner, admin gating |
| `custom_components/shabbat_scheduler/www/shabbat-scheduler-card.js` | rebuilt bundle |
| `docs/known-behaviours.md` | the accepted no-confirmation delete |
| `e2e/test_card_e2e.py` | +edit round trip, +create round trip |

---

### Task 1: `deviceOptions` — what a device actually offers

**Files:**
- Modify: `frontend/src/types.ts`, `frontend/src/format.ts`
- Test: `frontend/test/format.test.ts`

**Interfaces:**
- Consumes: nothing.
- Produces: `deviceOptions(states, entityIds) -> DeviceOptions`.

**Why:** the three air conditioners in this house genuinely disagree. `climate.air_conditioner_2` offers `quiet` and not `silent`; both `climate.aux_cloud_*` units offer `silent` and not `quiet`. Only `auto`, `low`, `medium`, `high` are common to all three. Offering a fixed list is how a rule gets saved with a fan mode its device will reject — at 11:00 on Shabbat, with nobody able to fix it.

- [ ] **Step 1: Add the types**

In `frontend/src/types.ts`:

```ts
/** The shape Home Assistant's `hass.states` entries have, as much of it as we read. */
export interface HassEntity {
  state: string;
  attributes: Record<string, unknown>;
}

export interface DeviceOptions {
  hvacModes: string[];
  fanModes: string[];
  minTemp: number | null;
  maxTemp: number | null;
  tempStep: number | null;
  /** Entity ids that could not be read - missing, unavailable or unknown. */
  unreadable: string[];
  /** False when not one selected device is a climate entity. */
  climate: boolean;
  /** True when more than one climate device contributed, so these are an intersection. */
  intersected: boolean;
}
```

- [ ] **Step 2: Write the failing tests**

Append to `frontend/test/format.test.ts`:

```ts
import { deviceOptions } from '../src/format';
import type { HassEntity } from '../src/types';

// The real attributes of the three units this system drives.
const SALON: HassEntity = {
  state: 'off',
  attributes: {
    hvac_modes: ['off', 'heat_cool', 'cool', 'fan_only', 'dry', 'heat'],
    fan_modes: ['auto', 'quiet', 'low', 'medlow', 'medium', 'medhigh', 'high', 'strong'],
    min_temp: 16.0, max_temp: 31.0, target_temp_step: 0.5,
  },
};
const KIDS: HassEntity = {
  state: 'off',
  attributes: {
    hvac_modes: ['off', 'auto', 'cool', 'heat', 'dry', 'fan_only'],
    fan_modes: ['auto', 'low', 'medium', 'high', 'turbo', 'silent'],
    min_temp: 16, max_temp: 32, target_temp_step: 0.5,
  },
};
const BOOLEAN: HassEntity = { state: 'off', attributes: {} };

describe('deviceOptions', () => {
  it('offers exactly what a single device declares', () => {
    const o = deviceOptions({ 'climate.salon': SALON }, ['climate.salon']);
    expect(o.fanModes).toContain('quiet');
    expect(o.fanModes).not.toContain('silent');
    expect(o.minTemp).toBe(16);
    expect(o.maxTemp).toBe(31);
    expect(o.climate).toBe(true);
    expect(o.intersected).toBe(false);
  });

  it('intersects when devices disagree, dropping what only one offers', () => {
    const o = deviceOptions(
      { 'climate.salon': SALON, 'climate.kids': KIDS },
      ['climate.salon', 'climate.kids'],
    );
    expect(o.fanModes).toEqual(['auto', 'low', 'medium', 'high']);
    expect(o.fanModes).not.toContain('quiet');
    expect(o.fanModes).not.toContain('silent');
    expect(o.intersected).toBe(true);
  });

  it('narrows the temperature range to what every device accepts', () => {
    const o = deviceOptions(
      { 'climate.salon': SALON, 'climate.kids': KIDS },
      ['climate.salon', 'climate.kids'],
    );
    expect(o.minTemp).toBe(16);
    expect(o.maxTemp).toBe(31); // the salon's ceiling, not the kids' 32
  });

  it('reports a device it cannot read rather than pretending it offers nothing', () => {
    const o = deviceOptions({ 'climate.salon': SALON }, ['climate.salon', 'climate.gone']);
    expect(o.unreadable).toEqual(['climate.gone']);
    // The readable device still contributes - an absent one must not
    // intersect every option away to nothing.
    expect(o.fanModes).toContain('quiet');
  });

  it('treats an unavailable entity as unreadable', () => {
    const o = deviceOptions(
      { 'climate.salon': { state: 'unavailable', attributes: {} } },
      ['climate.salon'],
    );
    expect(o.unreadable).toEqual(['climate.salon']);
    expect(o.climate).toBe(false);
  });

  it('says a non-climate device has no settings', () => {
    const o = deviceOptions({ 'input_boolean.t': BOOLEAN }, ['input_boolean.t']);
    expect(o.climate).toBe(false);
    expect(o.fanModes).toEqual([]);
    expect(o.unreadable).toEqual([]);
  });

  it('returns empty options for no devices at all', () => {
    const o = deviceOptions({}, []);
    expect(o.climate).toBe(false);
    expect(o.intersected).toBe(false);
  });
});
```

- [ ] **Step 3: Run and watch them fail**

```bash
npm --prefix frontend test format
```

Expected: FAIL — `deviceOptions is not a function`.

- [ ] **Step 4: Implement it in `format.ts`**

```ts
function readList(entity: HassEntity, key: string): string[] | null {
  const value = entity.attributes[key];
  return Array.isArray(value) ? value.map(String) : null;
}

function readNumber(entity: HassEntity, key: string): number | null {
  const value = entity.attributes[key];
  return typeof value === 'number' ? value : null;
}

/**
 * What the selected devices actually offer, read from their own state.
 *
 * The three units here disagree: the salon offers `quiet` and not
 * `silent`, the AUX units the reverse. Offering a fixed list is how a
 * rule gets saved with a fan mode its device rejects - discovered at
 * 11:00 on Shabbat, when nobody can fix it. With several devices the
 * intersection is the only honest answer: a mode only one of them
 * supports cannot be applied to the others.
 *
 * A device that cannot be read is REPORTED, never silently treated as
 * offering nothing - that would intersect every option away and present
 * an empty form as though the device were the problem.
 */
export function deviceOptions(
  states: Record<string, HassEntity | undefined>,
  entityIds: string[],
): DeviceOptions {
  const unreadable: string[] = [];
  const readable: HassEntity[] = [];

  for (const id of entityIds) {
    const entity = states[id];
    if (
      entity === undefined ||
      entity.state === 'unavailable' ||
      entity.state === 'unknown'
    ) {
      unreadable.push(id);
      continue;
    }
    readable.push(entity);
  }

  const climates = readable.filter((entity) => readList(entity, 'hvac_modes') !== null);
  if (climates.length === 0) {
    return {
      hvacModes: [], fanModes: [], minTemp: null, maxTemp: null,
      tempStep: null, unreadable, climate: false, intersected: false,
    };
  }

  const intersect = (key: string): string[] =>
    climates
      .map((entity) => readList(entity, key) ?? [])
      .reduce((acc, list) => acc.filter((item) => list.includes(item)));

  const bounds = (key: string, pick: (values: number[]) => number): number | null => {
    const values = climates
      .map((entity) => readNumber(entity, key))
      .filter((value): value is number => value !== null);
    return values.length ? pick(values) : null;
  };

  return {
    hvacModes: intersect('hvac_modes'),
    fanModes: intersect('fan_modes'),
    // The narrowest range every device accepts.
    minTemp: bounds('min_temp', (values) => Math.max(...values)),
    maxTemp: bounds('max_temp', (values) => Math.min(...values)),
    tempStep: bounds('target_temp_step', (values) => Math.max(...values)),
    unreadable,
    climate: true,
    intersected: climates.length > 1,
  };
}
```

Add `DeviceOptions` and `HassEntity` to the existing `import type { ... } from './types';` group.

- [ ] **Step 5: Run tests and typecheck**

```bash
npm --prefix frontend test && npm --prefix frontend run typecheck
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/types.ts frontend/src/format.ts frontend/test/format.test.ts
git commit -m "feat: deviceOptions - what the selected devices actually offer"
```

---

### Task 2: profile-aware grouping and preview mode

**Files:**
- Modify: `frontend/src/format.ts`
- Test: `frontend/test/format.test.ts`

**Interfaces:**
- Consumes: `buildGroups(state)` as it exists today.
- Produces: `buildGroups(state, profile?)` and `isPreview(state, profile) -> boolean`.

**Why:** authoring a 3-day Chag profile means viewing it, and its dates do not exist — the coming block is a plain Shabbat. Showing computed hypothetical dates was rejected: they look exactly like real ones, and not being able to tell what is real is this project's founding complaint. In preview the day headings carry no date and no zmanim marker.

This also removes the need for the `preview` websocket command entirely: every profile's rules are already in the payload, and a preview block's day count is the profile number.

- [ ] **Step 1: Write the failing tests**

```ts
import { isPreview } from '../src/format';

describe('buildGroups with a profile', () => {
  const threeDayRule = rule({ id: 'chag', profile: 3, day: '2', time: '11:00:00' });

  it('shows the current profile with real dates when it matches the block', () => {
    const groups = buildGroups(state({ rules: [rule({ id: 'a', profile: 1, day: '1' })] }), 1);
    expect(groups.map((g) => g.day)).toEqual(['erev', '1']);
    expect(groups[1].date).toBe('2026-08-15');
    expect(groups[1].marker?.kind).toBe('havdalah');
  });

  it('gives a preview profile the right number of days', () => {
    const groups = buildGroups(state({ rules: [threeDayRule] }), 3);
    expect(groups.map((g) => g.day)).toEqual(['erev', '1', '2', '3']);
  });

  it('drops dates and markers in preview, so nothing reads as a real date', () => {
    const groups = buildGroups(state({ rules: [threeDayRule] }), 3);
    for (const group of groups) {
      expect(group.date).toBeNull();
      expect(group.marker).toBeNull();
    }
  });

  it('shows the selected profile rules, not the block-length ones', () => {
    const groups = buildGroups(
      state({ rules: [rule({ id: 'one', profile: 1, day: '1' }), threeDayRule] }),
      3,
    );
    expect(groups.flatMap((g) => g.rules.map((r) => r.id))).toEqual(['chag']);
  });

  it('still works with no block at all, so the card is not a dead end', () => {
    const groups = buildGroups(state({ block: null, rules: [threeDayRule] }), 3);
    expect(groups.map((g) => g.day)).toEqual(['erev', '1', '2', '3']);
    expect(groups[0].date).toBeNull();
  });

  it('defaults to the block length when no profile is given', () => {
    const groups = buildGroups(state({ rules: [rule({ id: 'a', profile: 1, day: '1' })] }));
    expect(groups.map((g) => g.day)).toEqual(['erev', '1']);
    expect(groups[1].date).toBe('2026-08-15');
  });
});

describe('isPreview', () => {
  it('is false for the coming block length', () => {
    expect(isPreview(state({}), 1)).toBe(false);
  });
  it('is true for any other length', () => {
    expect(isPreview(state({}), 3)).toBe(true);
  });
  it('is true whenever there is no block to be current about', () => {
    expect(isPreview(state({ block: null }), 1)).toBe(true);
  });
});
```

- [ ] **Step 2: Run and watch them fail**

```bash
npm --prefix frontend test format
```

Expected: FAIL — `isPreview is not a function`, and the preview cases fail because `buildGroups` ignores its second argument.

- [ ] **Step 3: Replace `buildGroups` and add `isPreview` in `format.ts`**

```ts
/** True when the selected length is not the one actually coming. */
export function isPreview(state: CardState, profile: number): boolean {
  return state.block === null || state.block.length !== profile;
}

function daysFor(length: number): string[] {
  const days = ['erev'];
  for (let i = 1; i <= length; i += 1) days.push(String(i));
  return days;
}

/**
 * The timeline for one profile.
 *
 * With no `profile`, or one equal to the coming block's length, this is
 * the real thing: real dates on the headings and the zmanim markers in
 * place. For any other length it is a PREVIEW - the same rules, but no
 * dates and no markers at all.
 *
 * Dropping the dates is deliberate. A hypothetical Chag's dates would be
 * a guess that looks exactly like a real one, and this card exists
 * because its user could not otherwise tell what was real.
 *
 * Only rules of the selected profile are shown: rules are authored per
 * profile, and a 3-day Chag's rules must not appear on a plain Shabbat.
 */
export function buildGroups(state: CardState, profile?: number): DayGroup[] {
  const { block } = state;
  const length = profile ?? block?.length ?? null;
  if (length === null) return [];

  const preview = isPreview(state, length);
  const lastDay = String(length);

  return daysFor(length)
    .map((day) => {
      const rules = state.rules
        .filter((rule) => rule.profile === length && rule.day === day)
        .sort((a, b) => a.time.localeCompare(b.time));

      let marker: DayGroup['marker'] = null;
      if (!preview && block !== null) {
        if (day === 'erev') {
          marker = { kind: 'candle_lighting', at: block.candle_lighting };
        } else if (day === lastDay) {
          marker = { kind: 'havdalah', at: block.havdalah };
        }
      }

      const date = preview || block === null ? null : (block.dates[day] ?? null);
      return { day, date, rules, marker };
    })
    .sort((a, b) => dayRank(a.day) - dayRank(b.day));
}
```

Delete the now-unused `dayKeys(block)` **only if** `orderedDates` no longer needs it — `orderedDates` still does, so keep `dayKeys` and let it call `daysFor(block.length)` internally:

```ts
function dayKeys(block: BlockData): string[] {
  return daysFor(block.length);
}
```

- [ ] **Step 4: Run the whole frontend suite**

```bash
npm --prefix frontend test && npm --prefix frontend run typecheck
```

Expected: PASS, including every pre-existing `buildGroups` test — the no-argument form must behave exactly as before.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/format.ts frontend/test/format.test.ts
git commit -m "feat: profile-aware grouping, with a dateless preview mode"
```

---

### Task 3: form state in and out of a rule

**Files:**
- Modify: `frontend/src/types.ts`, `frontend/src/format.ts`
- Test: `frontend/test/format.test.ts`

**Interfaces:**
- Consumes: `RuleData` from `types.ts`.
- Produces: `ruleToForm(rule) -> RuleFormState`, `formToCreate(form, profile) -> Record<string, unknown>`, `formToChanges(form, original) -> Record<string, unknown>`.

**Why a partial update:** `changes_from_api` accepts a partial, and sending an unchanged full rule makes every save look like an edit of every field. `formToChanges` returns only what genuinely differs, and `{}` when nothing did.

- [ ] **Step 1: Add the type**

```ts
/** Everything the rule dialog edits. Mirrors RuleData minus `id` and `profile`. */
export interface RuleFormState {
  day: string;
  time: string;
  action: string;
  devices: string[];
  settings: Record<string, unknown>;
  name: string | null;
  icon: string | null;
  color: string | null;
  enabled: boolean;
  script: string | null;
  variables: Record<string, unknown>;
  replay_on_restart: boolean;
}
```

- [ ] **Step 2: Write the failing tests**

```ts
import { formToChanges, formToCreate, ruleToForm } from '../src/format';

const base = rule({
  id: 'r1', profile: 1, day: '1', time: '11:00:00', action: 'on',
  devices: ['climate.salon'], settings: { temperature: 26 }, name: 'Morning',
});

describe('ruleToForm / formToCreate / formToChanges', () => {
  it('round-trips a rule through the form unchanged', () => {
    expect(formToChanges(ruleToForm(base), base)).toEqual({});
  });

  it('sends only what changed', () => {
    const form = { ...ruleToForm(base), time: '12:00:00' };
    expect(formToChanges(form, base)).toEqual({ time: '12:00:00' });
  });

  it('detects a changed device list, not just a changed reference', () => {
    const same = { ...ruleToForm(base), devices: ['climate.salon'] };
    expect(formToChanges(same, base)).toEqual({});
    const different = { ...ruleToForm(base), devices: ['climate.kids'] };
    expect(formToChanges(different, base)).toEqual({ devices: ['climate.kids'] });
  });

  it('detects a changed setting value', () => {
    const form = { ...ruleToForm(base), settings: { temperature: 24 } };
    expect(formToChanges(form, base)).toEqual({ settings: { temperature: 24 } });
  });

  it('sends a cleared name as null rather than omitting it', () => {
    const form = { ...ruleToForm(base), name: null };
    expect(formToChanges(form, base)).toEqual({ name: null });
  });

  it('builds a create payload carrying the profile and every field', () => {
    const payload = formToCreate(ruleToForm(base), 3);
    expect(payload.profile).toBe(3);
    expect(payload.day).toBe('1');
    expect(payload.action).toBe('on');
    expect(payload.devices).toEqual(['climate.salon']);
    // A create must never carry an id - the server generates it.
    expect(payload.id).toBeUndefined();
  });

  it('keeps enabled as a real boolean, never a string', () => {
    const payload = formToCreate({ ...ruleToForm(base), enabled: false }, 1);
    expect(payload.enabled).toBe(false);
    expect(typeof payload.enabled).toBe('boolean');
  });
});
```

- [ ] **Step 3: Run and watch them fail**

```bash
npm --prefix frontend test format
```

Expected: FAIL — `ruleToForm is not a function`.

- [ ] **Step 4: Implement in `format.ts`**

```ts
const FORM_FIELDS = [
  'day', 'time', 'action', 'devices', 'settings', 'name', 'icon',
  'color', 'enabled', 'script', 'variables', 'replay_on_restart',
] as const;

export function ruleToForm(rule: RuleData): RuleFormState {
  return {
    day: rule.day,
    time: rule.time,
    action: rule.action,
    devices: [...rule.devices],
    settings: { ...rule.settings },
    name: rule.name,
    icon: rule.icon,
    color: rule.color,
    enabled: rule.enabled,
    script: rule.script,
    variables: { ...rule.variables },
    replay_on_restart: rule.replay_on_restart,
  };
}

/** Everything, plus the profile the day is being authored under. */
export function formToCreate(
  form: RuleFormState,
  profile: number,
): Record<string, unknown> {
  return { ...form, profile };
}

/**
 * Only the fields that genuinely differ.
 *
 * `changes_from_api` takes a partial, and sending the whole rule back
 * would record an edit of every field in the logbook every time anyone
 * saved anything. Compared by value, not reference - a devices array
 * rebuilt from the same strings has not changed.
 */
export function formToChanges(
  form: RuleFormState,
  original: RuleData,
): Record<string, unknown> {
  const changes: Record<string, unknown> = {};
  for (const field of FORM_FIELDS) {
    const next = form[field];
    const prev = (original as unknown as Record<string, unknown>)[field];
    if (JSON.stringify(next) !== JSON.stringify(prev)) changes[field] = next;
  }
  return changes;
}
```

- [ ] **Step 5: Run tests and typecheck**

```bash
npm --prefix frontend test && npm --prefix frontend run typecheck
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/types.ts frontend/src/format.ts frontend/test/format.test.ts
git commit -m "feat: rule form state, and partial updates that say only what changed"
```

---

### Task 4: `<shabbat-device-settings>`

**Files:**
- Create: `frontend/src/device-settings.ts`
- Modify: `frontend/src/strings.ts`
- Test: `frontend/test/device-settings.test.ts`

**Interfaces:**
- Consumes: `deviceOptions` (Task 1), `t` from `strings.ts`.
- Produces: `<shabbat-device-settings>` with properties `states: Record<string, HassEntity | undefined>`, `devices: string[]`, `settings: Record<string, unknown>`, `disabled: boolean`, `language: string`. Fires `settings-changed` with detail `{ settings }` and `devices-changed` with detail `{ devices }`.

Shared deliberately between the rule dialog and the defaults dialog: both edit the same `devices` + `settings` shape and the engine merges one into the other. Two implementations would let the form that authors a default disagree with the form that overrides it.

- [ ] **Step 1: Add the strings**

Add to both `en` and `he` in `frontend/src/strings.ts`:

```ts
    devices: 'Devices',
    temperature: 'Temperature',
    hvac_mode: 'Mode',
    fan_mode: 'Fan',
    intersected: 'Showing only what every selected device supports.',
    unreadable: 'Could not read these devices, so their options are unknown:',
    not_climate: 'These devices take no settings — on and off only.',
    kept_setting: 'kept, but this device does not list it',
```

```ts
    devices: 'מכשירים',
    temperature: 'טמפרטורה',
    hvac_mode: 'מצב',
    fan_mode: 'מאוורר',
    intersected: 'מוצג רק מה שכל המכשירים שנבחרו תומכים בו.',
    unreadable: 'לא ניתן לקרוא את המכשירים האלה, לכן האפשרויות שלהם אינן ידועות:',
    not_climate: 'המכשירים האלה לא מקבלים הגדרות — הפעלה וכיבוי בלבד.',
    kept_setting: 'נשמר, אך המכשיר לא מציג אותו',
```

- [ ] **Step 2: Write the failing tests**

`frontend/test/device-settings.test.ts`:

```ts
import { describe, expect, it, vi } from 'vitest';
import '../src/device-settings';
import type { HassEntity } from '../src/types';

const SALON: HassEntity = {
  state: 'off',
  attributes: {
    hvac_modes: ['off', 'cool', 'heat'],
    fan_modes: ['auto', 'quiet', 'low'],
    min_temp: 16, max_temp: 31, target_temp_step: 0.5,
  },
};
const KIDS: HassEntity = {
  state: 'off',
  attributes: {
    hvac_modes: ['off', 'cool', 'heat'],
    fan_modes: ['auto', 'silent', 'low'],
    min_temp: 16, max_temp: 32, target_temp_step: 0.5,
  },
};

async function render(props: Record<string, unknown>) {
  const el = document.createElement('shabbat-device-settings') as HTMLElement &
    Record<string, any>;
  Object.assign(el, {
    states: { 'climate.salon': SALON, 'climate.kids': KIDS },
    devices: ['climate.salon'], settings: {}, disabled: false, language: 'en',
    ...props,
  });
  document.body.appendChild(el);
  await el.updateComplete;
  return el;
}

describe('shabbat-device-settings', () => {
  it("offers the selected device's own fan modes", async () => {
    const el = await render({});
    const options = [...el.shadowRoot!.querySelectorAll('.fan option')].map(
      (o) => (o as HTMLOptionElement).value,
    );
    expect(options).toContain('quiet');
    expect(options).not.toContain('silent');
  });

  it('says so when it is showing an intersection', async () => {
    const el = await render({ devices: ['climate.salon', 'climate.kids'] });
    expect(el.shadowRoot!.textContent).toContain('every selected device');
    const options = [...el.shadowRoot!.querySelectorAll('.fan option')].map(
      (o) => (o as HTMLOptionElement).value,
    );
    expect(options).not.toContain('quiet');
    expect(options).not.toContain('silent');
  });

  it('names a device it could not read', async () => {
    const el = await render({ devices: ['climate.salon', 'climate.gone'] });
    const text = el.shadowRoot!.textContent!;
    expect(text).toContain('Could not read');
    expect(text).toContain('climate.gone');
  });

  it('keeps a saved setting the device does not list, and flags it', async () => {
    const el = await render({ settings: { fan_mode: 'turbo' } });
    const text = el.shadowRoot!.textContent!;
    expect(text).toContain('turbo');
    expect(text).toContain('does not list it');
  });

  it('says a non-climate device takes no settings', async () => {
    const el = await render({
      states: { 'input_boolean.t': { state: 'off', attributes: {} } },
      devices: ['input_boolean.t'],
    });
    expect(el.shadowRoot!.textContent).toContain('no settings');
  });

  it('reports a changed setting rather than mutating its own property', async () => {
    const el = await render({});
    const listener = vi.fn();
    el.addEventListener('settings-changed', listener);

    const select = el.shadowRoot!.querySelector('.fan') as HTMLSelectElement;
    select.value = 'quiet';
    select.dispatchEvent(new Event('change'));

    expect(listener).toHaveBeenCalledOnce();
    expect((listener.mock.calls[0][0] as CustomEvent).detail.settings.fan_mode)
      .toBe('quiet');
    expect(el.settings.fan_mode).toBeUndefined();
  });

  it('disables every control when disabled', async () => {
    const el = await render({ disabled: true });
    for (const control of el.shadowRoot!.querySelectorAll('select, input')) {
      expect((control as HTMLInputElement).disabled).toBe(true);
    }
  });
});
```

- [ ] **Step 3: Run and watch them fail**

```bash
npm --prefix frontend test device-settings
```

Expected: FAIL — cannot resolve `../src/device-settings`.

- [ ] **Step 4: Create `frontend/src/device-settings.ts`**

```ts
import { LitElement, css, html, nothing } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { deviceOptions } from './format';
import { t } from './strings';
import type { DeviceOptions, HassEntity } from './types';

@customElement('shabbat-device-settings')
export class ShabbatDeviceSettings extends LitElement {
  @property({ attribute: false }) states: Record<string, HassEntity | undefined> = {};
  @property({ attribute: false }) devices: string[] = [];
  @property({ attribute: false }) settings: Record<string, unknown> = {};
  @property({ type: Boolean }) disabled = false;
  @property() language = 'en';

  static override styles = css`
    .field {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-block: 8px;
    }
    .field label { min-inline-size: 7em; }
    select, input {
      font: inherit;
      padding-block: 4px;
      padding-inline: 6px;
      flex: 1;
      min-inline-size: 0;
    }
    .note {
      color: var(--secondary-text-color, #666);
      font-size: 0.85em;
      margin-block: 4px;
    }
    .warn { color: var(--warning-color, #d9822b); }
  `;

  private get _options(): DeviceOptions {
    return deviceOptions(this.states, this.devices);
  }

  private _emit(settings: Record<string, unknown>) {
    // Reports intent. The parent owns the value and passes it back down,
    // so this element never disagrees with what will actually be saved.
    this.dispatchEvent(new CustomEvent('settings-changed', { detail: { settings } }));
  }

  private _set(key: string, value: unknown) {
    const next = { ...this.settings };
    if (value === '' || value === null) delete next[key];
    else next[key] = value;
    this._emit(next);
  }

  /** A saved value the current devices do not list. Kept, never dropped. */
  private _orphan(key: string, offered: string[]): string | null {
    const value = this.settings[key];
    if (typeof value !== 'string' || value === '') return null;
    return offered.includes(value) ? null : value;
  }

  private _select(key: 'hvac_mode' | 'fan_mode', offered: string[]) {
    const current = this.settings[key];
    const orphan = this._orphan(key, offered);
    return html`
      <div class="field">
        <label for=${key}>${t(this.language, key)}</label>
        <select
          id=${key}
          class=${key === 'fan_mode' ? 'fan' : 'hvac'}
          ?disabled=${this.disabled}
          @change=${(event: Event) =>
            this._set(key, (event.target as HTMLSelectElement).value)}
        >
          <option value=""></option>
          ${orphan !== null
            ? html`<option value=${orphan} selected>${orphan}</option>`
            : nothing}
          ${offered.map(
            (option) => html`
              <option value=${option} ?selected=${current === option}>
                ${option}
              </option>
            `,
          )}
        </select>
      </div>
      ${orphan !== null
        ? html`<div class="note warn">
            ${orphan} — ${t(this.language, 'kept_setting')}
          </div>`
        : nothing}
    `;
  }

  override render() {
    const options = this._options;
    return html`
      <div class="settings">
        ${options.unreadable.length
          ? html`<div class="note warn">
              ${t(this.language, 'unreadable')} ${options.unreadable.join(', ')}
            </div>`
          : nothing}
        ${options.intersected
          ? html`<div class="note">${t(this.language, 'intersected')}</div>`
          : nothing}
        ${options.climate
          ? html`
              <div class="field">
                <label for="temperature">${t(this.language, 'temperature')}</label>
                <input
                  id="temperature"
                  class="temperature"
                  type="number"
                  .value=${String(this.settings.temperature ?? '')}
                  min=${options.minTemp ?? 5}
                  max=${options.maxTemp ?? 35}
                  step=${options.tempStep ?? 0.5}
                  ?disabled=${this.disabled}
                  @change=${(event: Event) => {
                    const raw = (event.target as HTMLInputElement).value;
                    this._set('temperature', raw === '' ? null : Number(raw));
                  }}
                />
              </div>
              ${this._select('hvac_mode', options.hvacModes)}
              ${this._select('fan_mode', options.fanModes)}
            `
          : html`<div class="note">${t(this.language, 'not_climate')}</div>`}
      </div>
    `;
  }
}
```

- [ ] **Step 5: Run tests and typecheck**

```bash
npm --prefix frontend test && npm --prefix frontend run typecheck
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/device-settings.ts frontend/src/strings.ts frontend/test/device-settings.test.ts
git commit -m "feat: device-aware settings, offering what the devices actually support"
```

---

### Task 5: `<shabbat-rule-dialog>` — the form

**Files:**
- Create: `frontend/src/rule-dialog.ts`
- Modify: `frontend/src/strings.ts`
- Test: `frontend/test/rule-dialog.test.ts`

**Interfaces:**
- Consumes: `ruleToForm` (Task 3), `<shabbat-device-settings>` (Task 4).
- Produces: `<shabbat-rule-dialog>` with properties `rule: RuleData | null` (null = create), `seed: RuleFormState | null`, `day: string`, `profile: number`, `defaults: Defaults`, `states`, `canWrite: boolean`, `language: string`, `error: string | null`, `busy: boolean`. Fires `dialog-save` (detail `{ form, rule }`), `dialog-delete` (detail `{ rule }`), `dialog-duplicate` (detail `{ form, rule }`), `dialog-close`.

`seed` is what makes duplication actually duplicate: a create opened with a
seed starts from those values instead of an empty form.

This task renders the form and its states. Task 6 wires the actions to the server.

- [ ] **Step 1: Add the strings**

Add to both languages (`en` shown; translate for `he`):

```ts
    edit_rule: 'Edit rule',
    add_rule: 'Add rule',
    time: 'Time',
    action: 'Action',
    name: 'Name',
    enabled: 'Enabled',
    advanced: 'Advanced',
    icon: 'Icon',
    colour: 'Colour',
    script: 'Script',
    replay: 'Re-apply after a restart',
    save: 'Save',
    cancel: 'Cancel',
    delete_rule: 'Delete',
    duplicate: 'Duplicate',
    read_only: 'You do not have permission to change the schedule.',
    will_conflict: 'This overlaps another rule. You can still save it — nothing is resolved for you.',
```

Hebrew equivalents: `'עריכת כלל'`, `'הוספת כלל'`, `'שעה'`, `'פעולה'`, `'שם'`, `'מופעל'`, `'מתקדם'`, `'סמל'`, `'צבע'`, `'סקריפט'`, `'החלה מחדש לאחר הפעלה מחדש'`, `'שמירה'`, `'ביטול'`, `'מחיקה'`, `'שכפול'`, `'אין לך הרשאה לשנות את הלוח.'`, `'הכלל חופף לכלל אחר. אפשר לשמור בכל זאת — שום דבר לא ייפתר עבורך.'`

- [ ] **Step 2: Write the failing tests**

`frontend/test/rule-dialog.test.ts`:

```ts
import { describe, expect, it, vi } from 'vitest';
import '../src/rule-dialog';
import type { RuleData } from '../src/types';

const existing: RuleData = {
  id: 'r1', profile: 1, day: '1', time: '11:00:00', action: 'on',
  devices: ['climate.salon'], settings: { temperature: 26 }, name: 'Morning',
  icon: null, enabled: true, script: null, variables: {},
  replay_on_restart: false, color: null,
};

async function render(props: Record<string, unknown> = {}) {
  const el = document.createElement('shabbat-rule-dialog') as HTMLElement &
    Record<string, any>;
  Object.assign(el, {
    rule: existing, day: '1', profile: 1, defaults: {}, states: {},
    canWrite: true, language: 'en', error: null, busy: false, ...props,
  });
  document.body.appendChild(el);
  await el.updateComplete;
  return el;
}

describe('shabbat-rule-dialog', () => {
  it('opens an existing rule with its values filled in', async () => {
    const el = await render();
    expect((el.shadowRoot!.querySelector('.time') as HTMLInputElement).value)
      .toBe('11:00:00');
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

    const time = el.shadowRoot!.querySelector('.time') as HTMLInputElement;
    time.value = '12:30:00';
    time.dispatchEvent(new Event('change'));
    (el.shadowRoot!.querySelector('.save') as HTMLElement).click();

    const detail = (listener.mock.calls[0][0] as CustomEvent).detail;
    expect(detail.form.time).toBe('12:30:00');
    expect(detail.rule.id).toBe('r1');
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
    expect((el.shadowRoot!.querySelector('.time') as HTMLInputElement).disabled)
      .toBe(true);
  });

  it('disables the actions while a command is in flight', async () => {
    const el = await render({ busy: true });
    expect((el.shadowRoot!.querySelector('.save') as HTMLButtonElement).disabled)
      .toBe(true);
  });

  it('shows the advanced fields only once asked for', async () => {
    const el = await render();
    expect(el.shadowRoot!.querySelector('.icon')).toBeNull();
    (el.shadowRoot!.querySelector('.advanced-toggle') as HTMLElement).click();
    await el.updateComplete;
    expect(el.shadowRoot!.querySelector('.icon')).not.toBeNull();
  });

  it('asks for a script when the action is custom', async () => {
    const el = await render({
      rule: { ...existing, action: 'custom', script: 'script.boiler' },
    });
    expect((el.shadowRoot!.querySelector('.script') as HTMLInputElement).value)
      .toBe('script.boiler');
  });

  it('starts a seeded create from the seed, which is what makes duplicate duplicate', async () => {
    const el = await render({
      rule: null,
      seed: { ...ruleToForm(existing), time: '11:00:00' },
    });
    expect(el.shadowRoot!.textContent).toContain('Add rule');
    expect((el.shadowRoot!.querySelector('.name') as HTMLInputElement).value)
      .toBe('Morning');
    expect((el.shadowRoot!.querySelector('.time') as HTMLInputElement).value)
      .toBe('11:00:00');
    // Still a create - a duplicate that offered delete would delete the
    // rule it was copied from.
    expect(el.shadowRoot!.querySelector('.delete')).toBeNull();
  });
});
```

- [ ] **Step 3: Run and watch them fail**

```bash
npm --prefix frontend test rule-dialog
```

Expected: FAIL — cannot resolve `../src/rule-dialog`.

- [ ] **Step 4: Create `frontend/src/rule-dialog.ts`**

```ts
import { LitElement, css, html, nothing } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import './device-settings';
import { ruleToForm } from './format';
import { t } from './strings';
import type { Defaults, HassEntity, RuleData, RuleFormState } from './types';

const EMPTY_FORM: RuleFormState = {
  day: 'erev', time: '', action: 'on', devices: [], settings: {},
  name: null, icon: null, color: null, enabled: true, script: null,
  variables: {}, replay_on_restart: false,
};

@customElement('shabbat-rule-dialog')
export class ShabbatRuleDialog extends LitElement {
  /** null means create. */
  @property({ attribute: false }) rule: RuleData | null = null;
  /** Pre-filled values for a create. This is what duplication uses. */
  @property({ attribute: false }) seed: RuleFormState | null = null;
  @property() day = 'erev';
  @property({ type: Number }) profile = 1;
  @property({ attribute: false }) defaults: Defaults = {};
  @property({ attribute: false }) states: Record<string, HassEntity | undefined> = {};
  @property({ type: Boolean }) canWrite = false;
  @property({ type: Boolean }) busy = false;
  @property() error: string | null = null;
  @property() language = 'en';

  @state() private _form: RuleFormState = EMPTY_FORM;
  @state() private _advanced = false;
  private _seeded: string | null = null;

  static override styles = css`
    .sheet {
      position: fixed;
      inset: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      background: rgba(0, 0, 0, 0.4);
      z-index: 10;
    }
    .panel {
      background: var(--card-background-color, #fff);
      color: var(--primary-text-color, #111);
      border-radius: 12px;
      padding: 16px;
      inline-size: min(28rem, 92vw);
      max-block-size: 88vh;
      overflow: auto;
    }
    h2 { margin-block: 0 12px; font-size: 1.1em; }
    .field { display: flex; align-items: center; gap: 12px; margin-block: 8px; }
    .field label { min-inline-size: 7em; }
    input, select {
      font: inherit;
      padding-block: 4px;
      padding-inline: 6px;
      flex: 1;
      min-inline-size: 0;
    }
    .actions {
      display: flex;
      gap: 8px;
      justify-content: flex-end;
      margin-block-start: 16px;
      flex-wrap: wrap;
    }
    .actions .delete { margin-inline-end: auto; color: var(--error-color, #d64545); }
    button {
      font: inherit;
      padding-block: 6px;
      padding-inline: 12px;
      border-radius: 6px;
      border: 1px solid var(--divider-color, #e0e0e0);
      background: var(--card-background-color, #fff);
      color: inherit;
      cursor: pointer;
    }
    button[disabled] { opacity: 0.5; cursor: not-allowed; }
    .error {
      color: var(--error-color, #d64545);
      margin-block: 8px;
      font-size: 0.9em;
    }
    .note { color: var(--secondary-text-color, #666); font-size: 0.85em; }
    .advanced-toggle {
      background: none;
      border: none;
      padding-inline: 0;
      color: var(--primary-color, #03a9f4);
    }
  `;

  override willUpdate() {
    // Seed the form once per opened rule. Re-seeding on every update
    // would throw away what the user has typed each time a push arrives -
    // and pushes arrive constantly, since `hass` is reassigned on every
    // state change in the whole system.
    const key = this.rule
      ? `edit:${this.rule.id}`
      : `new:${this.day}:${this.profile}:${this.seed ? 'seeded' : 'blank'}`;
    if (this._seeded !== key) {
      this._seeded = key;
      if (this.rule) {
        this._form = ruleToForm(this.rule);
      } else if (this.seed) {
        // A duplicate: same values, no id, so saving creates a new rule.
        this._form = { ...this.seed, day: this.day };
      } else {
        this._form = { ...EMPTY_FORM, day: this.day };
      }
      this._advanced = false;
    }
  }

  private _patch(patch: Partial<RuleFormState>) {
    this._form = { ...this._form, ...patch };
  }

  private _emit(type: string) {
    this.dispatchEvent(
      new CustomEvent(type, { detail: { form: this._form, rule: this.rule } }),
    );
  }

  private _text(
    key: 'time' | 'name' | 'icon' | 'color' | 'script',
    label: string,
  ) {
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

  override render() {
    const editing = this.rule !== null;
    return html`
      <div class="sheet" @click=${(event: Event) => {
        if (event.target === event.currentTarget) {
          this.dispatchEvent(new CustomEvent('dialog-close'));
        }
      }}>
        <div class="panel">
          <h2>${t(this.language, editing ? 'edit_rule' : 'add_rule')}</h2>

          ${this.canWrite
            ? nothing
            : html`<div class="note">${t(this.language, 'read_only')}</div>`}
          ${this.error !== null
            ? html`<div class="error">${this.error}</div>`
            : nothing}

          <div class="form">
            ${this._text('time', t(this.language, 'time'))}
            <div class="field">
              <label for="action">${t(this.language, 'action')}</label>
              <select
                id="action"
                class="action"
                ?disabled=${!this.canWrite}
                @change=${(event: Event) =>
                  this._patch({ action: (event.target as HTMLSelectElement).value })}
              >
                ${['on', 'off', 'custom'].map(
                  (option) => html`
                    <option value=${option} ?selected=${this._form.action === option}>
                      ${option}
                    </option>
                  `,
                )}
              </select>
            </div>
            ${this._text('name', t(this.language, 'name'))}

            ${this._form.action === 'custom'
              ? this._text('script', t(this.language, 'script'))
              : html`
                  <shabbat-device-settings
                    .states=${this.states}
                    .devices=${this._form.devices.length
                      ? this._form.devices
                      : (this.defaults.devices ?? [])}
                    .settings=${this._form.settings}
                    .disabled=${!this.canWrite}
                    .language=${this.language}
                    @settings-changed=${(event: Event) =>
                      this._patch({ settings: (event as CustomEvent).detail.settings })}
                  ></shabbat-device-settings>
                `}

            <div class="field">
              <label for="enabled">${t(this.language, 'enabled')}</label>
              <input
                id="enabled"
                class="enabled"
                type="checkbox"
                .checked=${this._form.enabled}
                ?disabled=${!this.canWrite}
                @change=${(event: Event) =>
                  this._patch({ enabled: (event.target as HTMLInputElement).checked })}
              />
            </div>

            <button
              class="advanced-toggle"
              @click=${() => { this._advanced = !this._advanced; }}
            >
              ${t(this.language, 'advanced')}
            </button>
            ${this._advanced
              ? html`
                  ${this._text('icon', t(this.language, 'icon'))}
                  ${this._text('color', t(this.language, 'colour'))}
                  <div class="field">
                    <label for="replay">${t(this.language, 'replay')}</label>
                    <input
                      id="replay"
                      class="replay"
                      type="checkbox"
                      .checked=${this._form.replay_on_restart}
                      ?disabled=${!this.canWrite}
                      @change=${(event: Event) =>
                        this._patch({
                          replay_on_restart: (event.target as HTMLInputElement).checked,
                        })}
                    />
                  </div>
                `
              : nothing}
          </div>

          <div class="actions">
            ${this.canWrite && editing
              ? html`<button
                  class="delete"
                  ?disabled=${this.busy}
                  @click=${() => this._emit('dialog-delete')}
                >
                  ${t(this.language, 'delete_rule')}
                </button>`
              : nothing}
            <button @click=${() => this.dispatchEvent(new CustomEvent('dialog-close'))}>
              ${t(this.language, 'cancel')}
            </button>
            ${this.canWrite && editing
              ? html`<button
                  class="duplicate"
                  ?disabled=${this.busy}
                  @click=${() => this._emit('dialog-duplicate')}
                >
                  ${t(this.language, 'duplicate')}
                </button>`
              : nothing}
            ${this.canWrite
              ? html`<button
                  class="save"
                  ?disabled=${this.busy}
                  @click=${() => this._emit('dialog-save')}
                >
                  ${t(this.language, 'save')}
                </button>`
              : nothing}
          </div>
        </div>
      </div>
    `;
  }
}
```

- [ ] **Step 5: Run tests and typecheck**

```bash
npm --prefix frontend test && npm --prefix frontend run typecheck
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/rule-dialog.ts frontend/src/strings.ts frontend/test/rule-dialog.test.ts
git commit -m "feat: the rule dialog"
```

---

### Task 6: `<shabbat-defaults-dialog>`

**Files:**
- Create: `frontend/src/defaults-dialog.ts`
- Modify: `frontend/src/strings.ts`
- Test: `frontend/test/defaults-dialog.test.ts`

**Interfaces:**
- Consumes: `<shabbat-device-settings>` (Task 4).
- Produces: `<shabbat-defaults-dialog>` with properties `defaults: Defaults`, `states`, `canWrite`, `busy`, `error`, `language`. Fires `defaults-save` (detail `{ defaults }`) and `dialog-close`.

**Why it matters:** `merge_defaults` reads only `devices` and `settings` at the top level. `validate_defaults` **rejects** anything else, so a flat `temperature: 26` is an error, not a silently ignored key. This dialog must produce the nested shape and nothing else.

- [ ] **Step 1: Add the strings**

```ts
    defaults_title: 'Shared defaults',
    defaults_help: 'Rules inherit these unless they set their own.',
```

```ts
    defaults_title: 'ברירות מחדל משותפות',
    defaults_help: 'כללים יורשים אותן אלא אם הגדירו משלהם.',
```

- [ ] **Step 2: Write the failing tests**

`frontend/test/defaults-dialog.test.ts`:

```ts
import { describe, expect, it, vi } from 'vitest';
import '../src/defaults-dialog';

async function render(props: Record<string, unknown> = {}) {
  const el = document.createElement('shabbat-defaults-dialog') as HTMLElement &
    Record<string, any>;
  Object.assign(el, {
    defaults: { devices: ['climate.salon'], settings: { temperature: 26 } },
    states: {}, canWrite: true, busy: false, error: null, language: 'en', ...props,
  });
  document.body.appendChild(el);
  await el.updateComplete;
  return el;
}

describe('shabbat-defaults-dialog', () => {
  it('shows the shared defaults', async () => {
    const el = await render();
    expect(el.shadowRoot!.textContent).toContain('Shared defaults');
    expect(el.shadowRoot!.querySelector('shabbat-device-settings')).not.toBeNull();
  });

  it('saves the nested devices/settings shape and nothing else', async () => {
    const el = await render();
    const listener = vi.fn();
    el.addEventListener('defaults-save', listener);

    (el.shadowRoot!.querySelector('.save') as HTMLElement).click();

    const { defaults } = (listener.mock.calls[0][0] as CustomEvent).detail;
    // validate_defaults rejects any key other than these two, so a flat
    // `temperature` here is an error the server refuses - not a
    // harmlessly ignored extra.
    expect(Object.keys(defaults).sort()).toEqual(['devices', 'settings']);
    expect(defaults.settings.temperature).toBe(26);
  });

  it('shows a server rejection and stays open', async () => {
    const el = await render({ error: "unknown field(s): ['temperature']" });
    expect(el.shadowRoot!.textContent).toContain('unknown field');
    expect(el.shadowRoot!.querySelector('shabbat-device-settings')).not.toBeNull();
  });

  it('offers no save to a read-only user', async () => {
    const el = await render({ canWrite: false });
    expect(el.shadowRoot!.querySelector('.save')).toBeNull();
  });
});
```

- [ ] **Step 3: Run and watch them fail**

```bash
npm --prefix frontend test defaults-dialog
```

Expected: FAIL — cannot resolve `../src/defaults-dialog`.

- [ ] **Step 4: Create `frontend/src/defaults-dialog.ts`**

```ts
import { LitElement, css, html, nothing } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import './device-settings';
import { t } from './strings';
import type { Defaults, HassEntity } from './types';

@customElement('shabbat-defaults-dialog')
export class ShabbatDefaultsDialog extends LitElement {
  @property({ attribute: false }) defaults: Defaults = {};
  @property({ attribute: false }) states: Record<string, HassEntity | undefined> = {};
  @property({ type: Boolean }) canWrite = false;
  @property({ type: Boolean }) busy = false;
  @property() error: string | null = null;
  @property() language = 'en';

  @state() private _draft: Defaults | null = null;

  static override styles = css`
    .sheet {
      position: fixed;
      inset: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      background: rgba(0, 0, 0, 0.4);
      z-index: 10;
    }
    .panel {
      background: var(--card-background-color, #fff);
      color: var(--primary-text-color, #111);
      border-radius: 12px;
      padding: 16px;
      inline-size: min(28rem, 92vw);
    }
    h2 { margin-block: 0 4px; font-size: 1.1em; }
    .note { color: var(--secondary-text-color, #666); font-size: 0.85em; }
    .error { color: var(--error-color, #d64545); margin-block: 8px; font-size: 0.9em; }
    .actions {
      display: flex;
      gap: 8px;
      justify-content: flex-end;
      margin-block-start: 16px;
    }
    button {
      font: inherit;
      padding-block: 6px;
      padding-inline: 12px;
      border-radius: 6px;
      border: 1px solid var(--divider-color, #e0e0e0);
      background: var(--card-background-color, #fff);
      color: inherit;
      cursor: pointer;
    }
    button[disabled] { opacity: 0.5; cursor: not-allowed; }
  `;

  private get _current(): Defaults {
    return this._draft ?? this.defaults;
  }

  override render() {
    const current = this._current;
    return html`
      <div class="sheet" @click=${(event: Event) => {
        if (event.target === event.currentTarget) {
          this.dispatchEvent(new CustomEvent('dialog-close'));
        }
      }}>
        <div class="panel">
          <h2>${t(this.language, 'defaults_title')}</h2>
          <div class="note">${t(this.language, 'defaults_help')}</div>
          ${this.error !== null
            ? html`<div class="error">${this.error}</div>`
            : nothing}

          <shabbat-device-settings
            .states=${this.states}
            .devices=${current.devices ?? []}
            .settings=${current.settings ?? {}}
            .disabled=${!this.canWrite}
            .language=${this.language}
            @settings-changed=${(event: Event) => {
              this._draft = {
                ...current,
                settings: (event as CustomEvent).detail.settings,
              };
            }}
          ></shabbat-device-settings>

          <div class="actions">
            <button @click=${() => this.dispatchEvent(new CustomEvent('dialog-close'))}>
              ${t(this.language, 'cancel')}
            </button>
            ${this.canWrite
              ? html`<button
                  class="save"
                  ?disabled=${this.busy}
                  @click=${() =>
                    this.dispatchEvent(
                      new CustomEvent('defaults-save', {
                        // Exactly the two keys validate_defaults accepts.
                        // Anything else is rejected outright, not ignored.
                        detail: {
                          defaults: {
                            devices: current.devices ?? [],
                            settings: current.settings ?? {},
                          },
                        },
                      }),
                    )}
                >
                  ${t(this.language, 'save')}
                </button>`
              : nothing}
          </div>
        </div>
      </div>
    `;
  }
}
```

- [ ] **Step 5: Run tests and typecheck**

```bash
npm --prefix frontend test && npm --prefix frontend run typecheck
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/defaults-dialog.ts frontend/src/strings.ts frontend/test/defaults-dialog.test.ts
git commit -m "feat: the shared-defaults dialog"
```

---

### Task 7: profile chips and the defaults gear in the header

**Files:**
- Modify: `frontend/src/block-header.ts`
- Test: `frontend/test/block-header.test.ts`

**Interfaces:**
- Consumes: existing `<shabbat-block-header>` properties.
- Produces: two new properties — `selectedProfile: number`, `canWrite: boolean` (already present) — and two new events: `profile-selected` (detail `{ profile }`) and `defaults-open`.

- [ ] **Step 1: Write the failing tests**

Append to `frontend/test/block-header.test.ts`:

```ts
describe('profile chips', () => {
  it('offers 1, 2 and 3 day chips', async () => {
    const el = await render({ selectedProfile: 1 });
    const chips = [...el.shadowRoot!.querySelectorAll('.chip')].map(
      (c) => (c as HTMLElement).textContent!.trim(),
    );
    expect(chips).toEqual(['1d', '2d', '3d']);
  });

  it('marks the selected one', async () => {
    const el = await render({ selectedProfile: 3 });
    const active = el.shadowRoot!.querySelector('.chip.active') as HTMLElement;
    expect(active.textContent!.trim()).toBe('3d');
  });

  it('reports a selection rather than changing itself', async () => {
    const el = await render({ selectedProfile: 1 });
    const listener = vi.fn();
    el.addEventListener('profile-selected', listener);

    (el.shadowRoot!.querySelectorAll('.chip')[2] as HTMLElement).click();

    expect((listener.mock.calls[0][0] as CustomEvent).detail).toEqual({ profile: 3 });
    expect((el as unknown as { selectedProfile: number }).selectedProfile).toBe(1);
  });

  it('offers the defaults gear to a writer and not to a reader', async () => {
    expect((await render({ canWrite: true })).shadowRoot!.querySelector('.gear'))
      .not.toBeNull();
    expect((await render({ canWrite: false })).shadowRoot!.querySelector('.gear'))
      .toBeNull();
  });

  it('asks for the defaults dialog when the gear is used', async () => {
    const el = await render({ canWrite: true });
    const listener = vi.fn();
    el.addEventListener('defaults-open', listener);
    (el.shadowRoot!.querySelector('.gear') as HTMLElement).click();
    expect(listener).toHaveBeenCalledOnce();
  });
});
```

Add `selectedProfile: 1` to the defaults in that file's existing `render` helper.

- [ ] **Step 2: Run and watch them fail**

```bash
npm --prefix frontend test block-header
```

Expected: FAIL — no `.chip` elements.

- [ ] **Step 3: Add the property and the markup**

In `frontend/src/block-header.ts`, add the property:

```ts
  @property({ type: Number }) selectedProfile = 1;
```

Add to `static override styles`:

```css
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
```

Insert inside the existing `.header` div, before the master button:

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
        </div>
        ${this.canWrite
          ? html`<button
              class="gear"
              @click=${() => this.dispatchEvent(new CustomEvent('defaults-open'))}
            >
              ⚙
            </button>`
          : nothing}
```

- [ ] **Step 4: Run tests and typecheck**

```bash
npm --prefix frontend test && npm --prefix frontend run typecheck
```

Expected: PASS, including every pre-existing block-header test.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/block-header.ts frontend/test/block-header.test.ts
git commit -m "feat: profile chips and the defaults gear"
```

---

### Task 8: the per-day add button

**Files:**
- Modify: `frontend/src/day-group.ts`
- Test: `frontend/test/day-group.test.ts`

**Interfaces:**
- Consumes: existing `<shabbat-day-group>` properties.
- Produces: new property `canWrite: boolean`; new event `rule-add` with detail `{ day }`.

**Why per-day:** the day is implied by where you tapped, so it is one fewer decision in the form and one fewer thing to get wrong.

- [ ] **Step 1: Write the failing tests**

```ts
it('offers an add button that names its own day', async () => {
  const el = await render({ group: group({ day: '1' }), canWrite: true });
  const listener = vi.fn();
  el.addEventListener('rule-add', listener);

  (el.shadowRoot!.querySelector('.add') as HTMLElement).click();

  expect((listener.mock.calls[0][0] as CustomEvent).detail).toEqual({ day: '1' });
});

it('offers no add button to a read-only user', async () => {
  const el = await render({ canWrite: false });
  expect(el.shadowRoot!.querySelector('.add')).toBeNull();
});

it('still offers add on a day with no rules', async () => {
  const el = await render({ group: group({ rules: [] }), canWrite: true });
  expect(el.shadowRoot!.querySelector('.add')).not.toBeNull();
});
```

Add `canWrite: false` to the file's existing `render` defaults.

- [ ] **Step 2: Run and watch them fail**

```bash
npm --prefix frontend test day-group
```

Expected: FAIL — no `.add` element.

- [ ] **Step 3: Add the property, style and markup**

```ts
  @property({ type: Boolean }) canWrite = false;
```

```css
    .add {
      font: inherit;
      font-size: 0.9em;
      background: none;
      border: none;
      color: var(--primary-color, #03a9f4);
      padding-block: 6px;
      padding-inline: 4px;
      cursor: pointer;
    }
```

Inside the existing single root element, after the rules and before the marker:

```ts
      ${this.canWrite
        ? html`<button
            class="add"
            @click=${() =>
              this.dispatchEvent(
                new CustomEvent('rule-add', { detail: { day: this.group.day } }),
              )}
          >
            + ${t(this.language, 'add_rule')}
          </button>`
        : nothing}
```

- [ ] **Step 4: Run tests and typecheck**

```bash
npm --prefix frontend test && npm --prefix frontend run typecheck
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/day-group.ts frontend/test/day-group.test.ts
git commit -m "feat: a per-day add button, so the day is never a question"
```

---

### Task 9: wire it all into the card

**Files:**
- Modify: `frontend/src/card.ts`, `frontend/src/rule-row.ts`, `frontend/src/strings.ts`
- Test: `frontend/test/card.test.ts`

**Interfaces:**
- Consumes: every element and pure function above.
- Produces: the complete authoring loop.

This is where the websocket commands are actually sent. Everything before this task is inert.

- [ ] **Step 1: Add the preview-banner strings**

```ts
    preview_banner: 'Preview — not the coming Shabbat. Dates are not shown because this block is not scheduled.',
```

```ts
    preview_banner: 'תצוגה מקדימה — לא השבת הקרובה. התאריכים אינם מוצגים כי הבלוק הזה אינו מתוכנן.',
```

- [ ] **Step 2: Make a rule row report a tap**

In `frontend/src/rule-row.ts`, add to the `.row` div:

```ts
        @click=${() =>
          this.dispatchEvent(
            new CustomEvent('rule-open', {
              detail: { rule: this.rule },
              bubbles: true,
              composed: true,
            }),
          )}
```

`bubbles` and `composed` are both required: the event has to cross the shadow boundaries of `<shabbat-day-group>` and reach the card.

- [ ] **Step 3: Write the failing tests**

Append to `frontend/test/card.test.ts`:

```ts
describe('authoring', () => {
  const withRules = () =>
    state({ rules: [
      { id: 'r1', profile: 1, day: '1', time: '11:00:00', action: 'on',
        devices: [], settings: {}, name: null, icon: null, enabled: true,
        script: null, variables: {}, replay_on_restart: false, color: null },
    ] });

  it('opens the dialog when a row asks to be opened', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(withRules());
    await el.updateComplete;

    el.shadowRoot!.querySelector('shabbat-day-group')!.dispatchEvent(
      new CustomEvent('rule-open', {
        detail: { rule: withRules().rules[0] }, bubbles: true, composed: true,
      }),
    );
    await el.updateComplete;

    expect(el.shadowRoot!.querySelector('shabbat-rule-dialog')).not.toBeNull();
  });

  it('sends rules/update with only the changed fields', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(withRules());
    await el.updateComplete;
    el._editing = withRules().rules[0];
    await el.updateComplete;

    el.shadowRoot!.querySelector('shabbat-rule-dialog')!.dispatchEvent(
      new CustomEvent('dialog-save', {
        detail: {
          rule: withRules().rules[0],
          form: { ...ruleToForm(withRules().rules[0]), time: '12:00:00' },
        },
      }),
    );
    await el.updateComplete;

    expect(hass.callWS).toHaveBeenCalledWith({
      type: 'shabbat_scheduler/rules/update',
      rule_id: 'r1',
      changes: { time: '12:00:00' },
    });
  });

  it('sends rules/create carrying the selected profile', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(state());
    el._selectedProfile = 3;
    el._creatingDay = '2';
    await el.updateComplete;

    el.shadowRoot!.querySelector('shabbat-rule-dialog')!.dispatchEvent(
      new CustomEvent('dialog-save', {
        detail: { rule: null, form: { ...EMPTY, day: '2', time: '11:00:00' } },
      }),
    );
    await el.updateComplete;

    const sent = hass.callWS.mock.calls[0][0];
    expect(sent.type).toBe('shabbat_scheduler/rules/create');
    expect(sent.rule.profile).toBe(3);
  });

  it('keeps the dialog open and shows the message when the server refuses', async () => {
    const { hass, send } = fakeHass();
    hass.callWS = vi.fn(async () => { throw { code: 'invalid_format', message: 'time is not a valid clock time' }; });
    const el = await mount(hass);
    send(withRules());
    el._editing = withRules().rules[0];
    await el.updateComplete;

    el.shadowRoot!.querySelector('shabbat-rule-dialog')!.dispatchEvent(
      new CustomEvent('dialog-save', {
        detail: { rule: withRules().rules[0], form: ruleToForm(withRules().rules[0]) },
      }),
    );
    await el.updateComplete;
    await el.updateComplete;

    const dialog = el.shadowRoot!.querySelector('shabbat-rule-dialog') as any;
    expect(dialog).not.toBeNull();
    expect(dialog.error).toContain('not a valid clock time');
  });

  it('shows the preview banner and hides dates for a non-current profile', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(withRules());
    el._selectedProfile = 3;
    await el.updateComplete;

    expect(el.shadowRoot!.textContent).toContain('Preview');
    const groups = [...el.shadowRoot!.querySelectorAll('shabbat-day-group')];
    expect(groups.length).toBe(4);
    for (const group of groups) {
      expect((group as any).group.date).toBeNull();
    }
  });

  it('duplicating opens a create pre-filled from the original', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(withRules());
    el._editing = withRules().rules[0];
    await el.updateComplete;

    el.shadowRoot!.querySelector('shabbat-rule-dialog')!.dispatchEvent(
      new CustomEvent('dialog-duplicate', {
        detail: {
          rule: withRules().rules[0],
          form: ruleToForm(withRules().rules[0]),
        },
      }),
    );
    await el.updateComplete;

    const dialog = el.shadowRoot!.querySelector('shabbat-rule-dialog') as any;
    // A create, not an edit - saving must add a rule, not overwrite one.
    expect(dialog.rule).toBeNull();
    // ...but carrying the original's values, or it duplicates nothing.
    expect(dialog.seed.time).toBe('11:00:00');
  });

  it('offers no authoring at all to a read-only user', async () => {
    const { hass, send } = fakeHass({ user: { is_admin: false } });
    const el = await mount(hass);
    send(withRules());
    await el.updateComplete;
    const group = el.shadowRoot!.querySelector('shabbat-day-group') as any;
    expect(group.canWrite).toBe(false);
  });
});
```

Add to the top of the file:

```ts
import { ruleToForm } from '../src/format';

const EMPTY = {
  day: 'erev', time: '', action: 'on', devices: [], settings: {},
  name: null, icon: null, color: null, enabled: true, script: null,
  variables: {}, replay_on_restart: false,
};
```

and add `callWS: vi.fn(async () => ({}))` to the `fakeHass` object, returning it alongside `callService`.

- [ ] **Step 4: Run and watch them fail**

```bash
npm --prefix frontend test card
```

Expected: FAIL — no `shabbat-rule-dialog` is rendered and `callWS` is never called.

- [ ] **Step 5: Wire the card**

Add the imports:

```ts
import './rule-dialog';
import './defaults-dialog';
import { buildGroups, formToChanges, formToCreate, isPreview } from './format';
import type { CardState, DayGroup, RuleData, RuleFormState } from './types';
```

Add the state:

```ts
  @state() private _selectedProfile: number | null = null;
  @state() private _editing: RuleData | null = null;
  @state() private _creatingDay: string | null = null;
  @state() private _defaultsOpen = false;
  @state() private _dialogError: string | null = null;
  @state() private _busy = false;
```

Add the profile resolution and the groups getter:

```ts
  /** The selected profile, defaulting to the coming block's length. */
  private get _profile(): number {
    return this._selectedProfile ?? this._state?.block?.length ?? 1;
  }

  private get _groups(): DayGroup[] {
    const state = this._state;
    if (state === null || !Array.isArray(state.rules)) return [];
    return buildGroups(state, this._profile);
  }
```

Note this replaces the existing `_groups`, which bailed on `!state.block`. With a profile selected the card must still render when no block can be derived — that is the dead end this plan removes.

Add the command sender and the handlers:

```ts
  /**
   * A websocket command, with its rejection surfaced.
   *
   * Nothing here is optimistic: the dialog closes only after the server
   * accepts, and the redraw comes from the following push. On rejection
   * the dialog stays open carrying the server's own message, because
   * `rule_schema.py` owns validation and its wording is the truth.
   */
  private async _send(message: object): Promise<boolean> {
    this._busy = true;
    this._dialogError = null;
    try {
      await this._hass.callWS(message);
      return true;
    } catch (err) {
      const detail = err as { message?: string } | null;
      this._dialogError = detail?.message ?? String(err);
      return false;
    } finally {
      this._busy = false;
    }
  }

  private _closeDialogs = () => {
    this._editing = null;
    this._creatingDay = null;
    this._duplicateSeed = null;
    this._defaultsOpen = false;
    this._dialogError = null;
  };

  private _onRuleOpen = (event: Event) => {
    this._editing = (event as CustomEvent).detail.rule as RuleData;
    this._creatingDay = null;
    this._duplicateSeed = null;
    this._dialogError = null;
  };

  private _onRuleAdd = (event: Event) => {
    this._creatingDay = (event as CustomEvent).detail.day as string;
    this._editing = null;
    this._duplicateSeed = null;
    this._dialogError = null;
  };

  private _onSave = async (event: Event) => {
    const { form, rule } = (event as CustomEvent).detail as {
      form: RuleFormState;
      rule: RuleData | null;
    };
    const ok =
      rule === null
        ? await this._send({
            type: 'shabbat_scheduler/rules/create',
            rule: formToCreate(form, this._profile),
          })
        : await this._saveChanges(form, rule);
    if (ok) this._closeDialogs();
  };

  private async _saveChanges(form: RuleFormState, rule: RuleData) {
    const changes = formToChanges(form, rule);
    // Nothing changed - closing without a round trip is the honest
    // outcome, and it keeps an untouched rule out of the logbook.
    if (Object.keys(changes).length === 0) return true;
    return this._send({
      type: 'shabbat_scheduler/rules/update',
      rule_id: rule.id,
      changes,
    });
  }

  private _onDelete = async (event: Event) => {
    const { rule } = (event as CustomEvent).detail as { rule: RuleData };
    if (await this._send({
      type: 'shabbat_scheduler/rules/delete',
      rule_id: rule.id,
    })) {
      this._closeDialogs();
    }
  };

  @state() private _duplicateSeed: RuleFormState | null = null;

  private _onDuplicate = (event: Event) => {
    // Composed client-side from rules/create: the dialog reopens as a
    // CREATE carrying the same values, so the user can move it before
    // saving. The server generates the id, so no rules/duplicate command
    // is needed. `_duplicateSeed` must be reactive and must be passed to
    // the dialog's `seed` property - without that the dialog reseeds from
    // EMPTY_FORM and a duplicate duplicates nothing.
    const { form } = (event as CustomEvent).detail as { form: RuleFormState };
    this._editing = null;
    this._creatingDay = form.day;
    this._duplicateSeed = form;
    this._dialogError = null;
  };

  private _onDefaultsSave = async (event: Event) => {
    const { defaults } = (event as CustomEvent).detail;
    if (await this._send({
      type: 'shabbat_scheduler/defaults/update',
      defaults,
    })) {
      this._closeDialogs();
    }
  };
```

In `render()`, pass the new properties down and host the dialogs. Replace the `<shabbat-block-header>` and day-group loop with:

```ts
        <shabbat-block-header
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
        ${isPreview(this._state, this._profile)
          ? html`<div class="preview">${t(this._language, 'preview_banner')}</div>`
          : nothing}
```

and give each `<shabbat-day-group>` `.canWrite=${this._canWrite}` plus `@rule-add=${this._onRuleAdd}`, and add `@rule-open=${this._onRuleOpen}` to the `<ha-card>`.

After the day groups, inside the same `<ha-card>`:

```ts
        ${this._editing !== null || this._creatingDay !== null
          ? html`<shabbat-rule-dialog
              .rule=${this._editing}
              .seed=${this._duplicateSeed}
              .day=${this._creatingDay ?? this._editing?.day ?? 'erev'}
              .profile=${this._profile}
              .defaults=${this._state.defaults}
              .states=${this._hass?.states ?? {}}
              .canWrite=${this._canWrite}
              .busy=${this._busy}
              .error=${this._dialogError}
              .language=${this._language}
              @dialog-save=${this._onSave}
              @dialog-delete=${this._onDelete}
              @dialog-duplicate=${this._onDuplicate}
              @dialog-close=${this._closeDialogs}
            ></shabbat-rule-dialog>`
          : nothing}
        ${this._defaultsOpen
          ? html`<shabbat-defaults-dialog
              .defaults=${this._state.defaults}
              .states=${this._hass?.states ?? {}}
              .canWrite=${this._canWrite}
              .busy=${this._busy}
              .error=${this._dialogError}
              .language=${this._language}
              @defaults-save=${this._onDefaultsSave}
              @dialog-close=${this._closeDialogs}
            ></shabbat-defaults-dialog>`
          : nothing}
```

Add the banner style:

```css
    .preview {
      background: var(--secondary-background-color, #f4f4f4);
      border-inline-start: 3px solid var(--primary-color, #03a9f4);
      padding-block: 8px;
      padding-inline: 12px;
      margin-block: 8px;
      font-size: 0.9em;
    }
```

- [ ] **Step 6: Run everything**

```bash
npm --prefix frontend test && npm --prefix frontend run typecheck
```

Expected: PASS, including every pre-existing card test.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/card.ts frontend/src/rule-row.ts frontend/src/strings.ts frontend/test/card.test.ts
git commit -m "feat: the authoring loop - open, save, delete, duplicate, defaults"
```

---

### Task 10: rebuild the bundle and document what shipped

**Files:**
- Modify: `custom_components/shabbat_scheduler/www/shabbat-scheduler-card.js`, `frontend/bundle-manifest.json`, `frontend/src/version.ts`, `custom_components/shabbat_scheduler/frontend.py`, `README.md`, `docs/known-behaviours.md`
- Test: `tests/test_frontend.py` (existing tests must pass unchanged)

**Interfaces:**
- Consumes: everything above.
- Produces: a committed bundle serving the authoring card.

- [ ] **Step 1: Bump both versions in step**

`frontend/src/version.ts` and `custom_components/shabbat_scheduler/frontend.py` both carry `CARD_VERSION`. Set both to `0.2.0`. `tests/test_frontend.py` fails if they drift, and the Lovelace resource URL is stamped with the Python one — an unbumped version means browsers keep serving the old card from cache.

- [ ] **Step 2: Rebuild**

```bash
npm --prefix frontend run build
git status --porcelain
```

Expected: the bundle and `frontend/bundle-manifest.json` are both modified. The manifest is regenerated by the build; do not hand-edit it.

- [ ] **Step 3: Run the Python suite**

```bash
uv run pytest -q
```

Expected: PASS. The bundle tests check all five original element tags plus `customElements.define` and the `const CARD_VERSION` declaration — confirm they now see `0.2.0`.

- [ ] **Step 4: Document in `README.md`**

Replace the last paragraph of the `## The card` section (the one saying editing comes later) with:

````markdown
Tap any rule to edit it, or use the **+ add** button under a day to create one
there — the day and block length are taken from where you tapped. The dialog
reads each device's own capabilities, so it offers exactly the fan modes and
temperature range that device supports; select several devices and you get only
what they all support, stated plainly.

The **1d / 2d / 3d** chips switch which block length you are looking at, so a
3-day Chag can be set up long before one arrives. Any length other than the
coming one is shown as a preview: no dates, no candle-lighting or havdalah
markers, and a banner saying so. Editing works exactly the same there.

The gear opens the **shared defaults** — the devices and settings every rule
inherits unless it sets its own.
````

- [ ] **Step 5: Document the accepted trade-off in `docs/known-behaviours.md`**

````markdown
## Deleting a rule is immediate, with no confirmation

Delete lives inside the edit dialog and acts at once. There is no confirmation
step and no undo: the rule and its switch entity are gone.

This was chosen deliberately rather than overlooked. Reaching delete already
takes two intentional actions — open the row, then tap delete — and a
confirmation modal on a wall tablet becomes muscle memory within a week, which
buys nothing. Recovering a deleted rule means adding it again, or re-importing
a YAML export.
````

- [ ] **Step 6: Commit**

```bash
git add custom_components/shabbat_scheduler/www frontend/bundle-manifest.json frontend/src/version.ts custom_components/shabbat_scheduler/frontend.py README.md docs/known-behaviours.md
git commit -m "build: ship the authoring card, and document what it does"
```

---

### Task 11: end-to-end, in a real browser

**Files:**
- Modify: `e2e/test_card_e2e.py`

**Interfaces:**
- Consumes: the built bundle and the running dev container.
- Produces: proof the authoring loop works outside happy-dom.

**Why this matters here specifically:** every dialog above is tested under happy-dom, which does not implement layout, focus, or real event dispatch faithfully. The read view already had a defect class that only a real browser exposed. A form is far more sensitive to that than a list.

**Production is not involved.** Nothing in this task may address 192.168.1.14.

- [ ] **Step 1: Write the failing tests**

Append to `e2e/test_card_e2e.py`:

```python
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
    card = _card(page, base_url)
    card.locator("shabbat-block-header button.chip").nth(2).click()

    page.wait_for_timeout(500)
    dates = card.locator("shabbat-day-group .date").all_inner_texts()
    assert all(date.strip() == "" for date in dates), dates
    assert "Preview" in card.inner_text() or "תצוגה" in card.inner_text()
```

- [ ] **Step 2: Bring the container up and run them**

```bash
docker compose -f dev/docker-compose.yml up -d
# wait for http://127.0.0.1:8124 to answer
export HA_DEV_TOKEN=$(uv run python dev/seed.py)
uv run pytest e2e/ -q
```

Expected: the three new tests FAIL before Tasks 1–10 are built, and PASS after. If `seed.py` reports the onboarding step failing, the container already has its user — `docker compose -f dev/docker-compose.yml down -v` and start again.

If the block does not match the seeded dates, clear the persisted active block as `dev/README.md` describes; re-seeding the sensors alone does not move it.

- [ ] **Step 3: Confirm the fast suite is untouched**

```bash
uv run pytest -q && npm --prefix frontend test
```

Expected: PASS, and `e2e/` is not collected by the default run.

- [ ] **Step 4: Commit**

```bash
git add e2e/test_card_e2e.py
git commit -m "test: the authoring loop in a real browser"
```

---

## Plan Self-Review

**Spec coverage:** device-aware form → Tasks 1, 4. Intersection, unreadable, non-climate, kept-orphan setting → Tasks 1, 4. Profile selector and preview mode → Tasks 2, 7, 9. Rule dialog with advanced fields → Task 5. Save as partial update → Tasks 3, 9. Duplicate composed client-side → Tasks 5, 9. Delete without confirmation → Tasks 5, 9, documented in 10. Defaults editor → Tasks 6, 7, 9. Server-owned validation with the dialog staying open → Tasks 5, 9. Non-admin read-only → Tasks 5, 6, 7, 8, 9. No new backend command → nothing in this plan touches Python except `CARD_VERSION`. Testing at three levels → Tasks 1–9 (vitest), 11 (Playwright), 10 (the existing Python bundle tests).

**Placeholder scan:** clean — every code step carries the actual code, and every test step the actual assertions.

**Type consistency:** `RuleFormState` is defined in Task 3 and used in Tasks 5 and 9. `DeviceOptions` and `HassEntity` are defined in Task 1 and used in Tasks 1, 4, 5, 6. `buildGroups(state, profile?)` is defined in Task 2 and called in Task 9. Event names are consistent: `settings-changed`, `devices-changed`, `dialog-save`, `dialog-delete`, `dialog-duplicate`, `dialog-close`, `defaults-save`, `profile-selected`, `defaults-open`, `rule-add`, `rule-open`.

**A gap this review caught, now closed.** The first draft declared `devices-changed` on `<shabbat-device-settings>` but wired no picker — so a rule's devices could only come from the defaults, and "pick a device and the form adapts" was unreachable. That is the spec's central promise, so it is now Task 4a below rather than a deferral.

**One thing deliberately left out:** `variables` has no field. It applies only to `custom` rules driving a script, and a key-value editor is not worth the surface until someone wants one. A `custom` rule's script is editable; its variables stay YAML-only.

---

### Task 4a: choosing the devices

**Files:**
- Modify: `frontend/src/format.ts`, `frontend/src/device-settings.ts`, `frontend/src/strings.ts`
- Test: `frontend/test/format.test.ts`, `frontend/test/device-settings.test.ts`

**Interfaces:**
- Consumes: `deviceOptions` (Task 1), `<shabbat-device-settings>` (Task 4).
- Produces: `selectableDevices(states) -> string[]`; `<shabbat-device-settings>` fires `devices-changed` with detail `{ devices }`.

**Why:** without this, picking a device is impossible and the device-aware form only ever reflects the defaults. A plain multi-select populated from `hass.states` is used rather than Home Assistant's `<ha-entity-picker>`: the picker is not reliably available to a custom element under test, and this plan adds no dependencies. The domains offered are `climate`, `switch` and `input_boolean` — the three this integration can actually drive.

- [ ] **Step 1: Write the failing test for the pure part**

Append to `frontend/test/format.test.ts`:

```ts
import { selectableDevices } from '../src/format';

describe('selectableDevices', () => {
  const states = {
    'climate.salon': SALON,
    'input_boolean.t': BOOLEAN,
    'switch.boiler': { state: 'off', attributes: {} },
    'sensor.temperature': { state: '21', attributes: {} },
    'light.kitchen': { state: 'off', attributes: {} },
  };

  it('offers only the domains this integration can drive', () => {
    expect(selectableDevices(states)).toEqual([
      'climate.salon', 'input_boolean.t', 'switch.boiler',
    ]);
  });

  it('is sorted, so the list does not reshuffle between renders', () => {
    const ids = selectableDevices(states);
    expect(ids).toEqual([...ids].sort());
  });

  it('copes with no entities at all', () => {
    expect(selectableDevices({})).toEqual([]);
  });
});
```

- [ ] **Step 2: Run and watch it fail**

```bash
npm --prefix frontend test format
```

Expected: FAIL — `selectableDevices is not a function`.

- [ ] **Step 3: Implement it in `format.ts`**

```ts
/** The domains this integration can actually drive. */
const DRIVABLE = ['climate.', 'input_boolean.', 'switch.'];

/**
 * Entities a rule may target, sorted.
 *
 * Sorted because an unsorted list reshuffles whenever `hass.states` is
 * rebuilt, which is every state change in the whole system - a select
 * whose options move under the user's finger.
 */
export function selectableDevices(
  states: Record<string, HassEntity | undefined>,
): string[] {
  return Object.keys(states)
    .filter((id) => DRIVABLE.some((prefix) => id.startsWith(prefix)))
    .sort();
}
```

- [ ] **Step 4: Write the failing element tests**

Append to `frontend/test/device-settings.test.ts`:

```ts
it('lists the drivable entities as options', async () => {
  const el = await render({});
  const options = [...el.shadowRoot!.querySelectorAll('.devices option')].map(
    (o) => (o as HTMLOptionElement).value,
  );
  expect(options).toContain('climate.salon');
  expect(options).toContain('climate.kids');
});

it('marks the currently selected devices', async () => {
  const el = await render({ devices: ['climate.kids'] });
  const selected = [...el.shadowRoot!.querySelectorAll('.devices option')]
    .filter((o) => (o as HTMLOptionElement).selected)
    .map((o) => (o as HTMLOptionElement).value);
  expect(selected).toEqual(['climate.kids']);
});

it('reports a device change rather than mutating its own property', async () => {
  const el = await render({ devices: ['climate.salon'] });
  const listener = vi.fn();
  el.addEventListener('devices-changed', listener);

  const select = el.shadowRoot!.querySelector('.devices') as HTMLSelectElement;
  for (const option of select.options) option.selected = option.value === 'climate.kids';
  select.dispatchEvent(new Event('change'));

  expect((listener.mock.calls[0][0] as CustomEvent).detail.devices)
    .toEqual(['climate.kids']);
  expect(el.devices).toEqual(['climate.salon']);
});

it('re-offers options for the newly chosen device, not the old one', async () => {
  const el = await render({ devices: ['climate.kids'] });
  const fans = [...el.shadowRoot!.querySelectorAll('.fan option')].map(
    (o) => (o as HTMLOptionElement).value,
  );
  expect(fans).toContain('silent');
  expect(fans).not.toContain('quiet');
});
```

- [ ] **Step 5: Run and watch them fail**

```bash
npm --prefix frontend test device-settings
```

Expected: FAIL — no `.devices` element.

- [ ] **Step 6: Add the picker to `device-settings.ts`**

Import `selectableDevices` alongside `deviceOptions`, add the string usage, and render this as the first field inside the existing `.settings` root:

```ts
        <div class="field">
          <label for="devices">${t(this.language, 'devices')}</label>
          <select
            id="devices"
            class="devices"
            multiple
            size="4"
            ?disabled=${this.disabled}
            @change=${(event: Event) => {
              const select = event.target as HTMLSelectElement;
              const devices = [...select.selectedOptions].map((o) => o.value);
              this.dispatchEvent(
                new CustomEvent('devices-changed', { detail: { devices } }),
              );
            }}
          >
            ${selectableDevices(this.states).map(
              (id) => html`
                <option value=${id} ?selected=${this.devices.includes(id)}>
                  ${id}
                </option>
              `,
            )}
          </select>
        </div>
```

- [ ] **Step 7: Handle it in the rule dialog**

In `frontend/src/rule-dialog.ts`, add to the `<shabbat-device-settings>` element:

```ts
                    @devices-changed=${(event: Event) =>
                      this._patch({ devices: (event as CustomEvent).detail.devices })}
```

And in `frontend/src/defaults-dialog.ts`:

```ts
            @devices-changed=${(event: Event) => {
              this._draft = {
                ...current,
                devices: (event as CustomEvent).detail.devices,
              };
            }}
```

- [ ] **Step 8: Run everything**

```bash
npm --prefix frontend test && npm --prefix frontend run typecheck
```

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/format.ts frontend/src/device-settings.ts frontend/src/rule-dialog.ts frontend/src/defaults-dialog.ts frontend/test/format.test.ts frontend/test/device-settings.test.ts
git commit -m "feat: choosing the devices a rule drives"
```

**Ordering note for the executor:** Task 4a depends on Tasks 1 and 4, and Tasks 5 and 6 must exist before its Step 7 can edit them. Run it **after Task 6** and before Task 7, or fold Steps 7–8 into Task 9's wiring if that reads more naturally.
