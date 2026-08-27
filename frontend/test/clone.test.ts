import { describe, expect, it, vi } from 'vitest';
import '../src/card';
import type { CardState, RuleData } from '../src/types';
import { fakeHass, flush, mount } from './helpers';

const rule = (over: Partial<RuleData> = {}): RuleData => ({
  id: 'a', profile: 1, day: 'erev', time: '11:00:00',
  action: 'climate.turn_on', target: { entity_id: ['climate.a'] },
  data: {}, condition: [], replay: { enabled: false },
  name: null, icon: null, enabled: true, color: null,
  last_outcome: null, ...over,
});

const state = (over: Partial<CardState> = {}): CardState => ({
  defaults: {}, rules: [], enabled: false, warnings: [],
  master_entity_id: 'switch.master',
  block: {
    length: 1, candle_lighting: '2026-08-14T18:44:00+03:00',
    havdalah: '2026-08-15T20:01:00+03:00',
    dates: { erev: '2026-08-14', '1': '2026-08-15' },
  },
  ...over,
} as CardState);

describe('_cloneRules', () => {
  it('creates one rule per source id, day and profile rewritten to the target', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(state({ rules: [rule({ id: 'a' }), rule({ id: 'b', time: '12:00:00' })] }));
    await el.updateComplete;

    await (el as any)._cloneRules(['a', 'b'], 2, '1', 'extend');

    expect(hass.callWS).toHaveBeenCalledTimes(2);
    const calls = hass.callWS.mock.calls.map((c: any) => c[0]);
    expect(calls.every((c: any) => c.type === 'shabbat_scheduler/rules/create')).toBe(true);
    expect(calls[0].rule.day).toBe('1');
    expect(calls[0].rule.profile).toBe(2);
    expect(calls[1].rule.time).toBe('12:00:00');
  });

  it('deletes every rule on the target day first in overwrite mode, before creating', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(state({
      rules: [
        rule({ id: 'a' }), // source
        rule({ id: 'existing1', profile: 2, day: '1' }), // to be deleted
        rule({ id: 'existing2', profile: 2, day: '1' }), // to be deleted
      ],
    }));
    await el.updateComplete;

    await (el as any)._cloneRules(['a'], 2, '1', 'overwrite');

    const calls = hass.callWS.mock.calls.map((c: any) => c[0]);
    const deletes = calls.filter((c: any) => c.type === 'shabbat_scheduler/rules/delete');
    const creates = calls.filter((c: any) => c.type === 'shabbat_scheduler/rules/create');
    expect(deletes.map((d: any) => d.rule_id).sort()).toEqual(['existing1', 'existing2']);
    expect(creates).toHaveLength(1);
    // Deletes strictly before creates - never interleaved.
    const lastDeleteIndex = calls.lastIndexOf(deletes[deletes.length - 1]);
    const firstCreateIndex = calls.indexOf(creates[0]);
    expect(lastDeleteIndex).toBeLessThan(firstCreateIndex);
  });

  it('does not delete anything in extend mode, only creates', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(state({
      rules: [rule({ id: 'a' }), rule({ id: 'existing', profile: 2, day: '1' })],
    }));
    await el.updateComplete;

    await (el as any)._cloneRules(['a'], 2, '1', 'extend');

    const calls = hass.callWS.mock.calls.map((c: any) => c[0]);
    expect(calls.some((c: any) => c.type === 'shabbat_scheduler/rules/delete')).toBe(false);
  });

  it('stops issuing creates after the first rejection and reports exactly what landed', async () => {
    const { hass, send } = fakeHass();
    let call = 0;
    hass.callWS = vi.fn(async (message: any) => {
      call += 1;
      if (message.type === 'shabbat_scheduler/rules/create' && call === 2) {
        throw { message: 'rejected' };
      }
      return {};
    });
    const el = await mount(hass);
    send(state({ rules: [rule({ id: 'a' }), rule({ id: 'b' }), rule({ id: 'c' })] }));
    await el.updateComplete;

    const report = await (el as any)._cloneRules(['a', 'b', 'c'], 2, '1', 'extend');

    expect(report.landed).toEqual(['a']);
    expect(report.failed).toEqual(['b', 'c']);
    expect(report.error).toBe('rejected');
    // Only 2 creates attempted (a succeeded, b failed) - c never attempted.
    const creates = hass.callWS.mock.calls.filter(
      (c: any) => c[0].type === 'shabbat_scheduler/rules/create',
    );
    expect(creates).toHaveLength(2);
  });

  it('stops before any create when overwrite mode fails to clear the target', async () => {
    const { hass, send } = fakeHass();
    hass.callWS = vi.fn(async (message: any) => {
      if (message.type === 'shabbat_scheduler/rules/delete') throw { message: 'delete failed' };
      return {};
    });
    const el = await mount(hass);
    send(state({ rules: [rule({ id: 'a' }), rule({ id: 'existing', profile: 2, day: '1' })] }));
    await el.updateComplete;

    const report = await (el as any)._cloneRules(['a'], 2, '1', 'overwrite');

    expect(report.landed).toEqual([]);
    expect(report.failed).toEqual(['a']);
    const creates = hass.callWS.mock.calls.filter(
      (c: any) => c[0].type === 'shabbat_scheduler/rules/create',
    );
    expect(creates).toHaveLength(0);
  });
});

describe('clone dialog wiring in card.ts', () => {
  it('opens the clone dialog on clone-open from a day group', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(state({ rules: [rule({ id: 'a' })] }));
    await el.updateComplete;

    el.shadowRoot!.querySelector('shabbat-day-group')!.dispatchEvent(
      new CustomEvent('clone-open', {
        detail: { scope: 'day', profile: 1, day: 'erev' },
        bubbles: true, composed: true,
      }),
    );
    await el.updateComplete;

    expect(el.shadowRoot!.querySelector('shabbat-clone-dialog')).not.toBeNull();
  });

  it('clones a whole profile day-by-day, skipping days the target does not have', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(state({
      rules: [
        rule({ id: 'erev-rule', profile: 3, day: 'erev' }),
        rule({ id: 'day1-rule', profile: 3, day: '1' }),
        rule({ id: 'day3-rule', profile: 3, day: '3' }), // target (1d) has no day '3'
      ],
    }));
    await el.updateComplete;

    el.shadowRoot!.querySelector('shabbat-block-header')!.dispatchEvent(
      new CustomEvent('clone-open', {
        detail: { scope: 'profile', profile: 3 }, bubbles: true, composed: true,
      }),
    );
    await el.updateComplete;

    const dialog = el.shadowRoot!.querySelector('shabbat-clone-dialog') as any;
    dialog._targetProfile = 1;
    dialog.dispatchEvent(new CustomEvent('dialog-clone-confirm', {
      detail: {
        sourceRuleIds: ['erev-rule', 'day1-rule', 'day3-rule'],
        sourceScope: 'profile', sourceProfile: 3,
        targetProfile: 1, mode: 'extend',
      },
    }));
    await flush();

    const creates = hass.callWS.mock.calls
      .map((c: any) => c[0])
      .filter((c: any) => c.type === 'shabbat_scheduler/rules/create');
    expect(creates).toHaveLength(2); // erev and day 1 only, day 3 skipped
    expect(creates.map((c: any) => c.rule.day).sort()).toEqual(['1', 'erev']);
  });

  it('clones a narrow (1-day) source profile onto a wider (3-day) target, touching only the shared day', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(state({
      rules: [
        rule({ id: 'erev-rule', profile: 1, day: 'erev' }),
        rule({ id: 'day1-rule', profile: 1, day: '1' }),
      ],
    }));
    await el.updateComplete;

    el.shadowRoot!.querySelector('shabbat-block-header')!.dispatchEvent(
      new CustomEvent('clone-open', {
        detail: { scope: 'profile', profile: 1 }, bubbles: true, composed: true,
      }),
    );
    await el.updateComplete;

    const dialog = el.shadowRoot!.querySelector('shabbat-clone-dialog') as any;
    dialog._targetProfile = 3;
    dialog.dispatchEvent(new CustomEvent('dialog-clone-confirm', {
      detail: {
        sourceRuleIds: ['erev-rule', 'day1-rule'],
        sourceScope: 'profile', sourceProfile: 1,
        targetProfile: 3, mode: 'extend',
      },
    }));
    await flush();

    const creates = hass.callWS.mock.calls
      .map((c: any) => c[0])
      .filter((c: any) => c.type === 'shabbat_scheduler/rules/create');
    // Days 2 and 3 of the target are untouched - only erev and day 1 land.
    expect(creates.map((c: any) => c.rule.day).sort()).toEqual(['1', 'erev']);
    expect(creates.every((c: any) => c.rule.profile === 3)).toBe(true);
  });

  it('marks every rule from a day never attempted as failed too, after an earlier target day fails', async () => {
    const { hass, send } = fakeHass();
    let creates = 0;
    hass.callWS = vi.fn(async (message: any) => {
      if (message.type === 'shabbat_scheduler/rules/create') {
        creates += 1;
        if (creates === 1) throw { message: 'rejected' };
      }
      return {};
    });
    const el = await mount(hass);
    send(state({
      rules: [
        rule({ id: 'erev-rule', profile: 3, day: 'erev' }),
        rule({ id: 'day1-rule', profile: 3, day: '1' }),
      ],
    }));
    await el.updateComplete;

    el.shadowRoot!.querySelector('shabbat-block-header')!.dispatchEvent(
      new CustomEvent('clone-open', {
        detail: { scope: 'profile', profile: 3 }, bubbles: true, composed: true,
      }),
    );
    await el.updateComplete;

    let dialog = el.shadowRoot!.querySelector('shabbat-clone-dialog') as any;
    dialog.dispatchEvent(new CustomEvent('dialog-clone-confirm', {
      detail: {
        sourceRuleIds: ['erev-rule', 'day1-rule'],
        sourceScope: 'profile', sourceProfile: 3,
        targetProfile: 3, mode: 'extend',
      },
    }));
    await flush();
    await el.updateComplete;

    dialog = el.shadowRoot!.querySelector('shabbat-clone-dialog') as any;
    // erev failed outright; day 1 was never even attempted - both must be
    // reported as still missing, not silently dropped.
    expect(dialog.failed.slice().sort()).toEqual(['day1-rule', 'erev-rule']);
    expect(dialog.landed).toEqual([]);
  });

  it('retries only the still-missing rules on the next confirm, and closes once they all land', async () => {
    const { hass, send } = fakeHass();
    let creates = 0;
    hass.callWS = vi.fn(async (message: any) => {
      if (message.type === 'shabbat_scheduler/rules/create') {
        creates += 1;
        if (creates === 2) throw { message: 'rejected' };
      }
      return {};
    });
    const el = await mount(hass);
    send(state({
      rules: [
        rule({ id: 'a', profile: 1, day: 'erev', time: '11:00:00' }),
        rule({ id: 'b', profile: 1, day: 'erev', time: '12:00:00' }),
      ],
    }));
    await el.updateComplete;

    el.shadowRoot!.querySelector('shabbat-day-group')!.dispatchEvent(
      new CustomEvent('clone-open', {
        detail: { scope: 'day', profile: 1, day: 'erev' }, bubbles: true, composed: true,
      }),
    );
    await el.updateComplete;

    let dialog = el.shadowRoot!.querySelector('shabbat-clone-dialog') as any;
    dialog._targetProfile = 2;
    dialog.dispatchEvent(new CustomEvent('dialog-clone-confirm', {
      detail: {
        sourceRuleIds: ['a', 'b'], sourceScope: 'day', sourceProfile: 1,
        targetProfile: 2, targetDay: 'erev', mode: 'extend',
      },
    }));
    await flush();
    await el.updateComplete;

    dialog = el.shadowRoot!.querySelector('shabbat-clone-dialog') as any;
    expect(dialog.failed).toEqual(['b']);

    // Retry via the dialog's own confirm button: `failed` is now fed back
    // in as a prop, so the dialog itself narrows to the remainder.
    (dialog.shadowRoot!.querySelector('.confirm') as HTMLElement).click();
    await flush();
    await el.updateComplete;

    const createCalls = hass.callWS.mock.calls
      .map((c: any) => c[0])
      .filter((c: any) => c.type === 'shabbat_scheduler/rules/create');
    // First attempt: 'a' lands, 'b' fails (2 creates). Retry: only 'b' is
    // re-attempted (1 more create) - 'a' is never re-sent.
    expect(createCalls).toHaveLength(3);
    expect(createCalls.map((c: any) => c.rule.time)).toEqual([
      '11:00:00', '12:00:00', '12:00:00',
    ]);
    // Fully landed on retry - the dialog closes.
    expect(el.shadowRoot!.querySelector('shabbat-clone-dialog')).toBeNull();
  });
});
