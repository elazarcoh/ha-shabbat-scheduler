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

  // The pick above is two explicit keys, not a spread of `_draft` - and
  // `_draft` is built by spreading the server's own defaults object. The
  // day the server's payload grows a third key, spreading it would send
  // that key straight into `defaults/update`, where `_check_unknown_fields`
  // rejects the WHOLE call: shared defaults would stop saving at all, and
  // every rule that inherits them would keep whatever it had. Only a stray
  // key in the incoming payload can prove the pick is doing the work.
  it('never forwards a key the server did not ask for, even one it sent itself', async () => {
    const el = await render({
      defaults: {
        devices: ['climate.salon'],
        settings: { temperature: 26 },
        // A field a future server version might add to the read payload.
        updated_at: '2026-08-19T00:00:00+03:00',
      },
    });
    const listener = vi.fn();
    el.addEventListener('defaults-save', listener);

    (el.shadowRoot!.querySelector('.save') as HTMLElement).click();

    const { defaults } = (listener.mock.calls[0][0] as CustomEvent).detail;
    expect(Object.keys(defaults).sort()).toEqual(['devices', 'settings']);
    expect('updated_at' in defaults).toBe(false);
    // ...and the two keys it does send are still the real values.
    expect(defaults.devices).toEqual(['climate.salon']);
    expect(defaults.settings.temperature).toBe(26);
  });

  it('still forwards only the two keys after the user has edited a draft', async () => {
    // `_draft` is `{...current, devices}` - the spread carries the stray
    // key forward, so an edited draft is the same trap one step later.
    const el = await render({
      defaults: {
        devices: ['climate.salon'],
        settings: {},
        updated_at: '2026-08-19T00:00:00+03:00',
      },
    });
    el.shadowRoot!.querySelector('shabbat-device-settings')!.dispatchEvent(
      new CustomEvent('devices-changed', { detail: { devices: ['climate.kids'] } }),
    );
    await el.updateComplete;

    const listener = vi.fn();
    el.addEventListener('defaults-save', listener);
    (el.shadowRoot!.querySelector('.save') as HTMLElement).click();

    const { defaults } = (listener.mock.calls[0][0] as CustomEvent).detail;
    expect(Object.keys(defaults).sort()).toEqual(['devices', 'settings']);
    expect(defaults.devices).toEqual(['climate.kids']);
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
