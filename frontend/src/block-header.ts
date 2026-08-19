import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { orderedDates } from './format';
import { t } from './strings';
import type { BlockData } from './types';

@customElement('shabbat-block-header')
export class ShabbatBlockHeader extends LitElement {
  @property({ attribute: false }) block: BlockData | null = null;
  @property({ type: Boolean }) enabled = false;
  @property({ type: Boolean }) dryRun = false;
  @property({ type: Boolean }) canWrite = false;
  @property() masterEntityId: string | null = null;
  @property() language = 'en';

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
    button.active {
      background: var(--primary-color, #03a9f4);
      color: var(--text-primary-color, #fff);
      border-color: transparent;
    }
    .none { color: var(--secondary-text-color, #666); }
  `;

  private _dates(): string {
    if (this.block === null) return '';
    return orderedDates(this.block).join(' → ');
  }

  // No optimistic update anywhere here: the control reports intent and
  // keeps rendering the pushed state until the server confirms.
  private _toggleMaster() {
    this.dispatchEvent(
      new CustomEvent('shabbat-master-toggle', {
        detail: { enabled: !this.enabled },
      }),
    );
  }

  private _toggleDryRun() {
    this.dispatchEvent(
      new CustomEvent('shabbat-dry-run-toggle', {
        detail: { dryRun: !this.dryRun },
      }),
    );
  }

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
        <button
          class="master ${this.enabled ? 'active' : ''}"
          ?disabled=${!this.canWrite || this.masterEntityId === null}
          @click=${this._toggleMaster}
        >
          ${t(this.language, 'master')}
        </button>
        <button
          class="dry-run ${this.dryRun ? 'active' : ''}"
          ?disabled=${!this.canWrite}
          @click=${this._toggleDryRun}
        >
          ${t(this.language, 'dry_run')}
        </button>
      </div>
    `;
  }
}
