import { describe, expect, it, vi } from 'vitest';
import '../src/card';
import type { CardState, RuleData } from '../src/types';
import { fakeHass, mount } from './helpers';

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
