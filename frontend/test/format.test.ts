import { describe, expect, it } from 'vitest';
import {
  actionColour,
  buildGroups,
  ruleBrief,
  unattachedWarnings,
  warningsForRule,
} from '../src/format';
import type { CardState, RuleData } from '../src/types';

const rule = (over: Partial<RuleData>): RuleData => ({
  id: 'r', profile: 1, day: '1', time: '11:00:00', action: 'on',
  devices: [], settings: {}, name: null, icon: null, enabled: true,
  script: null, variables: {}, replay_on_restart: false, color: null,
  ...over,
});

const state = (over: Partial<CardState>): CardState => ({
  defaults: {}, rules: [], enabled: true, dry_run: false, warnings: [],
  master_entity_id: 'switch.master',
  block: {
    length: 1,
    candle_lighting: '2026-08-14T18:44:00+03:00',
    havdalah: '2026-08-15T20:01:00+03:00',
    dates: { erev: '2026-08-14', '1': '2026-08-15' },
  },
  ...over,
});

describe('buildGroups', () => {
  it('puts erev before day 1', () => {
    const groups = buildGroups(state({
      rules: [rule({ id: 'a', day: '1' }), rule({ id: 'b', day: 'erev' })],
    }));
    expect(groups.map((g) => g.day)).toEqual(['erev', '1']);
  });

  it('orders rules within a day by time', () => {
    const groups = buildGroups(state({
      rules: [
        rule({ id: 'late', day: '1', time: '18:00:00' }),
        rule({ id: 'early', day: '1', time: '11:00:00' }),
      ],
    }));
    // groups[0] is the (empty) erev group of the default 1-day block;
    // the day-1 rules land in groups[1].
    expect(groups[1].rules.map((r) => r.id)).toEqual(['early', 'late']);
  });

  it('shows only rules for the current block length', () => {
    const groups = buildGroups(state({
      rules: [rule({ id: 'one', profile: 1 }), rule({ id: 'three', profile: 3 })],
    }));
    const ids = groups.flatMap((g) => g.rules.map((r) => r.id));
    expect(ids).toEqual(['one']);
  });

  it('attaches candle lighting to erev and havdalah to the last day', () => {
    const groups = buildGroups(state({
      rules: [rule({ day: 'erev' }), rule({ day: '1' })],
    }));
    expect(groups[0].marker?.kind).toBe('candle_lighting');
    expect(groups[1].marker?.kind).toBe('havdalah');
  });

  it('gives every day of the block a group, even with no rules', () => {
    const groups = buildGroups(state({ rules: [] }));
    expect(groups.map((g) => g.day)).toEqual(['erev', '1']);
  });

  it('returns nothing when there is no block', () => {
    expect(buildGroups(state({ block: null }))).toEqual([]);
  });
});

describe('ruleBrief', () => {
  it('falls back to the defaults devices when the rule has none', () => {
    const brief = ruleBrief(rule({ devices: [] }), { devices: ['climate.salon'] });
    expect(brief).toContain('climate.salon');
  });

  it('prefers the rule devices over the defaults', () => {
    const brief = ruleBrief(rule({ devices: ['climate.kids'] }), {
      devices: ['climate.salon'],
    });
    expect(brief).toContain('climate.kids');
    expect(brief).not.toContain('climate.salon');
  });

  it('merges settings over the defaults settings', () => {
    const brief = ruleBrief(
      rule({ devices: ['climate.a'], settings: { temperature: 24 } }),
      { settings: { temperature: 26, fan_mode: 'quiet' } },
    );
    expect(brief).toContain('24');
    expect(brief).toContain('quiet');
    expect(brief).not.toContain('26');
  });

  it('names the script for a custom action', () => {
    const brief = ruleBrief(
      rule({ action: 'custom', script: 'script.boiler' }), {},
    );
    expect(brief).toContain('script.boiler');
  });
});

describe('actionColour', () => {
  it('gives on, off and custom three distinguishable colours', () => {
    const colours = new Set(['on', 'off', 'custom'].map(actionColour));
    expect(colours.size).toBe(3);
  });

  it('does not throw on an action it has never seen', () => {
    expect(typeof actionColour('something-new')).toBe('string');
  });
});

describe('warning attachment', () => {
  const conflict = { kind: 'conflict', message: 'clash', rule_ids: ['a', 'b'] };
  const noProfile = { kind: 'no_profile', message: 'nothing enabled' };

  it('attaches a conflict to each rule it names', () => {
    expect(warningsForRule('a', [conflict, noProfile])).toEqual([conflict]);
    expect(warningsForRule('b', [conflict, noProfile])).toEqual([conflict]);
  });

  it('attaches nothing to an unnamed rule', () => {
    expect(warningsForRule('c', [conflict, noProfile])).toEqual([]);
  });

  it('leaves warnings naming no rule for the banner', () => {
    expect(unattachedWarnings([conflict, noProfile])).toEqual([noProfile]);
  });
});
