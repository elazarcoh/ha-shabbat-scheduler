import { LitElement, css, html, nothing } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import './device-settings';
import { ruleToForm } from './format';
import { t } from './strings';
import type { Defaults, HassEntity, RuleData, RuleFormState } from './types';

const EMPTY_FORM: RuleFormState = {
  day: 'erev', time: '', action: 'on', devices: [], settings: {},
  name: null, icon: null, color: null, enabled: true, script: null,
  variables: {}, replay_on_restart: false,
};

@customElement('shabbat-rule-dialog')
export class ShabbatRuleDialog extends LitElement {
  /** null means create. */
  @property({ attribute: false }) rule: RuleData | null = null;
  /** Pre-filled values for a create. This is what duplication uses. */
  @property({ attribute: false }) seed: RuleFormState | null = null;
  @property() day = 'erev';
  @property({ type: Number }) profile = 1;
  @property({ attribute: false }) defaults: Defaults = {};
  @property({ attribute: false }) states: Record<string, HassEntity | undefined> = {};
  @property({ type: Boolean }) canWrite = false;
  @property({ type: Boolean }) busy = false;
  @property() error: string | null = null;
  @property() language = 'en';

  @state() private _form: RuleFormState = EMPTY_FORM;
  @state() private _advanced = false;
  private _seeded: string | null = null;

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
      max-block-size: 88vh;
      overflow: auto;
    }
    h2 { margin-block: 0 12px; font-size: 1.1em; }
    .field { display: flex; align-items: center; gap: 12px; margin-block: 8px; }
    .field label { min-inline-size: 7em; }
    input, select {
      font: inherit;
      padding-block: 4px;
      padding-inline: 6px;
      flex: 1;
      min-inline-size: 0;
    }
    .actions {
      display: flex;
      gap: 8px;
      justify-content: flex-end;
      margin-block-start: 16px;
      flex-wrap: wrap;
    }
    .actions .delete { margin-inline-end: auto; color: var(--error-color, #d64545); }
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
    .error {
      color: var(--error-color, #d64545);
      margin-block: 8px;
      font-size: 0.9em;
    }
    .note { color: var(--secondary-text-color, #666); font-size: 0.85em; }
    .advanced-toggle {
      background: none;
      border: none;
      padding-inline: 0;
      color: var(--primary-color, #03a9f4);
    }
  `;

  override willUpdate() {
    // Seed the form once per opened rule. Re-seeding on every update
    // would throw away what the user has typed each time a push arrives -
    // and pushes arrive constantly, since `hass` is reassigned on every
    // state change in the whole system.
    //
    // The create key is keyed off the seed's *content*, not just whether
    // one is present: the dialog instance persists across opens, so two
    // different duplicates on the same day/profile ('new:1:1:seeded' both
    // times) would otherwise be indistinguishable and the second duplicate
    // would silently keep the first one's values. Keying on content is
    // correct by construction - if two seeds are identical, skipping the
    // reseed leaves the form showing exactly those values anyway.
    const key = this.rule
      ? `edit:${this.rule.id}`
      : `new:${this.day}:${this.profile}:${JSON.stringify(this.seed)}`;
    if (this._seeded !== key) {
      this._seeded = key;
      if (this.rule) {
        this._form = ruleToForm(this.rule);
      } else if (this.seed) {
        // A duplicate: same values, no id, so saving creates a new rule.
        this._form = { ...this.seed, day: this.day };
      } else {
        this._form = { ...EMPTY_FORM, day: this.day };
      }
      this._advanced = false;
    }
  }

  private _patch(patch: Partial<RuleFormState>) {
    this._form = { ...this._form, ...patch };
  }

  private _emit(type: string) {
    this.dispatchEvent(
      new CustomEvent(type, { detail: { form: this._form, rule: this.rule } }),
    );
  }

  private _text(
    key: 'time' | 'name' | 'icon' | 'color' | 'script',
    label: string,
  ) {
    return html`
      <div class="field">
        <label for=${key}>${label}</label>
        <input
          id=${key}
          class=${key}
          .value=${String(this._form[key] ?? '')}
          ?disabled=${!this.canWrite}
          @change=${(event: Event) => {
            const value = (event.target as HTMLInputElement).value;
            this._patch({ [key]: value === '' ? null : value } as Partial<RuleFormState>);
          }}
        />
      </div>
    `;
  }

  override render() {
    const editing = this.rule !== null;
    return html`
      <div class="sheet" @click=${(event: Event) => {
        if (event.target === event.currentTarget) {
          this.dispatchEvent(new CustomEvent('dialog-close'));
        }
      }}>
        <div class="panel">
          <h2>${t(this.language, editing ? 'edit_rule' : 'add_rule')}</h2>

          ${this.canWrite
            ? nothing
            : html`<div class="note">${t(this.language, 'read_only')}</div>`}
          ${this.error !== null
            ? html`<div class="error">${this.error}</div>`
            : nothing}

          <div class="form">
            ${this._text('time', t(this.language, 'time'))}
            <div class="field">
              <label for="action">${t(this.language, 'action')}</label>
              <select
                id="action"
                class="action"
                ?disabled=${!this.canWrite}
                @change=${(event: Event) =>
                  this._patch({ action: (event.target as HTMLSelectElement).value })}
              >
                ${['on', 'off', 'custom'].map(
                  (option) => html`
                    <option value=${option} ?selected=${this._form.action === option}>
                      ${option}
                    </option>
                  `,
                )}
              </select>
            </div>
            ${this._text('name', t(this.language, 'name'))}

            ${this._form.action === 'custom'
              ? this._text('script', t(this.language, 'script'))
              : html`
                  <shabbat-device-settings
                    .states=${this.states}
                    .devices=${this._form.devices.length
                      ? this._form.devices
                      : (this.defaults.devices ?? [])}
                    .settings=${this._form.settings}
                    .disabled=${!this.canWrite}
                    .language=${this.language}
                    @settings-changed=${(event: Event) =>
                      this._patch({ settings: (event as CustomEvent).detail.settings })}
                  ></shabbat-device-settings>
                `}

            <div class="field">
              <label for="enabled">${t(this.language, 'enabled')}</label>
              <input
                id="enabled"
                class="enabled"
                type="checkbox"
                .checked=${this._form.enabled}
                ?disabled=${!this.canWrite}
                @change=${(event: Event) =>
                  this._patch({ enabled: (event.target as HTMLInputElement).checked })}
              />
            </div>

            <button
              class="advanced-toggle"
              @click=${() => { this._advanced = !this._advanced; }}
            >
              ${t(this.language, 'advanced')}
            </button>
            ${this._advanced
              ? html`
                  ${this._text('icon', t(this.language, 'icon'))}
                  ${this._text('color', t(this.language, 'colour'))}
                  <div class="field">
                    <label for="replay">${t(this.language, 'replay')}</label>
                    <input
                      id="replay"
                      class="replay"
                      type="checkbox"
                      .checked=${this._form.replay_on_restart}
                      ?disabled=${!this.canWrite}
                      @change=${(event: Event) =>
                        this._patch({
                          replay_on_restart: (event.target as HTMLInputElement).checked,
                        })}
                    />
                  </div>
                `
              : nothing}
          </div>

          <div class="actions">
            ${this.canWrite && editing
              ? html`<button
                  class="delete"
                  ?disabled=${this.busy}
                  @click=${() => this._emit('dialog-delete')}
                >
                  ${t(this.language, 'delete_rule')}
                </button>`
              : nothing}
            <button @click=${() => this.dispatchEvent(new CustomEvent('dialog-close'))}>
              ${t(this.language, 'cancel')}
            </button>
            ${this.canWrite && editing
              ? html`<button
                  class="duplicate"
                  ?disabled=${this.busy}
                  @click=${() => this._emit('dialog-duplicate')}
                >
                  ${t(this.language, 'duplicate')}
                </button>`
              : nothing}
            ${this.canWrite
              ? html`<button
                  class="save"
                  ?disabled=${this.busy}
                  @click=${() => this._emit('dialog-save')}
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
