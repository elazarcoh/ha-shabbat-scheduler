/** Mirrors the integration's own en/he translations. */

const STRINGS = {
  en: {
    erev: 'Erev',
    day: 'Day',
    candle_lighting: 'Candle lighting',
    havdalah: 'Havdalah',
    master: 'Shabbat Scheduler',
    dry_run: 'Dry run',
    no_block: 'No upcoming Shabbat could be derived from the Jewish Calendar sensors.',
    not_set_up: 'Shabbat Scheduler is not configured.',
    stale: 'Connection lost — showing the last known state.',
    no_rules: 'No rules for this block.',
    disabled_rule: 'disabled',
    runs_script: 'runs',
  },
  he: {
    erev: 'ערב',
    day: 'יום',
    candle_lighting: 'הדלקת נרות',
    havdalah: 'הבדלה',
    master: 'שעון שבת',
    dry_run: 'הרצה יבשה',
    no_block: 'לא ניתן לגזור שבת קרובה מחיישני לוח השנה העברי.',
    not_set_up: 'שעון שבת אינו מוגדר.',
    stale: 'החיבור אבד — מוצג המצב האחרון הידוע.',
    no_rules: 'אין כללים לבלוק הזה.',
    disabled_rule: 'מושבת',
    runs_script: 'מריץ',
  },
} as const;

export type StringKey = keyof (typeof STRINGS)['en'];

export function t(language: string | undefined, key: StringKey): string {
  const table = language === 'he' ? STRINGS.he : STRINGS.en;
  return table[key];
}
