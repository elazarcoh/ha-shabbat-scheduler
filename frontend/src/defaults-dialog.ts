import { LitElement, css, html, nothing } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import './device-settings';
import { t } from './strings';
import type { Defaults, HassEntity } from './types';

@customElement('shabbat-defaults-dialog')
export class ShabbatDefaultsDialog extends LitElement {
  @property({ attribute: false }) defaults: Defaults = {};
  @property({ attribute: false }) states: Record<string, HassEntity | undefined> = {};
  @property({ type: Boolean }) canWrite = false;
  @property({ type: Boolean }) busy = false;
  @property() error: string | null = null;
  @property() language = 'en';

  @state() private _draft: Defaults | null = null;

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

  private get _current(): Defaults {
    return this._draft ?? this.defaults;
  }

  override render() {
    const current = this._current;
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

          <shabbat-device-settings
            .states=${this.states}
            .devices=${current.devices ?? []}
            .settings=${current.settings ?? {}}
            .disabled=${!this.canWrite}
            .language=${this.language}
            @settings-changed=${(event: Event) => {
              this._draft = {
                ...current,
                settings: (event as CustomEvent).detail.settings,
              };
            }}
            @devices-changed=${(event: Event) => {
              this._draft = {
                ...current,
                devices: (event as CustomEvent).detail.devices,
              };
            }}
          ></shabbat-device-settings>

          <div class="actions">
            <button @click=${() => this.dispatchEvent(new CustomEvent('dialog-close'))}>
              ${t(this.language, 'cancel')}
            </button>
            ${this.canWrite
              ? html`<button
                  class="save"
                  ?disabled=${this.busy}
                  @click=${() =>
                    this.dispatchEvent(
                      new CustomEvent('defaults-save', {
                        // Exactly the two keys validate_defaults accepts.
                        // Anything else is rejected outright, not ignored.
                        detail: {
                          defaults: {
                            devices: current.devices ?? [],
                            settings: current.settings ?? {},
                          },
                        },
                      }),
                    )}
                >
                  ${t(this.language, 'save')}
                </button>`
              : nothing}
          </div>
        </div>
      </div>
    `;
  }
}
