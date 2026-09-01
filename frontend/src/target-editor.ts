import { LitElement, css, html, nothing } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { describeTarget } from './format';
import { t } from './strings';
import type { Hass } from './types';

/**
 * The rule's target, on Home Assistant's own target selector.
 *
 * Deliberately `<ha-selector>` with `{target: {}}` rather than
 * `<ha-target-picker>`: on a dashboard the picker is NOT pre-registered,
 * while `ha-selector` always is and dynamically imports whatever
 * sub-selector it is handed. See the spec's "Frontend availability"
 * section - this was verified in real Chromium, not assumed.
 */
@customElement('shabbat-target-editor')
export class ShabbatTargetEditor extends LitElement {
  @property({ attribute: false }) hass: Hass | null = null;
  @property({ attribute: false }) value: Record<string, unknown> = {};
  /** The shared defaults' target, used only for the note. */
  @property({ attribute: false }) inherited: Record<string, unknown> = {};
  @property({ type: Boolean }) disabled = false;
  @property() language = 'en';

  static override styles = css`
    .note {
      color: var(--secondary-text-color, #666);
      font-size: 0.85em;
      margin-block-start: 4px;
      overflow-wrap: anywhere;
    }
  `;

  override render() {
    const own = describeTarget(this.value, this.hass);
    const inheritedText = describeTarget(this.inherited, this.hass);
    const inherits = own === '' && inheritedText !== '';
    return html`
      <div class="wrap">
        <ha-selector
          .hass=${this.hass}
          .selector=${{ target: {} }}
          .value=${this.value}
          .disabled=${this.disabled}
          @value-changed=${this._onChange}
        ></ha-selector>
        ${inherits
          ? html`<div class="note inherited">
              ${t(this.language, 'inherits_target_from_defaults')}
              ${inheritedText}
            </div>`
          : own === ''
            ? html`<div class="note empty">${t(this.language, 'target_none')}</div>`
            : nothing}
      </div>
    `;
  }

  private _onChange = (event: CustomEvent) => {
    // `ha-selector` emits `undefined` when the last target is removed. The
    // rest of this card, and rule_schema.py, expect an object - so
    // normalise here rather than letting undefined reach the form state
    // and become a missing key in the websocket payload.
    const value = (event.detail?.value ?? {}) as Record<string, unknown>;
    this.dispatchEvent(
      new CustomEvent('target-changed', { detail: { value } }),
    );
  };
}
