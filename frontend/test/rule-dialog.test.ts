import { describe, expect, it, vi } from 'vitest';
import '../src/rule-dialog';
import { ruleToForm } from '../src/format';
import type { RuleData } from '../src/types';

const existing: RuleData = {
  id: 'r1', profile: 1, day: '1', time: '11:00:00',
  action: 'climate.set_temperature',
  target: { entity_id: ['climate.salon'] },
  data: { temperature: 26 },
  condition: [],
  replay: { enabled: false },
  name: 'Morning', icon: null, enabled: true, color: null,
  last_outcome: null,
};

async function render(props: Record<string, unknown> = {}) {
  const el = document.createElement('shabbat-rule-dialog') as HTMLElement &
    Record<string, any>;
  Object.assign(el, {
    rule: existing, day: '1', profile: 1, defaults: {},
    canWrite: true, language: 'en', error: null, busy: false,
    hass: { states: {} }, ...props,
  });
  document.body.appendChild(el);
  await el.updateComplete;
  return el;
}

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

  // ---- the day a create is authored under ----
  //
  // The dialog stamps `day` in two separate places - once for an empty
  // create, once for a seeded (duplicate) one - and neither had a test.
  // Either one silently falling back to 'erev' would put every added rule
  // on erev while every other assertion in the suite stayed green, and an
  // air conditioner would run on the wrong day of a three-day Chag.

  it('creates on the day it was opened for, not on erev', async () => {
    const el = await render({ rule: null, seed: null, day: '2' });
    const listener = vi.fn();
    el.addEventListener('dialog-save', listener);

    (el.shadowRoot!.querySelector('.save') as HTMLElement).click();

    expect((listener.mock.calls[0][0] as CustomEvent).detail.form.day).toBe('2');
  });

  it('re-stamps the day when the same dialog is reopened for another day', async () => {
    // The dialog instance persists across opens: a `day` that only took
    // effect on first construction would strand every later create on the
    // first day ever opened.
    const el = await render({ rule: null, seed: null, day: 'erev' });
    el.day = '3';
    await el.updateComplete;

    const listener = vi.fn();
    el.addEventListener('dialog-save', listener);
    (el.shadowRoot!.querySelector('.save') as HTMLElement).click();

    expect((listener.mock.calls[0][0] as CustomEvent).detail.form.day).toBe('3');
  });

  it('puts a duplicate on the day it was opened for, overriding the seed\'s own day', async () => {
    // The seed is the original rule's form, day and all. The dialog's own
    // `day` is where the user is putting the copy, and it must win.
    //
    // The target day is deliberately NOT 'erev'. Erev is what every
    // fallback in this chain falls back to, so a test that expects 'erev'
    // passes whether the day was honoured or hard-coded - verified: with
    // `day: 'erev'` here, forcing this branch to 'erev' left 168/168
    // green. '3' can only come from `this.day`.
    const el = await render({
      rule: null,
      seed: { ...ruleToForm(existing), day: '1' },
      day: '3',
    });
    const listener = vi.fn();
    el.addEventListener('dialog-save', listener);

    (el.shadowRoot!.querySelector('.save') as HTMLElement).click();

    const { form } = (listener.mock.calls[0][0] as CustomEvent).detail;
    expect(form.day).toBe('3');
    // ...while everything else still comes from the seed.
    expect(form.time).toBe('11:00:00');
    expect(form.name).toBe('Morning');
  });

  it('reseeds when a different rule is duplicated for the same day and profile', async () => {
    const other: RuleData = {
      ...existing, id: 'r2', name: 'Evening', time: '22:00:00',
      target: { entity_id: ['climate.mamad'] },
    };
    const el = await render({ rule: null, seed: ruleToForm(existing) });
    expect((el.shadowRoot!.querySelector('.name') as HTMLInputElement).value)
      .toBe('Morning');

    // A second, unrelated duplicate opened on the same day/profile - same
    // dialog instance, different rule copied. The key must tell them apart.
    el.seed = ruleToForm(other);
    await el.updateComplete;

    expect((el.shadowRoot!.querySelector('.name') as HTMLInputElement).value)
      .toBe('Evening');
    expect((el.shadowRoot!.querySelector('.time') as HTMLInputElement).value)
      .toBe('22:00:00');
  });

  it('does not reseed or discard typed input on an unrelated re-render while a create is open', async () => {
    const el = await render({ rule: null, seed: null });
    const name = el.shadowRoot!.querySelector('.name') as HTMLInputElement;
    name.value = 'Typed by the user';
    name.dispatchEvent(new Event('change'));
    await el.updateComplete;

    // Simulate an unrelated push arriving - e.g. `hass` reassigned elsewhere
    // in the system, propagating a new `defaults` reference with the same
    // day/profile/seed. This must not touch what the user has typed.
    el.defaults = { ...el.defaults };
    await el.updateComplete;

    expect((el.shadowRoot!.querySelector('.name') as HTMLInputElement).value)
      .toBe('Typed by the user');
  });

  it('still reseeds when switching from editing one rule to editing another', async () => {
    const el = await render({ rule: existing });
    expect((el.shadowRoot!.querySelector('.name') as HTMLInputElement).value)
      .toBe('Morning');

    const other: RuleData = {
      ...existing, id: 'r2', name: 'Evening', time: '22:00:00',
    };
    el.rule = other;
    await el.updateComplete;

    expect((el.shadowRoot!.querySelector('.name') as HTMLInputElement).value)
      .toBe('Evening');
    expect((el.shadowRoot!.querySelector('.time') as HTMLInputElement).value)
      .toBe('22:00:00');
  });

  // ---- fields the dialog seeds but does not itself touch on save ----
  //
  // `target`, `data`, `condition` and `replay` are now real editors (see
  // the tests further below), but a save where the user never touched
  // one of them must still carry it through unchanged: an edit must not
  // turn "the user did not touch this" into "this is now empty".

  it('carries the fields the user did not touch through a save untouched', async () => {
    // An edit that dropped a rule's conditions would make it fire on a
    // day it was meant to be blocked.
    const rule = {
      ...existing,
      condition: [{ condition: 'state', entity_id: 'binary_sensor.gate', state: 'on' }],
      replay: { enabled: true, within: '02:00:00' },
    };
    const el = await render({ rule });
    const listener = vi.fn();
    el.addEventListener('dialog-save', listener);

    const name = el.shadowRoot!.querySelector('.name') as HTMLInputElement;
    name.value = 'Renamed';
    name.dispatchEvent(new Event('change'));
    (el.shadowRoot!.querySelector('.save') as HTMLElement).click();

    const { form } = (listener.mock.calls[0][0] as CustomEvent).detail;
    expect(form.name).toBe('Renamed');
    expect(form.target).toEqual(rule.target);
    expect(form.data).toEqual(rule.data);
    expect(form.condition).toEqual(rule.condition);
    expect(form.replay).toEqual(rule.replay);
  });

  it('says so when a rule could not be migrated, instead of showing it as normal', async () => {
    const el = await render({
      rule: {
        ...existing,
        migration_error: 'no v2 target could be derived from the v1 devices',
      },
    });
    expect(el.shadowRoot!.textContent).toContain('could not be converted');
    expect(el.shadowRoot!.textContent).toContain('no v2 target could be derived');
  });

  // ---- the real editors, replacing the read-only block ----

  const editors = (el: any) => ({
    target: el.shadowRoot!.querySelector('shabbat-target-editor'),
    service: el.shadowRoot!.querySelector('shabbat-service-editor'),
    condition: el.shadowRoot!.querySelector('shabbat-condition-editor'),
    replay: el.shadowRoot!.querySelector('shabbat-replay-editor'),
  });

  it('offers all four editors instead of a read-only block', async () => {
    const el = await render();
    const found = editors(el);
    expect(found.target).not.toBeNull();
    expect(found.service).not.toBeNull();
    expect(found.condition).not.toBeNull();
    expect(found.replay).not.toBeNull();
    expect(el.shadowRoot!.querySelector('.readonly')).toBeNull();
    expect(el.shadowRoot!.querySelector('input.action')).toBeNull();
  });

  it('seeds every editor from the rule being edited', async () => {
    // Replay is deliberately seeded NON-default here ({enabled: false} is
    // both the fixture's usual value and the replay editor's own default,
    // so asserting that would pass even with the `.value` binding deleted
    // outright).
    const el = await render({
      rule: { ...existing, replay: { enabled: true, within: '02:00:00' } },
    });
    const found = editors(el);
    expect(found.service.action).toBe('climate.set_temperature');
    expect(found.service.data).toEqual({ temperature: 26 });
    expect(found.target.value).toEqual({ entity_id: ['climate.salon'] });
    expect(found.replay.value).toEqual({ enabled: true, within: '02:00:00' });
  });

  it('passes hass and language to the editors that need them', async () => {
    const el = await render();
    const found = editors(el);
    expect(found.service.hass).toBe(el.hass);
    expect(found.target.hass).toBe(el.hass);
    expect(found.condition.language).toBe('en');
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
    (el.shadowRoot!.querySelector('button.save') as HTMLElement).click();
    expect(saved[0].action).toBe('switch.turn_on');
    expect(saved[0].data).toEqual({});
  });

  /**
   * The OPPOSITE of the defaults dialog, deliberately, and the reason
   * `service-editor` reports "HA said nothing about data" separately from
   * "data is empty" instead of deciding for itself.
   *
   * Here the action is part of the rule. HA omits `data` from the event on
   * every service change, and data shaped for the service the author just
   * navigated away from does not belong to the one they picked - so it
   * goes. That is Home Assistant's own behaviour and it is right here. The
   * defaults dialog needs the other answer, because its `_action` is a
   * throwaway lens rather than a stored value.
   *
   * `toStrictEqual({})`, not `toEqual`: the thing to rule out is `data`
   * arriving as `undefined`, which `toEqual({})` accepts, and which would
   * reach `formToChanges` and go over the socket as a null.
   */
  it('clears the data when a service pick sends none, unlike the defaults dialog', async () => {
    const el = await render();      // seeded with data { temperature: 26 }
    const saved: any[] = [];
    el.addEventListener('dialog-save', (e: Event) => {
      saved.push((e as CustomEvent).detail.form);
    });
    editors(el).service.dispatchEvent(new CustomEvent('service-changed', {
      // The shape `service-editor` emits for a real HA service change.
      detail: { action: 'switch.turn_on' },
    }));
    await el.updateComplete;
    (el.shadowRoot!.querySelector('button.save') as HTMLElement).click();
    expect(saved[0].action).toBe('switch.turn_on');
    expect(saved[0].data).toStrictEqual({});
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
    (el.shadowRoot!.querySelector('button.save') as HTMLElement).click();
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
    (el.shadowRoot!.querySelector('button.save') as HTMLElement).click();
    expect(saved[0].condition).toEqual([
      { condition: 'state', entity_id: 'x', state: 'on' },
    ]);
    expect(saved[0].replay).toEqual({ enabled: true, within: '00:30:00' });
  });

  it('replaces replay wholesale rather than merging, so turning it off drops `within`', async () => {
    // Starts ENABLED with a `within` - the load-bearing direction. A
    // fixture that starts at `{enabled: false}` (the replay editor's own
    // default) can't catch a deep merge here: merging `{enabled: false}`
    // into an already-`{enabled: false}` form looks identical to
    // replacing it. `toStrictEqual` (not `toEqual`) so a merge that left
    // a stale `within: '02:00:00'` key present - which `toEqual` treats
    // as equal to `within: undefined` - actually fails this assertion.
    const el = await render({
      rule: { ...existing, replay: { enabled: true, within: '02:00:00' } },
    });
    const saved: any[] = [];
    el.addEventListener('dialog-save', (e: Event) => {
      saved.push((e as CustomEvent).detail.form);
    });
    editors(el).replay.dispatchEvent(new CustomEvent('replay-changed', {
      detail: { value: { enabled: false } },
    }));
    await el.updateComplete;
    (el.shadowRoot!.querySelector('button.save') as HTMLElement).click();
    expect(saved[0].replay).toStrictEqual({ enabled: false });
  });

  it('refuses to save while a condition is unparseable', async () => {
    // Seeded with one condition already present: `area` below is captured
    // from that pre-existing row, and non-keyed list rendering reuses the
    // same DOM node across the edits that follow, so it stays attached
    // throughout - starting from zero rows would mean `area` was captured
    // before any row (and its textarea) existed at all.
    const el = await render({
      rule: {
        ...existing,
        condition: [{ condition: 'state', entity_id: 'binary_sensor.gate', state: 'on' }],
      },
    });
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
    (el.shadowRoot!.querySelector('button.save') as HTMLElement).click();
    await el.updateComplete;
    expect(saved).toEqual([]);
    // The specific blocked-save message, not just any element with
    // `.error` - the generic error block also matches `.error`.
    expect(el.shadowRoot!.querySelector('.error.condition-blocked')).not.toBeNull();
    expect(area).not.toBeNull();
  });

  it('keeps the blocked-save banner up while a second condition row is still broken', async () => {
    // Two broken rows; fixing one must not clear the banner (and the
    // save refusal it explains) while the other is still unparseable -
    // `condition-changed` must ask the editor's CURRENT `hasError`, not
    // hard-code `false`.
    const el = await render({
      rule: {
        ...existing,
        condition: [
          { condition: 'state', entity_id: 'binary_sensor.a', state: 'on' },
          { condition: 'state', entity_id: 'binary_sensor.b', state: 'on' },
        ],
      },
    });
    const saved: any[] = [];
    el.addEventListener('dialog-save', () => { saved.push(true); });
    const condition = editors(el).condition as any;
    const boxes = () =>
      condition.shadowRoot.querySelectorAll('textarea') as NodeListOf<HTMLTextAreaElement>;

    boxes()[0].value = 'condition: [state';
    boxes()[0].dispatchEvent(new Event('change'));
    await condition.updateComplete;
    boxes()[1].value = 'condition: [state';
    boxes()[1].dispatchEvent(new Event('change'));
    await condition.updateComplete;
    await el.updateComplete;

    // Both rows broken: attempting to save raises the banner.
    (el.shadowRoot!.querySelector('button.save') as HTMLElement).click();
    await el.updateComplete;
    expect(saved).toEqual([]);
    expect(el.shadowRoot!.querySelector('.error.condition-blocked')).not.toBeNull();

    // Fix only the first row. The second is still broken - the banner
    // (and the refusal it explains) must not vanish.
    boxes()[0].value = 'condition: state';
    boxes()[0].dispatchEvent(new Event('change'));
    await condition.updateComplete;
    await el.updateComplete;

    expect(el.shadowRoot!.querySelector('.error.condition-blocked')).not.toBeNull();
    (el.shadowRoot!.querySelector('button.save') as HTMLElement).click();
    await el.updateComplete;
    expect(saved).toEqual([]);
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
});

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
