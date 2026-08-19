# Shabbat Scheduler Card — Authoring (Plan 2b-ii) Design

**Follows:** Plan 2b-i — the card read view (`docs/superpowers/specs/2026-08-19-shabbat-scheduler-card-read-view-design.md`)
**Completes:** the Lovelace client for the websocket API built in Plan 2a

## Why this exists

Plan 2a built a write API. Plan 2b-i built a card that only reads. Today a rule
can be created or changed only through `import_yaml` or by hand-editing
`.storage` — so the API's `rules/create`, `rules/update`, `rules/delete` and
`defaults/update` have no client at all, and the card cannot do the thing the
whole project was started for: let a schedule be built and adjusted without
writing YAML.

This plan adds authoring: an edit dialog reached by tapping a rule, a per-day
add button, duplication, deletion, a shared-defaults editor, and a block-length
selector for authoring the 2- and 3-day Chag profiles before a Chag arrives.

## Scope

**In:** the rule edit/create dialog including advanced fields; device-aware
settings controls; duplicate; delete; the shared-defaults editor; the
1/2/3-day profile selector and its preview mode; the pure additions that
support them; tests at three levels.

**Out:** any new backend command — this plan adds none. Also out: undo,
reordering by drag, bulk edits, and editing the master switch's behaviour.

**Out (later):** deploying to the production instance and retiring the seven
plain automations. That remains its own decision after this is proven.

## Global constraints

- **No new write API.** The card uses `rules/create`, `rules/update`,
  `rules/delete` and `defaults/update` exactly as Plan 2a shipped them.
- **No optimistic local state.** A dialog closes on the server's confirmation,
  and the following push is what redraws the card. This is the same discipline
  Plan 2b-i established and it is not negotiable: a card that shows a change
  the server did not accept is lying on the one day nobody can check.
- **No client-side revalidation.** `rule_schema.py` owns validation. The dialog
  sends the command and renders whatever the server says. A second
  implementation in TypeScript is how the two drift apart.
- **Conflicts are warned, never blocking.** Saving a conflicting rule succeeds.
- The Python purity boundary is unchanged, and `format.ts` remains the
  frontend's DOM-free core.
- RTL: logical CSS properties only.
- Home Assistant 2026.8.2; no new npm dependencies.
- Development and testing happen against the throwaway Docker instance.
  Production (192.168.1.14) is not touched by this plan.

## Architecture

Three new Lit elements, one of them shared:

| File | Responsibility |
|---|---|
| `frontend/src/rule-dialog.ts` | `<shabbat-rule-dialog>` — create/edit form, save, delete, duplicate |
| `frontend/src/device-settings.ts` | `<shabbat-device-settings>` — the device-aware controls |
| `frontend/src/defaults-dialog.ts` | `<shabbat-defaults-dialog>` — the shared defaults |

`<shabbat-device-settings>` is deliberately shared between the rule form and
the defaults editor: both edit the same `devices` + `settings` shape, and the
engine merges one into the other. Two implementations would let the form that
authors a default disagree with the form that overrides it.

`<shabbat-block-header>` gains the profile chips and the defaults gear.
`<shabbat-day-group>` gains the per-day add button.

### Additions to the pure core (`format.ts`)

- `deviceOptions(states, entityIds)` — given the entities' attribute maps,
  returns the offerable `hvacModes`, `fanModes`, and temperature range. Pure,
  and where the intersection rule below lives.
- `rulePayload(formState)` — form state into the dict `rules/create` and
  `rules/update` accept, omitting untouched fields so an update is a genuine
  partial.
- `buildGroups` gains a profile argument and a dateless preview mode.

## The device-aware form

Picking a device makes the form read that entity from `hass.states` and offer
exactly what it declares — `fan_modes`, `hvac_modes`, `min_temp`, `max_temp`,
`target_temp_step`. This is the point of the whole feature: the three units in
this house genuinely disagree, and the mismatch has already caused a real bug.

Their actual attributes today:

| Entity | `fan_modes` | `hvac_modes` | temp |
|---|---|---|---|
| `climate.air_conditioner_2` (salon) | auto, **quiet**, low, medlow, medium, medhigh, high, strong | off, **heat_cool**, cool, fan_only, dry, heat | 16–31, step 0.5 |
| `climate.aux_cloud_e87072dbfee2_ac` (kids) | auto, low, medium, high, turbo, **silent** | off, **auto**, cool, heat, dry, fan_only | 16–32, step 0.5 |
| `climate.aux_cloud_348e895c4a59_ac` (master) | auto, low, medium, high, turbo, **silent** | off, **auto**, cool, heat, dry, fan_only | 16–32, step 0.5 |

The salon offers `quiet` and not `silent`; both AUX units offer `silent` and
not `quiet`. Only `auto`, `low`, `medium` and `high` are common to all three.

Four cases the form must handle, each visibly rather than silently:

1. **One device.** Offer its own options.
2. **Several devices.** Offer the **intersection**, and say that is what is
   being shown. Selecting all three above leaves four fan modes, and a user who
   wanted `quiet` learns immediately that it is not available for every device
   they selected — rather than at 11:00 on Shabbat.
3. **Entity unavailable or unknown.** Its capabilities cannot be read. Keep the
   saved value, show it, and say the device could not be read — never silently
   drop a setting or present an empty list as though the device offers nothing.
4. **Not a climate entity** (an `input_boolean`, a `switch`). No settings
   apply; offer action only.

A setting already saved on the rule but absent from the current options is kept
and flagged, not discarded. Discarding it would rewrite the user's schedule as
a side effect of opening a dialog.

## The profile selector and preview mode

The header carries `1d / 2d / 3d` chips. The selected length decides which
profile is displayed and authored.

- **Selected length equals the coming block's length:** today's view. Real
  dates on the day headings, candle-lighting and havdalah markers in place.
- **Any other length:** preview. Day headings become `Erev`, `Day 1`, `Day 2`
  with **no dates**, the zmanim markers are **not** drawn, and a banner states
  this is a preview, not the coming block. Authoring stays fully enabled — that
  is how a 3-day Chag gets set up in advance.

Dropping the dates rather than computing plausible ones is deliberate. A
hypothetical Chag's dates are a guess that looks exactly like a real date, and
this project's founding complaint was not being able to tell what was real.

Two consequences worth stating:

- **No `preview` websocket call is needed.** Every profile's rules are already
  in the state payload, and a preview block's day count is simply the profile
  number. This resolves the Plan 2a spec's deferred question in the negative.
- **When no block can be derived** (`block: null`), the selector is still a way
  in. Plan 2b-i rendered nothing usable in that state; now the user can select a
  length and author against it.

Conflicts already arrive unfiltered by profile, so a conflict in the profile
being viewed attaches to its rows naturally, and one belonging to another
profile continues to surface in the banner.

## Saving

The dialog sends `rules/create` or `rules/update` and waits. On success it
closes, and the server's push redraws the card. On rejection it **stays open**
with the user's input intact and shows the server's message.

An update sends only the fields that changed. `changes_from_api` already
accepts a partial, and sending an unchanged full rule would make every save
look like an edit of every field in the logbook.

Duplicate is composed client-side: read the rule, open the create dialog
pre-filled, let the user change the time or day, and `rules/create` it. The
server generates the new id. No `rules/duplicate` command is added.

## Delete

Delete lives inside the edit dialog and acts immediately. **There is no
confirmation step and no undo** — the rule and its switch entity are gone.

This is an accepted trade-off, chosen deliberately: reaching delete already
takes two intentional actions (open the row, then tap delete), and a
confirmation modal on a touch tablet is mostly muscle memory. It will be
recorded in `docs/known-behaviours.md` so it is a known property rather than a
surprise.

## Permissions and errors

Plan 2a made reads open and every mutator `require_admin`, and Plan 2b-i
disabled the master and dry-run controls for non-admins. The dialog follows
the same rule: a non-admin can open a rule and read every setting, with the
controls disabled and no save, delete or duplicate. Add buttons and the gear
are not offered at all.

Every failure is visible. A rejected command shows its message; it is never
swallowed. This is the same commitment that made a silently failing
`callService` a defect in Plan 2b-i.

## Testing

**Vitest, pure.** `deviceOptions` against the three real attribute shapes above
— including the intersection of all three, an unavailable entity, and a
non-climate entity. `rulePayload` — that an unchanged field is omitted and a
cleared field is sent. `buildGroups` in preview mode — right number of days,
no dates, no markers.

**Vitest + happy-dom, component.** The dialog: the intersection notice appears
when devices disagree; a saved setting absent from the current options is kept
and flagged; a server rejection leaves the dialog open with input intact; the
non-admin state disables everything; delete calls `rules/delete` and closes.

**Python + Playwright, end-to-end.** In the throwaway instance: open a rule,
change its time, save, and watch the timeline redraw at the new time — the
whole loop the card exists for, in a real browser. Plus one create through the
per-day add button.

Every test for a new behaviour must be observed failing before the behaviour
exists.

## Rollout

Unchanged. The card is added alongside the existing dashboard content, the
master switch stays off, and the seven production automations remain in charge
until the whole thing is proven across a real Shabbat — which is a decision
after this plan, not part of it.

## Open questions

None. The Plan 2a deferred question about `rules/duplicate` is resolved above:
the card composes duplication from `rules/create` and no new command is added.
