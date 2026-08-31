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

  // The direction that actually distinguishes replace from merge: seed a
  // key the edit does NOT touch (`entity_id`/`fan_mode`) and change to a
  // shape that shares no keys with it (`area_id`/only `temperature`). A
  // deep merge and a replace agree on every key the edit *does* touch, so
  // a test that only checks the touched key would pass under either
  // implementation - this is why `toStrictEqual`, not `toEqual`, is load
  // bearing here: an old `entity_id` sitting alongside the new `area_id`
  // is a key `toEqual` cannot see missing.
  it('replaces the target wholesale on save, not merges it', async () => {
    const el = await render({
      canWrite: true,
      defaults: { target: { entity_id: ['switch.a'] }, data: {} },
    });
    const saved: any[] = [];
    el.addEventListener('dialog-save', (e: Event) => {
      saved.push((e as CustomEvent).detail.defaults);
    });
    el.shadowRoot!.querySelector('shabbat-target-editor')!
      .dispatchEvent(new CustomEvent('target-changed', {
        detail: { value: { area_id: ['salon'] } },
      }));
    await el.updateComplete;
    (el.shadowRoot!.querySelector('button.save') as HTMLButtonElement).click();
    expect(saved[0].target).toStrictEqual({ area_id: ['salon'] });
  });

  it('replaces the data wholesale on save, not merges it', async () => {
    const el = await render({
      canWrite: true,
      defaults: { target: {}, data: { temperature: 20, fan_mode: 'high' } },
    });
    const saved: any[] = [];
    el.addEventListener('dialog-save', (e: Event) => {
      saved.push((e as CustomEvent).detail.defaults);
    });
    el.shadowRoot!.querySelector('shabbat-service-editor')!
      .dispatchEvent(new CustomEvent('service-changed', {
        detail: { action: '', data: { temperature: 24 } },
      }));
    await el.updateComplete;
    (el.shadowRoot!.querySelector('button.save') as HTMLButtonElement).click();
    expect(saved[0].data).toStrictEqual({ temperature: 24 });
  });

  /**
   * The blocker, driven as a CHAIN rather than link by link.
   *
   * Every link here was already tested in isolation and the defect still
   * shipped: `service-editor.test.ts` pinned the normalisation, this file
   * pinned replace-not-merge with a NON-EMPTY payload (which is not what
   * HA sends), and no e2e test saved this dialog at all. So this drives
   * the exact event HA fires on a service pick - `{action, target}`, no
   * `data` key - all the way to what Save would send.
   *
   * Picking a service here is a change of VIEW, not of value: the shared
   * defaults carry no action, so `_action` is only a lens onto whose
   * schema the data form is rendered through. It used to persist `{}` and
   * delete the user's stored payload from every rule that inherited it,
   * on the one path a user has to see that payload - and
   * `known-behaviours.md` recommended exactly that action as the remedy.
   */
  it('keeps the stored data when a service pick sends no data', async () => {
    const el = await render({
      canWrite: true,
      defaults: { target: {}, data: { temperature: 26, fan_mode: 'quiet' } },
    });
    const saved: any[] = [];
    el.addEventListener('dialog-save', (e: Event) => {
      saved.push((e as CustomEvent).detail.defaults);
    });
    el.shadowRoot!.querySelector('shabbat-service-editor')!
      .dispatchEvent(new CustomEvent('service-changed', {
        // No `data` key. This is what `service-editor` emits when HA's
        // element reports a service change, which is every service change.
        detail: { action: 'climate.set_temperature' },
      }));
    await el.updateComplete;

    // The lens moved, so the picker now shows the chosen service...
    expect(
      (el.shadowRoot!.querySelector('shabbat-service-editor') as any).action,
    ).toBe('climate.set_temperature');
    // ...and the stored data is still there, under it, editable.
    expect(
      (el.shadowRoot!.querySelector('shabbat-service-editor') as any).data,
    ).toStrictEqual({ temperature: 26, fan_mode: 'quiet' });

    (el.shadowRoot!.querySelector('button.save') as HTMLButtonElement).click();
    expect(saved[0].data).toStrictEqual({ temperature: 26, fan_mode: 'quiet' });
  });

  /**
   * THE SAME PROPERTY, DRIVEN THROUGH THE WHOLE CHAIN.
   *
   * The test above dispatches `service-changed` on the editor element, so
   * it pins this dialog's handler and nothing else. That is exactly the
   * shape of coverage that let the blocker ship: every link was tested and
   * the chain never was, so a defect that lived in the JOIN between two
   * correct-looking links was invisible to both suites.
   *
   * So this one starts one level lower - at `ha-service-control`'s own
   * `value-changed`, inside the real `<shabbat-service-editor>` this dialog
   * composes - with byte-for-byte the payload HA 2026.8.2 emits. Both the
   * editor's omission and the dialog's preservation have to be right for
   * it to pass, and either one alone is not enough.
   */
  it('survives the real HA event travelling through the real service editor', async () => {
    const el = await render({
      canWrite: true,
      defaults: { target: {}, data: { temperature: 26 } },
    });
    const saved: any[] = [];
    el.addEventListener('dialog-save', (e: Event) => {
      saved.push((e as CustomEvent).detail.defaults);
    });

    const editor = el.shadowRoot!.querySelector('shabbat-service-editor') as any;
    await editor.updateComplete;
    editor.shadowRoot!.querySelector('ha-service-control')!
      .dispatchEvent(new CustomEvent('value-changed', {
        // `ha-service-control._serviceChanged`, verbatim: an action, a
        // target it computed itself, and NO `data` key.
        detail: { value: {
          action: 'climate.set_temperature',
          target: { entity_id: ['climate.salon'] },
        } },
      }));
    await el.updateComplete;

    (el.shadowRoot!.querySelector('button.save') as HTMLButtonElement).click();
    expect(saved[0].data).toStrictEqual({ temperature: 26 });
    // And HA's stray target never reaches the payload either: this dialog's
    // target comes from its own target editor.
    expect(saved[0].target).toStrictEqual({});
  });

  /**
   * The direction where preserve and replace differ, so neither can pass
   * for the other. An explicitly empty `data` is a real edit - the user
   * cleared every field in HA's own form - and must still land, or nothing
   * could ever empty a shared default. A fix that simply ignored `data`
   * whenever it was falsy or empty would pass the test above and fail this
   * one.
   */
  it('still empties the data when the picker sends an explicitly empty one', async () => {
    const el = await render({
      canWrite: true,
      defaults: { target: {}, data: { temperature: 26 } },
    });
    const saved: any[] = [];
    el.addEventListener('dialog-save', (e: Event) => {
      saved.push((e as CustomEvent).detail.defaults);
    });
    el.shadowRoot!.querySelector('shabbat-service-editor')!
      .dispatchEvent(new CustomEvent('service-changed', {
        detail: { action: 'climate.set_temperature', data: {} },
      }));
    await el.updateComplete;
    (el.shadowRoot!.querySelector('button.save') as HTMLButtonElement).click();
    expect(saved[0].data).toStrictEqual({});
  });

  it('hands the language ha-selector the current override and Auto/English/Hebrew options', async () => {
    const el = await render({ languageOverride: 'he' });
    const sel = el.shadowRoot!.querySelector('ha-selector') as any;
    expect(sel).not.toBeNull();
    expect(sel.value).toBe('he');
    expect(sel.selector.select.options.map((o: any) => o.value)).toEqual(
      ['', 'en', 'he'],
    );
  });

  it('shows Auto (empty string) when no override is set', async () => {
    const el = await render({ languageOverride: null });
    expect((el.shadowRoot!.querySelector('ha-selector') as any).value).toBe('');
  });

  it('emits language-changed immediately on selection, not gated behind Save', async () => {
    const el = await render({ languageOverride: null });
    const seen: unknown[] = [];
    el.addEventListener('language-changed', (e: Event) => {
      seen.push((e as CustomEvent).detail.language);
    });
    el.shadowRoot!.querySelector('ha-selector')!.dispatchEvent(
      new CustomEvent('value-changed', { detail: { value: 'he' } }),
    );
    expect(seen).toEqual(['he']);
  });

  it('emits null, not an empty string, when Auto is chosen', async () => {
    const el = await render({ languageOverride: 'he' });
    const seen: unknown[] = [];
    el.addEventListener('language-changed', (e: Event) => {
      seen.push((e as CustomEvent).detail.language);
    });
    el.shadowRoot!.querySelector('ha-selector')!.dispatchEvent(
      new CustomEvent('value-changed', { detail: { value: '' } }),
    );
    expect(seen).toEqual([null]);
  });

  it('disables the language selector when the user cannot write', async () => {
    const el = await render({ canWrite: false });
    expect((el.shadowRoot!.querySelector('ha-selector') as any).disabled).toBe(true);
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
