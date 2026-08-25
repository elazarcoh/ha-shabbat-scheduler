import { LitElement, css, html, nothing } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { describeTarget } from './format';
import { t } from './strings';
import type { Defaults } from './types';

/**
 * The shared defaults, shown but not editable.
 *
 * v1's editor was a device multi-select plus a climate settings form, and
 * it wrote `{devices, settings}`. `validate_defaults` (rule_schema.py) now
 * accepts exactly `{target, data}` - a Home Assistant target selector and
 * an opaque service payload - so the old form's save was already certain
 * to be rejected on every press. A save button that cannot succeed is
 * worse than no save button, and a form that quietly rewrote the defaults
 * into a v1 shape would be worse still.
 *
 * So this shows what the defaults ACTUALLY are and says where to change
 * them. Plan 2 builds the target/data editors.
 */
@customElement('shabbat-defaults-dialog')
export class ShabbatDefaultsDialog extends LitElement {
  @property({ attribute: false }) defaults: Defaults = {};
  @property({ type: Boolean }) canWrite = false;
  @property({ type: Boolean }) busy = false;
  @property() error: string | null = null;
  @property() language = 'en';

  static override styles = css`
    .sheet {
      position: fixed;
      inset: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      background: rgba(0, 0, 0, 0.4);
      z-index: 10;
    }
    .panel {
      background: var(--card-background-color, #fff);
      color: var(--primary-text-color, #111);
      border-radius: 12px;
      padding: 16px;
      inline-size: min(28rem, 92vw);
    }
    h2 { margin-block: 0 4px; font-size: 1.1em; }
    .note { color: var(--secondary-text-color, #666); font-size: 0.85em; }
    .error { color: var(--error-color, #d64545); margin-block: 8px; font-size: 0.9em; }
    dl { margin-block: 12px; display: grid; grid-template-columns: auto 1fr; gap: 4px 12px; }
    dt { color: var(--secondary-text-color, #666); }
    dd { margin: 0; overflow-wrap: anywhere; }
    .actions {
      display: flex;
      gap: 8px;
      justify-content: flex-end;
      margin-block-start: 16px;
    }
    button {
      font: inherit;
      padding-block: 6px;
      padding-inline: 12px;
      border-radius: 6px;
      border: 1px solid var(--divider-color, #e0e0e0);
      background: var(--card-background-color, #fff);
      color: inherit;
      cursor: pointer;
    }
    button[disabled] { opacity: 0.5; cursor: not-allowed; }
  `;

  private _describeData(): string {
    const entries = Object.entries(this.defaults.data ?? {});
    if (!entries.length) return t(this.language, 'none_set');
    return entries.map(([key, value]) => `${key}: ${JSON.stringify(value)}`).join(', ');
  }

  override render() {
    const target = describeTarget(this.defaults.target ?? {});
    return html`
      <div class="sheet" @click=${(event: Event) => {
        if (event.target === event.currentTarget) {
          this.dispatchEvent(new CustomEvent('dialog-close'));
        }
      }}>
        <div class="panel">
          <h2>${t(this.language, 'defaults_title')}</h2>
          <div class="note">${t(this.language, 'defaults_help')}</div>
          ${this.error !== null
            ? html`<div class="error">${this.error}</div>`
            : nothing}

          <dl>
            <dt>${t(this.language, 'target')}</dt>
            <dd class="ro-target">${target !== '' ? target : t(this.language, 'none_set')}</dd>
            <dt>${t(this.language, 'data')}</dt>
            <dd class="ro-data">${this._describeData()}</dd>
          </dl>
          <div class="note">${t(this.language, 'read_only_fields')}</div>

          <div class="actions">
            <button @click=${() => this.dispatchEvent(new CustomEvent('dialog-close'))}>
              ${t(this.language, 'cancel')}
            </button>
          </div>
        </div>
      </div>
    `;
  }
}
