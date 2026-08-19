import { describe, expect, it, vi } from 'vitest';
import '../src/block-header';
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
    block, enabled: false, dryRun: false, canWrite: true,
    masterEntityId: 'switch.master', language: 'en', ...props,
  });
  document.body.appendChild(el);
  await (el as unknown as { updateComplete: Promise<unknown> }).updateComplete;
  return el;
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

  it('fires an event rather than mutating its own state', async () => {
    const el = await render({ enabled: false });
    const listener = vi.fn();
    el.addEventListener('shabbat-master-toggle', listener);

    (el.shadowRoot!.querySelector('.master') as HTMLElement).click();

    expect(listener).toHaveBeenCalledOnce();
    expect((listener.mock.calls[0][0] as CustomEvent).detail).toEqual({
      enabled: true,
    });
    // No optimistic update: the control still reads the pushed state.
    expect((el as unknown as { enabled: boolean }).enabled).toBe(false);
  });

  it('disables both controls for a read-only user', async () => {
    const el = await render({ canWrite: false });
    const master = el.shadowRoot!.querySelector('.master') as HTMLButtonElement;
    const dryRun = el.shadowRoot!.querySelector('.dry-run') as HTMLButtonElement;
    expect(master.disabled).toBe(true);
    expect(dryRun.disabled).toBe(true);
  });

  it('disables the master control when the entity is unknown', async () => {
    const el = await render({ masterEntityId: null });
    const master = el.shadowRoot!.querySelector('.master') as HTMLButtonElement;
    expect(master.disabled).toBe(true);
  });
});
