import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { t } from './strings';
import type { ReplayData } from './types';

/** Offered when replay is first switched on. One hour, in HH:MM:SS. */
const DEFAULT_WITHIN = '01:00:00';

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
 * absent `within` means "no bound" to rule_schema.py, and a plain
 * `<input type="text">` is used rather than a duration selector because
 * `ha-textfield` is NOT pre-registered on a dashboard.
 */
@customElement('shabbat-replay-editor')
export class ShabbatReplayEditor extends LitElement {
  @property({ attribute: false }) value: ReplayData = { enabled: false };
  @property({ type: Boolean }) disabled = false;
  @property() language = 'en';

  static override styles = css`
    .field { display: flex; align-items: center; gap: 12px; margin-block: 8px; }
    .field label { min-inline-size: 9em; }
    input[type='text'] {
      font: inherit;
      padding-block: 4px;
      padding-inline: 6px;
      flex: 1;
      min-inline-size: 0;
    }
    .help { color: var(--secondary-text-color, #666); font-size: 0.85em; }
  `;

  override render() {
    return html`
      <div class="wrap">
        <div class="field">
          <label for="replay-enabled">
            ${t(this.language, 'replay_after_restart')}
          </label>
          <input
            id="replay-enabled"
            class="replay-enabled"
            type="checkbox"
            .checked=${this.value.enabled}
            ?disabled=${this.disabled}
            @change=${this._onEnabled}
          />
        </div>
        ${this.value.enabled
          ? html`<div class="field">
              <label for="replay-within">
                ${t(this.language, 'replay_within_label')}
              </label>
              <input
                id="replay-within"
                class="replay-within"
                type="text"
                placeholder="HH:MM:SS"
                .value=${this.value.within ?? ''}
                ?disabled=${this.disabled}
                @change=${this._onWithin}
              />
            </div>`
          : html`<div class="help">${t(this.language, 'replay_help')}</div>`}
      </div>
    `;
  }

  private _emit(value: ReplayData) {
    this.dispatchEvent(new CustomEvent('replay-changed', { detail: { value } }));
  }

  private _onEnabled = (event: Event) => {
    const enabled = (event.target as HTMLInputElement).checked;
    // Switching off drops the window entirely: a remembered window on a
    // disabled replay is state the user cannot see, and it would come
    // back if they toggled twice.
    this._emit(
      enabled
        ? { enabled: true, within: this.value.within ?? DEFAULT_WITHIN }
        : { enabled: false },
    );
  };

  private _onWithin = (event: Event) => {
    const within = (event.target as HTMLInputElement).value.trim();
    // No validation here - rule_schema.py owns that, and a half-typed
    // "01:" must not be silently rewritten under the user's cursor.
    this._emit(within === '' ? { enabled: true } : { enabled: true, within });
  };
}
