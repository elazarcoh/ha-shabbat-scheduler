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
    .tag { font-size: 0.8em; color: var(--secondary-text-color, #666); }
  `;

  override render() {
    const conflicts = warningsForRule(this.rule.id, this.warnings);
    const title = this.rule.name;
    return html`
      <div class="row ${this.rule.enabled ? '' : 'disabled'}">
        <span class="dot" style="background:${actionColour(this.rule.action)}"></span>
        <span class="time">${this.rule.time.slice(0, 5)}</span>
        <div class="body">
          ${title ? html`<div class="title">${title}</div>` : nothing}
          <div class="brief">${ruleBrief(this.rule, this.defaults)}</div>
        </div>
        ${this.rule.enabled
          ? nothing
          : html`<span class="tag">${t(this.language, 'disabled_rule')}</span>`}
        ${conflicts.length
          ? html`<span class="conflict" title=${formatWarning(conflicts[0], this.language)}>⚠</span>`
          : nothing}
      </div>
    `;
  }
}
