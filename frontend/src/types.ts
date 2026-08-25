/** Mirrors _state_payload in websocket_api.py. Keep the two in step. */

/**
 * One rule: a Home Assistant service call, scheduled.
 *
 * v1's `action`/`devices`/`settings`/`script`/`variables` are gone. A rule
 * now names any `domain.service` (`action`), the entities/areas/labels it
 * applies to (`target`, a Home Assistant target selector) and that
 * service's own payload (`data`) - so a rule can drive anything Home
 * Assistant can, not just the four domains v1 understood.
 */
export interface RuleData {
  id: string;
  profile: number;
  day: string;            // 'erev' | '1' | '2' | '3'
  time: string;           // 'HH:MM:SS'
  action: string;         // 'domain.service', e.g. 'climate.set_temperature'
  target: Record<string, unknown>;   // HA target selector
  data: Record<string, unknown>;     // the service's own data
  condition: Record<string, unknown>[];  // HA condition configs; all must pass
  replay: ReplayData;
  name: string | null;
  icon: string | null;
  enabled: boolean;
  color: string | null;
  /**
   * Server-owned and read-only. Set by the v1 -> v2 migration on a rule it
   * could not convert, so the card can say WHICH rule needs attention
   * rather than showing a plausible-looking rule that will never fire.
   * `rule_schema.py` drops these on the way back in - a client cannot set
   * them, and echoing them back is not an error.
   */
  migration_error?: string | null;
  migration_source?: Record<string, unknown> | null;
}

/** Whether, and how late, a rule may be re-run after a restart. */
export interface ReplayData {
  enabled: boolean;
  within?: string;        // 'HH:MM:SS'; absent means no bound
}

/**
 * Everything the rule dialog carries. Mirrors RuleData minus `id` and
 * `profile`.
 *
 * NOT all of it is editable yet - see `rule-dialog.ts`. `target`, `data`,
 * `condition` and `replay` are carried through untouched and displayed
 * read-only, so an edit cannot silently drop them and a duplicate cannot
 * silently lose them. Plan 2 builds the editors.
 */
export interface RuleFormState {
  day: string;
  time: string;
  action: string;
  target: Record<string, unknown>;
  data: Record<string, unknown>;
  condition: Record<string, unknown>[];
  replay: ReplayData;
  name: string | null;
  icon: string | null;
  color: string | null;
  enabled: boolean;
}

/** The two keys `validate_defaults` (rule_schema.py) accepts. */
export interface Defaults {
  target?: Record<string, unknown>;
  data?: Record<string, unknown>;
}

/**
 * This card's `_state_payload` (websocket_api.py) fills `warnings` from
 * `_conflict_warnings` -> `block.conflict_warnings` (block.py), which
 * emits exactly `{kind: "conflict", targets, profile, day, time,
 * rule_ids}` and NEVER a `message`. There is no `message` field on the
 * warnings this card ever receives.
 *
 * `targets` is a LIST, not a single string. v1's key was `device`, one
 * entity id; a conflict is now the INTERSECTION of two rules' resolved
 * targets, which an area or label can expand to several entities, so one
 * string could no longer represent it.
 *
 * `no_profile` and `no_block` do carry `message`, but they come from
 * `preview_payload` (block.py), a different websocket command this card
 * does not call. `message` is kept here, optional, only so a payload
 * from that other command still typechecks if it is ever plumbed
 * through - do not rely on it being present.
 */
export interface WarningData {
  kind: string;                 // 'conflict' from this card; 'no_profile' | 'no_block' from preview_payload only
  targets?: string[];           // conflict: the entity ids two rules both resolve to
  profile?: number;             // conflict: the block length the clash was found in
  day?: string;                 // conflict: 'erev' | '1' | '2' | '3'
  time?: string;                // conflict: 'HH:MM:SS'
  rule_ids?: string[];          // conflict: the rules that disagree
  message?: string;             // preview_payload only - never present on a conflict from this card
}

export interface BlockData {
  length: number;
  candle_lighting: string;      // ISO 8601
  havdalah: string;             // ISO 8601
  dates: Record<string, string>; // 'erev' | '1'.. -> 'YYYY-MM-DD'
}

export interface CardState {
  defaults: Defaults;
  rules: RuleData[];
  enabled: boolean;
  dry_run: boolean;
  warnings: WarningData[];
  block: BlockData | null;
  master_entity_id: string | null;
}

export interface DayGroup {
  day: string;                  // 'erev' | '1'..
  date: string | null;          // 'YYYY-MM-DD'
  rules: RuleData[];
  marker: { kind: 'candle_lighting' | 'havdalah'; at: string } | null;
}

/** The shape Home Assistant's `hass.states` entries have, as much of it as we read. */
export interface HassEntity {
  state: string;
  attributes: Record<string, unknown>;
}
