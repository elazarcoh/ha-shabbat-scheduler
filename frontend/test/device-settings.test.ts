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

  // ---- "cannot read it" and "it has no settings" are different things ----
  //
  // Both come back from deviceOptions as `climate: false`. Rendering the
  // second sentence for the first case told the user a rule holding
  // {temperature: 24, hvac_mode: 'cool'} sets nothing at all, while the
  // engine went on applying 24/cool the next morning. These two tests are
  // deliberately separate, one per case, so neither can drift into the
  // other's wording again.

  it('says a non-climate device takes no settings', async () => {
    const el = await render({
      states: { 'input_boolean.t': { state: 'off', attributes: {} } },
      devices: ['input_boolean.t'],
    });
    const text = el.shadowRoot!.textContent!;
    expect(text).toContain('no settings');
    // ...and does NOT claim it could not read anything: it read it fine.
    expect(text).not.toContain('cannot be read');
  });

  it('never tells the user an unreadable device takes no settings', async () => {
    const el = await render({
      states: { 'climate.dead': { state: 'unavailable', attributes: {} } },
      devices: ['climate.dead'],
      settings: { temperature: 24, hvac_mode: 'cool' },
    });
    const text = el.shadowRoot!.textContent!;
    expect(text).toContain('Could not read');
    // The contradiction this closes: it used to print both sentences.
    expect(text).not.toContain('take no settings');
    expect(text).toContain('cannot be read');
  });

  it('still shows the settings a rule holds when its devices cannot be read', async () => {
    const el = await render({
      states: { 'climate.dead': { state: 'unavailable', attributes: {} } },
      devices: ['climate.dead'],
      settings: { temperature: 24, hvac_mode: 'cool' },
    });
    const text = el.shadowRoot!.textContent!;
    // A saved setting the card does not show is a saved setting nobody
    // knows about - and this one fires the air conditioners at 11:00.
    expect(text).toContain('24');
    expect(text).toContain('cool');
    expect(el.shadowRoot!.querySelectorAll('.kept-row').length).toBe(2);
  });

  it('treats an entity that is merely `unknown` the same as an unavailable one', async () => {
    // A cloud-backed unit reports `unknown` after a restart, before its
    // first poll - the most ordinary way to reach this branch.
    const el = await render({
      states: { 'climate.aux': { state: 'unknown', attributes: {} } },
      devices: ['climate.aux'],
      settings: { fan_mode: 'quiet' },
    });
    const text = el.shadowRoot!.textContent!;
    expect(text).toContain('cannot be read');
    expect(text).not.toContain('take no settings');
    expect(text).toContain('quiet');
  });

  it('says the same thing in Hebrew, in Hebrew', async () => {
    const el = await render({
      states: { 'climate.dead': { state: 'unavailable', attributes: {} } },
      devices: ['climate.dead'],
      settings: { temperature: 24 },
      language: 'he',
    });
    const text = el.shadowRoot!.textContent!;
    expect(text).toContain('אי אפשר לערוך');
    expect(text).toContain('24');
    // The false sentence, in Hebrew, must be absent here too.
    expect(text).not.toContain('לא מקבלים הגדרות');
    // The household reads Hebrew; an English-only honesty fix is no fix.
    expect(text).not.toContain('cannot be read');
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

  // ---- clearing a setting has to actually clear it ----
  //
  // `changes_from_api` feeds `dataclasses.replace`, so `settings` is
  // replaced wholesale server-side: whatever this element emits is
  // exactly what the rule will hold. Emitting `fan_mode: ''` instead of
  // dropping the key hands an empty string to the climate service on
  // Shabbat morning.

  it('drops a setting the user cleared instead of sending an empty value', async () => {
    const el = await render({ settings: { fan_mode: 'quiet', temperature: 24 } });
    const listener = vi.fn();
    el.addEventListener('settings-changed', listener);

    const select = el.shadowRoot!.querySelector('.fan') as HTMLSelectElement;
    select.value = '';
    select.dispatchEvent(new Event('change'));

    const { settings } = (listener.mock.calls[0][0] as CustomEvent).detail;
    expect('fan_mode' in settings).toBe(false);
    // and only that one: clearing the fan must not clear the temperature.
    expect(settings.temperature).toBe(24);
  });

  it('drops a cleared temperature rather than sending null or NaN', async () => {
    const el = await render({ settings: { temperature: 24, fan_mode: 'quiet' } });
    const listener = vi.fn();
    el.addEventListener('settings-changed', listener);

    const input = el.shadowRoot!.querySelector('.temperature') as HTMLInputElement;
    input.value = '';
    input.dispatchEvent(new Event('change'));

    const { settings } = (listener.mock.calls[0][0] as CustomEvent).detail;
    expect('temperature' in settings).toBe(false);
    expect(settings.fan_mode).toBe('quiet');
  });

  it('disables every control when disabled', async () => {
    const el = await render({ disabled: true });
    for (const control of el.shadowRoot!.querySelectorAll('select, input')) {
      expect((control as HTMLInputElement).disabled).toBe(true);
    }
  });

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

  it('re-offers options for the device newly chosen through the picker', async () => {
    // Starts on the salon (offers 'quiet', not 'silent') - distinct from
    // the "offers the selected device's own fan modes" test above, which
    // never touches the control at all. This one drives the actual
    // <select class="devices">, takes what it reports, feeds it back in
    // the way a real parent (rule-dialog) would via `devices-changed`,
    // and checks the offered fan options moved to the newly-selected
    // device's - proving the picker and the settings it drives are
    // actually wired together, not just each independently correct for
    // a fixed `devices` prop.
    const el = await render({ devices: ['climate.salon'] });
    const listener = vi.fn();
    el.addEventListener('devices-changed', listener);

    const select = el.shadowRoot!.querySelector('.devices') as HTMLSelectElement;
    for (const option of select.options) option.selected = option.value === 'climate.kids';
    select.dispatchEvent(new Event('change'));

    el.devices = (listener.mock.calls[0][0] as CustomEvent).detail.devices;
    await el.updateComplete;

    const fans = [...el.shadowRoot!.querySelectorAll('.fan option')].map(
      (o) => (o as HTMLOptionElement).value,
    );
    expect(fans).toContain('silent');
    expect(fans).not.toContain('quiet');
  });
});
