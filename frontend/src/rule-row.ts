import { LitElement, css, html, nothing } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { actionColour, formatWarning, ruleBrief, warningsForRule } from './format';
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
    .tag { font-size: 0.8em; color: var(--secondary-text-color, #666); }
  `;

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
    return html`
      <div
        class="row ${this.rule.enabled ? '' : 'disabled'}"
        @click=${() =>
          this.dispatchEvent(
            new CustomEvent('rule-open', {
              detail: { rule: this.rule },
              bubbles: true,
              composed: true,
            }),
          )}
      >
        <span class="dot" style="background:${actionColour(this.rule.action)}"></span>
        <span class="time">${this.rule.time.slice(0, 5)}</span>
        <div class="body">
          ${title ? html`<div class="title">${title}</div>` : nothing}
          <div class="brief">${ruleBrief(this.rule, this.defaults)}</div>
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
