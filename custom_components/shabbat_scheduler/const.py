"""Constants for the Shabbat Scheduler integration."""

DOMAIN = "shabbat_scheduler"

STORAGE_KEY = "shabbat_scheduler.rules"
STORAGE_VERSION = 2

EVENT_RULE_APPLIED = "shabbat_scheduler_rule_applied"
EVENT_RULE_COMPLETED = "shabbat_scheduler_rule_completed"
SIGNAL_RULES_CHANGED = "shabbat_scheduler_rules_changed"

RETRY_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 30

CONF_CANDLE_SENSOR = "candle_sensor"
CONF_HAVDALAH_SENSOR = "havdalah_sensor"

# The Jewish Calendar integration derives these entity ids from its own
# config entry's TITLE, not from anything stable - a second instance, for a
# different location or candle-lighting offset, names its sensors after its
# own title instead. These are only the config flow's suggested defaults,
# used when an entity by that name happens to exist; the engine always
# reads whatever the config entry (or its options) actually name.
DEFAULT_CANDLE_SENSOR = "sensor.jewish_calendar_upcoming_candle_lighting"
DEFAULT_HAVDALAH_SENSOR = "sensor.jewish_calendar_upcoming_havdalah"

# Pre-Task-10 names, kept as aliases so tests and code elsewhere that still
# import the bare constant keep working unchanged. New code should read the
# configured entity ids from the config entry instead of these.
CANDLE_SENSOR = DEFAULT_CANDLE_SENSOR
HAVDALAH_SENSOR = DEFAULT_HAVDALAH_SENSOR
