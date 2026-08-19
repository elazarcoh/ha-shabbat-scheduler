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
