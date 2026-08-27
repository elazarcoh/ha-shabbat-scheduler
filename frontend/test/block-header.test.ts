import { describe, expect, it, vi } from 'vitest';
import '../src/block-header';
import { ShabbatBlockHeader } from '../src/block-header';
import type { BlockData } from '../src/types';

const block: BlockData = {
  length: 1,
  candle_lighting: '2026-08-14T18:44:00+03:00',
  havdalah: '2026-08-15T20:01:00+03:00',
  dates: { erev: '2026-08-14', '1': '2026-08-15' },
};

async function render(props: Record<string, unknown>) {
  const el = document.createElement('shabbat-block-header') as HTMLElement &
    Record<string, unknown>;
  Object.assign(el, {
    block, enabled: false, canWrite: true,
    masterEntityId: 'switch.master', language: 'en', selectedProfile: 1, hass: {}, ...props,
  });
  document.body.appendChild(el);
  await (el as unknown as { updateComplete: Promise<unknown> }).updateComplete;
  return el;
}

function master(el: any) {
  return el.shadowRoot.querySelector('ha-selector.master');
}

describe('shabbat-block-header', () => {
  it('shows the block length and its dates', async () => {
    const el = await render({});
    const text = el.shadowRoot!.textContent!;
    expect(text).toContain('2026-08-15');
  });

  it('orders the dates erev-first, not by object key enumeration', async () => {
    const el = await render({});
    const text = el.shadowRoot!.textContent!;
    // erev (2026-08-14) precedes day 1 (2026-08-15); the raw `dates`
    // object has integer-like keys ('1') enumerate before 'erev', so a
    // naive Object.values(...).join(...) would render this backwards.
    expect(text).toContain('2026-08-14 → 2026-08-15');
  });

  it('says so when there is no block instead of rendering an empty header', async () => {
    const el = await render({ block: null });
    expect(el.shadowRoot!.textContent).toContain('No upcoming Shabbat');
  });

  it('hands the master ha-selector a boolean selector and the current value', async () => {
    const el = await render({ enabled: true });
    const sel = master(el);
    expect(sel).not.toBeNull();
    expect(sel.selector).toEqual({ boolean: {} });
    expect(sel.value).toBe(true);
    expect(sel.hass).toBe(el.hass);
  });

  it('fires an event rather than mutating its own state', async () => {
    const el = await render({ enabled: false });
    const listener = vi.fn();
    el.addEventListener('shabbat-master-toggle', listener);

    master(el).dispatchEvent(
      new CustomEvent('value-changed', { detail: { value: true } }),
    );

    expect(listener).toHaveBeenCalledOnce();
    expect((listener.mock.calls[0][0] as CustomEvent).detail).toEqual({
      enabled: true,
    });
    // No optimistic update: the control still reads the pushed state.
    expect((el as unknown as { enabled: boolean }).enabled).toBe(false);
  });

  it('disables the master control for a read-only user', async () => {
    const el = await render({ canWrite: false });
    expect(master(el).disabled).toBe(true);
  });

  it('disables the master control when the entity is unknown', async () => {
    const el = await render({ masterEntityId: null });
    expect(master(el).disabled).toBe(true);
  });
});

describe('profile chips', () => {
  it('offers 1, 2 and 3 day chips', async () => {
    const el = await render({ selectedProfile: 1 });
    const chips = [...el.shadowRoot!.querySelectorAll('.chip')].map(
      (c) => (c as HTMLElement).textContent!.trim(),
    );
    expect(chips).toEqual(['1d', '2d', '3d']);
  });

  it('marks the selected one', async () => {
    const el = await render({ selectedProfile: 3 });
    const active = el.shadowRoot!.querySelector('.chip.active') as HTMLElement;
    expect(active.textContent!.trim()).toBe('3d');
  });

  it('reports a selection rather than changing itself', async () => {
    const el = await render({ selectedProfile: 1 });
    const listener = vi.fn();
    el.addEventListener('profile-selected', listener);

    (el.shadowRoot!.querySelectorAll('.chip')[2] as HTMLElement).click();

    expect((listener.mock.calls[0][0] as CustomEvent).detail).toEqual({ profile: 3 });
    expect((el as unknown as { selectedProfile: number }).selectedProfile).toBe(1);
  });

  it('offers the defaults gear to a writer and not to a reader', async () => {
    expect((await render({ canWrite: true })).shadowRoot!.querySelector('.gear'))
      .not.toBeNull();
    expect((await render({ canWrite: false })).shadowRoot!.querySelector('.gear'))
      .toBeNull();
  });

  it('asks for the defaults dialog when the gear is used', async () => {
    const el = await render({ canWrite: true });
    const listener = vi.fn();
    el.addEventListener('defaults-open', listener);
    (el.shadowRoot!.querySelector('.gear') as HTMLElement).click();
    expect(listener).toHaveBeenCalledOnce();
  });

  it('offers the simulate icon to a writer and not to a reader', async () => {
    expect((await render({ canWrite: true })).shadowRoot!.querySelector('.simulate-open'))
      .not.toBeNull();
    expect((await render({ canWrite: false })).shadowRoot!.querySelector('.simulate-open'))
      .toBeNull();
  });

  it('dispatches simulate-open when the icon is used', async () => {
    const el = await render({ canWrite: true });
    const listener = vi.fn();
    el.addEventListener('simulate-open', listener);
    (el.shadowRoot!.querySelector('.simulate-open') as HTMLElement).click();
    expect(listener).toHaveBeenCalledOnce();
  });
});

describe('shabbat-block-header mobile layout', () => {
  it('wraps header controls onto their own row under 600px with 44px tap targets', () => {
    const cssText = (ShabbatBlockHeader.styles as unknown as { cssText: string }).cssText;
    expect(cssText).toContain('@media (max-width: 599px)');
    expect(cssText).toContain('min-block-size: 44px');
  });
});
