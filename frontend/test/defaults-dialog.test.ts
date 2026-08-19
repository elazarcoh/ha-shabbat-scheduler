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
