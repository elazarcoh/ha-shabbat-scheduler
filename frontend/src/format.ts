import { t, type StringKey } from './strings';
import type {
  BlockData,
  CardState,
  DayGroup,
  Defaults,
  LastOutcome,
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
 * One line describing what a rule does: its action, then what it applies
 * to, resolved exactly the way the engine resolves it - the rule's own
 * `target`/`data` win, and anything it omits falls back to the defaults
 * (see `merge_defaults` in block.py).
 *
 * A rule is now an arbitrary Home Assistant service call, so there is no
 * on/off/custom vocabulary left to describe. Naming the service is the
 * honest summary: `climate.set_temperature` says exactly what will
 * happen, where v1's "on" left the reader to remember what "on" meant
 * for that particular device.
 */
export function ruleBrief(rule: RuleData, defaults: Defaults): string {
  const target = Object.keys(rule.target).length
    ? rule.target
    : (defaults.target ?? {});
  const data = { ...(defaults.data ?? {}), ...rule.data };

  const parts = [rule.action, describeTarget(target)];
  for (const value of Object.values(data)) {
    if (value !== undefined && value !== null) parts.push(String(value));
  }
  return parts.filter((part) => part !== '').join(' \u00b7 ');
}

/**
 * A target selector as a flat, readable list of what it names.
 *
 * A selector may hold `entity_id`, `area_id`, `device_id`, `floor_id` or
 * `label_id`, each a string or a list of strings. Everything it names is
 * shown; nothing is guessed at, expanded or filtered. An area target
 * reads as its area id rather than as the entities it will expand to,
 * because the card cannot resolve that and inventing an answer is the
 * one thing it must not do.
 */
export function describeTarget(target: Record<string, unknown>): string {
  const names: string[] = [];
  for (const value of Object.values(target)) {
    if (Array.isArray(value)) names.push(...value.map(String));
    else if (value !== null && value !== undefined) names.push(String(value));
  }
  return names.join(', ');
}

/**
 * The colour of a rule's dot.
 *
 * v1 keyed this off its three-value action enum: green for on, red for
 * off, blue for custom. A v2 action is an arbitrary "domain.service", so
 * there is no on/off to read - and guessing from the service name would
 * be wrong for exactly the actions that are not switches
 * (`climate.set_temperature`, `notify.mobile_app`). The rule's own
 * `color` field is how an author says what they want; everything else
 * gets one neutral colour rather than a colour that means nothing.
 */
export function ruleColour(rule: RuleData): string {
  return rule.color ?? 'var(--secondary-text-color, #888)';
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
 * a conflict becomes human-readable text, naming the entities and the
 * time so the person who must resolve it (nothing here auto-resolves)
 * knows exactly what to look at.
 *
 * Reads `warning.targets`, a LIST. It used to read `warning.device`, a
 * single string, and when the backend renamed that key every conflict
 * warning silently stopped rendering: the guard below was never true, so
 * a genuinely conflicting schedule displayed as clean while the conflict
 * sat correctly detected and unread in the payload.
 *
 * Falls back to `message` for the `preview_payload` shape this card
 * does not currently receive, so a stray warning still renders as
 * something rather than nothing.
 */
export function formatWarning(warning: WarningData, language?: string): string {
  if (
    warning.kind === 'conflict' &&
    warning.targets !== undefined &&
    warning.targets.length > 0 &&
    warning.time !== undefined
  ) {
    const parts = [t(language, 'conflict_prefix'), warning.targets.join(', ')];
    if (warning.day !== undefined) parts.push(dayLabel(warning.day, language));
    parts.push(warning.time);
    return parts.join(' · ');
  }
  return warning.message ?? '';
}

/**
 * The English phrase the server itself uses for a misspelt entity id,
 * byte-identical to `UNKNOWN_ENTITY_PREFIX` in const.py.
 *
 * Kept separately from the translated string because the two do different
 * jobs. The translated string is what the reader SEES; this is what
 * `formatOutcome` de-duplicates AGAINST - a total miss already reads "no
 * such entity: light.x" in `detail`, because that is what `_call` puts in
 * the failed result's `error`, and the card must not say it twice. The
 * server always sends `detail` in English, so the check has to be against
 * English whatever language the card is in.
 *
 * There is deliberately NO twin for `NO_LIVE_TARGETS_NOTE`, and the
 * symmetry with logbook.py is tempting and false. `logbook.py` de-duplicates
 * on both phrases because it BUILDS its own message and appends the note
 * itself. Here `detail` comes from the server, and `NO_LIVE_TARGETS_NOTE`
 * is never written into any result key at all - `engine.py` passes it only
 * as an argument to a `_LOGGER.warning`. A guard for it could never run,
 * and no test could ever notice its absence, so there is none.
 */
const SERVER_NO_SUCH_ENTITY = 'no such entity: ';

const OUTCOME_LABELS: Record<string, StringKey> = {
  called: 'outcome_called',
  would_call: 'outcome_would_call',
  failed: 'outcome_failed',
  blocked: 'outcome_blocked',
  skipped_stale: 'outcome_skipped_stale',
};

/**
 * A rule's own verdict as one line of prose.
 *
 * The same words the logbook row carries, on purpose. `detail` arrives
 * already written by the server - `_condition_block_reason`'s "condition 1
 * of 1 (state on input_boolean.kids) not met", the stale skip's "6:00:43
 * late, window 1:00:00", the failure's type-prefixed error - and the card
 * showing exactly those words is a feature: the person reading the card
 * and the person reading the logbook must not be told two different things
 * about the same rule.
 *
 * Both diagnostics are appended AFTER the outcome rather than replacing
 * it, most actionable first, in the same order `_note_diagnostics` uses in
 * logbook.py. A misspelling is the one the reader can fix; "reached
 * nothing" is the one that says a call that really happened changed
 * nothing anyway. Neither is an outcome, and a rule can be `called` and
 * carry either. Only the misspelling is de-duplicated - see
 * `SERVER_NO_SUCH_ENTITY` for why the other guard would be dead code.
 *
 * An unrecognised `outcome` still renders: this arrives over a socket from
 * a server that may be a version ahead, and a blank line reads as "nothing
 * happened", which is the one thing this card must never imply.
 */
export function formatOutcome(outcome: LastOutcome, language?: string): string {
  const key = OUTCOME_LABELS[outcome.outcome];
  let text = t(language, key ?? 'outcome_unknown');
  if (outcome.detail) text = `${text}: ${outcome.detail}`;

  const unknown = outcome.unknown_targets ?? [];
  if (unknown.length > 0 && !text.includes(SERVER_NO_SUCH_ENTITY)) {
    text = `${text} — ${t(language, 'outcome_no_such_entity')}${unknown.join(', ')}`;
  }
  if (outcome.no_live_targets === true) {
    text = `${text} — ${t(language, 'outcome_reached_nothing')}`;
  }
  return text;
}

/**
 * True when this verdict is something to worry about.
 *
 * The three non-firing outcomes, plus either target diagnostic on an
 * outcome that otherwise reads as success. That second half is the point:
 * `called` with a misspelt entity, or `called` having reached nothing, is
 * a rule that reported success and changed less than it claimed - which is
 * the failure mode this integration exists to surface, so it must not be
 * drawn as quietly as a rule that simply worked.
 */
export function outcomeIsBad(outcome: LastOutcome): boolean {
  return (
    outcome.outcome === 'failed' ||
    outcome.outcome === 'blocked' ||
    outcome.outcome === 'skipped_stale' ||
    (outcome.unknown_targets ?? []).length > 0 ||
    outcome.no_live_targets === true ||
    !(outcome.outcome in OUTCOME_LABELS)
  );
}

/**
 * When the verdict was reached, short and local.
 *
 * A durable outcome with no date is indistinguishable from last week's,
 * and a row reading "did not run — blocked" about a Shabbat that is long
 * over would send someone looking for a problem that no longer exists.
 *
 * Empty string for anything unparseable, so the caller can omit the
 * element entirely rather than render the literal "Invalid Date" - and so
 * a bad timestamp never takes the reason down with it.
 */
export function formatOutcomeAt(at: string, language?: string): string {
  const when = new Date(at);
  if (Number.isNaN(when.getTime())) return '';
  return when.toLocaleString(language === 'he' ? 'he-IL' : 'en-GB', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * Every field the form carries, including the four it displays read-only.
 *
 * `target`, `data`, `condition` and `replay` are in the diff on purpose
 * even though nothing edits them: carrying them means an edit cannot
 * silently drop a rule's payload, and it makes a duplicate a real
 * duplicate rather than a stripped copy. They compare equal on an
 * ordinary edit, so they simply never appear in the changes.
 */
const FORM_FIELDS = [
  'day', 'time', 'action', 'target', 'data', 'condition', 'replay',
  'name', 'icon', 'color', 'enabled',
] as const;

export function ruleToForm(rule: RuleData): RuleFormState {
  return {
    day: rule.day,
    time: rule.time,
    action: rule.action,
    target: { ...rule.target },
    data: { ...rule.data },
    condition: rule.condition.map((item) => ({ ...item })),
    replay: { ...rule.replay },
    name: rule.name,
    icon: rule.icon,
    color: rule.color,
    enabled: rule.enabled,
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
 * `changes_from_api` takes a partial, so a small diff keeps the write
 * small and the push it triggers meaningful. This is not what makes an
 * unchanged save skip the round trip, though - it does not: the card
 * always asks the server rather than assuming a diff of `{}` means
 * nothing could go wrong (the entry could be unloaded, the connection
 * dead, the rule deleted by another client). See `_saveChanges` in
 * `card.ts`. Compared by value, not reference - a target rebuilt
 * from the same keys has not changed.
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
