import { describe, expect, it } from 'vitest';
import '../src/defaults-dialog';

async function render(props: Record<string, unknown> = {}) {
  const el = document.createElement('shabbat-defaults-dialog') as HTMLElement &
    Record<string, any>;
  Object.assign(el, {
    defaults: {
      target: { entity_id: ['climate.salon'] },
      data: { temperature: 26 },
    },
    canWrite: true, busy: false, error: null, language: 'en',
    hass: { states: {} }, ...props,
  });
  document.body.appendChild(el);
  await el.updateComplete;
  return el;
}

/**
 * v1's editor wrote `{devices, settings}`; `validate_defaults`
 * (rule_schema.py) now accepts exactly `{target, data}`, so every press of
 * the old save button was rejected by the server, and the button was
 * removed rather than left broken. This composes the same target and
 * service editors the rule dialog uses (target-editor.ts,
 * service-editor.ts) so authoring works again on the shape the server
 * actually accepts.
 */
describe('shabbat-defaults-dialog', () => {
  it('offers a target editor and a data editor', async () => {
    const el = await render({ canWrite: true });
    expect(el.shadowRoot!.querySelector('shabbat-target-editor')).not.toBeNull();
    expect(el.shadowRoot!.querySelector('shabbat-service-editor')).not.toBeNull();
  });

  it('seeds them from the current defaults', async () => {
    const el = await render({
      canWrite: true,
      defaults: { target: { entity_id: ['switch.a'] }, data: { temperature: 20 } },
    });
    expect(
      (el.shadowRoot!.querySelector('shabbat-target-editor') as any).value,
    ).toEqual({ entity_id: ['switch.a'] });
    expect(
      (el.shadowRoot!.querySelector('shabbat-service-editor') as any).data,
    ).toEqual({ temperature: 20 });
  });

  it('has a save button again, and emits what was edited', async () => {
    const el = await render({ canWrite: true, defaults: {} });
    const saved: any[] = [];
    el.addEventListener('dialog-save', (e: Event) => {
      saved.push((e as CustomEvent).detail.defaults);
    });
    el.shadowRoot!.querySelector('shabbat-target-editor')!
      .dispatchEvent(new CustomEvent('target-changed', {
        detail: { value: { area_id: ['salon'] } },
      }));
    await el.updateComplete;
    const save = el.shadowRoot!.querySelector('button.save') as HTMLButtonElement;
    expect(save).not.toBeNull();
    save.click();
    expect(saved).toEqual([{ target: { area_id: ['salon'] }, data: {} }]);
  });

  it('offers no save button to a user who cannot write', async () => {
    const el = await render({ canWrite: false });
    expect(el.shadowRoot!.querySelector('button.save')).toBeNull();
  });

  it('sends only the data half of the service editor, never an action', async () => {
    const el = await render({ canWrite: true, defaults: {} });
    const saved: any[] = [];
    el.addEventListener('dialog-save', (e: Event) => {
      saved.push((e as CustomEvent).detail.defaults);
    });
    el.shadowRoot!.querySelector('shabbat-service-editor')!
      .dispatchEvent(new CustomEvent('service-changed', {
        detail: { action: 'climate.set_temperature', data: { temperature: 22 } },
      }));
    await el.updateComplete;
    (el.shadowRoot!.querySelector('button.save') as HTMLButtonElement).click();
    expect(saved[0].data).toEqual({ temperature: 22 });
    // Deliberately not `toEqual`: an omitted key and `action: undefined`
    // are indistinguishable to `toEqual`, so only an `in` check (or
    // `toStrictEqual`) can actually fail here if a stray key crept back in.
    expect('action' in saved[0]).toBe(false);
  });

  it('shows a server rejection and stays open, editors intact', async () => {
    const el = await render({ error: "unknown field(s): ['temperature']" });
    expect(el.shadowRoot!.textContent).toContain('unknown field');
    expect(el.shadowRoot!.querySelector('shabbat-target-editor')).not.toBeNull();
    expect(el.shadowRoot!.querySelector('shabbat-service-editor')).not.toBeNull();
  });

  it('closes on cancel', async () => {
    const el = await render();
    let closed = false;
    el.addEventListener('dialog-close', () => { closed = true; });
    (el.shadowRoot!.querySelector('button') as HTMLElement).click();
    expect(closed).toBe(true);
  });

  it('does not re-seed the draft when hass is reassigned', async () => {
    const el = await render({ canWrite: true, defaults: {} });
    el.shadowRoot!.querySelector('shabbat-target-editor')!
      .dispatchEvent(new CustomEvent('target-changed', {
        detail: { value: { area_id: ['salon'] } },
      }));
    await el.updateComplete;
    // A fresh object, same shape - this is what a `hass` push looks like.
    el.hass = { states: {} };
    await el.updateComplete;
    expect(
      (el.shadowRoot!.querySelector('shabbat-target-editor') as any).value,
    ).toEqual({ area_id: ['salon'] });
  });
});
