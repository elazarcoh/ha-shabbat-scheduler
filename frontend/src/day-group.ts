import { LitElement, css, html, nothing } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import './rule-row';
import { t } from './strings';
import type { DayGroup, Defaults, WarningData } from './types';

/**
 * '2026-08-15T20:01:00+03:00' -> '20:01', without a timezone library.
 * Falls back to the raw value when it can't be parsed, so a malformed
 * zmanim timestamp shows up as something visibly wrong next to the
 * marker icon instead of a silent blank.
 */
function clock(iso: string): string {
  const match = /T(\d{2}:\d{2})/.exec(iso);
  return match ? match[1] : iso;
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
    // Everything lives inside one root element. Under this repo's pinned
    // lit-html@3.3.3 + happy-dom@15.11.7, a render() template with more
    // than one top-level node - even just one static heading <div> beside
    // a single dynamic ternary - fails to render *either* branch of that
    // ternary, not just the not-taken one. The rule this leaves us with:
    // wrap every render() root in a single element, as rule-row.ts already
    // does. This was reproduced under happy-dom only and not confirmed
    // against a real browser, so it's a test-environment constraint we're
    // shaping code around here, not a known lit-html defect in
    // production - Task 12's end-to-end tests run in a real browser and
    // will show whether it matters there.
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
