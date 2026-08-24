"""Constants for the Shabbat Scheduler integration."""

DOMAIN = "shabbat_scheduler"

STORAGE_KEY = "shabbat_scheduler.rules"
STORAGE_VERSION = 2

EVENT_RULE_APPLIED = "shabbat_scheduler_rule_applied"
EVENT_RULE_COMPLETED = "shabbat_scheduler_rule_completed"
SIGNAL_RULES_CHANGED = "shabbat_scheduler_rules_changed"

RETRY_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 30

CANDLE_SENSOR = "sensor.jewish_calendar_upcoming_candle_lighting"
HAVDALAH_SENSOR = "sensor.jewish_calendar_upcoming_havdalah"
