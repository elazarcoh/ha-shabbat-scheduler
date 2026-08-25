import { LitElement, css, html, nothing } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { describeTarget, ruleToForm } from './format';
import { t } from './strings';
import type { Defaults, Hass, RuleData, RuleFormState } from './types';

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
    .readonly {
      margin-block: 12px 4px;
      padding-block: 8px;
      padding-inline: 10px;
      border-inline-start: 3px solid var(--divider-color, #e0e0e0);
      background: var(--secondary-background-color, #f4f4f4);
      font-size: 0.9em;
    }
    .readonly dl { margin: 0; display: grid; grid-template-columns: auto 1fr; gap: 4px 12px; }
    .readonly dt { color: var(--secondary-text-color, #666); }
    .readonly dd { margin: 0; overflow-wrap: anywhere; font-variant-numeric: tabular-nums; }
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
    key: 'time' | 'action' | 'name' | 'icon' | 'color',
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

  private _describeData(): string {
    const entries = Object.entries(this._form.data);
    if (!entries.length) return t(this.language, 'none_set');
    return entries.map(([key, value]) => `${key}: ${JSON.stringify(value)}`).join(', ');
  }

  private _describeConditions(): string {
    const { condition } = this._form;
    if (!condition.length) return t(this.language, 'none_set');
    return condition.map((item) => JSON.stringify(item)).join(' ; ');
  }

  private _describeReplay(): string {
    const { replay } = this._form;
    if (!replay.enabled) return t(this.language, 'replay_no');
    const yes = t(this.language, 'replay_yes');
    return replay.within
      ? `${yes} (${t(this.language, 'replay_within')} ${replay.within})`
      : yes;
  }

  /**
   * The fields this dialog can still edit CORRECTLY, plus a read-only
   * view of the ones it cannot.
   *
   * v1's device picker and climate settings form are gone: a rule is now
   * an arbitrary service call with a Home Assistant target selector and
   * an opaque data payload, and there is no honest way to render either
   * with a device multi-select and a temperature slider. Saving a
   * v1-shaped payload would be worse than not offering the control, and
   * OMITTING the fields would be worse still - a rule that carries a
   * condition and a replay window would look like a rule that carries
   * neither. So they are shown, verbatim, marked as not editable here.
   *
   * They are still carried through the form (see `ruleToForm`), so an
   * edit cannot drop them and a duplicate is a real duplicate.
   *
   * Plan 2 builds the real editors.
   */
  override render() {
    const editing = this.rule !== null;
    const inheritedTarget = this.defaults.target ?? {};
    const ownTarget = describeTarget(this._form.target);
    const inherits = ownTarget === '' && Object.keys(inheritedTarget).length > 0;
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

          <div class="form">
            ${this._text('time', t(this.language, 'time'))}
            ${this._text('action', t(this.language, 'action'))}
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

            <div class="readonly">
              <div class="note">${t(this.language, 'read_only_fields')}</div>
              <dl>
                <dt>${t(this.language, 'target')}</dt>
                <dd class="ro-target">
                  ${ownTarget !== ''
                    ? ownTarget
                    : inherits
                      ? `${t(this.language, 'inherits_target')} ${describeTarget(inheritedTarget)}`
                      : t(this.language, 'none_set')}
                </dd>
                <dt>${t(this.language, 'data')}</dt>
                <dd class="ro-data">${this._describeData()}</dd>
                <dt>${t(this.language, 'condition')}</dt>
                <dd class="ro-condition">${this._describeConditions()}</dd>
                <dt>${t(this.language, 'replay')}</dt>
                <dd class="ro-replay">${this._describeReplay()}</dd>
              </dl>
            </div>

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
