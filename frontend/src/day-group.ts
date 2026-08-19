import { LitElement, css, html, nothing } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import './rule-row';
import { t } from './strings';
import type { DayGroup, Defaults, WarningData } from './types';

/** '2026-08-15T20:01:00+03:00' -> '20:01', without a timezone library. */
function clock(iso: string): string {
  const match = /T(\d{2}:\d{2})/.exec(iso);
  return match ? match[1] : '';
}

@customElement('shabbat-day-group')
export class ShabbatDayGroup extends LitElement {
  @property({ attribute: false }) group!: DayGroup;
  @property({ attribute: false }) defaults: Defaults = {};
  @property({ attribute: false }) warnings: WarningData[] = [];
  @property() language = 'en';

  static override styles = css`
    .heading {
      display: flex;
      align-items: baseline;
      gap: 8px;
      margin-block: 16px 4px;
      font-weight: 600;
    }
    .date { color: var(--secondary-text-color, #666); font-weight: 400; }
    .empty {
      color: var(--secondary-text-color, #666);
      padding-block: 8px;
      padding-inline: 4px;
      font-size: 0.9em;
    }
    .marker {
      display: flex;
      align-items: center;
      gap: 8px;
      padding-block: 6px;
      padding-inline: 4px;
      color: var(--secondary-text-color, #666);
      font-size: 0.9em;
    }
  `;

  private label(): string {
    const { day } = this.group;
    return day === 'erev'
      ? t(this.language, 'erev')
      : `${t(this.language, 'day')} ${day}`;
  }

  override render() {
    const { marker, rules } = this.group;
    // Everything lives inside one root element: with several top-level
    // dynamic sibling parts, happy-dom's TreeWalker/Range shims fail to
    // patch the not-taken branch of a nested ternary (verified: the
    // false branch simply never renders). Nesting them all under a
    // single wrapping element - as rule-row.ts already does - avoids it.
    return html`
      <div class="day-group">
        <div class="heading">
          <span>${this.label()}</span>
          <span class="date">${this.group.date ?? ''}</span>
        </div>
        ${rules.length
          ? rules.map(
              (rule) => html`
                <shabbat-rule-row
                  .rule=${rule}
                  .defaults=${this.defaults}
                  .warnings=${this.warnings}
                  .language=${this.language}
                ></shabbat-rule-row>
              `,
            )
          : html`<div class="empty">${t(this.language, 'no_rules')}</div>`}
        ${marker
          ? html`
              <div class="marker">
                <span>${marker.kind === 'havdalah' ? '✨' : '🕯️'}</span>
                <span>${t(this.language, marker.kind)}</span>
                <span>${clock(marker.at)}</span>
              </div>
            `
          : nothing}
      </div>
    `;
  }
}
