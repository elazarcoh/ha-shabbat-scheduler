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
};

async function render(props: Record<string, unknown> = {}) {
  const el = document.createElement('shabbat-rule-dialog') as HTMLElement &
    Record<string, any>;
  Object.assign(el, {
    rule: existing, day: '1', profile: 1, defaults: {},
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

  // v1 had a separate `script` text field, shown only when the action was
  // the magic value 'custom'. In v2 a script rule is just an action, so
  // the special case is gone and the action itself is the text field.
  it('edits the action as free text, since any service is now valid', async () => {
    const el = await render({
      rule: { ...existing, action: 'script.turn_on' },
    });
    const action = el.shadowRoot!.querySelector('.action') as HTMLInputElement;
    expect(action.value).toBe('script.turn_on');

    const listener = vi.fn();
    el.addEventListener('dialog-save', listener);
    action.value = 'notify.mobile_app';
    action.dispatchEvent(new Event('change'));
    (el.shadowRoot!.querySelector('.save') as HTMLElement).click();

    expect((listener.mock.calls[0][0] as CustomEvent).detail.form.action)
      .toBe('notify.mobile_app');
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

  // ---- the fields the dialog cannot yet edit ----
  //
  // v1's device multi-select and climate settings form are gone: a rule is
  // now an arbitrary service call with a Home Assistant target selector
  // and an opaque data payload, and neither can be rendered honestly as a
  // device list and a temperature slider. The rule for this task is that
  // where the card cannot edit something it must SHOW THE TRUTH, never a
  // stale climate-shaped guess and never silence.

  it('shows the target, data, conditions and replay it cannot edit', async () => {
    const el = await render({
      rule: {
        ...existing,
        condition: [{ condition: 'state', entity_id: 'binary_sensor.gate', state: 'on' }],
        replay: { enabled: true, within: '02:00:00' },
      },
    });
    const text = el.shadowRoot!.textContent!;
    expect(text).toContain('climate.salon');     // target
    expect(text).toContain('temperature');       // data
    expect(text).toContain('binary_sensor.gate');// condition
    expect(text).toContain('02:00:00');          // replay window
    // ...and says out loud that they are not editable here, rather than
    // showing them as if they were inputs.
    expect(text).toContain('Not editable here');
    expect(el.shadowRoot!.querySelector('shabbat-device-settings')).toBeNull();
  });

  it('says a rule has no target rather than showing an empty gap', async () => {
    const el = await render({ rule: { ...existing, target: {}, data: {} } });
    expect((el.shadowRoot!.querySelector('.ro-target') as HTMLElement).textContent)
      .toContain('none');
    expect((el.shadowRoot!.querySelector('.ro-data') as HTMLElement).textContent)
      .toContain('none');
  });

  it('says a rule with no target of its own inherits the defaults', async () => {
    const el = await render({
      rule: { ...existing, target: {} },
      defaults: { target: { entity_id: ['climate.mamad'] } },
    });
    const text = (el.shadowRoot!.querySelector('.ro-target') as HTMLElement).textContent!;
    expect(text).toContain('inherits');
    expect(text).toContain('climate.mamad');
  });

  it('carries the fields it cannot edit through a save untouched', async () => {
    // The dialog must not turn "I cannot edit this" into "this is now
    // empty". An edit that dropped a rule's conditions would make it
    // fire on a day it was meant to be blocked.
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
});
