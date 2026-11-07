import { LitElement, css, html, nothing } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
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
import type { Defaults, Hass, RuleData, WarningData } from './types';

@customElement('shabbat-rule-row')
export class ShabbatRuleRow extends LitElement {
  @property({ attribute: false }) hass: Hass | null = null;
  @property({ attribute: false }) rule!: RuleData;
  @property({ attribute: false }) defaults: Defaults = {};
  @property({ attribute: false }) warnings: WarningData[] = [];
  @property({ type: Boolean }) canWrite = false;
  @property() toggleError: string | null = null;
  @property() language = 'en';

  /** Where the row menu is open, in viewport pixels; null when closed. */
  @state() private _menu: { x: number; y: number } | null = null;
  private _pressTimer: ReturnType<typeof setTimeout> | null = null;
  private _pressStart: { x: number; y: number } | null = null;
  /** A long press just opened the menu: swallow the click that follows. */
  private _suppressClick = false;

  /** How long a touch must be held to open the menu. */
  static LONG_PRESS_MS = 500;

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
    /* A rule with no name has no .title to caption, so .brief takes
       over its exact look instead of staying a small, grey second line
       with nothing above it to be second TO. Same text either way -
       only a rule's own name changes which class it renders in. */
    .brief.promoted {
      color: inherit;
      font-size: 1em;
      font-weight: 500;
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
    .row-toggle { flex: none; }
    .row-error {
      color: var(--error-color, #c62828);
      font-size: 0.85em;
      overflow-wrap: anywhere;
      margin-block-start: 2px;
    }
    .row { cursor: pointer; }
    .row:focus-visible { outline: 2px solid var(--primary-color, #03a9f4); outline-offset: -2px; }
    /* Below 600px, .body's children (title, brief, last-outcome,
       conflict-detail) become direct flex items of .row via
       display: contents - the same unwrap trick rule-dialog.ts's
       .advanced class already uses, for the same reason: only that lets
       .title stay on the row's first line, next to the dot and time,
       while .brief/.last-outcome/.conflict-detail wrap onto their
       own full-width lines below. .body itself has no visual box (no
       padding/border/background), so nothing is lost by unwrapping it. */
    /* A long press on a touch screen must open OUR menu, not select the
       row's text or pop the browser's own callout. */
    .row { -webkit-touch-callout: none; user-select: none; -webkit-user-select: none; }
    .menu-backdrop { position: fixed; inset: 0; z-index: 9; }
    .menu {
      position: fixed;
      z-index: 10;
      min-inline-size: 9em;
      background: var(--card-background-color, #fff);
      color: var(--primary-text-color, #111);
      border: 1px solid var(--divider-color, #e0e0e0);
      border-radius: 8px;
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
      padding-block: 4px;
    }
    .menu button {
      display: block;
      inline-size: 100%;
      font: inherit;
      text-align: start;
      background: none;
      border: none;
      color: inherit;
      padding-block: 10px;
      padding-inline: 16px;
      cursor: pointer;
    }
    .menu button:hover { background: var(--secondary-background-color, #f4f4f4); }
    .menu .menu-delete { color: var(--error-color, #c62828); }
    @media (max-width: 599px) {
      .row { flex-wrap: wrap; row-gap: 4px; }
      .body { display: contents; }
      .brief, .last-outcome, .conflict-detail { flex-basis: 100%; }
    }
  `;

  override disconnectedCallback() {
    super.disconnectedCallback();
    this._cancelPress();
  }

  private _openMenu(x: number, y: number) {
    if (!this.canWrite) return;
    // Keep the menu on screen near the pointer: it is ~10em wide and two
    // items tall, so pull it back from the right and bottom edges.
    const maxX = Math.max(0, window.innerWidth - 180);
    const maxY = Math.max(0, window.innerHeight - 110);
    this._menu = { x: Math.min(x, maxX), y: Math.min(y, maxY) };
  }

  private _closeMenu() {
    this._menu = null;
  }

  private _cancelPress() {
    if (this._pressTimer !== null) clearTimeout(this._pressTimer);
    this._pressTimer = null;
    this._pressStart = null;
  }

  /**
   * Touch only. A mouse already has right-click (`contextmenu`), and
   * Android Chrome fires `contextmenu` on a long press too - but iOS
   * Safari never does, so the timer is what makes it work on an iPad.
   * Both paths just set `_menu`, so a browser that fires both opens it
   * once.
   */
  private _onPointerDown(event: PointerEvent) {
    if (!this.canWrite || event.pointerType === 'mouse') return;
    this._cancelPress();
    this._pressStart = { x: event.clientX, y: event.clientY };
    this._pressTimer = setTimeout(() => {
      const start = this._pressStart;
      this._pressTimer = null;
      if (start === null) return;
      this._suppressClick = true;
      this._openMenu(start.x, start.y);
    }, ShabbatRuleRow.LONG_PRESS_MS);
  }

  private _onPointerMove(event: PointerEvent) {
    // A scroll, not a hold.
    const start = this._pressStart;
    if (start === null) return;
    if (Math.abs(event.clientX - start.x) > 10 || Math.abs(event.clientY - start.y) > 10) {
      this._cancelPress();
    }
  }

  private _onContextMenu(event: MouseEvent) {
    if (!this.canWrite) return;
    event.preventDefault();
    this._cancelPress();
    this._openMenu(event.clientX, event.clientY);
  }

  private _onRowClick() {
    if (this._suppressClick) {
      this._suppressClick = false;
      return;
    }
    this._open();
  }

  private _delete() {
    this._closeMenu();
    this.dispatchEvent(
      new CustomEvent('rule-delete', {
        detail: { rule: this.rule },
        bubbles: true,
        composed: true,
      }),
    );
  }

  private _renderMenu() {
    if (this._menu === null) return nothing;
    return html`<div class="menu-layer">
      <div
        class="menu-backdrop"
        @click=${(event: Event) => { event.stopPropagation(); this._closeMenu(); }}
        @contextmenu=${(event: Event) => { event.preventDefault(); this._closeMenu(); }}
      ></div>
      <div
        class="menu"
        role="menu"
        style="left:${this._menu.x}px;top:${this._menu.y}px"
      >
        <button
          class="menu-edit"
          role="menuitem"
          @click=${(event: Event) => { event.stopPropagation(); this._closeMenu(); this._open(); }}
        >${t(this.language, 'edit_rule')}</button>
        <button
          class="menu-delete"
          role="menuitem"
          @click=${(event: Event) => { event.stopPropagation(); this._delete(); }}
        >${t(this.language, 'delete_rule')}</button>
      </div>
    </div>`;
  }

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
      <div class="row-wrap">
      <div
        class="row ${this.rule.enabled ? '' : 'disabled'}"
        tabindex="0"
        role="button"
        @click=${() => this._onRowClick()}
        @contextmenu=${(event: MouseEvent) => this._onContextMenu(event)}
        @pointerdown=${(event: PointerEvent) => this._onPointerDown(event)}
        @pointermove=${(event: PointerEvent) => this._onPointerMove(event)}
        @pointerup=${() => this._cancelPress()}
        @pointercancel=${() => this._cancelPress()}
        @pointerleave=${() => this._cancelPress()}
        @keydown=${(event: KeyboardEvent) => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            this._open();
          } else if (event.key === 'ContextMenu' || (event.shiftKey && event.key === 'F10')) {
            event.preventDefault();
            const box = (event.currentTarget as HTMLElement).getBoundingClientRect();
            this._openMenu(box.left + 16, box.top + box.height / 2);
          }
        }}
      >
        ${this.canWrite
          ? html`<ha-selector
              class="row-toggle"
              .hass=${this.hass}
              .selector=${{ boolean: {} }}
              .value=${this.rule.enabled}
              @click=${(event: Event) => event.stopPropagation()}
              @keydown=${(event: Event) => event.stopPropagation()}
              @value-changed=${() => {
                this.dispatchEvent(
                  new CustomEvent('rule-toggle-enabled', {
                    detail: { rule: this.rule },
                    bubbles: true,
                    composed: true,
                  }),
                );
              }}
            ></ha-selector>`
          : nothing}
        <span class="dot" style="background:${ruleColour(this.rule)}"></span>
        <span class="time">${this.rule.time.slice(0, 5)}</span>
        <div class="body">
          ${title ? html`<div class="title">${title}</div>` : nothing}
          <div class="brief ${title ? '' : 'promoted'}">
            ${ruleBrief(this.rule, this.defaults, this.hass)}
          </div>
          ${this.toggleError !== null
            ? html`<div class="row-error">${this.toggleError}</div>`
            : nothing}
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
      ${this._renderMenu()}
      </div>
    `;
  }
}
