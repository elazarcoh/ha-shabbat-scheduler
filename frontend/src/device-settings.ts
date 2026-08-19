import { LitElement, css, html, nothing } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { deviceOptions, selectableDevices } from './format';
import { t } from './strings';
import type { DeviceOptions, HassEntity } from './types';

@customElement('shabbat-device-settings')
export class ShabbatDeviceSettings extends LitElement {
  @property({ attribute: false }) states: Record<string, HassEntity | undefined> = {};
  @property({ attribute: false }) devices: string[] = [];
  @property({ attribute: false }) settings: Record<string, unknown> = {};
  @property({ type: Boolean }) disabled = false;
  @property() language = 'en';

  static override styles = css`
    .field {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-block: 8px;
    }
    .field label { min-inline-size: 7em; }
    select, input {
      font: inherit;
      padding-block: 4px;
      padding-inline: 6px;
      flex: 1;
      min-inline-size: 0;
    }
    .note {
      color: var(--secondary-text-color, #666);
      font-size: 0.85em;
      margin-block: 4px;
    }
    .warn { color: var(--warning-color, #d9822b); }
  `;

  private get _options(): DeviceOptions {
    return deviceOptions(this.states, this.devices);
  }

  private _emit(settings: Record<string, unknown>) {
    // Reports intent. The parent owns the value and passes it back down,
    // so this element never disagrees with what will actually be saved.
    this.dispatchEvent(new CustomEvent('settings-changed', { detail: { settings } }));
  }

  private _set(key: string, value: unknown) {
    const next = { ...this.settings };
    if (value === '' || value === null) delete next[key];
    else next[key] = value;
    this._emit(next);
  }

  /** A saved value the current devices do not list. Kept, never dropped. */
  private _orphan(key: string, offered: string[]): string | null {
    const value = this.settings[key];
    if (typeof value !== 'string' || value === '') return null;
    return offered.includes(value) ? null : value;
  }

  private _select(key: 'hvac_mode' | 'fan_mode', offered: string[]) {
    const current = this.settings[key];
    const orphan = this._orphan(key, offered);
    // Wrapped in one root: under happy-dom 15.11.7 with lit-html 3.3.3, a
    // template result with more than one top-level node - here the field
    // and the conditional orphan note - fails to render either branch of
    // a ternary in tests. A real browser is unaffected, but this is
    // shared with the rule and defaults dialogs and must render in tests.
    return html`
      <div>
        <div class="field">
          <label for=${key}>${t(this.language, key)}</label>
          <select
            id=${key}
            class=${key === 'fan_mode' ? 'fan' : 'hvac'}
            ?disabled=${this.disabled}
            @change=${(event: Event) =>
              this._set(key, (event.target as HTMLSelectElement).value)}
          >
            <option value=""></option>
            ${orphan !== null
              ? html`<option value=${orphan} selected>${orphan}</option>`
              : nothing}
            ${offered.map(
              (option) => html`
                <option value=${option} ?selected=${current === option}>
                  ${option}
                </option>
              `,
            )}
          </select>
        </div>
        ${orphan !== null
          ? html`<div class="note warn">
              ${orphan} — ${t(this.language, 'kept_setting')}
            </div>`
          : nothing}
      </div>
    `;
  }

  override render() {
    const options = this._options;
    return html`
      <div class="settings">
        <div class="field">
          <label for="devices">${t(this.language, 'devices')}</label>
          <select
            id="devices"
            class="devices"
            multiple
            size="4"
            ?disabled=${this.disabled}
            @change=${(event: Event) => {
              const select = event.target as HTMLSelectElement;
              const devices = [...select.selectedOptions].map((o) => o.value);
              this.dispatchEvent(
                new CustomEvent('devices-changed', { detail: { devices } }),
              );
            }}
          >
            ${selectableDevices(this.states).map(
              (id) => html`
                <option value=${id} ?selected=${this.devices.includes(id)}>
                  ${id}
                </option>
              `,
            )}
          </select>
        </div>
        ${options.unreadable.length
          ? html`<div class="note warn">
              ${t(this.language, 'unreadable')} ${options.unreadable.join(', ')}
            </div>`
          : nothing}
        ${options.intersected
          ? html`<div class="note">${t(this.language, 'intersected')}</div>`
          : nothing}
        ${options.climate
          ? html`
              <div>
                <div class="field">
                  <label for="temperature">${t(this.language, 'temperature')}</label>
                  <input
                    id="temperature"
                    class="temperature"
                    type="number"
                    .value=${String(this.settings.temperature ?? '')}
                    min=${options.minTemp ?? 5}
                    max=${options.maxTemp ?? 35}
                    step=${options.tempStep ?? 0.5}
                    ?disabled=${this.disabled}
                    @change=${(event: Event) => {
                      const raw = (event.target as HTMLInputElement).value;
                      this._set('temperature', raw === '' ? null : Number(raw));
                    }}
                  />
                </div>
                ${this._select('hvac_mode', options.hvacModes)}
                ${this._select('fan_mode', options.fanModes)}
              </div>
            `
          : html`<div class="note">${t(this.language, 'not_climate')}</div>`}
      </div>
    `;
  }
}
