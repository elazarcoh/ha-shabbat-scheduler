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

/** Warnings naming no rule at all, for the banner. */
export function unattachedWarnings(warnings: WarningData[]): WarningData[] {
  return warnings.filter((warning) => !warning.rule_ids?.length);
}
