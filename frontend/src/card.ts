import { LitElement, css, html, nothing } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import './block-header';
import './day-group';
import './warnings';
import { buildGroups } from './format';
import { t } from './strings';
import type { CardState } from './types';
import { CARD_VERSION } from './version';

interface CardConfig {
  type?: string;
  title?: string;
}

@customElement('shabbat-scheduler-card')
export class ShabbatSchedulerCard extends LitElement {
  @state() private _state: CardState | null = null;
  @state() private _error: string | null = null;
  @property({ attribute: false }) private _config: CardConfig = {};

  private _hass: any;
  private _unsubscribe: (() => Promise<void>) | null = null;
  private _subscribed = false;

  static override styles = css`
    ha-card { padding: 16px; }
    .title { font-size: 1.1em; font-weight: 600; margin-block-end: 8px; }
    .message { color: var(--secondary-text-color, #666); padding-block: 8px; }
  `;

  setConfig(config: CardConfig) {
    this._config = config ?? {};
  }

  getCardSize() {
    return 3 + (this._state?.rules.length ?? 0);
  }

  static getStubConfig() {
    return { type: 'custom:shabbat-scheduler-card' };
  }

  set hass(hass: any) {
    this._hass = hass;
    // Subscribe exactly once. Home Assistant reassigns `hass` on every
    // state change in the whole system; subscribing per assignment would
    // open a subscription per tick.
    if (!this._subscribed) {
      this._subscribed = true;
      void this._subscribe();
    }
  }

  get hass() {
    return this._hass;
  }

  private async _subscribe() {
    try {
      this._unsubscribe = await this._hass.connection.subscribeMessage(
        (payload: CardState) => {
          this._state = payload;
          this._error = null;
        },
        { type: 'shabbat_scheduler/subscribe' },
      );
    } catch (err) {
      this._error = String(err);
    }
  }

  override disconnectedCallback() {
    super.disconnectedCallback();
    void this._unsubscribe?.();
    this._unsubscribe = null;
    this._subscribed = false;
  }

  private get _language(): string {
    return this._hass?.locale?.language ?? 'en';
  }

  private get _canWrite(): boolean {
    // 2a made reads open and every mutator require_admin. Offering a
    // control that is certain to fail is worse than not offering it.
    return this._hass?.user?.is_admin === true;
  }

  private _onMaster = (event: Event) => {
    const { enabled } = (event as CustomEvent).detail;
    const entityId = this._state?.master_entity_id;
    if (!entityId) return;
    void this._hass.callService(
      'switch',
      enabled ? 'turn_on' : 'turn_off',
      { entity_id: entityId },
    );
  };

  private _onDryRun = (event: Event) => {
    const { dryRun } = (event as CustomEvent).detail;
    void this._hass.callService('shabbat_scheduler', 'set_dry_run', {
      enabled: dryRun,
    });
  };

  override render() {
    if (this._error !== null) {
      return html`
        <ha-card>
          <div class="message">${t(this._language, 'not_set_up')}</div>
        </ha-card>
      `;
    }
    if (this._state === null) {
      return html`<ha-card><div class="message">…</div></ha-card>`;
    }

    const groups = buildGroups(this._state);
    // The ids of every rule actually rendered on screen right now - only
    // rules matching the block's current profile length, per buildGroups.
    // `unattachedWarnings` (used inside <shabbat-warnings>) needs this
    // exact set: without it, a conflict on a displayed rule would render
    // twice (once on its row, once in the banner), and worse, a conflict
    // naming only rules from another profile would never render at all.
    const displayedRuleIds = groups.flatMap((group) =>
      group.rules.map((rule) => rule.id),
    );

    return html`
      <ha-card>
        ${this._config.title
          ? html`<div class="title">${this._config.title}</div>`
          : nothing}
        <shabbat-block-header
          .block=${this._state.block}
          .enabled=${this._state.enabled}
          .dryRun=${this._state.dry_run}
          .canWrite=${this._canWrite}
          .masterEntityId=${this._state.master_entity_id}
          .language=${this._language}
          @shabbat-master-toggle=${this._onMaster}
          @shabbat-dry-run-toggle=${this._onDryRun}
        ></shabbat-block-header>
        <shabbat-warnings
          .warnings=${this._state.warnings}
          .displayedRuleIds=${displayedRuleIds}
          .language=${this._language}
        ></shabbat-warnings>
        ${groups.map(
          (group) => html`
            <shabbat-day-group
              .group=${group}
              .defaults=${this._state!.defaults}
              .warnings=${this._state!.warnings}
              .language=${this._language}
            ></shabbat-day-group>
          `,
        )}
      </ha-card>
    `;
  }
}

(window as any).customCards = (window as any).customCards ?? [];
(window as any).customCards.push({
  type: 'shabbat-scheduler-card',
  name: 'Shabbat Scheduler',
  description: 'The coming Shabbat or Chag as a timeline.',
});

console.info(`shabbat-scheduler-card ${CARD_VERSION}`);
