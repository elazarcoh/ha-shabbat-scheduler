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
 */
interface DurationValue {
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
 * empty rather than "00:00:00". A malformed string also becomes
 * `undefined` rather than guessed at - `rule_schema.py` is the only owner
 * of what counts as a valid duration.
 */
export function durationStringToObject(value: string | undefined): DurationValue | undefined {
  if (value === undefined) return undefined;
  const parts = value.split(':');
  if (parts.length !== 3) return undefined;
  const [hours, minutes, seconds] = parts.map((p) => Number(p));
  if ([hours, minutes, seconds].some((n) => Number.isNaN(n))) return undefined;
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
 * Note `within` is dropped rather than set to null when cleared. An
 * absent `within` means "no bound" to rule_schema.py.
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
    // <input> this replaced.
    this._emit(
      raw === undefined
        ? { enabled: true }
        : { enabled: true, within: durationObjectToString(raw) },
    );
  };
}
