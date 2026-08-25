import { LitElement, css, html, nothing } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { ruleToForm } from './format';
import { t } from './strings';
import type { Defaults, Hass, RuleData, RuleFormState } from './types';
import './condition-editor';
import './replay-editor';
import './service-editor';
import './target-editor';

const EMPTY_FORM: RuleFormState = {
  day: 'erev', time: '', action: '', target: {}, data: {}, condition: [],
  replay: { enabled: false }, name: null, icon: null, color: null,
  enabled: true,
};

@customElement('shabbat-rule-dialog')
export class ShabbatRuleDialog extends LitElement {
  /**
   * Passed straight to the Home Assistant elements the editors embed.
   * Reassigned on every state change in the whole system, so nothing may
   * key form-seeding off it - see `willUpdate`.
   */
  @property({ attribute: false }) hass: Hass | null = null;
  /** null means create. */
  @property({ attribute: false }) rule: RuleData | null = null;
  /** Pre-filled values for a create. This is what duplication uses. */
  @property({ attribute: false }) seed: RuleFormState | null = null;
  @property() day = 'erev';
  @property({ type: Number }) profile = 1;
  @property({ attribute: false }) defaults: Defaults = {};
  @property({ type: Boolean }) canWrite = false;
  @property({ type: Boolean }) busy = false;
  @property() error: string | null = null;
  @property() language = 'en';

  @state() private _form: RuleFormState = EMPTY_FORM;
  @state() private _advanced = false;
  @state() private _conditionError = false;
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
    .migration {
      color: var(--error-color, #d64545);
      margin-block: 8px;
      font-size: 0.9em;
      overflow-wrap: anywhere;
    }
    /* The wrapper around the advanced fields is load-bearing under this
       repo's pinned lit-html + happy-dom: a template whose root holds
       several top-level expressions renders NONE of them. Same constraint
       day-group.ts documents. Do not unwrap it. */
    .advanced { display: contents; }
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
    key: 'time' | 'name' | 'icon' | 'color',
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

  /**
   * Save, unless a condition is currently unparseable.
   *
   * The editor is ASKED (`hasError`) rather than the text re-parsed here:
   * one parser, one answer. Re-parsing would be a second implementation of
   * the same rule, and the two would drift.
   *
   * This is not client-side revalidation of the rule - the Python side
   * still owns whether a condition is *valid*. It is refusing to send
   * something that is not even a condition yet.
   */
  private _onSave() {
    const editor = this.shadowRoot?.querySelector(
      'shabbat-condition-editor',
    ) as (HTMLElement & { hasError?: boolean }) | null;
    if (editor?.hasError) {
      this._conditionError = true;
      return;
    }
    this._conditionError = false;
    this._emit('dialog-save');
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
          ${this.rule?.migration_error
            ? html`<div class="migration">
                ${t(this.language, 'migration_error')} ${this.rule.migration_error}
              </div>`
            : nothing}
          ${this.error !== null
            ? html`<div class="error">${this.error}</div>`
            : nothing}
          ${this._conditionError
            ? html`<div class="error condition-blocked">
                ${t(this.language, 'condition_unparseable')}
              </div>`
            : nothing}

          <div class="form">
            ${this._text('time', t(this.language, 'time'))}
            ${this._text('name', t(this.language, 'name'))}

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

            <shabbat-service-editor
              .hass=${this.hass}
              .action=${this._form.action}
              .data=${this._form.data}
              .disabled=${!this.canWrite}
              @service-changed=${(event: CustomEvent) =>
                this._patch({
                  action: event.detail.action, data: event.detail.data,
                })}
            ></shabbat-service-editor>

            <shabbat-target-editor
              .hass=${this.hass}
              .value=${this._form.target}
              .inherited=${this.defaults.target ?? {}}
              .disabled=${!this.canWrite}
              .language=${this.language}
              @target-changed=${(event: CustomEvent) =>
                this._patch({ target: event.detail.value })}
            ></shabbat-target-editor>

            <shabbat-condition-editor
              .value=${this._form.condition}
              .disabled=${!this.canWrite}
              .language=${this.language}
              @condition-changed=${(event: CustomEvent) => {
                // Read the editor's OWN current `hasError`, not a
                // hard-coded `false`: with two broken rows, fixing one
                // still leaves the other unparseable, and the banner (and
                // the save refusal it explains) must not vanish while a
                // save would still be blocked.
                const editor = event.target as HTMLElement & { hasError?: boolean };
                this._conditionError = editor.hasError === true;
                this._patch({ condition: event.detail.value });
              }}
            ></shabbat-condition-editor>

            <shabbat-replay-editor
              .value=${this._form.replay}
              .disabled=${!this.canWrite}
              .language=${this.language}
              @replay-changed=${(event: CustomEvent) =>
                this._patch({ replay: event.detail.value })}
            ></shabbat-replay-editor>

            <button
              class="advanced-toggle"
              @click=${() => { this._advanced = !this._advanced; }}
            >
              ${t(this.language, 'advanced')}
            </button>
            ${this._advanced
              ? html`
                  <div class="advanced">
                    ${this._text('icon', t(this.language, 'icon'))}
                    ${this._text('color', t(this.language, 'colour'))}
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
                  @click=${() => this._onSave()}
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
