import { LitElement, css, html, nothing } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import './block-header';
import './day-group';
import './warnings';
import './rule-dialog';
import './defaults-dialog';
import { buildGroups, formToChanges, formToCreate, isPreview } from './format';
import { t } from './strings';
import type { CardState, DayGroup, RuleData, RuleFormState } from './types';
import { CARD_VERSION } from './version';

interface CardConfig {
  type?: string;
  title?: string;
}

/**
 * The only failure the server states as a fact: `ws_subscribe`
 * (websocket_api.py) answers exactly this code when no config entry is
 * loaded. Everything else - a closed socket, a timeout, or core's
 * `unknown_command` because this integration has not registered its
 * command yet during Home Assistant startup - is transient. Calling a
 * transient failure "not configured" is a lie a wall tablet cannot
 * recover from without a page reload, on the one day nobody can operate
 * anything by hand.
 */
const NOT_SET_UP = 'not_set_up';

function isNotSetUp(error: unknown): boolean {
  // home-assistant-js-websocket rejects with a plain `{code, message}`
  // object, so `code` is the reliable signal; the `message` fallback is
  // for a thrown Error, which carries no code.
  const code = (error as { code?: unknown } | null | undefined)?.code;
  if (typeof code === 'string') return code === NOT_SET_UP;
  const message = (error as { message?: unknown } | null | undefined)?.message;
  return typeof message === 'string' && message.includes(NOT_SET_UP);
}

@customElement('shabbat-scheduler-card')
export class ShabbatSchedulerCard extends LitElement {
  @state() private _state: CardState | null = null;
  /**
   * `not_set_up` only when the server said so; `stale` when the card
   * could not reach the server at all (a failed subscribe attempt);
   * `command_failed` when it reached the server and the server refused
   * the call. All three leave the last state on screen and nothing else
   * changed, but they are three different things to go and check, and
   * telling someone the connection is lost when it plainly is not sends
   * them to the wrong place.
   */
  @state() private _error: 'not_set_up' | 'stale' | 'command_failed' | null =
    null;
  @property({ attribute: false }) private _config: CardConfig = {};

  @state() private _selectedProfile: number | null = null;
  @state() private _editing: RuleData | null = null;
  @state() private _creatingDay: string | null = null;
  @state() private _defaultsOpen = false;
  @state() private _dialogError: string | null = null;
  @state() private _busy = false;
  @state() private _duplicateSeed: RuleFormState | null = null;

  private _hass: any;
  private _unsubscribe: (() => Promise<void>) | null = null;
  private _subscribed = false;
  /**
   * Bumped on every detach. An in-flight `_subscribe` compares the value
   * it captured against this one, so a subscription that resolves onto a
   * detached card is torn down instead of being stored where nothing
   * will ever call it. Lovelace moves cards in the DOM on every
   * edit-mode and view switch, so a leak here accumulates for the life
   * of the page.
   */
  private _generation = 0;

  static override styles = css`
    ha-card { padding: 16px; }
    .title { font-size: 1.1em; font-weight: 600; margin-block-end: 8px; }
    .message { color: var(--secondary-text-color, #666); padding-block: 8px; }
    .notice { color: var(--warning-color, #d9822b); }
    .preview {
      background: var(--secondary-background-color, #f4f4f4);
      border-inline-start: 3px solid var(--primary-color, #03a9f4);
      padding-block: 8px;
      padding-inline: 12px;
      margin-block: 8px;
      font-size: 0.9em;
    }
  `;

  setConfig(config: CardConfig) {
    this._config = config ?? {};
  }

  getCardSize() {
    // The rules actually drawn, not every rule in every profile: a
    // 3-day chag's rules are not on screen during a plain Shabbat.
    return (
      3 + this._groups.reduce((total, group) => total + group.rules.length, 0)
    );
  }

  static getStubConfig() {
    return { type: 'custom:shabbat-scheduler-card' };
  }

  set hass(hass: any) {
    // Only a change to something this card renders from is worth a
    // re-render. Home Assistant reassigns `hass` on every state change
    // in the whole system, and re-rendering on each would be its own
    // bug - but never re-rendering means a language switch, or a
    // `hass.user` that was not there at mount, never reaches the view.
    const language = this._language;
    const canWrite = this._canWrite;
    this._hass = hass;
    if (this._language !== language || this._canWrite !== canWrite) {
      this.requestUpdate();
    }

    this._ensureSubscribed();
  }

  get hass() {
    return this._hass;
  }

  /**
   * Subscribe once, and never treat a failure as terminal: `_subscribe`
   * clears `_subscribed` when an attempt fails, so the next `hass`
   * assignment tries again. The flag stays set for the whole in-flight
   * attempt, so a broken server gets one attempt per assignment and
   * never a tight loop.
   */
  private _ensureSubscribed() {
    if (this._subscribed || !this._hass || !this.isConnected) return;
    this._subscribed = true;
    void this._subscribe();
  }

  private async _subscribe() {
    const generation = this._generation;
    try {
      const unsubscribe = await this._hass.connection.subscribeMessage(
        (payload: CardState) => {
          if (generation !== this._generation) return;
          // A tapped chip is honest (the preview banner says so) and
          // recoverable (tap the matching chip again) - but a wall
          // dashboard left on, say, 3d must not stay in preview once the
          // coming block is actually a 3-day Chag. Reset only when the
          // length itself changes, not on every push - a push is every
          // state change in the whole system, and resetting on each would
          // throw away a deliberate preview choice mid-use.
          if (this._state?.block?.length !== payload.block?.length) {
            this._selectedProfile = null;
          }
          this._state = payload;
          this._error = null;
        },
        { type: 'shabbat_scheduler/subscribe' },
      );
      if (generation !== this._generation || !this.isConnected) {
        // Detached while this was in flight. The card that asked for
        // this subscription is gone and nothing would ever call this
        // unsubscribe, so call it here.
        void this._teardown(unsubscribe);
        return;
      }
      this._unsubscribe = unsubscribe;
    } catch (error) {
      if (generation !== this._generation) return;
      this._error = isNotSetUp(error) ? 'not_set_up' : 'stale';
      this._subscribed = false;
    }
  }

  /** Unsubscribing from an already-closed socket is not an error. */
  private async _teardown(unsubscribe: (() => Promise<void>) | null) {
    if (unsubscribe === null) return;
    try {
      await unsubscribe();
    } catch {
      // The socket is gone; there is nothing left to unsubscribe from.
    }
  }

  override connectedCallback() {
    super.connectedCallback();
    // Re-attached (a view switch, leaving edit mode): subscribe again
    // rather than sit dead until the next `hass` assignment.
    this._ensureSubscribed();
  }

  override disconnectedCallback() {
    super.disconnectedCallback();
    this._generation += 1;
    const unsubscribe = this._unsubscribe;
    this._unsubscribe = null;
    this._subscribed = false;
    void this._teardown(unsubscribe);
  }

  private get _language(): string {
    return this._hass?.locale?.language ?? 'en';
  }

  private get _canWrite(): boolean {
    // 2a made reads open and every mutator require_admin. Offering a
    // control that is certain to fail is worse than not offering it.
    return this._hass?.user?.is_admin === true;
  }

  /** The selected profile, defaulting to the coming block's length. */
  private get _profile(): number {
    return this._selectedProfile ?? this._state?.block?.length ?? 1;
  }

  /**
   * The day groups actually rendered, and `[]` for any payload this card
   * cannot draw. Total on purpose: `render` and `getCardSize` both go
   * through here, and Lovelace calls `getCardSize` while laying a view
   * out, where a throw takes the whole view down with it.
   */
  private get _groups(): DayGroup[] {
    const state = this._state;
    if (state === null || !Array.isArray(state.rules)) return [];
    return buildGroups(state, this._profile);
  }

  private _onMaster = (event: Event) => {
    const { enabled } = (event as CustomEvent).detail;
    const entityId = this._state?.master_entity_id;
    if (!entityId) return;
    void this._call('switch', enabled ? 'turn_on' : 'turn_off', {
      entity_id: entityId,
    });
  };

  private _onDryRun = (event: Event) => {
    const { dryRun } = (event as CustomEvent).detail;
    void this._call('shabbat_scheduler', 'set_dry_run', { enabled: dryRun });
  };

  /**
   * A write that fails has to say so. Nothing here is optimistic - the
   * controls only ever show what the server pushed - so a swallowed
   * rejection is a control that visibly does nothing with no
   * explanation, which is this system's cardinal sin. The notice clears
   * itself on the next push, i.e. as soon as a write does land.
   *
   * `command_failed`, not `stale`: reaching this catch means the socket
   * carried the call and the server answered with a rejection - the
   * entity was unavailable, the service errored, permission was refused.
   * Reporting that as "connection lost" is a wrong diagnosis, and on the
   * one day nobody can operate anything by hand it sends the household
   * to check the network instead of the appliance.
   */
  private async _call(domain: string, service: string, data: object) {
    try {
      await this._hass.callService(domain, service, data);
    } catch {
      this._error = 'command_failed';
    }
  }

  /**
   * A websocket command, with its rejection surfaced.
   *
   * Nothing here is optimistic: the dialog closes only after the server
   * accepts, and the redraw comes from the following push. On rejection
   * the dialog stays open carrying the server's own message, because
   * `rule_schema.py` owns validation and its wording is the truth.
   */
  private async _send(message: object): Promise<boolean> {
    this._busy = true;
    this._dialogError = null;
    try {
      await this._hass.callWS(message);
      return true;
    } catch (err) {
      const detail = err as { message?: string } | null;
      this._dialogError = detail?.message ?? String(err);
      return false;
    } finally {
      this._busy = false;
    }
  }

  private _closeDialogs = () => {
    this._editing = null;
    this._creatingDay = null;
    this._duplicateSeed = null;
    this._defaultsOpen = false;
    this._dialogError = null;
  };

  private _onRuleOpen = (event: Event) => {
    this._editing = (event as CustomEvent).detail.rule as RuleData;
    this._creatingDay = null;
    this._duplicateSeed = null;
    this._dialogError = null;
  };

  private _onRuleAdd = (event: Event) => {
    this._creatingDay = (event as CustomEvent).detail.day as string;
    this._editing = null;
    this._duplicateSeed = null;
    this._dialogError = null;
  };

  private _onSave = async (event: Event) => {
    const { form, rule } = (event as CustomEvent).detail as {
      form: RuleFormState;
      rule: RuleData | null;
    };
    const ok =
      rule === null
        ? await this._send({
            type: 'shabbat_scheduler/rules/create',
            rule: formToCreate(form, this._profile),
          })
        : await this._saveChanges(form, rule);
    if (ok) this._closeDialogs();
  };

  private async _saveChanges(form: RuleFormState, rule: RuleData) {
    // Always a round trip, even for an empty diff: the dialog cannot
    // know locally whether the server will accept the save, and a
    // client-side skip here would mean "nothing changed" quietly wins
    // over a rejection the server would otherwise have raised.
    //
    // `rule` is the snapshot taken when the dialog opened (`_editing`),
    // NOT the latest pushed copy, and that is deliberate. If another
    // client edits the same rule while this dialog is open, the diff
    // basis is stale - but every key the diff emits still carries exactly
    // the value the form is showing, so the write itself can never be
    // wrong. Diffing against the fresh copy instead would turn "a field
    // the user can see was not sent" into "a field the user never touched
    // silently overwrites what the other client just saved", which is
    // strictly worse on a system where nobody can undo it by hand.
    // Reseeding the form from the push is worse still: it discards what
    // the user has typed, and pushes arrive on every state change in the
    // whole system. Staying conservative is the correct trade.
    return this._send({
      type: 'shabbat_scheduler/rules/update',
      rule_id: rule.id,
      changes: formToChanges(form, rule),
    });
  }

  private _onDelete = async (event: Event) => {
    const { rule } = (event as CustomEvent).detail as { rule: RuleData };
    if (await this._send({
      type: 'shabbat_scheduler/rules/delete',
      rule_id: rule.id,
    })) {
      this._closeDialogs();
    }
  };

  private _onDuplicate = (event: Event) => {
    // Composed client-side from rules/create: the dialog reopens as a
    // CREATE carrying the same values, so the user can move it before
    // saving. The server generates the id, so no rules/duplicate command
    // is needed. `_duplicateSeed` must be reactive and must be passed to
    // the dialog's `seed` property - without that the dialog reseeds from
    // EMPTY_FORM and a duplicate duplicates nothing.
    const { form } = (event as CustomEvent).detail as { form: RuleFormState };
    this._editing = null;
    this._creatingDay = form.day;
    this._duplicateSeed = form;
    this._dialogError = null;
  };

  /**
   * Same shape as `_onSave`: a plain websocket round trip, nothing
   * optimistic. `validate_defaults` (rule_schema.py) owns whether the
   * `{target, data}` the dialog emits is acceptable, so a rejection lands
   * in `_dialogError` and the dialog stays open exactly like a rule save's
   * does.
   */
  private _onDefaultsSave = async (event: Event) => {
    const { defaults } = (event as CustomEvent).detail as {
      defaults: CardState['defaults'];
    };
    if (await this._send({
      type: 'shabbat_scheduler/defaults/update',
      defaults,
    })) {
      this._closeDialogs();
    }
  };

  override render() {
    // Read once into a local: `_error` is a field, and TypeScript's
    // narrowing of a property access does not survive the intervening
    // calls below, so the notice branch would lose the type that makes
    // it a valid string key.
    const error = this._error;
    if (error === 'not_set_up') {
      return html`
        <ha-card>
          <div class="message">${t(this._language, 'not_set_up')}</div>
        </ha-card>
      `;
    }
    if (this._state === null) {
      return html`
        <ha-card>
          <div class="message">
            ${error === null ? '…' : t(this._language, error)}
          </div>
        </ha-card>
      `;
    }

    const groups = this._groups;
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
      <ha-card @rule-open=${this._onRuleOpen}>
        ${this._config.title
          ? html`<div class="title">${this._config.title}</div>`
          : nothing}
        ${error !== null
          ? html`<div class="message notice">${t(this._language, error)}</div>`
          : nothing}
        <shabbat-block-header
          .block=${this._state.block}
          .enabled=${this._state.enabled}
          .dryRun=${this._state.dry_run}
          .canWrite=${this._canWrite}
          .masterEntityId=${this._state.master_entity_id}
          .selectedProfile=${this._profile}
          .language=${this._language}
          @shabbat-master-toggle=${this._onMaster}
          @shabbat-dry-run-toggle=${this._onDryRun}
          @profile-selected=${(event: Event) => {
            this._selectedProfile = (event as CustomEvent).detail.profile;
          }}
          @defaults-open=${() => { this._defaultsOpen = true; }}
        ></shabbat-block-header>
        ${isPreview(this._state, this._profile)
          ? html`<div class="preview">${t(this._language, 'preview_banner')}</div>`
          : nothing}
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
              .canWrite=${this._canWrite}
              @rule-add=${this._onRuleAdd}
            ></shabbat-day-group>
          `,
        )}
        ${this._editing !== null || this._creatingDay !== null
          ? html`<shabbat-rule-dialog
              .hass=${this._hass}
              .rule=${this._editing}
              .seed=${this._duplicateSeed}
              .day=${this._creatingDay ?? this._editing?.day ?? 'erev'}
              .profile=${this._profile}
              .defaults=${this._state.defaults}
              .canWrite=${this._canWrite}
              .busy=${this._busy}
              .error=${this._dialogError}
              .language=${this._language}
              @dialog-save=${this._onSave}
              @dialog-delete=${this._onDelete}
              @dialog-duplicate=${this._onDuplicate}
              @dialog-close=${this._closeDialogs}
            ></shabbat-rule-dialog>`
          : nothing}
        ${this._defaultsOpen
          ? html`<shabbat-defaults-dialog
              .hass=${this._hass}
              .defaults=${this._state.defaults}
              .canWrite=${this._canWrite}
              .busy=${this._busy}
              .error=${this._dialogError}
              .language=${this._language}
              @dialog-save=${this._onDefaultsSave}
              @dialog-close=${this._closeDialogs}
            ></shabbat-defaults-dialog>`
          : nothing}
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
