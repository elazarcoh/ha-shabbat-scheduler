import { LitElement, css, html, nothing } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { daysFor, foldCallResults, formatOutcome } from './format';
import { t } from './strings';
import type { Hass } from './types';

interface PreviewRule {
  when: string;
  rule_id: string;
  name: string | null;
  action: string;
  target: Record<string, unknown>;
  data: Record<string, unknown>;
  /**
   * The day name ('erev' | '1' | '2' | '3') this rule resolved to, from
   * `block.py`'s `preview_payload`. Absent on a server too old to send it
   * - `_previewRules` treats that as "cannot be filtered", not "belongs to
   * no day", so an old server's preview still shows something rather than
   * silently emptying out.
   */
  day?: string;
}

interface PreviewResponse {
  profile: number | null;
  rules: PreviewRule[];
  conflicts: unknown[];
  warnings: { kind: string; message?: string }[];
}

@customElement('shabbat-simulate-dialog')
export class ShabbatSimulateDialog extends LitElement {
  @property({ attribute: false }) hass: Hass | null = null;
  @property() language = 'en';
  @property({ type: Boolean }) canWrite = false;

  @state() private _profile = 1;
  @state() private _day = 'erev';
  @state() private _forceConditions = false;
  @state() private _preview: PreviewResponse | null = null;
  @state() private _busy = false;
  @state() private _error: string | null = null;
  @state() private _results: { ruleId: string; results: unknown[] }[] | null = null;
  /**
   * True while the inline "are you sure" step for "Run this day for real"
   * is showing - mirrors `rule-dialog.ts`'s own `_runConfirmOpen` for its
   * single-rule Run Now. Running a whole day's schedule for real is a
   * bigger action than running one rule, so it gets at least the same
   * deliberate second step; Simulate needs none of this; it calls nothing.
   */
  @state() private _runRealConfirmOpen = false;

  static override styles = css`
    .sheet {
      position: fixed; inset: 0; display: flex; align-items: center;
      justify-content: center; background: rgba(0, 0, 0, 0.4); z-index: 10;
    }
    .panel {
      background: var(--card-background-color, #fff);
      color: var(--primary-text-color, #111);
      border-radius: 12px; padding: 16px;
      inline-size: min(28rem, 92vw); max-block-size: 88vh; overflow: auto;
    }
    h2 { margin-block: 0 12px; font-size: 1.1em; }
    .field { display: flex; align-items: center; gap: 12px; margin-block: 8px; }
    .field label { min-inline-size: 9em; }
    select { font: inherit; padding-block: 4px; padding-inline: 6px; flex: 1; }
    .row {
      padding-block: 4px; font-size: 0.9em;
      border-block-end: 1px solid var(--divider-color, #e0e0e0);
    }
    .error { color: var(--error-color, #d64545); margin-block: 8px; font-size: 0.9em; }
    .actions {
      display: flex; gap: 8px; justify-content: flex-end;
      flex-wrap: wrap; margin-block-start: 16px;
    }
    button {
      font: inherit; padding-block: 6px; padding-inline: 12px;
      border-radius: 6px; border: 1px solid var(--divider-color, #e0e0e0);
      background: var(--card-background-color, #fff); color: inherit; cursor: pointer;
    }
    button[disabled] { opacity: 0.5; cursor: not-allowed; }
  `;

  override connectedCallback() {
    super.connectedCallback();
    void this._loadPreview();
  }

  private async _loadPreview() {
    if (this.hass === null) return;
    this._busy = true;
    try {
      this._preview = (await this.hass.callWS({
        type: 'shabbat_scheduler/preview', block_length: this._profile,
      })) as PreviewResponse;
    } catch (err) {
      const detail = err as { message?: string } | null;
      this._error = detail?.message ?? String(err);
    } finally {
      this._busy = false;
    }
  }

  /**
   * The previewed block's rules, filtered to the currently-selected day -
   * the same day `run_day` (the adjacent Simulate/Run-for-real buttons)
   * actually acts on. Unfiltered, this used to show the WHOLE block's
   * rules while the day picker only ever selected one day's worth to run,
   * so what was displayed did not correspond to what pressing the button
   * next to it would do.
   *
   * `preview`'s `when` is a resolved datetime; mapping it back to a day
   * NAME ('erev'/'1'/'2'...) is block.py's own logic (`preview_payload`'s
   * own `day` field), not re-derived here to avoid a second,
   * possibly-drifting implementation of it. A rule with no `day` at all
   * (an older server that has not been upgraded alongside this card) is
   * kept rather than dropped - filtering on a field that cannot be read is
   * indistinguishable from silently emptying the preview.
   */
  private _previewRules(): PreviewRule[] {
    return (this._preview?.rules ?? []).filter(
      (rule) => rule.day === undefined || rule.day === this._day,
    );
  }

  /**
   * Rule id -> display name, from the SAME preview payload the rows and
   * the day filter above already read - `preview`'s per-rule dict already
   * carries both `rule_id` and `name`, so `run_day`'s own result rows can
   * be labelled without a second round trip. Built from the UNFILTERED
   * preview list: a result belongs to whichever rule fired, and that rule
   * is always among the previewed ones regardless of which day is
   * currently selected in the picker.
   */
  private _label(ruleId: string): string {
    const rule = (this._preview?.rules ?? []).find((r) => r.rule_id === ruleId);
    if (rule === undefined) return ruleId;
    return rule.name ?? rule.action;
  }

  private async _run(simulate: boolean) {
    if (this.hass === null) return;
    this._runRealConfirmOpen = false;
    this._busy = true;
    this._error = null;
    try {
      const response = (await this.hass.callWS({
        type: 'shabbat_scheduler/rules/run_day',
        profile: this._profile,
        day: this._day,
        simulate,
        force_conditions: this._forceConditions,
      })) as { results: { rule_id: string; results: unknown[] }[] };
      this._results = response.results.map(
        (r) => ({ ruleId: r.rule_id, results: r.results }),
      );
    } catch (err) {
      const detail = err as { message?: string } | null;
      this._error = detail?.message ?? String(err);
    } finally {
      this._busy = false;
    }
  }

  private _dayLabel(day: string): string {
    return day === 'erev' ? t(this.language, 'erev') : `${t(this.language, 'day')} ${day}`;
  }

  override render() {
    return html`
      <div class="sheet" @click=${(event: Event) => {
        if (event.target === event.currentTarget) {
          this.dispatchEvent(new CustomEvent('dialog-close'));
        }
      }}>
        <div class="panel">
          <h2>${t(this.language, 'simulate_title')}</h2>
          ${this._error !== null ? html`<div class="error">${this._error}</div>` : nothing}

          <div class="field">
            <label>${t(this.language, 'simulate_profile')}</label>
            <select
              class="profile"
              .value=${String(this._profile)}
              @change=${(event: Event) => {
                this._profile = Number((event.target as HTMLSelectElement).value);
                if (!daysFor(this._profile).includes(this._day)) this._day = 'erev';
                this._runRealConfirmOpen = false;
                void this._loadPreview();
              }}
            >
              ${[1, 2, 3].map((p) => html`<option value=${p}>${p}d</option>`)}
            </select>
          </div>
          <div class="field">
            <label>${t(this.language, 'simulate_day')}</label>
            <select
              class="day"
              .value=${this._day}
              @change=${(event: Event) => {
                this._day = (event.target as HTMLSelectElement).value;
                this._runRealConfirmOpen = false;
              }}
            >
              ${daysFor(this._profile).map(
                (day) => html`<option value=${day}>${this._dayLabel(day)}</option>`,
              )}
            </select>
          </div>
          <div class="field">
            <label>${t(this.language, 'simulate_force_conditions')}</label>
            <ha-selector
              class="force-conditions"
              .hass=${this.hass}
              .selector=${{ boolean: {} }}
              .value=${this._forceConditions}
              .disabled=${!this.canWrite}
              @value-changed=${(event: CustomEvent) => {
                this._forceConditions = Boolean(event.detail?.value);
              }}
            ></ha-selector>
          </div>

          ${this._preview !== null
            ? html`<div class="preview">
                ${this._previewRules().map(
                  (rule) => html`<div class="row">
                    ${rule.when.slice(11, 16)} — ${rule.name ?? rule.action}
                  </div>`,
                )}
              </div>`
            : nothing}

          ${this._results !== null
            ? html`<div class="results">
                ${this._results.map((r) => {
                  const outcome = foldCallResults(
                    r.results as Record<string, unknown>[], new Date().toISOString(),
                  );
                  return html`<div class="row">
                    ${this._label(r.ruleId)}: ${formatOutcome(outcome, this.language)}
                  </div>`;
                })}
              </div>`
            : nothing}

          <div class="actions">
            <button @click=${() => this.dispatchEvent(new CustomEvent('dialog-close'))}>
              ${t(this.language, 'cancel')}
            </button>
            ${this.canWrite
              ? html`<button
                  class="run-simulate"
                  ?disabled=${this._busy}
                  @click=${() => this._run(true)}
                >${t(this.language, 'simulate_this_day')}</button>
                <button
                  class="run-real"
                  ?disabled=${this._busy}
                  @click=${() => {
                    this._runRealConfirmOpen = !this._runRealConfirmOpen;
                  }}
                >${t(this.language, 'simulate_run_for_real')}</button>`
              : nothing}
          </div>
          ${this._runRealConfirmOpen
            ? html`<div class="run-real-confirm">
                <div class="confirm-text">
                  ${t(this.language, 'simulate_run_for_real_confirm')} ${this._dayLabel(this._day)}.
                </div>
                <button
                  class="run-real-cancel"
                  @click=${() => { this._runRealConfirmOpen = false; }}
                >${t(this.language, 'cancel')}</button>
                <button
                  class="run-real-confirmed"
                  ?disabled=${this._busy}
                  @click=${() => this._run(false)}
                >${t(this.language, 'run_now_real')}</button>
              </div>`
            : nothing}
        </div>
      </div>
    `;
  }
}
