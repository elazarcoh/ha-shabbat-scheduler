"""Constants for the Shabbat Scheduler integration."""

DOMAIN = "shabbat_scheduler"

STORAGE_KEY = "shabbat_scheduler.rules"
STORAGE_VERSION = 2

EVENT_RULE_APPLIED = "shabbat_scheduler_rule_applied"
EVENT_RULE_COMPLETED = "shabbat_scheduler_rule_completed"
SIGNAL_RULES_CHANGED = "shabbat_scheduler_rules_changed"

RETRY_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 30

# A block spans at most three calendar days - a two-day Chag adjacent to
# Shabbat. This is the one place that bound is spelled out; everywhere
# else (rule_schema.py, websocket_api.py, __init__.py) imports it. It used
# to be six independently-typed literal "1..3"s -
# carried forward from Plan 2's final review as the kind of duplication
# that is fine right up until someone changes one copy and not the rest.
MIN_PROFILE = 1
MAX_PROFILE = 3

# The one wording for "this rule names an entity that does not exist",
# shared by the engine (which puts it in a failed result's `error`) and the
# logbook (which appends it to a row, and uses its presence to avoid saying
# it twice). Two independently-spelled copies would drift apart, and the
# logbook's de-duplication is a string match on exactly this.
UNKNOWN_ENTITY_PREFIX = "no such entity: "

# The one wording for "the call was made, and reached nothing". Deliberately
# NOT phrased as a failure: the call genuinely happened and nothing is
# misspelt - the target's entities are merely all unavailable or unloaded.
# But a rule that affected nothing must not report success in silence
# either, so this is the third diagnostic, between "called" and "failed".
# Shared by the engine and the logbook for the same reason as above.
NO_LIVE_TARGETS_NOTE = "reached no entity that exists"

# Which outcome a multi-call rule reports, worst first. The climate shim
# turns one authored action into up to three calls; if `set_hvac_mode`
# succeeds and `set_temperature` does not, the rule must read as a failure.
# "The first call worked" is not what the family needs to know.
#
# Shared for the same reason the two wordings above are: the logbook row and
# the durable per-rule outcome the card renders are two renderings of ONE
# verdict, and two independently-spelled precedence orders would eventually
# disagree about the same rule - the card saying it fired while the logbook
# says it did not.
# `skipped_no_replay` sits with `skipped_stale` rather than at the end: both
# say "did not run", and every non-firing outcome must outrank every firing
# one so a rule can never fold into a row reading "fired". Neither skip is
# written by `_call`, so the two can never actually meet in one rule's
# results - the position is about the invariant, not about a real contest.
OUTCOME_PRECEDENCE = (
    "failed",
    "blocked",
    "skipped_stale",
    "skipped_no_replay",
    "would_call",
    "called",
)

# The one wording for "this rule came due after a restart and its author
# never opted it into replay". Shared by the engine (which puts it in the
# skip result's `reason` and in the durable outcome's `detail`) and the
# logbook, for the same reason as the two notes above: the card row and the
# logbook row are two renderings of ONE verdict.
#
# Replay is off BY DEFAULT and deliberately, so this is not an edge case: it
# is what happens to every ordinary rule after every ordinary restart, and
# "why didn't my rules run?" is the question it exists to answer. It used to
# be answered with a bare `continue` - no result, no event, no outcome, no
# logbook row - and the catch-up summary then reported "no rule was due for
# replay" about a restart where several were.
NO_REPLAY_NOTE = "replay is switched off for this rule"

CONF_CANDLE_SENSOR = "candle_sensor"
CONF_HAVDALAH_SENSOR = "havdalah_sensor"

# Off by default: this is a behaviour change from every install's history
# so far (the master switch has never auto-reset), and existing installs
# must not have their armed state silently start disappearing on them.
# See engine.py's auto-disarm scheduling for what "on" actually does.
CONF_AUTO_DISARM = "auto_disarm"
DEFAULT_AUTO_DISARM = False

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
