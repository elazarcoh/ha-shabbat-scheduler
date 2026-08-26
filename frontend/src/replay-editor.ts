import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { t } from './strings';
import type { Hass, ReplayData } from './types';

/** Offered when replay is first switched on. One hour, in HH:MM:SS. */
const DEFAULT_WITHIN = '01:00:00';

/**
 * HA's duration selector value shape. VERIFIED against a real running
 * dev container (HA 2026.8.2, see dev/README.md) by injecting a bare
 * `<ha-selector .selector=${{duration: {}}}>` into a live dashboard page
 * and inspecting both its rendered `input`s and its `value-changed`
 * event: it is exactly `{hours, minutes, seconds}`, all numbers, all
 * three keys always present on an emitted event (partial objects are
 * accepted on the way in - a missing key renders as its input showing
 * zero - but the selector always emits all three back). Hours are NOT
 * clamped or zero-padded when rendered (confirmed with `{hours: 36}`,
 * which rendered as literal "36", not wrapped to "12" or padded to
 * "036"); minutes and seconds ARE zero-padded to two digits for display,
 * which is a rendering detail only and does not affect the object shape
 * read back on `value-changed`.
 *
 * ALSO VERIFIED, against the same running container: the widget has no
 * clear affordance (no X button, nothing in `ha-duration-input` beyond
 * the three number fields), and blanking all three fields by hand and
 * blurring does NOT emit `undefined` or `null` - it converges to a
 * `value-changed` of `{hours: 0, minutes: 0, seconds: 0}`, same as if
 * the user had typed zeros directly. There is no user-reachable path
 * through this widget that produces `undefined`. See `_onWithin` below
 * for what that means for the "no bound" branch.
 */
export interface DurationValue {
  hours?: number;
  minutes?: number;
  seconds?: number;
}

/**
 * {hours, minutes, seconds} -> 'HH:MM:SS', the shape `rule_schema.py`'s
 * `_duration` (and so every API client) accepts. Missing fields are 0;
 * hours are zero-padded to at least two digits but never clamped - a
 * duration selector allows values of 24 hours or more and `_duration`'s
 * `timedelta(hours=...)` does not care either.
 */
export function durationObjectToString(value: DurationValue | undefined): string {
  const hours = value?.hours ?? 0;
  const minutes = value?.minutes ?? 0;
  const seconds = value?.seconds ?? 0;
  return [hours, minutes, seconds].map((n) => String(n).padStart(2, '0')).join(':');
}

/**
 * 'HH:MM:SS' -> {hours, minutes, seconds}, the shape `ha-selector`'s
 * duration selector expects. `undefined` input (no window set) becomes
 * `undefined`, not a zeroed object, so the selector renders as genuinely
 * empty rather than "00:00:00" - this only ever happens on the way IN
 * (an existing rule with no `within` at all), since the widget itself
 * can never produce `undefined` on the way out; see `DurationValue`'s
 * comment. A malformed string - not three colon-separated parts, a
 * negative number, or a non-integer - also becomes `undefined` rather
 * than guessed at, mirroring `rule_schema.py`'s own `_duration`, which
 * requires each part to be `str.isdecimal()`: `rule_schema.py` is the
 * only owner of what counts as a valid duration.
 */
export function durationStringToObject(value: string | undefined): DurationValue | undefined {
  if (value === undefined) return undefined;
  const parts = value.split(':');
  if (parts.length !== 3) return undefined;
  if (!parts.every((p) => /^\d+$/.test(p))) return undefined;
  const [hours, minutes, seconds] = parts.map((p) => Number(p));
  return { hours, minutes, seconds };
}

/**
 * Whether, and how late, a rule may be re-run after a restart.
 *
 * Replay is OFF by default, and that is a deliberate product decision
 * rather than a conservative default: this integration's defining
 * property is fire-once-never-re-assert, and the owner chose the
 * strictest reading - after a restart, nothing unexpected ever fires.
 * See docs/known-behaviours.md.
 *
 * Note `_onWithin` drops `within` rather than setting it to null if it
 * ever receives an `undefined` value - an absent `within` means "no
 * bound" to rule_schema.py. In practice the real duration widget never
 * sends `undefined` (see `DurationValue`'s comment): a user cannot reach
 * "no bound" once replay is enabled, because there is no clear
 * affordance and blanking every field converges to an explicit
 * `00:00:00` (replay only if the restart was instant - in effect,
 * never), not to "no bound". That branch exists for defensive symmetry
 * with `durationStringToObject`'s `undefined` handling and for any
 * other caller of `replay-changed` that constructs a `value-changed`
 * event directly (this file's own unit tests do), not because a user
 * can trigger it through this UI today.
 *
 * `within` is edited through `<ha-selector>` with a `{duration: {}}`
 * selector, per this project's own rule (see target-editor.ts): a
 * specific picker element's dashboard availability varies picker by
 * picker, `ha-selector` itself is always registered. What IS specific to
 * `duration`: HA's duration selector value is an
 * `{hours, minutes, seconds}` object, not the 'HH:MM:SS' string
 * `rule_schema.py` (and so every other API client) expects -
 * `durationObjectToString`/`durationStringToObject` above convert
 * between the two on every read and write.
 */
@customElement('shabbat-replay-editor')
export class ShabbatReplayEditor extends LitElement {
  @property({ attribute: false }) hass: Hass | null = null;
  @property({ attribute: false }) value: ReplayData = { enabled: false };
  @property({ type: Boolean }) disabled = false;
  @property() language = 'en';

  static override styles = css`
    .field { display: flex; align-items: center; gap: 12px; margin-block: 8px; }
    .field label { min-inline-size: 9em; }
    .help { color: var(--secondary-text-color, #666); font-size: 0.85em; }
  `;

  override render() {
    return html`
      <div class="wrap">
        <div class="field">
          <label for="replay-enabled">
            ${t(this.language, 'replay_after_restart')}
          </label>
          <ha-selector
            id="replay-enabled"
            class="replay-enabled"
            .hass=${this.hass}
            .selector=${{ boolean: {} }}
            .value=${this.value.enabled}
            .disabled=${this.disabled}
            @value-changed=${this._onEnabled}
          ></ha-selector>
        </div>
        ${this.value.enabled
          ? html`<div class="field">
              <label for="replay-within">
                ${t(this.language, 'replay_within_label')}
              </label>
              <ha-selector
                id="replay-within"
                class="replay-within"
                .hass=${this.hass}
                .selector=${{ duration: {} }}
                .value=${durationStringToObject(this.value.within)}
                .disabled=${this.disabled}
                @value-changed=${this._onWithin}
              ></ha-selector>
            </div>`
          : html`<div class="help">${t(this.language, 'replay_help')}</div>`}
      </div>
    `;
  }

  private _emit(value: ReplayData) {
    this.dispatchEvent(new CustomEvent('replay-changed', { detail: { value } }));
  }

  private _onEnabled = (event: CustomEvent) => {
    const enabled = Boolean(event.detail?.value);
    // Switching off drops the window entirely: a remembered window on a
    // disabled replay is state the user cannot see, and it would come
    // back if they toggled twice.
    this._emit(
      enabled
        ? { enabled: true, within: this.value.within ?? DEFAULT_WITHIN }
        : { enabled: false },
    );
  };

  private _onWithin = (event: CustomEvent) => {
    const raw = event.detail?.value as DurationValue | undefined;
    // No validation here - rule_schema.py owns that, same as the plain
    // <input> this replaced. `raw === undefined` is defensive, not a
    // real-widget path - see the class doc comment above.
    this._emit(
      raw === undefined
        ? { enabled: true }
        : { enabled: true, within: durationObjectToString(raw) },
    );
  };
}
