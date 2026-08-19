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
    // Deliberately distinct from `stale`. The server was reachable and
    // refused the call - saying "connection lost" there is a wrong
    // diagnosis that sends someone to check the network.
    command_failed: 'That did not go through. Nothing was changed.',
    no_rules: 'No rules for this block.',
    disabled_rule: 'disabled',
    conflict_prefix: 'Conflict',
    devices: 'Devices',
    temperature: 'Temperature',
    hvac_mode: 'Mode',
    fan_mode: 'Fan',
    intersected: 'Showing only what every selected device supports.',
    unreadable: 'Could not read these devices, so their options are unknown:',
    not_climate: 'These devices take no settings — on and off only.',
    kept_setting: 'kept, but this device does not list it',
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
    command_failed: 'הפעולה לא בוצעה. שום דבר לא השתנה.',
    no_rules: 'אין כללים לבלוק הזה.',
    disabled_rule: 'מושבת',
    conflict_prefix: 'התנגשות',
    devices: 'מכשירים',
    temperature: 'טמפרטורה',
    hvac_mode: 'מצב',
    fan_mode: 'מאוורר',
    intersected: 'מוצג רק מה שכל המכשירים שנבחרו תומכים בו.',
    unreadable: 'לא ניתן לקרוא את המכשירים האלה, לכן האפשרויות שלהם אינן ידועות:',
    not_climate: 'המכשירים האלה לא מקבלים הגדרות — הפעלה וכיבוי בלבד.',
    kept_setting: 'נשמר, אך המכשיר לא מציג אותו',
  },
} as const;

export type StringKey = keyof (typeof STRINGS)['en'];

export function t(language: string | undefined, key: StringKey): string {
  const table = language === 'he' ? STRINGS.he : STRINGS.en;
  return table[key];
}
