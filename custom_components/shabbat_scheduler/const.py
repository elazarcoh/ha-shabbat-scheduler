"""Constants for the Shabbat Scheduler integration."""

DOMAIN = "shabbat_scheduler"

STORAGE_KEY = "shabbat_scheduler.rules"
STORAGE_VERSION = 1

EVENT_RULE_APPLIED = "shabbat_scheduler_rule_applied"

RETRY_ATTEMPTS = 3
RETRY_DELAY_SECONDS = 30

# Fan-mode names differ per manufacturer for the same intent. Ordered by
# preference: the requested value first, then acceptable substitutes.
FAN_SYNONYMS: dict[str, tuple[str, ...]] = {
    "quiet": ("quiet", "silent", "low"),
    "silent": ("silent", "quiet", "low"),
    "low": ("low", "quiet", "silent"),
}
