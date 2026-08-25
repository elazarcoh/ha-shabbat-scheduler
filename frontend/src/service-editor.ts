import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import type { Hass } from './types';

/**
 * The rule's action and its data, on Home Assistant's own service control.
 *
 * This is the whole point of v2 on the frontend: the form for every
 * service comes from Home Assistant's own schema for that service, so
 * this card carries no per-domain form code and gains support for new
 * services without changing.
 *
 * `<ha-service-control>` speaks a single `{action, target, data}` value,
 * and it HAS internal target logic - but on a dashboard its target UI
 * depends on `ha-target-picker`, which is not pre-registered outside the
 * automation editor. So this card owns the target separately (see
 * `target-editor.ts`) and this element neither passes a target down nor
 * lets one back up. Dropping it on the way out is not defensive coding:
 * without it, a stray target from HA's element would silently overwrite
 * what the user chose in the target editor.
 */
@customElement('shabbat-service-editor')
export class ShabbatServiceEditor extends LitElement {
  @property({ attribute: false }) hass: Hass | null = null;
  @property() action = '';
  @property({ attribute: false }) data: Record<string, unknown> = {};
  @property({ type: Boolean }) disabled = false;

  static override styles = css`
    :host { display: block; }
  `;

  override render() {
    return html`
      <div class="wrap">
        <ha-service-control
          .hass=${this.hass}
          .value=${{ action: this.action, data: this.data }}
          .disabled=${this.disabled}
          .showAdvanced=${true}
          @value-changed=${this._onChange}
        ></ha-service-control>
      </div>
    `;
  }

  private _onChange = (event: CustomEvent) => {
    const value = (event.detail?.value ?? {}) as Record<string, unknown>;
    this.dispatchEvent(new CustomEvent('service-changed', {
      detail: {
        action: typeof value.action === 'string' ? value.action : '',
        data: (value.data ?? {}) as Record<string, unknown>,
      },
    }));
  };
}
