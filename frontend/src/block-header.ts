import { LitElement, css, html, nothing } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { orderedDates } from './format';
import { t } from './strings';
import type { BlockData, Hass } from './types';

@customElement('shabbat-block-header')
export class ShabbatBlockHeader extends LitElement {
  @property({ attribute: false }) hass: Hass | null = null;
  @property({ attribute: false }) block: BlockData | null = null;
  @property({ type: Boolean }) enabled = false;
  @property({ type: Boolean }) canWrite = false;
  @property() masterEntityId: string | null = null;
  @property() language = 'en';
  @property({ type: Number }) selectedProfile = 1;

  static override styles = css`
    .header {
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
      padding-block-end: 8px;
      border-block-end: 1px solid var(--divider-color, #e0e0e0);
    }
    .label { flex: 1; min-inline-size: 0; font-weight: 600; }
    .dates { color: var(--secondary-text-color, #666); font-weight: 400; }
    button {
      font: inherit;
      padding-block: 4px;
      padding-inline: 10px;
      border-radius: 14px;
      border: 1px solid var(--divider-color, #e0e0e0);
      background: var(--card-background-color, #fff);
      color: inherit;
      cursor: pointer;
    }
    button[disabled] { opacity: 0.5; cursor: not-allowed; }
    .none { color: var(--secondary-text-color, #666); }
    .chips { display: flex; gap: 4px; }
    .chip {
      font: inherit;
      font-size: 0.85em;
      padding-block: 2px;
      padding-inline: 8px;
      border-radius: 10px;
      border: 1px solid var(--divider-color, #e0e0e0);
      background: var(--card-background-color, #fff);
      color: inherit;
      cursor: pointer;
    }
    .chip.active {
      background: var(--primary-color, #03a9f4);
      color: var(--text-primary-color, #fff);
      border-color: transparent;
    }
    .gear, .simulate-open { border: none; background: none; cursor: pointer; font-size: 1.1em; }
    .master-wrap { display: flex; align-items: center; gap: 6px; }
    .master-label { font-size: 0.9em; }
    @media (max-width: 599px) {
      .header { flex-wrap: wrap; }
      .label { flex-basis: 100%; }
      .chips, .gear, .master, button {
        min-block-size: 44px;
      }
      .chip { min-block-size: 44px; display: inline-flex; align-items: center; }
    }
  `;

  private _dates(): string {
    if (this.block === null) return '';
    return orderedDates(this.block).join(' → ');
  }

  // No optimistic update anywhere here: the control reports intent and
  // keeps rendering the pushed state until the server confirms.
  private _onMasterChanged = (event: CustomEvent) => {
    this.dispatchEvent(
      new CustomEvent('shabbat-master-toggle', {
        detail: { enabled: Boolean(event.detail?.value) },
      }),
    );
  };

  override render() {
    return html`
      <div class="header">
        <div class="label">
          ${this.block === null
            ? html`<span class="none">${t(this.language, 'no_block')}</span>`
            : html`
                <span>${t(this.language, 'day')} ×${this.block.length}</span>
                <span class="dates">${this._dates()}</span>
              `}
        </div>
        <div class="chips">
          ${[1, 2, 3].map(
            (profile) => html`
              <button
                class="chip ${this.selectedProfile === profile ? 'active' : ''}"
                @click=${() =>
                  this.dispatchEvent(
                    new CustomEvent('profile-selected', { detail: { profile } }),
                  )}
              >
                ${profile}d
              </button>
            `,
          )}
        </div>
        ${this.canWrite
          ? html`<button
              class="gear"
              @click=${() => this.dispatchEvent(new CustomEvent('defaults-open'))}
            >
              ⚙
            </button>`
          : nothing}
        ${this.canWrite
          ? html`<button
              class="simulate-open"
              aria-label=${t(this.language, 'simulate_title')}
              @click=${() =>
                this.dispatchEvent(
                  new CustomEvent('simulate-open', { bubbles: true, composed: true }),
                )}
            >
              ▶
            </button>`
          : nothing}
        <div class="master-wrap">
          <span class="master-label">${t(this.language, 'master')}</span>
          <ha-selector
            class="master"
            .hass=${this.hass}
            .selector=${{ boolean: {} }}
            .value=${this.enabled}
            .disabled=${!this.canWrite || this.masterEntityId === null}
            @value-changed=${this._onMasterChanged}
          ></ha-selector>
        </div>
      </div>
    `;
  }
}
