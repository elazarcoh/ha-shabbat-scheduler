import { describe, expect, it } from 'vitest';
import '../src/replay-editor';

async function render(props: Record<string, unknown> = {}) {
  const el = document.createElement('shabbat-replay-editor') as HTMLElement &
    Record<string, any>;
  Object.assign(el, {
    value: { enabled: false }, disabled: false, language: 'en', ...props,
  });
  document.body.appendChild(el);
  await el.updateComplete;
  return el;
}

const enabledBox = (el: any) =>
  el.shadowRoot!.querySelector('input.replay-enabled') as HTMLInputElement;
const withinBox = (el: any) =>
  el.shadowRoot!.querySelector('input.replay-within') as HTMLInputElement | null;

describe('shabbat-replay-editor', () => {
  it('is off by default and hides the window', async () => {
    const el = await render();
    expect(enabledBox(el).checked).toBe(false);
    expect(withinBox(el)).toBeNull();
  });

  it('emits enabled with a default window when switched on', async () => {
    const el = await render();
    const seen: any[] = [];
    el.addEventListener('replay-changed', (e: Event) => {
      seen.push((e as CustomEvent).detail.value);
    });
    enabledBox(el).checked = true;
    enabledBox(el).dispatchEvent(new Event('change'));
    expect(seen).toEqual([{ enabled: true, within: '01:00:00' }]);
  });

  it('shows the window once enabled', async () => {
    const el = await render({ value: { enabled: true, within: '02:30:00' } });
    expect(withinBox(el)!.value).toBe('02:30:00');
  });

  it('emits a changed window', async () => {
    const el = await render({ value: { enabled: true, within: '01:00:00' } });
    const seen: any[] = [];
    el.addEventListener('replay-changed', (e: Event) => {
      seen.push((e as CustomEvent).detail.value);
    });
    withinBox(el)!.value = '00:45:00';
    withinBox(el)!.dispatchEvent(new Event('change'));
    expect(seen).toEqual([{ enabled: true, within: '00:45:00' }]);
  });

  it('treats a cleared window as no bound, dropping the key', async () => {
    const el = await render({ value: { enabled: true, within: '01:00:00' } });
    const seen: any[] = [];
    el.addEventListener('replay-changed', (e: Event) => {
      seen.push((e as CustomEvent).detail.value);
    });
    withinBox(el)!.value = '';
    withinBox(el)!.dispatchEvent(new Event('change'));
    expect(seen).toEqual([{ enabled: true }]);
  });

  it('forgets the window when switched off, so off means off', async () => {
    const el = await render({ value: { enabled: true, within: '01:00:00' } });
    const seen: any[] = [];
    el.addEventListener('replay-changed', (e: Event) => {
      seen.push((e as CustomEvent).detail.value);
    });
    enabledBox(el).checked = false;
    enabledBox(el).dispatchEvent(new Event('change'));
    expect(seen).toEqual([{ enabled: false }]);
  });
});
