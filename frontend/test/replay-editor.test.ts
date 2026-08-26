import { describe, expect, it } from 'vitest';
import '../src/replay-editor';
import {
  durationObjectToString, durationStringToObject,
} from '../src/replay-editor';

async function render(props: Record<string, unknown> = {}) {
  const el = document.createElement('shabbat-replay-editor') as HTMLElement &
    Record<string, any>;
  Object.assign(el, {
    hass: {}, value: { enabled: false }, disabled: false, language: 'en', ...props,
  });
  document.body.appendChild(el);
  await el.updateComplete;
  return el;
}

const enabledSel = (el: any) =>
  el.shadowRoot!.querySelector('ha-selector.replay-enabled');
const withinSel = (el: any) =>
  el.shadowRoot!.querySelector('ha-selector.replay-within') as any | null;

describe('duration conversion', () => {
  it('converts a full object to HH:MM:SS', () => {
    expect(durationObjectToString({ hours: 2, minutes: 30, seconds: 5 })).toBe('02:30:05');
  });

  it('treats missing fields as zero', () => {
    expect(durationObjectToString({ hours: 1 })).toBe('01:00:00');
    expect(durationObjectToString({})).toBe('00:00:00');
    expect(durationObjectToString(undefined)).toBe('00:00:00');
  });

  it('does not clamp hours at 24', () => {
    expect(durationObjectToString({ hours: 36, minutes: 15, seconds: 0 })).toBe('36:15:00');
  });

  it('converts HH:MM:SS back to an object', () => {
    expect(durationStringToObject('02:30:05')).toEqual({ hours: 2, minutes: 30, seconds: 5 });
  });

  it('round-trips a value with hours over 24', () => {
    expect(durationStringToObject('36:15:00')).toEqual({ hours: 36, minutes: 15, seconds: 0 });
  });

  it('treats an undefined string as an undefined object, not zeroed', () => {
    expect(durationStringToObject(undefined)).toBeUndefined();
  });

  it('rejects a malformed string rather than guessing', () => {
    expect(durationStringToObject('not-a-duration')).toBeUndefined();
    expect(durationStringToObject('01:02')).toBeUndefined();
  });
});

describe('shabbat-replay-editor', () => {
  it('is off by default and hides the window', async () => {
    const el = await render();
    expect(enabledSel(el).value).toBe(false);
    expect(withinSel(el)).toBeNull();
  });

  it('emits enabled with a default window when switched on', async () => {
    const el = await render();
    const seen: any[] = [];
    el.addEventListener('replay-changed', (e: Event) => {
      seen.push((e as CustomEvent).detail.value);
    });
    enabledSel(el).dispatchEvent(
      new CustomEvent('value-changed', { detail: { value: true } }),
    );
    expect(seen).toEqual([{ enabled: true, within: '01:00:00' }]);
  });

  it('shows the window as an {hours,minutes,seconds} object once enabled', async () => {
    const el = await render({ value: { enabled: true, within: '02:30:00' } });
    expect(withinSel(el)!.value).toEqual({ hours: 2, minutes: 30, seconds: 0 });
  });

  it('emits a changed window, converted back to HH:MM:SS', async () => {
    const el = await render({ value: { enabled: true, within: '01:00:00' } });
    const seen: any[] = [];
    el.addEventListener('replay-changed', (e: Event) => {
      seen.push((e as CustomEvent).detail.value);
    });
    withinSel(el)!.dispatchEvent(
      new CustomEvent('value-changed', { detail: { value: { hours: 0, minutes: 45, seconds: 0 } } }),
    );
    expect(seen).toEqual([{ enabled: true, within: '00:45:00' }]);
  });

  it('treats a cleared window as no bound, dropping the key', async () => {
    const el = await render({ value: { enabled: true, within: '01:00:00' } });
    const seen: any[] = [];
    el.addEventListener('replay-changed', (e: Event) => {
      seen.push((e as CustomEvent).detail.value);
    });
    withinSel(el)!.dispatchEvent(
      new CustomEvent('value-changed', { detail: { value: undefined } }),
    );
    expect(seen).toStrictEqual([{ enabled: true }]);
    expect('within' in seen[0]).toBe(false);
  });

  it('forgets the window when switched off, so off means off', async () => {
    const el = await render({ value: { enabled: true, within: '01:00:00' } });
    const seen: any[] = [];
    el.addEventListener('replay-changed', (e: Event) => {
      seen.push((e as CustomEvent).detail.value);
    });
    enabledSel(el).dispatchEvent(
      new CustomEvent('value-changed', { detail: { value: false } }),
    );
    expect(seen).toStrictEqual([{ enabled: false }]);
    expect('within' in seen[0]).toBe(false);
  });

  it('hands both selectors the current hass', async () => {
    const hass = { fake: true };
    const el = await render({ hass, value: { enabled: true, within: '01:00:00' } });
    expect(enabledSel(el).hass).toBe(hass);
    expect(withinSel(el)!.hass).toBe(hass);
  });
});
