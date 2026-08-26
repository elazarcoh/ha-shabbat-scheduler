# Upgrading from v1

v1 rules were `on` / `off` / `custom` against a fixed list of devices,
with three hardcoded climate settings. v2 rules are any Home Assistant
service call: an `action` (`domain.service`), a `target` (Home
Assistant's own target selector), and `data` (that service's own
payload). The upgrade is automatic - **restarting Home Assistant with
this version installed migrates every existing rule** - but the shapes
are different enough that this page exists.

## What happens automatically

Every v1 rule is converted to the equivalent v2 shape on first start.
This is described in full, with every input shape that was checked, in
[`docs/known-behaviours.md`](known-behaviours.md) - the short version:

- `on`/`off` become the matching `domain.service` call for that device's
  domain (`switch.turn_on`, `light.turn_off`, and so on). `custom`
  becomes `script.turn_on` against the named script entity - v1's
  `custom` rules ignored `devices` entirely and acted through a script,
  so that's what migrates, with any `variables` carried into `data`
  unchanged.
- A rule's `devices` becomes its `target.entity_id`.
- A rule that named no `devices` of its own, relying on the shared
  `defaults.devices` instead, still inherits from the defaults on
  migration, exactly as v1 did. This is worth calling out because it was
  the single most consequential case found while building this
  migration: naming devices only in the shared defaults and leaving
  individual rules to inherit them is the *documented normal
  configuration* in v1, not an edge case, so getting this wrong would
  have silently emptied every rule in a schedule written the way v1's
  own README recommended.
- The three v1 climate settings (`hvac_mode`, `temperature`, `fan_mode`)
  become `data` on a `climate.set_temperature` call, expanded at fire
  time by the one climate compatibility shim this integration keeps (see
  the "Rule format" section of the main [README](../README.md), which
  points on to `known-behaviours.md` for the shim itself).
- A rule that named more than one domain is **split** into one rule per
  domain, since a v2 rule is one action. Both halves keep the same
  schedule; only the id changes (suffixed, e.g. `mine` becomes
  `mine-climate` and `mine-switch`) - **neither half keeps the original
  id**, so that nothing implies one of them is "the real rule" and the
  other a copy. See "After upgrading" below for what that means for the
  switch entity you had.

## What is NOT dropped

**A rule the migration cannot convert is kept, disabled, and reported -
never silently dropped.** You will see a repair issue in Settings →
System → Repairs ("Some rules could not be migrated") naming which rule
ids need attention, with the original v1 shape preserved in the rule's
YAML export so nothing is lost while you decide what to do. This was the
single hardest constraint on the migration: a schedule that goes
silently short is worse than one that visibly asks for help.

A split rule gets its own, separate repair issue ("Some rules were split
by the upgrade") - not because anything is wrong, but because the rule
count changed under you and that is exactly the kind of surprise this
project does not let pass in silence. There is nothing to fix; it is
there so you can confirm the card looks the way you expect and then
dismiss it.

## What changed in behaviour, not just shape

- **Replay after a restart ends up off for nearly every migrated rule.**
  The migration copies v1's `replay_on_restart` field onto the new
  `replay.enabled` field verbatim - but that field meant something
  narrower in v1: it only ever gated `custom` (script) rules. A v1
  `on`/`off` rule had no such switch at all - it got unconditional
  catch-up on every restart, whether it wanted it or not - so almost
  every migrated `on`/`off` rule now carries `replay.enabled: false` and
  loses that catch-up. (A `custom` rule that had `replay_on_restart: true`
  in v1 keeps replay on after migration.) The safer default was chosen
  deliberately for what v2 can no longer do safely: unlike v1, a v2 rule
  is an opaque service call with no state to compare against, so replaying
  it *re-fires* rather than reconciles - see `docs/known-behaviours.md`'s
  entry on this for the full reasoning.
- **Conflicts are detected differently, and more broadly.** v1 could only
  flag two enabled, non-`custom` rules that named the very same device at
  the same profile/day/time with opposite top-level actions (one `on`,
  one `off`) - it never looked at whether two climate rules actually
  disagreed on temperature, and it never considered `custom` rules at
  all. v2 detects any two enabled rules, in the same profile and day, at
  the same time, whose *resolved* targets overlap - any domain, any
  action, including two rules that would produce the exact same effect,
  and including an area or label that expands to overlap another rule's
  entity. Broader, and no longer tied to on/off.
- **The card can author anything now**, not just the four fields v1's
  form understood. If you used YAML export/import to work around v1's
  form limitations, you likely do not need to any more - the card's rule
  dialog now has real editors for action, target, condition and replay.

## After upgrading

1. Restart Home Assistant.
2. Check Settings → System → Repairs for any migration issues - one for
   rules that could not be converted, another (harmless, informational)
   for rules that had to be split.
3. Open the card and confirm your schedule still reads as you expect.
   The migration preserves rule ids for every rule except a split one:
   an ordinary migrated rule (and an unmigrated, disabled stub) keeps its
   original id and so keeps its switch entity, history and any dashboard
   customisation you had. A rule that had to be split gets two brand-new
   ids and therefore two brand-new switch entities - the original entity
   is gone, and neither new one inherits its history.
4. If you relied on v1's automatic catch-up after a restart, review which
   rules you now want to opt into replay: open the rule for editing and
   turn on "Replay after a restart" for the ones where re-firing is
   genuinely safe - it's shown directly in the rule dialog, no need to
   expand "Advanced" first, and it's off by default post-migration.

For the full v2 rule format, the card, and everything else this
integration does, see the main [README](../README.md#upgrading) - or
just [start from the top](../README.md).
