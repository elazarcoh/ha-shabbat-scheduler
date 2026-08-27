import { describe, expect, it, vi } from 'vitest';
import '../src/clone-dialog';
import type { RuleData } from '../src/types';

const rule = (over: Partial<RuleData> = {}): RuleData => ({
  id: 'a', profile: 1, day: 'erev', time: '11:00:00',
  action: 'climate.turn_on', target: {}, data: {}, condition: [],
  replay: { enabled: false }, name: null, icon: null, enabled: true,
  color: null, last_outcome: null, ...over,
});

async function render(props: Record<string, unknown> = {}) {
  const el = document.createElement('shabbat-clone-dialog') as HTMLElement &
    Record<string, any>;
  Object.assign(el, {
    source: { scope: 'day', profile: 1, day: 'erev' },
    rules: [rule({ id: 'a' })],
    canWrite: true, busy: false, error: null, landed: null, failed: null, language: 'en',
    ...props,
  });
  document.body.appendChild(el);
  await el.updateComplete;
  return el;
}

describe('shabbat-clone-dialog', () => {
  it('shows a day picker for a day-scope clone', async () => {
    const el = await render({ source: { scope: 'day', profile: 1, day: 'erev' } });
    expect(el.shadowRoot!.querySelector('select.target-day')).not.toBeNull();
  });

  it('shows no day picker for a profile-scope clone', async () => {
    const el = await render({ source: { scope: 'profile', profile: 1 } });
    expect(el.shadowRoot!.querySelector('select.target-day')).toBeNull();
  });

  it('disables confirm when the source has zero rules', async () => {
    const el = await render({ rules: [] });
    expect((el.shadowRoot!.querySelector('.confirm') as HTMLButtonElement).disabled).toBe(true);
  });

  it('enables confirm when the source has at least one rule', async () => {
    const el = await render();
    expect((el.shadowRoot!.querySelector('.confirm') as HTMLButtonElement).disabled).toBe(false);
  });

  it('defaults to extend mode, the non-destructive choice', async () => {
    const el = await render();
    expect(el.shadowRoot!.querySelector('.mode.extend')!.classList).toContain('active');
    expect(el.shadowRoot!.querySelector('.mode.overwrite')!.classList).not.toContain('active');
  });

  it('shows the existing-target-rules warning only when the target has rules', async () => {
    const el = await render({
      rules: [rule({ id: 'a', profile: 1, day: 'erev' }), rule({ id: 'b', profile: 2, day: 'erev' })],
    });
    (el as any)._targetProfile = 2;
    await el.updateComplete;
    expect(el.shadowRoot!.textContent).toContain('1');
  });

  it('says the same warning wording regardless of mode', async () => {
    const el = await render({
      rules: [rule({ id: 'a', profile: 1, day: 'erev' }), rule({ id: 'b', profile: 2, day: 'erev' })],
    });
    (el as any)._targetProfile = 2;
    (el as any)._mode = 'overwrite';
    await el.updateComplete;
    const overwriteText = el.shadowRoot!.querySelector('.warning')!.textContent;
    (el as any)._mode = 'extend';
    await el.updateComplete;
    expect(el.shadowRoot!.querySelector('.warning')!.textContent).toBe(overwriteText);
  });

  it('dispatches dialog-clone-confirm with the source rule ids, target and mode', async () => {
    const el = await render({
      source: { scope: 'day', profile: 1, day: 'erev' },
      rules: [rule({ id: 'a', profile: 1, day: 'erev' })],
    });
    const listener = vi.fn();
    el.addEventListener('dialog-clone-confirm', listener);
    (el.shadowRoot!.querySelector('.confirm') as HTMLElement).click();
    const detail = (listener.mock.calls[0][0] as CustomEvent).detail;
    expect(detail.sourceRuleIds).toEqual(['a']);
    expect(detail.sourceScope).toBe('day');
    expect(detail.mode).toBe('extend');
  });

  it('resets an out-of-range target day when the target profile shrinks', async () => {
    const el = await render({ source: { scope: 'day', profile: 3, day: '3' } });
    // Seeded target day is '3' (from the source), valid on a 3-day target.
    expect((el as any)._targetDay).toBe('3');
    const select = el.shadowRoot!.querySelector('select.target-profile') as HTMLSelectElement;
    select.value = '1';
    select.dispatchEvent(new Event('change'));
    await el.updateComplete;
    // '3' is not a valid day on a 1-day profile - must fall back to 'erev'.
    expect((el as any)._targetDay).toBe('erev');
    const dayOptions = [...el.shadowRoot!.querySelectorAll('select.target-day option')].map(
      (o) => (o as HTMLOptionElement).value,
    );
    expect(dayOptions).toEqual(['erev', '1']);
  });

  it('retries only the remainder still missing from the target after a partial failure', async () => {
    const el = await render({
      source: { scope: 'day', profile: 1, day: 'erev' },
      rules: [
        rule({ id: 'a', profile: 1, day: 'erev' }),
        rule({ id: 'b', profile: 1, day: 'erev' }),
      ],
      failed: ['b'],
    });
    const listener = vi.fn();
    el.addEventListener('dialog-clone-confirm', listener);
    (el.shadowRoot!.querySelector('.confirm') as HTMLElement).click();
    const detail = (listener.mock.calls[0][0] as CustomEvent).detail;
    expect(detail.sourceRuleIds).toEqual(['b']);
  });

  it('clicking the overwrite button switches modes and is reflected in the confirm dispatch', async () => {
    const el = await render();
    (el.shadowRoot!.querySelector('.mode.overwrite') as HTMLElement).click();
    await el.updateComplete;
    expect(el.shadowRoot!.querySelector('.mode.overwrite')!.classList).toContain('active');
    expect(el.shadowRoot!.querySelector('.mode.extend')!.classList).not.toContain('active');

    const listener = vi.fn();
    el.addEventListener('dialog-clone-confirm', listener);
    (el.shadowRoot!.querySelector('.confirm') as HTMLElement).click();
    expect((listener.mock.calls[0][0] as CustomEvent).detail.mode).toBe('overwrite');
  });

  it('does not disable confirm when failed is an empty array (a clean full success report)', async () => {
    const el = await render({ failed: [] });
    expect((el.shadowRoot!.querySelector('.confirm') as HTMLButtonElement).disabled).toBe(false);
  });

  describe('read-only (canWrite: false)', () => {
    it('shows no confirm button', async () => {
      const el = await render({ canWrite: false });
      expect(el.shadowRoot!.querySelector('.confirm')).toBeNull();
    });

    it('shows the read-only note', async () => {
      const el = await render({ canWrite: false });
      expect(el.shadowRoot!.textContent).toContain('permission');
    });

    it('disables the mode buttons and the target pickers', async () => {
      const el = await render({ canWrite: false });
      expect(
        (el.shadowRoot!.querySelector('.mode.extend') as HTMLButtonElement).disabled,
      ).toBe(true);
      expect(
        (el.shadowRoot!.querySelector('.mode.overwrite') as HTMLButtonElement).disabled,
      ).toBe(true);
      expect(
        (el.shadowRoot!.querySelector('select.target-profile') as HTMLSelectElement).disabled,
      ).toBe(true);
      expect(
        (el.shadowRoot!.querySelector('select.target-day') as HTMLSelectElement).disabled,
      ).toBe(true);
    });
  });

  describe('the landed/failed report names rules, never raw ids', () => {
    it('shows the source rule\'s name in the report, not its id', async () => {
      const el = await render({
        source: { scope: 'day', profile: 1, day: 'erev' },
        rules: [rule({ id: 'a', name: 'Lights on' })],
      });
      (el.shadowRoot!.querySelector('.confirm') as HTMLElement).click();
      await el.updateComplete;
      (el as any).landed = ['a'];
      (el as any).failed = [];
      await el.updateComplete;
      const report = el.shadowRoot!.querySelector('.report')!.textContent!;
      expect(report).toContain('Lights on');
      expect(report).not.toContain('>a<');
    });

    it('falls back to the action when the rule has no name', async () => {
      const el = await render({
        source: { scope: 'day', profile: 1, day: 'erev' },
        rules: [rule({ id: 'a', name: null, action: 'climate.turn_on' })],
      });
      (el.shadowRoot!.querySelector('.confirm') as HTMLElement).click();
      await el.updateComplete;
      (el as any).landed = ['a'];
      (el as any).failed = [];
      await el.updateComplete;
      expect(el.shadowRoot!.querySelector('.report')!.textContent).toContain('climate.turn_on');
    });

    it('still names a failed rule by the name captured at confirm time, even if it is gone from `rules` by render time', async () => {
      // Mirrors the critical clone bug's own shape: by the time the report
      // renders, `rules` may no longer contain the id the report is about.
      const el = await render({
        source: { scope: 'day', profile: 1, day: 'erev' },
        rules: [rule({ id: 'a', name: 'Lights on' })],
      });
      (el.shadowRoot!.querySelector('.confirm') as HTMLElement).click();
      await el.updateComplete;
      (el as any).rules = []; // the source is gone from the latest state push
      (el as any).landed = [];
      (el as any).failed = ['a'];
      await el.updateComplete;
      expect(el.shadowRoot!.querySelector('.report')!.textContent).toContain('Lights on');
    });
  });
});
