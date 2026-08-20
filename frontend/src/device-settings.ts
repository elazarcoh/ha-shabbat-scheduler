import { LitElement, css, html, nothing } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { deviceOptions, selectableDevices } from './format';
import { t } from './strings';
import type { StringKey } from './strings';
import type { DeviceOptions, HassEntity } from './types';

/** Settings keys this card has its own words for. Anything else reads raw. */
const LABELLED: string[] = ['temperature', 'hvac_mode', 'fan_mode'];

@customElement('shabbat-device-settings')
export class ShabbatDeviceSettings extends LitElement {
  @property({ attribute: false }) states: Record<string, HassEntity | undefined> = {};
  /** The rule's actual saved selection. Always shown in the picker as-is. */
  @property({ attribute: false }) devices: string[] = [];
  /**
   * The devices this rule will actually run against once inheritance is
   * applied - `devices` itself when the rule has its own, otherwise the
   * caller's merged-in defaults. Used only to compute what settings to
   * offer, never to decide what the picker shows: an empty `devices`
   * must still render as empty, or the picker would misrepresent what a
   * save sends. Defaults to `devices` so callers with no inheritance
   * concept (the defaults dialog itself) need not think about it.
   */
  @property({ attribute: false }) effectiveDevices: string[] | null = null;
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
    return deviceOptions(this.states, this.effectiveDevices ?? this.devices);
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

  /**
   * What to show when nothing could be read.
   *
   * `deviceOptions` returns `climate: false` both for a device that
   * genuinely takes no settings and for one it could not read at all -
   * but those are two different statements, and only the first one means
   * "this rule sets nothing". Rendering `not_climate` for an unreadable
   * device made a rule holding `{temperature: 24, hvac_mode: 'cool'}`
   * display as a rule with no settings at all, while the engine went on
   * applying 24 / cool at 11:00 the next morning. A cloud-backed unit
   * reports `unavailable` on any upstream hiccup and `unknown` after a
   * restart before its first poll, so this is the normal case, not an
   * exotic one.
   *
   * The values cannot be *edited* here - the bounds and the accepted
   * modes are exactly what could not be read, so offering a control
   * would be inventing them - but they must stay visible, because a
   * saved setting the card does not show is a saved setting nobody knows
   * about.
   */
  private _unreadableSettings() {
    const entries = Object.entries(this.settings).filter(
      ([, value]) => value !== null && value !== undefined && value !== '',
    );
    return html`
      <div class="unknown">
        <div class="note warn">${t(this.language, 'options_unknown')}</div>
        ${entries.length
          ? html`<div class="note kept">
              <div>${t(this.language, 'saved_settings')}</div>
              ${entries.map(
                ([key, value]) => html`<div class="kept-row">
                  ${LABELLED.includes(key) ? t(this.language, key as StringKey) : key}:
                  ${String(value)}
                </div>`,
              )}
            </div>`
          : nothing}
      </div>
    `;
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
    // Three distinct answers, never conflated: the real controls; "these
    // devices could not be read, and here is what the rule already
    // holds"; or "these devices genuinely take no settings". Computed
    // here rather than as a nested ternary inside the template, so each
    // branch is one whole template result - see the note in `_select`.
    const settings = options.climate
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
      : options.unreadable.length
        ? this._unreadableSettings()
        : html`<div class="note">${t(this.language, 'not_climate')}</div>`;
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
        ${settings}
      </div>
    `;
  }
}
