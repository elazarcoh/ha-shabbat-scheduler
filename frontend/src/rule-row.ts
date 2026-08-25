import { LitElement, css, html, nothing } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import {
  formatOutcome,
  formatOutcomeAt,
  formatWarning,
  outcomeIsBad,
  ruleBrief,
  ruleColour,
  warningsForRule,
} from './format';
import { t } from './strings';
import type { Defaults, RuleData, WarningData } from './types';

@customElement('shabbat-rule-row')
export class ShabbatRuleRow extends LitElement {
  @property({ attribute: false }) rule!: RuleData;
  @property({ attribute: false }) defaults: Defaults = {};
  @property({ attribute: false }) warnings: WarningData[] = [];
  @property() language = 'en';

  static override styles = css`
    .row {
      display: flex;
      align-items: center;
      gap: 12px;
      padding-block: 8px;
      padding-inline: 4px;
      border-block-end: 1px solid var(--divider-color, #e0e0e0);
    }
    .row.disabled { opacity: 0.5; }
    .dot { inline-size: 10px; block-size: 10px; border-radius: 50%; flex: none; }
    .time { font-variant-numeric: tabular-nums; min-inline-size: 3.5em; }
    .body { flex: 1; min-inline-size: 0; }
    .title { font-weight: 500; }
    .brief {
      color: var(--secondary-text-color, #666);
      font-size: 0.9em;
      overflow-wrap: anywhere;
    }
    .conflict { color: var(--warning-color, #d9822b); flex: none; }
    /* Inline and always visible - see the note on render(). */
    .conflict-detail {
      color: var(--warning-color, #d9822b);
      font-size: 0.85em;
      overflow-wrap: anywhere;
      margin-block-start: 2px;
    }
    /* Inline and always visible, for the same reason .conflict-detail is:
       there is no hover on the wall tablet this card is built for, so a
       tooltip would show nobody anything. */
    .last-outcome {
      font-size: 0.85em;
      color: var(--secondary-text-color, #666);
      overflow-wrap: anywhere;
      margin-block-start: 2px;
    }
    /* Not red: a rule that did not run is not an error in the card, and
       the conflict warning colour is already taken. Distinct enough to
       find while scanning, quiet enough not to shout on every row. */
    .last-outcome.bad { color: var(--error-color, #c62828); }
    .last-outcome-at { opacity: 0.8; margin-inline-start: 0.5em; }
    .tag { font-size: 0.8em; color: var(--secondary-text-color, #666); }
    .row { cursor: pointer; }
    .row:focus-visible { outline: 2px solid var(--primary-color, #03a9f4); outline-offset: -2px; }
  `;

  private _open() {
    this.dispatchEvent(
      new CustomEvent('rule-open', {
        detail: { rule: this.rule },
        bubbles: true,
        composed: true,
      }),
    );
  }

  /**
   * The conflict text is rendered inline, not only as a `title=` tooltip.
   * There is no hover on the wall tablet this card is built for, so the
   * tooltip showed nobody anything: the badge said a conflict existed and
   * gave no way to find out what it was. Conflicts are warned and never
   * auto-resolved, so which device and which time clash is the entire
   * actionable content.
   *
   * Always on rather than tap-to-expand: an expander nobody taps is the
   * same silence in a different shape. It costs one short line on the
   * rare row that has a conflict, so the timeline stays scannable.
   *
   * Every conflict, not just the first: `unattachedWarnings` treats a
   * warning as handled the moment it names a displayed rule, so a second
   * conflict on this row that we did not draw would show up nowhere at
   * all - not here and not in the banner.
   */
  override render() {
    const conflicts = warningsForRule(this.rule.id, this.warnings);
    const title = this.rule.name;
    // Nothing at all for a rule that has never come due - an empty
    // outcome line on every row of a fresh install would train the reader
    // to skip exactly the line that matters on the one night it appears.
    const outcome = this.rule.last_outcome ?? null;
    const when = outcome === null ? '' : formatOutcomeAt(outcome.at, this.language);
    return html`
      <div
        class="row ${this.rule.enabled ? '' : 'disabled'}"
        tabindex="0"
        role="button"
        @click=${() => this._open()}
        @keydown=${(event: KeyboardEvent) => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            this._open();
          }
        }}
      >
        <span class="dot" style="background:${ruleColour(this.rule)}"></span>
        <span class="time">${this.rule.time.slice(0, 5)}</span>
        <div class="body">
          ${title ? html`<div class="title">${title}</div>` : nothing}
          <div class="brief">${ruleBrief(this.rule, this.defaults)}</div>
          ${outcome !== null
            ? html`<div class="last-outcome ${outcomeIsBad(outcome) ? 'bad' : ''}">
                <span>${formatOutcome(outcome, this.language)}</span>
                ${when ? html`<span class="last-outcome-at">${when}</span>` : nothing}
              </div>`
            : nothing}
          ${conflicts.length
            ? html`<div class="conflict-detail">
                ${conflicts.map(
                  (conflict) =>
                    html`<div>${formatWarning(conflict, this.language)}</div>`,
                )}
              </div>`
            : nothing}
        </div>
        ${this.rule.enabled
          ? nothing
          : html`<span class="tag">${t(this.language, 'disabled_rule')}</span>`}
        ${conflicts.length
          ? html`<span
              class="conflict"
              role="img"
              aria-label=${conflicts
                .map((conflict) => formatWarning(conflict, this.language))
                .join('; ')}
              title=${formatWarning(conflicts[0], this.language)}
              >⚠</span
            >`
          : nothing}
      </div>
    `;
  }
}
