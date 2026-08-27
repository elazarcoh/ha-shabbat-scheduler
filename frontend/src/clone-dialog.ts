import { LitElement, css, html, nothing } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { t } from './strings';
import type { RuleData } from './types';

export interface CloneOpenDetail {
  scope: 'day' | 'profile';
  profile: number;
  day?: string;
}

function daysFor(length: number): string[] {
  const days = ['erev'];
  for (let i = 1; i <= length; i += 1) days.push(String(i));
  return days;
}

@customElement('shabbat-clone-dialog')
export class ShabbatCloneDialog extends LitElement {
  @property({ attribute: false }) source: CloneOpenDetail | null = null;
  @property({ attribute: false }) rules: RuleData[] = [];
  @property({ type: Boolean }) busy = false;
  @property() error: string | null = null;
  @property({ attribute: false }) landed: string[] | null = null;
  @property({ attribute: false }) failed: string[] | null = null;
  @property() language = 'en';

  @state() private _targetProfile = 1;
  @state() private _targetDay = 'erev';
  @state() private _mode: 'extend' | 'overwrite' = 'extend';
  private _seeded: string | null = null;

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
    .field label { min-inline-size: 7em; }
    select { font: inherit; padding-block: 4px; padding-inline: 6px; flex: 1; }
    .warning { color: var(--warning-color, #d9822b); margin-block: 8px; font-size: 0.9em; }
    .error { color: var(--error-color, #d64545); margin-block: 8px; font-size: 0.9em; }
    .report { font-size: 0.85em; margin-block: 8px; }
    .actions {
      display: flex; gap: 8px; justify-content: flex-end;
      margin-block-start: 16px; flex-wrap: wrap;
    }
    button {
      font: inherit; padding-block: 6px; padding-inline: 12px;
      border-radius: 6px; border: 1px solid var(--divider-color, #e0e0e0);
      background: var(--card-background-color, #fff); color: inherit; cursor: pointer;
    }
    button[disabled] { opacity: 0.5; cursor: not-allowed; }
    button.mode.active {
      background: var(--primary-color, #03a9f4);
      color: var(--text-primary-color, #fff); border-color: transparent;
    }
  `;

  override willUpdate() {
    const key = this.source
      ? `${this.source.scope}:${this.source.profile}:${this.source.day ?? ''}`
      : null;
    if (key !== this._seeded) {
      this._seeded = key;
      this._targetProfile = this.source?.profile ?? 1;
      this._targetDay = this.source?.day ?? 'erev';
      this._mode = 'extend';
    }
  }

  private get _dayScope(): boolean {
    return this.source?.scope === 'day';
  }

  private _sourceRuleIds(): string[] {
    if (this.source === null) return [];
    if (this._dayScope) {
      return this.rules
        .filter((r) => r.profile === this.source!.profile && r.day === this.source!.day)
        .map((r) => r.id);
    }
    return this.rules.filter((r) => r.profile === this.source!.profile).map((r) => r.id);
  }

  /**
   * What a confirm click actually sends. When `failed` carries a
   * non-empty remainder from a previous attempt, only that remainder is
   * re-attempted - re-sending the whole source set on retry would
   * re-create the rules that already landed, in extend mode as visible
   * duplicates. `failed === []` (a clean full-success report the caller
   * has not yet cleared) is not a remainder, so it falls through to the
   * full source set like `failed === null` does.
   */
  private _idsToSend(): string[] {
    if (this.failed !== null && this.failed.length > 0) return this.failed;
    return this._sourceRuleIds();
  }

  private _targetRuleCount(): number {
    if (this._dayScope) {
      return this.rules.filter(
        (r) => r.profile === this._targetProfile && r.day === this._targetDay,
      ).length;
    }
    return this.rules.filter((r) => r.profile === this._targetProfile).length;
  }

  private _title(): string {
    if (this.source === null) return '';
    if (this._dayScope) {
      const label = this.source.day === 'erev'
        ? t(this.language, 'erev') : `${t(this.language, 'day')} ${this.source.day}`;
      return `${t(this.language, 'clone_day_prefix')} ${label}`;
    }
    return `${t(this.language, 'clone_profile_prefix')} ${this.source.profile}${t(this.language, 'clone_profile_suffix')}`;
  }

  private _onConfirm() {
    this.dispatchEvent(new CustomEvent('dialog-clone-confirm', {
      detail: {
        sourceRuleIds: this._idsToSend(),
        sourceProfile: this.source?.profile,
        sourceScope: this.source?.scope,
        targetProfile: this._targetProfile,
        targetDay: this._dayScope ? this._targetDay : undefined,
        mode: this._mode,
      },
    }));
  }

  override render() {
    if (this.source === null) return nothing;
    const empty = this._idsToSend().length === 0;
    const targetCount = this._targetRuleCount();
    return html`
      <div class="sheet" @click=${(event: Event) => {
        if (event.target === event.currentTarget) {
          this.dispatchEvent(new CustomEvent('dialog-close'));
        }
      }}>
        <div class="panel">
          <h2>${this._title()}</h2>
          ${this.error !== null ? html`<div class="error">${this.error}</div>` : nothing}
          ${this.landed !== null
            ? html`<div class="report">
                ${t(this.language, 'clone_landed')}: ${this.landed.join(', ') || t(this.language, 'clone_none')}
                ${this.failed && this.failed.length
                  ? html`<br />${t(this.language, 'clone_failed')}: ${this.failed.join(', ')}`
                  : nothing}
              </div>`
            : nothing}

          <div class="field">
            <label>${t(this.language, 'clone_target_profile')}</label>
            <select
              class="target-profile"
              .value=${String(this._targetProfile)}
              @change=${(event: Event) => {
                this._targetProfile = Number((event.target as HTMLSelectElement).value);
                // The previously-valid target day may no longer exist on a
                // shorter target profile (e.g. day '3' on a 1-day target) -
                // fall back to 'erev' rather than leave the select showing
                // a day this profile does not have.
                if (this._dayScope && !daysFor(this._targetProfile).includes(this._targetDay)) {
                  this._targetDay = 'erev';
                }
              }}
            >
              ${[1, 2, 3].map((p) => html`<option value=${p}>${p}d</option>`)}
            </select>
          </div>
          ${this._dayScope
            ? html`<div class="field">
                <label>${t(this.language, 'clone_target_day')}</label>
                <select
                  class="target-day"
                  .value=${this._targetDay}
                  @change=${(event: Event) => {
                    this._targetDay = (event.target as HTMLSelectElement).value;
                  }}
                >
                  ${daysFor(this._targetProfile).map(
                    (day) => html`<option value=${day}>
                      ${day === 'erev' ? t(this.language, 'erev') : `${t(this.language, 'day')} ${day}`}
                    </option>`,
                  )}
                </select>
              </div>`
            : nothing}

          <div class="field">
            <button
              class="mode extend ${this._mode === 'extend' ? 'active' : ''}"
              @click=${() => { this._mode = 'extend'; }}
            >${t(this.language, 'clone_extend')}</button>
            <button
              class="mode overwrite ${this._mode === 'overwrite' ? 'active' : ''}"
              @click=${() => { this._mode = 'overwrite'; }}
            >${t(this.language, 'clone_overwrite')}</button>
          </div>

          ${targetCount > 0
            ? html`<div class="warning">${t(this.language, 'clone_target_has_rules')} ${targetCount}</div>`
            : nothing}

          <div class="actions">
            <button @click=${() => this.dispatchEvent(new CustomEvent('dialog-close'))}>
              ${t(this.language, 'cancel')}
            </button>
            <button
              class="confirm"
              ?disabled=${this.busy || empty}
              @click=${() => this._onConfirm()}
            >${t(this.language, 'clone_confirm')}</button>
          </div>
        </div>
      </div>
    `;
  }
}
