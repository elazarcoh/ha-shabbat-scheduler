import { t } from './strings';
import type {
  BlockData,
  CardState,
  DayGroup,
  Defaults,
  RuleData,
  WarningData,
} from './types';

/** Erev sorts before day 1, then days ascend numerically. */
function dayRank(day: string): number {
  return day === 'erev' ? -1 : Number(day);
}

function dayKeys(block: BlockData): string[] {
  const days = ['erev'];
  for (let i = 1; i <= block.length; i += 1) days.push(String(i));
  return days;
}

/**
 * The block's dates in calendar order: erev, then day 1, day 2, ….
 *
 * `block.dates` is a plain object keyed 'erev' | '1' | '2' ..., and
 * JavaScript enumerates integer-index-like keys in ascending numeric
 * order *before* string keys - so 'erev' comes last no matter how the
 * object was built. Relying on Object.values/Object.keys order here
 * renders the block's dates backwards. Missing days are skipped rather
 * than surfaced as empty strings.
 */
export function orderedDates(block: BlockData): string[] {
  return dayKeys(block)
    .map((day) => block.dates[day])
    .filter((date): date is string => date !== undefined);
}

/**
 * The timeline: one group per day of the block, in order, each carrying
 * its date, its rules ordered by time, and its zmanim marker if one
 * falls at its end.
 *
 * Only rules matching the block's length are shown - rules are authored
 * per profile, and a 3-day chag's rules must not appear on a plain
 * Shabbat.
 */
export function buildGroups(state: CardState): DayGroup[] {
  const { block } = state;
  if (block === null) return [];

  const lastDay = String(block.length);
  return dayKeys(block).map((day) => {
    const rules = state.rules
      .filter((rule) => rule.profile === block.length && rule.day === day)
      .sort((a, b) => a.time.localeCompare(b.time));

    let marker: DayGroup['marker'] = null;
    if (day === 'erev') {
      marker = { kind: 'candle_lighting', at: block.candle_lighting };
    } else if (day === lastDay) {
      marker = { kind: 'havdalah', at: block.havdalah };
    }

    return { day, date: block.dates[day] ?? null, rules, marker };
  }).sort((a, b) => dayRank(a.day) - dayRank(b.day));
}

/**
 * One line describing what a rule does, resolved exactly the way the
 * engine resolves it: the rule's own devices and settings win, and
 * anything it omits falls back to the defaults.
 */
export function ruleBrief(rule: RuleData, defaults: Defaults): string {
  if (rule.action === 'custom') {
    return rule.script ?? '';
  }

  const devices = rule.devices.length ? rule.devices : (defaults.devices ?? []);
  const settings = { ...(defaults.settings ?? {}), ...rule.settings };

  const parts = [devices.join(', ')];
  if (rule.action === 'on') {
    for (const value of Object.values(settings)) {
      if (value !== undefined && value !== null) parts.push(String(value));
    }
  }
  return parts.filter((part) => part !== '').join(' · ');
}

const COLOURS: Record<string, string> = {
  on: 'var(--success-color, #2e9e5b)',
  off: 'var(--error-color, #d64545)',
  custom: 'var(--info-color, #3b7ddd)',
};

export function actionColour(action: string): string {
  return COLOURS[action] ?? 'var(--secondary-text-color, #888)';
}

/** Warnings naming this rule, so a conflict shows where it happens. */
export function warningsForRule(
  ruleId: string,
  warnings: WarningData[],
): WarningData[] {
  return warnings.filter((warning) => warning.rule_ids?.includes(ruleId));
}

/**
 * Warnings that have nowhere else to go, for the banner.
 *
 * `buildGroups` only shows rules whose profile matches the current
 * block length, but warnings are never filtered by profile. A warning
 * naming no rule, or naming only rules that are not among the ones
 * currently displayed, would otherwise be shown on no row and dropped
 * here too - rendered nowhere. Conflicts are never auto-resolved, so a
 * conflict nobody can see is exactly the failure this card exists to
 * prevent; it must surface in the banner instead.
 */
export function unattachedWarnings(
  warnings: WarningData[],
  displayedRuleIds: string[],
): WarningData[] {
  const displayed = new Set(displayedRuleIds);
  return warnings.filter(
    (warning) => !warning.rule_ids?.some((id) => displayed.has(id)),
  );
}

/** 'erev' -> 'Erev' / 'ערב'; '1' -> 'Day 1' / 'יום 1'. */
function dayLabel(day: string, language: string | undefined): string {
  return day === 'erev' ? t(language, 'erev') : `${t(language, 'day')} ${day}`;
}

/**
 * A warning as prose a person can act on. The only warning this card's
 * `_state_payload` ever sends is a conflict - see the comment on
 * `WarningData` - which carries no `message`, so this is the sole place
 * a conflict becomes human-readable text, naming the device and the
 * time so the person who must resolve it (nothing here auto-resolves)
 * knows exactly what to look at.
 *
 * Falls back to `message` for the `preview_payload` shape this card
 * does not currently receive, so a stray warning still renders as
 * something rather than nothing.
 */
export function formatWarning(warning: WarningData, language?: string): string {
  if (warning.kind === 'conflict' && warning.device !== undefined && warning.time !== undefined) {
    const parts = [t(language, 'conflict_prefix'), warning.device];
    if (warning.day !== undefined) parts.push(dayLabel(warning.day, language));
    parts.push(warning.time);
    return parts.join(' · ');
  }
  return warning.message ?? '';
}
