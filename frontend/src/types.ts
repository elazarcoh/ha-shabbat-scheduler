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

export interface WarningData {
  kind: string;                 // 'conflict' | 'no_profile' | 'no_block'
  message: string;
  rule_ids?: string[];
  profile?: number;
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
