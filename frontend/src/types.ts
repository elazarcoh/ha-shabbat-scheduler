/** Mirrors _state_payload in websocket_api.py. Keep the two in step. */

export interface RuleData {
  id: string;
  profile: number;
  day: string;            // 'erev' | '1' | '2' | '3'
  time: string;           // 'HH:MM:SS'
  action: string;         // 'on' | 'off' | 'custom'
  devices: string[];
  settings: Record<string, unknown>;
  name: string | null;
  icon: string | null;
  enabled: boolean;
  script: string | null;
  variables: Record<string, unknown>;
  replay_on_restart: boolean;
  color: string | null;
}

export interface Defaults {
  devices?: string[];
  settings?: Record<string, unknown>;
}

/**
 * This card's `_state_payload` (websocket_api.py) fills `warnings` from
 * `_conflict_warnings` -> `block.conflict_warnings` (block.py:135-154),
 * which emits exactly `{kind: "conflict", device, profile, day, time,
 * rule_ids}` and NEVER a `message`. There is no `message` field on the
 * warnings this card ever receives.
 *
 * `no_profile` and `no_block` do carry `message`, but they come from
 * `preview_payload` (block.py), a different websocket command this card
 * does not call. `message` is kept here, optional, only so a payload
 * from that other command still typechecks if it is ever plumbed
 * through - do not rely on it being present.
 */
export interface WarningData {
  kind: string;                 // 'conflict' from this card; 'no_profile' | 'no_block' from preview_payload only
  device?: string;               // conflict: the device with two disagreeing rules
  profile?: number;              // conflict: the block length the clash was found in
  day?: string;                  // conflict: 'erev' | '1' | '2' | '3'
  time?: string;                 // conflict: 'HH:MM:SS'
  rule_ids?: string[];           // conflict: the rules that disagree
  message?: string;              // preview_payload only - never present on a conflict from this card
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
