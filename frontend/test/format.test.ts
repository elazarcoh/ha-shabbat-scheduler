import { describe, expect, it } from 'vitest';
import {
  actionColour,
  buildGroups,
  formatWarning,
  ruleBrief,
  unattachedWarnings,
  warningsForRule,
} from '../src/format';
import type { CardState, RuleData, WarningData } from '../src/types';

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
  // Shaped exactly like block.conflict_warnings emits (block.py:135-154):
  // no `message`, but device/profile/day/time and non-empty rule_ids.
  const conflict: WarningData = {
    kind: 'conflict',
    device: 'climate.salon',
    profile: 1,
    day: '1',
    time: '11:00:00',
    rule_ids: ['a', 'b'],
  };
  // preview_payload's shape (a different websocket command) - included
  // only to prove partitioning still works when a warning names no rule.
  const noProfile: WarningData = { kind: 'no_profile', message: 'nothing enabled' };

  it('attaches a conflict to each rule it names', () => {
    expect(warningsForRule('a', [conflict, noProfile])).toEqual([conflict]);
    expect(warningsForRule('b', [conflict, noProfile])).toEqual([conflict]);
  });

  it('attaches nothing to an unnamed rule', () => {
    expect(warningsForRule('c', [conflict, noProfile])).toEqual([]);
  });

  it('leaves warnings naming no rule for the banner', () => {
    // conflict's rules ('a', 'b') are among the displayed ones here, so
    // it is shown on those rows instead - see warningsForRule above.
    expect(unattachedWarnings([conflict, noProfile], ['a', 'b'])).toEqual([noProfile]);
  });

  // CONFIRMED DEFECT: buildGroups only shows rules whose profile matches
  // the current block length, but warnings are never filtered by profile.
  // A conflict naming only rules that are not displayed must still reach
  // the banner - otherwise it renders nowhere, and conflicts are never
  // auto-resolved, so a hidden one would surface only when that chag
  // actually arrived.
  it('surfaces a conflict in the banner when none of the rules it names are displayed', () => {
    const hiddenProfileConflict: WarningData = {
      kind: 'conflict',
      device: 'climate.salon',
      profile: 3,
      day: '1',
      time: '11:00:00',
      rule_ids: ['not-shown'],
    };
    expect(unattachedWarnings([hiddenProfileConflict], ['a', 'b'])).toEqual([
      hiddenProfileConflict,
    ]);
  });
});

describe('formatWarning', () => {
  // The real shape _conflict_warnings sends - no `message`, ever.
  const conflict: WarningData = {
    kind: 'conflict',
    device: 'climate.salon',
    profile: 1,
    day: '1',
    time: '11:00:00',
    rule_ids: ['rule-a', 'rule-b'],
  };

  it('names the device and the time in English', () => {
    const text = formatWarning(conflict, 'en');
    expect(text).toContain('climate.salon');
    expect(text).toContain('11:00:00');
    expect(text).not.toContain('undefined');
  });

  it('names the device and the time in Hebrew', () => {
    const text = formatWarning(conflict, 'he');
    expect(text).toContain('climate.salon');
    expect(text).toContain('11:00:00');
    expect(text).not.toContain('undefined');
  });

  it('gives English and Hebrew visibly different text', () => {
    expect(formatWarning(conflict, 'en')).not.toBe(formatWarning(conflict, 'he'));
  });
});

import { deviceOptions } from '../src/format';
import type { HassEntity } from '../src/types';

// The real attributes of the three units this system drives.
const SALON: HassEntity = {
  state: 'off',
  attributes: {
    hvac_modes: ['off', 'heat_cool', 'cool', 'fan_only', 'dry', 'heat'],
    fan_modes: ['auto', 'quiet', 'low', 'medlow', 'medium', 'medhigh', 'high', 'strong'],
    min_temp: 16.0, max_temp: 31.0, target_temp_step: 0.5,
  },
};
const KIDS: HassEntity = {
  state: 'off',
  attributes: {
    hvac_modes: ['off', 'auto', 'cool', 'heat', 'dry', 'fan_only'],
    fan_modes: ['auto', 'low', 'medium', 'high', 'turbo', 'silent'],
    min_temp: 16, max_temp: 32, target_temp_step: 0.5,
  },
};
const BOOLEAN: HassEntity = { state: 'off', attributes: {} };

describe('deviceOptions', () => {
  it('offers exactly what a single device declares', () => {
    const o = deviceOptions({ 'climate.salon': SALON }, ['climate.salon']);
    expect(o.fanModes).toContain('quiet');
    expect(o.fanModes).not.toContain('silent');
    expect(o.minTemp).toBe(16);
    expect(o.maxTemp).toBe(31);
    expect(o.climate).toBe(true);
    expect(o.intersected).toBe(false);
  });

  it('intersects when devices disagree, dropping what only one offers', () => {
    const o = deviceOptions(
      { 'climate.salon': SALON, 'climate.kids': KIDS },
      ['climate.salon', 'climate.kids'],
    );
    expect(o.fanModes).toEqual(['auto', 'low', 'medium', 'high']);
    expect(o.fanModes).not.toContain('quiet');
    expect(o.fanModes).not.toContain('silent');
    expect(o.intersected).toBe(true);
  });

  it('narrows the temperature range to what every device accepts', () => {
    const o = deviceOptions(
      { 'climate.salon': SALON, 'climate.kids': KIDS },
      ['climate.salon', 'climate.kids'],
    );
    expect(o.minTemp).toBe(16);
    expect(o.maxTemp).toBe(31); // the salon's ceiling, not the kids' 32
  });

  it('reports a device it cannot read rather than pretending it offers nothing', () => {
    const o = deviceOptions({ 'climate.salon': SALON }, ['climate.salon', 'climate.gone']);
    expect(o.unreadable).toEqual(['climate.gone']);
    // The readable device still contributes - an absent one must not
    // intersect every option away to nothing.
    expect(o.fanModes).toContain('quiet');
  });

  it('treats an unavailable entity as unreadable', () => {
    const o = deviceOptions(
      { 'climate.salon': { state: 'unavailable', attributes: {} } },
      ['climate.salon'],
    );
    expect(o.unreadable).toEqual(['climate.salon']);
    expect(o.climate).toBe(false);
  });

  it('says a non-climate device has no settings', () => {
    const o = deviceOptions({ 'input_boolean.t': BOOLEAN }, ['input_boolean.t']);
    expect(o.climate).toBe(false);
    expect(o.fanModes).toEqual([]);
    expect(o.unreadable).toEqual([]);
  });

  it('returns empty options for no devices at all', () => {
    const o = deviceOptions({}, []);
    expect(o.climate).toBe(false);
    expect(o.intersected).toBe(false);
  });
});
