import { LitElement, css, html, nothing } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import { formatWarning, unattachedWarnings } from './format';
import type { WarningData } from './types';

@customElement('shabbat-warnings')
export class ShabbatWarnings extends LitElement {
  @property({ attribute: false }) warnings: WarningData[] = [];
  /**
   * The rule ids currently shown on screen (across every visible day
   * group). A warning naming only rules outside this set has nowhere
   * else to appear, so it belongs in the banner - see `unattachedWarnings`.
   *
   * Defaults to `[]` deliberately: over-showing is the safe failure mode.
   * Until a parent passes the real ids, every conflict naming a displayed
   * rule will render twice - once on its row, once in this banner - since
   * none of its rule_ids will ever match this empty set. Task 10 must wire
   * the actual rendered rule ids in for that duplication to go away.
   */
  @property({ attribute: false }) displayedRuleIds: string[] = [];
  @property() language = 'en';

  static override styles = css`
    .banner {
      display: flex;
      flex-direction: column;
      gap: 4px;
      padding: 8px 12px;
      margin-block-end: 8px;
      border-inline-start: 3px solid var(--warning-color, #d9822b);
      background: var(--secondary-background-color, #f4f4f4);
      font-size: 0.9em;
    }
  `;

  override render() {
    // Warnings naming a displayed rule are shown on that row instead, so
    // the banner carries only what has nowhere else to go.
    const shown = unattachedWarnings(this.warnings, this.displayedRuleIds);
    if (!shown.length) return nothing;
    return html`
      <div class="banner">
        ${shown.map(
          (warning) => html`<span>${formatWarning(warning, this.language)}</span>`,
        )}
      </div>
    `;
  }
}
