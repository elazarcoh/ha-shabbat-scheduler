import { t } from './strings';
import type {
  BlockData,
  CardState,
  DayGroup,
  Defaults,
  DeviceOptions,
  HassEntity,
  RuleData,
  RuleFormState,
  WarningData,
} from './types';

/** Erev sorts before day 1, then days ascend numerically. */
function dayRank(day: string): number {
  return day === 'erev' ? -1 : Number(day);
}

function daysFor(length: number): string[] {
  const days = ['erev'];
  for (let i = 1; i <= length; i += 1) days.push(String(i));
  return days;
}

function dayKeys(block: BlockData): string[] {
  return daysFor(block.length);
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

/** True when the selected length is not the one actually coming. */
export function isPreview(state: CardState, profile: number): boolean {
  return state.block === null || state.block.length !== profile;
}

/**
 * The timeline for one profile.
 *
 * With no `profile`, or one equal to the coming block's length, this is
 * the real thing: real dates on the headings and the zmanim markers in
 * place. For any other length it is a PREVIEW - the same rules, but no
 * dates and no markers at all.
 *
 * Dropping the dates is deliberate. A hypothetical Chag's dates would be
 * a guess that looks exactly like a real one, and this card exists
 * because its user could not otherwise tell what was real.
 *
 * Only rules of the selected profile are shown: rules are authored per
 * profile, and a 3-day Chag's rules must not appear on a plain Shabbat.
 */
export function buildGroups(state: CardState, profile?: number): DayGroup[] {
  const { block } = state;
  const length = profile ?? block?.length ?? null;
  if (length === null) return [];

  const preview = isPreview(state, length);
  const lastDay = String(length);

  return daysFor(length)
    .map((day) => {
      const rules = state.rules
        .filter((rule) => rule.profile === length && rule.day === day)
        .sort((a, b) => a.time.localeCompare(b.time));

      let marker: DayGroup['marker'] = null;
      if (!preview && block !== null) {
        if (day === 'erev') {
          marker = { kind: 'candle_lighting', at: block.candle_lighting };
        } else if (day === lastDay) {
          marker = { kind: 'havdalah', at: block.havdalah };
        }
      }

      const date = preview || block === null ? null : (block.dates[day] ?? null);
      return { day, date, rules, marker };
    })
    .sort((a, b) => dayRank(a.day) - dayRank(b.day));
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

function readList(entity: HassEntity, key: string): string[] | null {
  const value = entity.attributes[key];
  return Array.isArray(value) ? value.map(String) : null;
}

function readNumber(entity: HassEntity, key: string): number | null {
  const value = entity.attributes[key];
  return typeof value === 'number' ? value : null;
}

/**
 * What the selected devices actually offer, read from their own state.
 *
 * The three units here disagree: the salon offers `quiet` and not
 * `silent`, the AUX units the reverse. Offering a fixed list is how a
 * rule gets saved with a fan mode its device rejects - discovered at
 * 11:00 on Shabbat, when nobody can fix it. With several devices the
 * intersection is the only honest answer: a mode only one of them
 * supports cannot be applied to the others.
 *
 * A device that cannot be read is REPORTED, never silently treated as
 * offering nothing - that would intersect every option away and present
 * an empty form as though the device were the problem.
 */
export function deviceOptions(
  states: Record<string, HassEntity | undefined>,
  entityIds: string[],
): DeviceOptions {
  const unreadable: string[] = [];
  const readable: HassEntity[] = [];

  for (const id of entityIds) {
    const entity = states[id];
    if (
      entity === undefined ||
      entity.state === 'unavailable' ||
      entity.state === 'unknown'
    ) {
      unreadable.push(id);
      continue;
    }
    readable.push(entity);
  }

  const climates = readable.filter((entity) => readList(entity, 'hvac_modes') !== null);
  if (climates.length === 0) {
    return {
      hvacModes: [], fanModes: [], minTemp: null, maxTemp: null,
      tempStep: null, unreadable, climate: false, intersected: false,
    };
  }

  const intersect = (key: string): string[] =>
    climates
      .map((entity) => readList(entity, key) ?? [])
      .reduce((acc, list) => acc.filter((item) => list.includes(item)));

  const bounds = (key: string, pick: (values: number[]) => number): number | null => {
    const values = climates
      .map((entity) => readNumber(entity, key))
      .filter((value): value is number => value !== null);
    return values.length ? pick(values) : null;
  };

  return {
    hvacModes: intersect('hvac_modes'),
    fanModes: intersect('fan_modes'),
    // The narrowest range every device accepts.
    minTemp: bounds('min_temp', (values) => Math.max(...values)),
    maxTemp: bounds('max_temp', (values) => Math.min(...values)),
    tempStep: bounds('target_temp_step', (values) => Math.max(...values)),
    unreadable,
    climate: true,
    intersected: climates.length > 1,
  };
}

const FORM_FIELDS = [
  'day', 'time', 'action', 'devices', 'settings', 'name', 'icon',
  'color', 'enabled', 'script', 'variables', 'replay_on_restart',
] as const;

export function ruleToForm(rule: RuleData): RuleFormState {
  return {
    day: rule.day,
    time: rule.time,
    action: rule.action,
    devices: [...rule.devices],
    settings: { ...rule.settings },
    name: rule.name,
    icon: rule.icon,
    color: rule.color,
    enabled: rule.enabled,
    script: rule.script,
    variables: { ...rule.variables },
    replay_on_restart: rule.replay_on_restart,
  };
}

/** Everything, plus the profile the day is being authored under. */
export function formToCreate(
  form: RuleFormState,
  profile: number,
): Record<string, unknown> {
  return { ...form, profile };
}

/**
 * Only the fields that genuinely differ.
 *
 * `changes_from_api` takes a partial, and sending the whole rule back
 * would record an edit of every field in the logbook every time anyone
 * saved anything. Compared by value, not reference - a devices array
 * rebuilt from the same strings has not changed.
 */
export function formToChanges(
  form: RuleFormState,
  original: RuleData,
): Record<string, unknown> {
  const changes: Record<string, unknown> = {};
  for (const field of FORM_FIELDS) {
    const next = form[field];
    const prev = (original as unknown as Record<string, unknown>)[field];
    if (JSON.stringify(next) !== JSON.stringify(prev)) changes[field] = next;
  }
  return changes;
}
