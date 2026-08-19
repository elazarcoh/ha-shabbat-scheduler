import { describe, expect, it, vi } from 'vitest';
import '../src/rule-dialog';
import { ruleToForm } from '../src/format';
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

  it('reseeds when a different rule is duplicated for the same day and profile', async () => {
    const other: RuleData = {
      ...existing, id: 'r2', name: 'Evening', time: '22:00:00',
      devices: ['climate.mamad'],
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
    // in the system, propagating a new `states` reference with the same
    // day/profile/seed. This must not touch what the user has typed.
    el.states = { ...el.states };
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

  const DEVICE_STATES = {
    'climate.salon': { state: 'off', attributes: {
      hvac_modes: ['off', 'cool'], fan_modes: ['auto', 'quiet'],
      min_temp: 16, max_temp: 31, target_temp_step: 0.5,
    } },
    'climate.mamad': { state: 'off', attributes: {} },
  };

  function devicesSelect(el: HTMLElement & Record<string, any>): HTMLSelectElement {
    const settings = el.shadowRoot!.querySelector('shabbat-device-settings') as HTMLElement &
      Record<string, any>;
    return settings.shadowRoot!.querySelector('.devices') as HTMLSelectElement;
  }

  it('never shows a rule\'s cleared devices as if the defaults were selected', async () => {
    // existing.devices is ['climate.salon']; clearing it must leave the
    // picker showing nothing selected, not silently redisplay the
    // defaults' devices as though they were the rule's own choice.
    const el = await render({
      defaults: { devices: ['climate.mamad', 'climate.salon'] },
      states: DEVICE_STATES,
    });

    const select = devicesSelect(el);
    for (const option of select.options) option.selected = false;
    select.dispatchEvent(new Event('change'));
    await el.updateComplete;

    const picked = [...devicesSelect(el).options].filter((o) => o.selected);
    expect(picked).toEqual([]);

    // Inheritance is now shown honestly, as a note, rather than by
    // faking the picker's selection.
    expect(el.shadowRoot!.textContent).toContain('climate.mamad');
    expect(el.shadowRoot!.textContent).toContain('climate.salon');
    expect(el.shadowRoot!.textContent).toContain('inherits');

    // And what would actually be saved agrees with what is shown: [].
    const listener = vi.fn();
    el.addEventListener('dialog-save', listener);
    (el.shadowRoot!.querySelector('.save') as HTMLElement).click();
    expect((listener.mock.calls[0][0] as CustomEvent).detail.form.devices).toEqual([]);
  });

  it('shows a rule\'s own devices with no inheritance note', async () => {
    const el = await render({
      defaults: { devices: ['climate.mamad'] },
      states: DEVICE_STATES,
    });

    const picked = [...devicesSelect(el).options]
      .filter((o) => o.selected)
      .map((o) => o.value);
    expect(picked).toEqual(['climate.salon']);
    expect(el.shadowRoot!.textContent).not.toContain('climate.mamad');
  });

  it('offers settings for the inherited devices even while the picker is empty', async () => {
    // The picker must show the truth (nothing selected), but the settings
    // beneath it must still reflect what will actually run: the inherited
    // devices from defaults.
    const el = await render({
      rule: { ...existing, devices: [] },
      defaults: { devices: ['climate.salon'] },
      states: DEVICE_STATES,
    });

    const picked = [...devicesSelect(el).options].filter((o) => o.selected);
    expect(picked).toEqual([]);

    const settings = el.shadowRoot!.querySelector('shabbat-device-settings') as HTMLElement &
      Record<string, any>;
    expect(settings.shadowRoot!.querySelector('.hvac')).not.toBeNull();
    const fans = [...settings.shadowRoot!.querySelectorAll('.fan option')].map(
      (o) => (o as HTMLOptionElement).value,
    );
    expect(fans).toContain('quiet');
  });
});
