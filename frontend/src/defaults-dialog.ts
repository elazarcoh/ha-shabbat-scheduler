import { LitElement, css, html, nothing } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { t } from './strings';
import type { Defaults, Hass } from './types';
import './service-editor';
import './target-editor';

/**
 * The shared defaults: a target and a service payload every rule inherits
 * unless it sets its own.
 *
 * v1's editor was a device multi-select plus a climate settings form, and
 * it wrote `{devices, settings}`. `validate_defaults` (rule_schema.py) now
 * accepts exactly `{target, data}` - a Home Assistant target selector and
 * an opaque service payload - so the old form's save was already certain
 * to be rejected on every press, and the button was removed rather than
 * left broken.
 *
 * This composes the same two editors the rule dialog does
 * (target-editor.ts, service-editor.ts). Defaults carry no action - a
 * rule's action is always its own - so the service editor's `action` half
 * is tracked only so its own picker keeps showing what was last chosen,
 * and is dropped on save: sending one would be refused by
 * `validate_defaults`, which knows only `target` and `data`.
 */
@customElement('shabbat-defaults-dialog')
export class ShabbatDefaultsDialog extends LitElement {
  /**
   * Passed straight to the Home Assistant elements the editors embed.
   * Reassigned on every state change in the whole system, so nothing may
   * key draft-seeding off it - see `willUpdate`.
   */
  @property({ attribute: false }) hass: Hass | null = null;
  @property({ attribute: false }) defaults: Defaults = {};
  @property({ type: Boolean }) canWrite = false;
  @property({ type: Boolean }) busy = false;
  @property() error: string | null = null;
  @property() language = 'en';

  @state() private _draft: Defaults = {};
  /**
   * Not part of `_draft`: `Defaults` has no action key, and this is never
   * sent. It only keeps `<shabbat-service-editor>`'s own picker showing
   * whatever service was last chosen, across re-renders of this dialog.
   */
  @state() private _action = '';
  private _seeded = false;

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
    h2 { margin-block: 0 4px; font-size: 1.1em; }
    .note { color: var(--secondary-text-color, #666); font-size: 0.85em; }
    .error { color: var(--error-color, #d64545); margin-block: 8px; font-size: 0.9em; }
    .section { margin-block: 12px; }
    .section .label { color: var(--secondary-text-color, #666); font-size: 0.85em; margin-block-end: 4px; }
    .actions {
      display: flex;
      gap: 8px;
      justify-content: flex-end;
      margin-block-start: 16px;
    }
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
  `;

  override willUpdate() {
    // Seed the draft once for this dialog's whole lifetime. `card.ts`
    // mounts a fresh `<shabbat-defaults-dialog>` only while `_defaultsOpen`
    // is true and unmounts it on close - unlike the rule dialog, this
    // component never gets handed a second, different thing to edit while
    // it stays mounted, so "once per open" and "once ever for this
    // instance" are the same fact here. Re-seeding on every update would
    // throw away what the user has typed each time a push arrives, and
    // pushes arrive constantly, since `hass` is reassigned on every state
    // change in the whole system.
    if (!this._seeded) {
      this._seeded = true;
      this._draft = {
        target: this.defaults.target ?? {},
        data: this.defaults.data ?? {},
      };
    }
  }

  private _onSave() {
    this.dispatchEvent(new CustomEvent('dialog-save', {
      detail: {
        defaults: {
          target: this._draft.target ?? {},
          data: this._draft.data ?? {},
        },
      },
    }));
  }

  override render() {
    return html`
      <div class="sheet" @click=${(event: Event) => {
        if (event.target === event.currentTarget) {
          this.dispatchEvent(new CustomEvent('dialog-close'));
        }
      }}>
        <div class="panel">
          <h2>${t(this.language, 'defaults_title')}</h2>
          <div class="note">${t(this.language, 'defaults_help')}</div>
          ${this.error !== null
            ? html`<div class="error">${this.error}</div>`
            : nothing}

          <div class="form">
            <div class="section">
              <div class="label">${t(this.language, 'target')}</div>
              <shabbat-target-editor
                .hass=${this.hass}
                .value=${this._draft.target ?? {}}
                .disabled=${!this.canWrite}
                .language=${this.language}
                @target-changed=${(event: CustomEvent) => {
                  this._draft = { ...this._draft, target: event.detail.value };
                }}
              ></shabbat-target-editor>
            </div>
            <div class="section">
              <div class="label">${t(this.language, 'data')}</div>
              <shabbat-service-editor
                .hass=${this.hass}
                .action=${this._action}
                .data=${this._draft.data ?? {}}
                .disabled=${!this.canWrite}
                @service-changed=${(event: CustomEvent) => {
                  this._action = event.detail.action;
                  this._draft = { ...this._draft, data: event.detail.data };
                }}
              ></shabbat-service-editor>
            </div>
          </div>

          <div class="actions">
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
    `;
  }
}
