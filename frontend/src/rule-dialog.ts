import { LitElement, css, html, nothing } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import {
  dayLabel, daysFor, foldCallResults, formatOutcome, formToChanges, ruleToForm,
} from './format';
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

/**
 * The run-now result folded to the single line `formatOutcome` renders,
 * language-aware - see the note on `_emitRunNow`'s caller in `render` for
 * why this cannot simply call `formatOutcome` with no language argument.
 */
function foldRunNowResults(
  result: { results: unknown[]; at: string },
  language?: string,
): string[] {
  const outcome = foldCallResults(result.results as Record<string, unknown>[], result.at);
  return [formatOutcome(outcome, language)];
}

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
  /** The last `rules/run_now` result, keyed to the rule it belongs to. */
  @property({ attribute: false }) runNowResult:
    { ruleId: string; results: unknown[]; at: string } | null = null;

  @state() private _form: RuleFormState = EMPTY_FORM;
  @state() private _advanced = false;
  @state() private _conditionError = false;
  @state() private _runConfirmOpen = false;
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
    /* Header, scrolling content, footer: the title and the Save button
       stay put however long the form gets. */
    .panel {
      display: flex;
      flex-direction: column;
      background: var(--card-background-color, #fff);
      color: var(--primary-text-color, #111);
      border-radius: 12px;
      inline-size: min(30rem, 94vw);
      max-block-size: 90vh;
      overflow: hidden;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.25);
    }
    .head {
      padding-block: 16px 8px;
      padding-inline: 20px;
      border-block-end: 1px solid var(--divider-color, #e0e0e0);
    }
    h2 { margin: 0; font-size: 1.2em; font-weight: 500; }
    .content {
      flex: 1;
      min-block-size: 0;
      overflow: auto;
      padding-block: 4px 16px;
      padding-inline: 20px;
    }
    .section { padding-block: 12px; }
    .section + .section { border-block-start: 1px solid var(--divider-color, #e0e0e0); }
    .section-title {
      margin-block: 0 8px;
      font-size: 0.75em;
      font-weight: 600;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--secondary-text-color, #666);
    }
    /* Label above its control: no 7em label column eating a phone's
       width. Toggles are the exception - label left, switch right. */
    .field { display: flex; flex-direction: column; gap: 4px; margin-block: 8px; }
    .field label { font-size: 0.85em; color: var(--secondary-text-color, #666); }
    .field.inline { flex-direction: row; align-items: center; justify-content: space-between; }
    .field.inline label { font-size: 1em; color: inherit; }
    /* Day and time side by side - together they ARE "when". */
    .when {
      display: grid;
      grid-template-columns: minmax(6.5em, 1fr) auto;
      gap: 12px;
      align-items: end;
    }
    .when .field { margin-block: 0; }
    /* Match Home Assistant's own text field height, so the select and
       the time picker beside it line up. */
    .when select { min-block-size: 56px; }
    input, select {
      font: inherit;
      box-sizing: border-box;
      min-block-size: 40px;
      padding-block: 6px;
      padding-inline: 10px;
      border: 1px solid var(--divider-color, #c8c8c8);
      border-radius: 8px;
      background: var(--card-background-color, #fff);
      color: inherit;
      inline-size: 100%;
      min-inline-size: 0;
    }
    input[type='color'] { padding: 2px; inline-size: 4em; }
    .foot {
      border-block-start: 1px solid var(--divider-color, #e0e0e0);
      padding-block: 10px;
      padding-inline: 16px;
      background: var(--card-background-color, #fff);
    }
    .actions {
      display: flex;
      gap: 8px;
      align-items: center;
      flex-wrap: wrap;
    }
    /* Secondary actions are quiet text buttons on the start side; Cancel
       and Save sit together at the end, Save the only filled one. */
    .actions .spacer { flex: 1; }
    .actions .delete, .actions .duplicate, .actions .run-now {
      border-color: transparent;
      background: none;
      padding-inline: 8px;
    }
    .actions .delete { color: var(--error-color, #d64545); }
    .actions .save {
      background: var(--primary-color, #03a9f4);
      border-color: var(--primary-color, #03a9f4);
      color: var(--text-primary-color, #fff);
      font-weight: 500;
    }
    button {
      font: inherit;
      min-block-size: 36px;
      padding-block: 6px;
      padding-inline: 14px;
      border-radius: 8px;
      border: 1px solid var(--divider-color, #e0e0e0);
      background: var(--card-background-color, #fff);
      color: inherit;
      cursor: pointer;
    }
    button[disabled] { opacity: 0.5; cursor: not-allowed; }
    .run-confirm { display: flex; gap: 8px; margin-block-start: 8px; flex-wrap: wrap; }
    .run-now-result { font-size: 0.9em; margin-block-start: 8px; }
    .error {
      color: var(--error-color, #d64545);
      margin-block: 8px;
      font-size: 0.9em;
    }
    .note { color: var(--secondary-text-color, #666); font-size: 0.85em; margin-block: 8px; }
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
    /* A phone: the dialog IS the screen. */
    @media (max-width: 600px) {
      .sheet { align-items: stretch; }
      .panel {
        inline-size: 100vw;
        max-block-size: none;
        block-size: 100%;
        border-radius: 0;
      }
      .head { padding-inline: 16px; }
      .content { padding-inline: 16px; }
      .foot { padding-block-end: max(10px, env(safe-area-inset-bottom)); }
      /* Secondary actions on their own row, primary row full width. */
      .actions .spacer { flex-basis: 100%; block-size: 0; }
      .actions button:not(.delete):not(.duplicate):not(.run-now) { flex: 1; }
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
      this._runConfirmOpen = false;
    }
  }

  override updated() {
    // Belt and braces with the per-option `?selected` in `_dayField`: the
    // select's own value is pinned to the form after every render, so
    // whatever order the options were (re)built in, it shows the day a
    // save will write.
    const select = this.shadowRoot?.querySelector('select.day') as HTMLSelectElement | null;
    if (select && select.value !== this._form.day) select.value = this._form.day;
  }

  private _patch(patch: Partial<RuleFormState>) {
    this._form = { ...this._form, ...patch };
    // An edit mid-confirm would leave the Simulate/Run-for-real choice
    // pointing at a rule that is no longer what is about to be saved -
    // close it rather than let it fire against stale values. `_dirty`
    // below keeps the button that reopens it disabled from this point on,
    // until the edit is saved.
    this._runConfirmOpen = false;
  }

  /**
   * True once the form has diverged from the saved rule - the same
   * per-field diff `_saveChanges` (card.ts) sends to the server, read here
   * only to ask "is there anything unsaved at all", never to build a
   * write.
   *
   * Run Now (`rule-dialog.ts`) is disabled while this is true: it
   * dispatches `this.rule`, the SAVED copy, and the server looks a rule up
   * by id from the store - so pressing it after editing but before saving
   * would run and report on the OLD version while the new, unsaved values
   * sit right above it in the form, which is exactly backwards for a
   * feature whose whole point is "prove this rule works as I've set it up
   * right now". The two inline confirm buttons (Simulate / Run for real)
   * carry the identical guard directly, not only through `_patch` closing
   * the confirm on every edit - `_patch` cannot catch `this.rule` changing
   * out from under an already-open confirm because of an edit made
   * elsewhere (another client, another tab), which flips `_dirty` true
   * without any local edit ever calling `_patch` at all.
   *
   * Also gates the displayed Run Now result: an edit after running leaves
   * `runNowResult.ruleId` still matching `this.rule.id` (same rule, just
   * edited), so without this the OLD result would stay visible underneath
   * the new, unsaved edits, looking like a preview of them rather than a
   * verdict on the version now superseded.
   *
   * `false` while creating (`this.rule === null`): Run Now (`canWrite &&
   * editing`) never renders there at all, so there is nothing for this to
   * gate.
   */
  private get _dirty(): boolean {
    if (this.rule === null) return false;
    return Object.keys(formToChanges(this._form, this.rule)).length > 0;
  }

  private _emit(type: string) {
    this.dispatchEvent(
      new CustomEvent(type, { detail: { form: this._form, rule: this.rule } }),
    );
  }

  private _text(key: 'name', label: string) {
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

  private _timeField() {
    return html`
      <div class="field">
        <label for="time">${t(this.language, 'time')}</label>
        <ha-selector
          id="time"
          class="time"
          .hass=${this.hass}
          .selector=${{ time: {} }}
          .value=${this._form.time || null}
          .disabled=${!this.canWrite}
          @value-changed=${(event: CustomEvent) =>
            this._patch({ time: (event.detail?.value as string) ?? '' })}
        ></ha-selector>
      </div>
    `;
  }

  /**
   * Which day of the block the rule belongs to. Shown on every open, edit
   * and create alike, so the day a save will write is always on screen
   * rather than implied by which group the dialog was opened from.
   *
   * The options are the PROFILE's days (`daysFor`), plus the rule's own
   * day if it is somehow outside them - a rule must never be silently
   * re-homed just because the picker could not show where it lives.
   * Selection uses `?selected` per option, not `.value` on the select:
   * setting `.value` before the options exist leaves the first option
   * (Erev) showing, which is exactly the "jumped to Erev" this field is
   * here to rule out.
   */
  private _dayField() {
    const days = daysFor(this.rule?.profile ?? this.profile);
    if (!days.includes(this._form.day)) days.push(this._form.day);
    return html`
      <div class="field">
        <label for="day">${t(this.language, 'day')}</label>
        <select
          id="day"
          class="day"
          ?disabled=${!this.canWrite}
          @change=${(event: Event) =>
            this._patch({ day: (event.target as HTMLSelectElement).value })}
        >
          ${days.map(
            (day) => html`<option value=${day} ?selected=${day === this._form.day}>
              ${dayLabel(day, this.language)}
            </option>`,
          )}
        </select>
      </div>
    `;
  }

  private _enabledField() {
    return html`
      <div class="field inline">
        <label for="enabled">${t(this.language, 'enabled')}</label>
        <ha-selector
          id="enabled"
          class="enabled"
          .hass=${this.hass}
          .selector=${{ boolean: {} }}
          .value=${this._form.enabled}
          .disabled=${!this.canWrite}
          @value-changed=${(event: CustomEvent) =>
            this._patch({ enabled: Boolean(event.detail?.value) })}
        ></ha-selector>
      </div>
    `;
  }

  private _iconField() {
    return html`
      <div class="field">
        <label for="icon">${t(this.language, 'icon')}</label>
        <ha-selector
          id="icon"
          class="icon"
          .hass=${this.hass}
          .selector=${{ icon: {} }}
          .value=${this._form.icon ?? ''}
          .disabled=${!this.canWrite}
          @value-changed=${(event: CustomEvent) => {
            const value = (event.detail?.value as string) ?? '';
            this._patch({ icon: value === '' ? null : value });
          }}
        ></ha-selector>
      </div>
    `;
  }

  private _colorField() {
    return html`
      <div class="field inline">
        <label for="color">${t(this.language, 'colour')}</label>
        <input
          id="color"
          class="color"
          type="color"
          .value=${this._form.color || '#000000'}
          ?disabled=${!this.canWrite}
          @change=${(event: Event) => {
            this._patch({ color: (event.target as HTMLInputElement).value });
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

  private _emitRunNow(simulate: boolean) {
    this._runConfirmOpen = false;
    this.dispatchEvent(
      new CustomEvent('dialog-run-now', { detail: { rule: this.rule, simulate } }),
    );
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
          <div class="head">
            <h2>${t(this.language, editing ? 'edit_rule' : 'add_rule')}</h2>
          </div>
          <div class="content">

          ${this.canWrite
            ? nothing
            : html`<div class="note">${t(this.language, 'read_only')}</div>`}
          ${this.error !== null
            ? html`<div class="error">${this.error}</div>`
            : nothing}
          ${this._conditionError
            ? html`<div class="error condition-blocked">
                ${t(this.language, 'condition_unparseable')}
              </div>`
            : nothing}

          <div class="form">
            <div class="section">
              ${this._text('name', t(this.language, 'name'))}
              <div class="when">
                ${this._dayField()}
                ${this._timeField()}
              </div>
            </div>

            <div class="section">
            <h3 class="section-title">${t(this.language, 'section_action')}</h3>

            <!-- \`data: … ?? {}\` below is on purpose, and it must NOT
                 become "preserve the old data" the way the defaults
                 dialog's handler does. HA omits \`data\` from the event on
                 every service change; for a RULE the action is part of the
                 rule, so data shaped for the service the author just
                 navigated away from does not belong to the new one, and
                 clearing it is Home Assistant's own semantics. See
                 \`service-editor.ts\`'s \`_onChange\` for why the two cases
                 are distinguishable at all. -->
            <shabbat-service-editor
              .hass=${this.hass}
              .action=${this._form.action}
              .data=${this._form.data}
              .disabled=${!this.canWrite}
              @service-changed=${(event: CustomEvent) =>
                this._patch({
                  action: event.detail.action, data: event.detail.data ?? {},
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
            </div>

            <div class="section">
            <h3 class="section-title">${t(this.language, 'section_conditions')}</h3>

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
            </div>

            <div class="section">
            <h3 class="section-title">${t(this.language, 'section_options')}</h3>
            ${this._enabledField()}

            <shabbat-replay-editor
              .hass=${this.hass}
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
                    ${this._iconField()}
                    ${this._colorField()}
                  </div>
                `
              : nothing}
            </div>
          </div>
          </div>

          <div class="foot">
          ${this._runConfirmOpen
            ? html`<div class="run-confirm">
                <button
                  class="run-simulate"
                  ?disabled=${this._dirty}
                  @click=${() => this._emitRunNow(true)}
                >${t(this.language, 'run_now_simulate')}</button>
                <button
                  class="run-real"
                  ?disabled=${this._dirty}
                  @click=${() => this._emitRunNow(false)}
                >${t(this.language, 'run_now_real')}</button>
              </div>`
            : nothing}
          ${this.rule !== null && !this._dirty && this.runNowResult?.ruleId === this.rule.id
            ? html`<div class="run-now-result">
                ${foldRunNowResults(this.runNowResult, this.language).map(
                  (line) => html`<div>${line}</div>`,
                )}
              </div>`
            : nothing}
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
            ${this.canWrite && editing
              ? html`<button
                  class="duplicate"
                  ?disabled=${this.busy}
                  @click=${() => this._emit('dialog-duplicate')}
                >
                  ${t(this.language, 'duplicate')}
                </button>`
              : nothing}
            ${this.canWrite && editing
              ? html`<button
                  class="run-now"
                  ?disabled=${this.busy || this._dirty}
                  title=${this._dirty ? t(this.language, 'run_now_disabled_dirty') : ''}
                  @click=${() => { this._runConfirmOpen = !this._runConfirmOpen; }}
                >
                  ▶ ${t(this.language, 'run_now_button')}
                </button>`
              : nothing}
            <span class="spacer"></span>
            <button @click=${() => this.dispatchEvent(new CustomEvent('dialog-close'))}>
              ${t(this.language, 'cancel')}
            </button>
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
      </div>
    `;
  }
}
