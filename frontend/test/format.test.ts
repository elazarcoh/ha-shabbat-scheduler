import { describe, expect, it } from 'vitest';
import {
  buildGroups,
  describeTarget,
  foldCallResults,
  formatWarning,
  isPreview,
  ruleBrief,
  ruleColour,
  unattachedWarnings,
  warningsForRule,
} from '../src/format';
import type { CardState, RuleData, WarningData } from '../src/types';

const rule = (over: Partial<RuleData>): RuleData => ({
  id: 'r', profile: 1, day: '1', time: '11:00:00',
  action: 'climate.turn_on', target: {}, data: {}, condition: [],
  replay: { enabled: false }, name: null, icon: null, enabled: true,
  color: null, last_outcome: null,
  ...over,
});

const state = (over: Partial<CardState>): CardState => ({
  defaults: {}, rules: [], enabled: true, warnings: [],
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

describe('buildGroups with a profile', () => {
  const threeDayRule = rule({ id: 'chag', profile: 3, day: '2', time: '11:00:00' });

  it('shows the current profile with real dates when it matches the block', () => {
    const groups = buildGroups(state({ rules: [rule({ id: 'a', profile: 1, day: '1' })] }), 1);
    expect(groups.map((g) => g.day)).toEqual(['erev', '1']);
    expect(groups[1].date).toBe('2026-08-15');
    expect(groups[1].marker?.kind).toBe('havdalah');
  });

  it('gives a preview profile the right number of days', () => {
    const groups = buildGroups(state({ rules: [threeDayRule] }), 3);
    expect(groups.map((g) => g.day)).toEqual(['erev', '1', '2', '3']);
  });

  it('drops dates and markers in preview, so nothing reads as a real date', () => {
    const groups = buildGroups(state({ rules: [threeDayRule] }), 3);
    for (const group of groups) {
      expect(group.date).toBeNull();
      expect(group.marker).toBeNull();
    }
  });

  it('shows the selected profile rules, not the block-length ones', () => {
    const groups = buildGroups(
      state({ rules: [rule({ id: 'one', profile: 1, day: '1' }), threeDayRule] }),
      3,
    );
    expect(groups.flatMap((g) => g.rules.map((r) => r.id))).toEqual(['chag']);
  });

  it('still works with no block at all, so the card is not a dead end', () => {
    const groups = buildGroups(state({ block: null, rules: [threeDayRule] }), 3);
    expect(groups.map((g) => g.day)).toEqual(['erev', '1', '2', '3']);
    expect(groups[0].date).toBeNull();
  });

  it('defaults to the block length when no profile is given', () => {
    const groups = buildGroups(state({ rules: [rule({ id: 'a', profile: 1, day: '1' })] }));
    expect(groups.map((g) => g.day)).toEqual(['erev', '1']);
    expect(groups[1].date).toBe('2026-08-15');
  });
});

describe('isPreview', () => {
  it('is false for the coming block length', () => {
    expect(isPreview(state({}), 1)).toBe(false);
  });
  it('is true for any other length', () => {
    expect(isPreview(state({}), 3)).toBe(true);
  });
  it('is true whenever there is no block to be current about', () => {
    expect(isPreview(state({ block: null }), 1)).toBe(true);
  });
});

describe('ruleBrief', () => {
  it('names the action, which is the whole description now', () => {
    const brief = ruleBrief(rule({ action: 'climate.set_temperature' }), {});
    expect(brief).toContain('climate.set_temperature');
  });

  it('falls back to the defaults target when the rule has none', () => {
    const brief = ruleBrief(
      rule({ target: {} }),
      { target: { entity_id: ['climate.salon'] } },
    );
    expect(brief).toContain('climate.salon');
  });

  it('prefers the rule target over the defaults', () => {
    const brief = ruleBrief(
      rule({ target: { entity_id: ['climate.kids'] } }),
      { target: { entity_id: ['climate.salon'] } },
    );
    expect(brief).toContain('climate.kids');
    expect(brief).not.toContain('climate.salon');
  });

  it('merges data over the defaults data', () => {
    const brief = ruleBrief(
      rule({
        action: 'climate.set_temperature',
        target: { entity_id: ['climate.a'] },
        data: { temperature: 24 },
      }),
      { data: { temperature: 26, fan_mode: 'quiet' } },
    );
    expect(brief).toContain('24');
    expect(brief).toContain('quiet');
    expect(brief).not.toContain('26');
  });

  it('describes a script rule, which v1 had a special case for', () => {
    const brief = ruleBrief(
      rule({ action: 'script.turn_on', target: { entity_id: ['script.boiler'] } }),
      {},
    );
    expect(brief).toContain('script.boiler');
  });
});

describe('describeTarget', () => {
  it('names every entity in an entity_id list', () => {
    expect(describeTarget({ entity_id: ['climate.a', 'climate.b'] }))
      .toBe('climate.a, climate.b');
  });

  it('accepts a bare string as well as a list', () => {
    expect(describeTarget({ entity_id: 'climate.a' })).toBe('climate.a');
  });

  it('names an area target as its area, never as guessed entities', () => {
    // The card cannot resolve an area to its entities; only the server
    // can. Showing the area id is the honest answer.
    expect(describeTarget({ area_id: ['salon'] })).toBe('salon');
  });

  it('names every selector key a target carries, not just the first', () => {
    const text = describeTarget({
      entity_id: ['climate.a'],
      area_id: ['salon'],
      label_id: 'shabbat',
    });
    expect(text).toContain('climate.a');
    expect(text).toContain('salon');
    expect(text).toContain('shabbat');
  });

  it('is empty for an empty target', () => {
    expect(describeTarget({})).toBe('');
  });
});

describe('ruleColour', () => {
  it("uses the rule's own colour when it has one", () => {
    expect(ruleColour(rule({ color: '#123456' }))).toBe('#123456');
  });

  it('gives a rule with no colour a neutral one rather than guessing', () => {
    // v1 coloured the dot from its on/off/custom enum. A v2 action is an
    // arbitrary service, so two different services must NOT get two
    // different colours invented for them.
    const on = ruleColour(rule({ action: 'switch.turn_on' }));
    const set = ruleColour(rule({ action: 'climate.set_temperature' }));
    expect(on).toBe(set);
    expect(typeof on).toBe('string');
  });
});

describe('warning attachment', () => {
  // Shaped exactly like block.conflict_warnings emits: no `message`, but
  // targets (a LIST) / profile / day / time and non-empty rule_ids.
  const conflict: WarningData = {
    kind: 'conflict',
    targets: ['climate.salon'],
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
      targets: ['climate.salon'],
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
  // The real shape _conflict_warnings sends - no `message`, ever, and
  // `targets` is a LIST.
  const conflict: WarningData = {
    kind: 'conflict',
    targets: ['climate.salon'],
    profile: 1,
    day: '1',
    time: '11:00:00',
    rule_ids: ['rule-a', 'rule-b'],
  };

  it('names the target and the time in English', () => {
    const text = formatWarning(conflict, 'en');
    expect(text).toContain('climate.salon');
    expect(text).toContain('11:00:00');
    expect(text).not.toContain('undefined');
  });

  it('names the target and the time in Hebrew', () => {
    const text = formatWarning(conflict, 'he');
    expect(text).toContain('climate.salon');
    expect(text).toContain('11:00:00');
    expect(text).not.toContain('undefined');
  });

  it('gives English and Hebrew visibly different text', () => {
    expect(formatWarning(conflict, 'en')).not.toBe(formatWarning(conflict, 'he'));
  });

  // REGRESSION TEST for a live break: the backend renamed this key from
  // `device` (one string) to `targets` (a sorted list), because a
  // conflict is the INTERSECTION of two rules' resolved targets and an
  // area can expand to several entities. The card kept testing
  // `warning.device !== undefined`, which is now never true, so every
  // conflict warning silently rendered as an empty string - a
  // conflicting schedule displayed as clean, on every install, with the
  // conflict correctly detected and sitting unread in the payload.
  it('renders a conflict that names SEVERAL entities', () => {
    const text = formatWarning(
      { ...conflict, targets: ['climate.a', 'climate.b'] },
      'en',
    );
    expect(text).toContain('climate.a');
    expect(text).toContain('climate.b');
    expect(text).not.toBe('');
  });

  it('never renders a conflict as an empty string', () => {
    expect(formatWarning(conflict, 'en')).not.toBe('');
  });

  it('falls back to `message` for a warning it cannot describe', () => {
    expect(formatWarning({ kind: 'no_block', message: 'no block' }, 'en'))
      .toBe('no block');
  });
});

import { formToChanges, formToCreate, ruleToForm } from '../src/format';

const base = rule({
  id: 'r1', profile: 1, day: '1', time: '11:00:00',
  action: 'climate.set_temperature',
  target: { entity_id: ['climate.salon'] },
  data: { temperature: 26 },
  condition: [{ condition: 'state', entity_id: 'binary_sensor.gate', state: 'on' }],
  replay: { enabled: true, within: '02:00:00' },
  name: 'Morning',
});

describe('ruleToForm / formToCreate / formToChanges', () => {
  it('round-trips a rule through the form unchanged', () => {
    expect(formToChanges(ruleToForm(base), base)).toEqual({});
  });

  it('sends only what changed', () => {
    const form = { ...ruleToForm(base), time: '12:00:00' };
    expect(formToChanges(form, base)).toEqual({ time: '12:00:00' });
  });

  it('detects a changed target, not just a changed reference', () => {
    const same = { ...ruleToForm(base), target: { entity_id: ['climate.salon'] } };
    expect(formToChanges(same, base)).toEqual({});
    const different = { ...ruleToForm(base), target: { entity_id: ['climate.kids'] } };
    expect(formToChanges(different, base))
      .toEqual({ target: { entity_id: ['climate.kids'] } });
  });

  it('detects a changed data value', () => {
    const form = { ...ruleToForm(base), data: { temperature: 24 } };
    expect(formToChanges(form, base)).toEqual({ data: { temperature: 24 } });
  });

  // The dialog does not EDIT these, but the form carries them so that an
  // ordinary edit cannot drop them and a duplicate is a real duplicate.
  it('carries condition and replay through an untouched edit', () => {
    const form = { ...ruleToForm(base), name: 'renamed' };
    expect(formToChanges(form, base)).toEqual({ name: 'renamed' });
  });

  it('sends a cleared name as null rather than omitting it', () => {
    const form = { ...ruleToForm(base), name: null };
    expect(formToChanges(form, base)).toEqual({ name: null });
  });

  it('builds a create payload carrying the profile and every field', () => {
    const payload = formToCreate(ruleToForm(base), 3);
    expect(payload.profile).toBe(3);
    expect(payload.day).toBe('1');
    expect(payload.action).toBe('climate.set_temperature');
    expect(payload.target).toEqual({ entity_id: ['climate.salon'] });
    // A duplicate goes through formToCreate too, so the payload it
    // cannot edit must still travel with it - otherwise "Duplicate"
    // quietly produces a rule that does something different.
    expect(payload.data).toEqual({ temperature: 26 });
    expect(payload.condition).toEqual(base.condition);
    expect(payload.replay).toEqual({ enabled: true, within: '02:00:00' });
    // A create must never carry an id - the server generates it.
    expect(payload.id).toBeUndefined();
  });

  it('keeps enabled as a real boolean, never a string', () => {
    const payload = formToCreate({ ...ruleToForm(base), enabled: false }, 1);
    expect(payload.enabled).toBe(false);
    expect(typeof payload.enabled).toBe('boolean');
  });
});

describe('foldCallResults', () => {
  it('reports the single result verbatim', () => {
    const result = foldCallResults(
      [{ outcome: 'would_call' }], '2026-08-25T18:00:00Z',
    );
    expect(result).toEqual({ outcome: 'would_call', at: '2026-08-25T18:00:00Z', detail: null });
  });

  it('picks the worst outcome across multiple calls, precedence-ordered', () => {
    const result = foldCallResults(
      [{ outcome: 'called' }, { outcome: 'failed', error: 'boom' }],
      '2026-08-25T18:00:00Z',
    );
    expect(result.outcome).toBe('failed');
    expect(result.detail).toBe('boom');
  });

  it('unions unknown_targets across calls', () => {
    const result = foldCallResults(
      [
        { outcome: 'called', unknown_targets: ['a.x'] },
        { outcome: 'called', unknown_targets: ['a.y'] },
      ],
      '2026-08-25T18:00:00Z',
    );
    expect(result.unknown_targets).toEqual(['a.x', 'a.y']);
  });

  it('reports unknown for an empty results list rather than throwing', () => {
    expect(foldCallResults([], '2026-08-25T18:00:00Z').outcome).toBe('unknown');
  });

  it('reads reason as detail for a blocked result, which has no error key', () => {
    const result = foldCallResults(
      [{ outcome: 'blocked', reason: 'condition 1 of 1 not met' }],
      '2026-08-25T18:00:00Z',
    );
    expect(result.detail).toBe('condition 1 of 1 not met');
  });
});
