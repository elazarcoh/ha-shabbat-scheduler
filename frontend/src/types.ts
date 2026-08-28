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
   * What happened the last time this rule came due. `null` for a rule that
   * never has.
   *
   * Always present on every rule in `_state_payload` - the server attaches
   * it per rule rather than storing it on the rule, so it is required here
   * and nullable, not optional. Also server-owned: `rule_schema.py` drops
   * it on the way back in, so echoing it is safe and forging it is not.
   *
   * This exists because `engine.last_run` is ONE value for the whole
   * integration, overwritten by the next rule to act. A rule that does not
   * fire must say why, in the logbook AND on the card; without a per-rule
   * record the card could only ever say what happened most recently, to
   * some other rule.
   */
  last_outcome: LastOutcome | null;
}

/**
 * One rule's own verdict, as `engine.build_outcome` writes it.
 *
 * TWO AXES, deliberately not collapsed into one. `outcome` says whether
 * the call happened and, if not, why not. The two optional diagnostics say
 * whether it reached anything - a different question, whose answer can be
 * "no" while the call genuinely was made. `called` plus `no_live_targets`
 * is a real and common combination (an existing group whose members are
 * all unavailable), and rendering it as a failure would blame a
 * misspelling that is not there.
 *
 * The diagnostics are ABSENT rather than `[]`/`false` when they do not
 * apply, so a healthy rule cannot render a warning-shaped nothing.
 */
export interface LastOutcome {
  /**
   * `called` | `would_call` | `failed` | `blocked` | `skipped_stale` |
   * `skipped_no_replay`.
   *
   * Typed as `string`, not a union, on purpose: this arrives over a socket
   * from a server that may be a version ahead, and the card must render
   * *something* for a value it does not know rather than a blank line. See
   * `formatOutcome`'s fallback.
   */
  outcome: string;
  at: string;                    // ISO 8601, UTC
  /** The reason, in the same words the logbook row uses. */
  detail: string | null;
  /** Entity ids the rule names that do not exist. */
  unknown_targets?: string[];
  /** The call was made and resolved to no entity that exists. */
  no_live_targets?: boolean;
  /**
   * Reasons a targeted entity's OWN advertised options (`fan_modes`,
   * `hvac_modes`, and the like) would refuse a value in `data`, right now.
   * Simulate-only (see `engine.py`'s `_call`): a real failing call gets the
   * same story from Home Assistant itself, in `detail`, so this never
   * appears alongside a `failed` outcome - only alongside `would_call`.
   */
  invalid_data?: string[];
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

/**
 * As much of Home Assistant's `hass` object as this card reads, plus the
 * fields the HA elements we embed require to be present. It is passed
 * straight through to `<ha-service-control>` and `<ha-selector>`, which
 * read far more of it than this - so this is a *lower bound*, not a
 * description, and it must never be used to construct a hass object.
 */
export interface Hass {
  states: Record<string, HassEntity>;
  locale?: { language?: string };
  user?: { is_admin?: boolean };
  connection: unknown;
  callWS: (message: Record<string, unknown>) => Promise<unknown>;
  callService: (
    domain: string, service: string, data?: Record<string, unknown>,
  ) => Promise<unknown>;
  /**
   * The user's own advanced-mode preference. Passed to
   * `<ha-service-control>` so this card shows advanced service fields
   * exactly when Home Assistant itself would - hard-coding it on would
   * override a preference the user set deliberately.
   */
  userData?: { showAdvanced?: boolean };
  [key: string]: unknown;
}
