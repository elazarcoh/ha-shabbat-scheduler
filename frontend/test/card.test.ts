import { describe, expect, it, vi } from 'vitest';
import '../src/card';
import { ruleToForm } from '../src/format';
import type { CardState, RuleData } from '../src/types';
// The mount/subscribe mechanism lives in one place so that
// `payload-contract.test.ts` renders the same card this file does, rather
// than a second one that merely looks the same. See helpers.ts.
import {
  attach,
  fakeHass,
  flush,
  mount,
  ruleRows,
  type Card,
  type SubscribeFn,
  type Unsubscribe,
} from './helpers';

const EMPTY = {
  day: 'erev', time: '', action: 'climate.turn_on', target: {}, data: {},
  condition: [], replay: { enabled: false },
  name: null, icon: null, color: null, enabled: true,
};

const rule = (over: Partial<RuleData> = {}): RuleData => ({
  id: 'a', profile: 1, day: '1', time: '11:00:00',
  action: 'climate.turn_on',
  target: { entity_id: ['climate.salon'] },
  data: {}, condition: [], replay: { enabled: false },
  name: null, icon: null, enabled: true, color: null,
  last_outcome: null, ...over,
});

const state = (over: Partial<CardState> = {}): CardState => ({
  defaults: {}, rules: [], enabled: false, warnings: [],
  master_entity_id: 'switch.master',
  block: {
    length: 1,
    candle_lighting: '2026-08-14T18:44:00+03:00',
    havdalah: '2026-08-15T20:01:00+03:00',
    dates: { erev: '2026-08-14', '1': '2026-08-15' },
  },
  ...over,
});

describe('shabbat-scheduler-card', () => {
  it('subscribes once even when hass is reassigned repeatedly', async () => {
    const { hass } = fakeHass();
    const el = await mount(hass);
    el.hass = { ...hass };
    el.hass = { ...hass };
    await el.updateComplete;
    expect(hass.connection.subscribeMessage).toHaveBeenCalledOnce();
  });

  it('renders a day group per day once the state arrives', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(state());
    await el.updateComplete;
    expect(el.shadowRoot!.querySelectorAll('shabbat-day-group').length).toBe(2);
  });

  it('unsubscribes when removed from the document', async () => {
    const { hass, unsubscribe } = fakeHass();
    const el = await mount(hass);
    el.remove();
    await Promise.resolve();
    expect(unsubscribe).toHaveBeenCalledOnce();
  });

  it('calls switch.turn_on when the master control asks to enable', async () => {
    const { hass, send, callService } = fakeHass();
    const el = await mount(hass);
    send(state({ enabled: false }));
    await el.updateComplete;

    el.shadowRoot!
      .querySelector('shabbat-block-header')!
      .dispatchEvent(
        new CustomEvent('shabbat-master-toggle', { detail: { enabled: true } }),
      );

    expect(callService).toHaveBeenCalledWith('switch', 'turn_on', {
      entity_id: 'switch.master',
    });
  });

  it('does not update its own state from a control - only the push does', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(state({ enabled: false }));
    await el.updateComplete;

    el.shadowRoot!
      .querySelector('shabbat-block-header')!
      .dispatchEvent(
        new CustomEvent('shabbat-master-toggle', { detail: { enabled: true } }),
      );
    await el.updateComplete;

    const header = el.shadowRoot!.querySelector('shabbat-block-header') as any;
    expect(header.enabled).toBe(false);
  });

  it('renders the not-configured message when the subscription is refused', async () => {
    const { hass } = fakeHass();
    hass.connection.subscribeMessage = vi.fn(async () => {
      throw new Error('not_set_up');
    });
    const el = await mount(hass);
    await el.updateComplete;
    expect(el.shadowRoot!.textContent).toContain('not configured');
  });

  it('tells a read-only user it cannot write', async () => {
    const { hass, send } = fakeHass({ user: { is_admin: false } });
    const el = await mount(hass);
    send(state());
    await el.updateComplete;
    const header = el.shadowRoot!.querySelector('shabbat-block-header') as any;
    expect(header.canWrite).toBe(false);
  });

  // The known gap this task must close: `unattachedWarnings` only works if
  // the card passes the ids of the rules actually on screen. With the
  // default `[]`, a conflict on a displayed rule would render twice - once
  // on its row, once in the banner.
  it('shows a conflict on a displayed rule only on its row, not in the banner', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(
      state({
        rules: [
          rule({ id: 'a' }),
        ],
        warnings: [
          {
            kind: 'conflict', targets: ['climate.salon'], profile: 1, day: '1',
            time: '11:00:00', rule_ids: ['a'],
          },
        ],
      }),
    );
    await el.updateComplete;

    expect(el.shadowRoot!.querySelector('shabbat-warnings')!.shadowRoot!.querySelector('.banner')).toBeNull();
    expect((await ruleRows(el)).length).toBe(1);
  });

  it('shows a conflict on a non-displayed rule in the banner', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(
      state({
        rules: [],
        warnings: [
          {
            kind: 'conflict', targets: ['climate.salon'], profile: 3, day: '1',
            time: '11:00:00', rule_ids: ['not-shown'],
          },
        ],
      }),
    );
    await el.updateComplete;

    const warningsEl = el.shadowRoot!.querySelector('shabbat-warnings')!;
    const text = warningsEl.shadowRoot!.textContent!;
    expect(text).toContain('climate.salon');
  });

  // The case that tells `displayed` ids apart from `all` ids: the rule
  // EXISTS in state.rules but is not drawn, because its profile is not the
  // current block's length. Passing every id would mark this conflict
  // "attached" to a row that is not on screen and it would vanish entirely
  // - a conflict nobody can see, on the one day nobody can fix it by hand.
  it('shows a conflict on a rule from another profile in the banner', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(
      state({
        rules: [
          rule({ id: 'shown', profile: 1, day: '1' }),
          rule({ id: 'other-profile', profile: 3, day: '2', time: '09:00:00',
                 target: { entity_id: ['climate.mamad'] } }),
        ],
        warnings: [
          {
            kind: 'conflict', targets: ['climate.mamad'], profile: 3, day: '2',
            time: '09:00:00', rule_ids: ['other-profile'],
          },
        ],
      }),
    );
    await el.updateComplete;

    const warningsEl = el.shadowRoot!.querySelector('shabbat-warnings') as Card;
    await warningsEl.updateComplete;
    expect(warningsEl.shadowRoot!.querySelector('.banner')).not.toBeNull();
    expect(warningsEl.shadowRoot!.textContent).toContain('climate.mamad');
  });

  // ---- a failed first subscribe must not be terminal ----

  it('retries the subscription on a later hass assignment after a failure', async () => {
    const { hass, unsubscribe } = fakeHass();
    const subscribeMessage = vi.fn<SubscribeFn>(async () => unsubscribe);
    subscribeMessage.mockRejectedValueOnce({ code: 'unknown_command' });
    hass.connection.subscribeMessage = subscribeMessage;

    const el = await mount(hass);
    await flush();
    el.hass = { ...hass };
    await flush();
    await el.updateComplete;

    expect(subscribeMessage).toHaveBeenCalledTimes(2);
  });

  it('recovers its state once a retried subscription succeeds', async () => {
    const { hass, unsubscribe } = fakeHass();
    let push: ((s: CardState) => void) | null = null;
    const subscribeMessage = vi.fn<SubscribeFn>(async (cb) => {
      push = cb;
      return unsubscribe;
    });
    subscribeMessage.mockRejectedValueOnce({ code: 'unknown_command' });
    hass.connection.subscribeMessage = subscribeMessage;

    const el = await mount(hass);
    await flush();
    el.hass = { ...hass };
    await flush();
    push!(state());
    await el.updateComplete;

    expect(el.shadowRoot!.querySelectorAll('shabbat-day-group').length).toBe(2);
  });

  it('makes at most one attempt while a subscribe is still in flight', async () => {
    const { hass } = fakeHass();
    const subscribeMessage = vi.fn<SubscribeFn>(
      () => new Promise<Unsubscribe>(() => {}),
    );
    hass.connection.subscribeMessage = subscribeMessage;

    const el = attach(hass);
    for (let i = 0; i < 20; i += 1) el.hass = { ...hass };
    await flush();

    expect(subscribeMessage).toHaveBeenCalledTimes(1);
  });

  it('says the connection failed, not that nothing is configured', async () => {
    const { hass } = fakeHass();
    hass.connection.subscribeMessage = vi.fn<SubscribeFn>(async () => {
      throw { code: 'unknown_command', message: 'unknown command' };
    });

    const el = await mount(hass);
    await flush();
    await el.updateComplete;

    const text = el.shadowRoot!.textContent!;
    expect(text).toContain('Connection lost');
    expect(text).not.toContain('not configured');
  });

  it('says not configured when the server itself says not_set_up', async () => {
    const { hass } = fakeHass();
    hass.connection.subscribeMessage = vi.fn<SubscribeFn>(async () => {
      throw { code: 'not_set_up', message: 'Integration is not set up' };
    });

    const el = await mount(hass);
    await flush();
    await el.updateComplete;

    expect(el.shadowRoot!.textContent).toContain('not configured');
  });

  // ---- a subscription resolving after detach must be torn down ----

  it('tears down a subscription that resolves after the card was detached', async () => {
    const { hass, unsubscribe } = fakeHass();
    let resolve!: (u: Unsubscribe) => void;
    hass.connection.subscribeMessage = vi.fn<SubscribeFn>(
      () => new Promise<Unsubscribe>((r) => { resolve = r; }),
    );

    const el = attach(hass);
    el.remove();
    resolve(unsubscribe);
    await flush();

    expect(unsubscribe).toHaveBeenCalledOnce();
  });

  it('unsubscribes once and resubscribes once across a detach and re-attach', async () => {
    const { hass, unsubscribe } = fakeHass();
    const el = await mount(hass);

    el.remove();
    await flush();
    document.body.appendChild(el);
    await flush();
    await el.updateComplete;

    expect(unsubscribe).toHaveBeenCalledOnce();
    expect(hass.connection.subscribeMessage).toHaveBeenCalledTimes(2);
  });

  it('survives an unsubscribe that rejects on an already-closed socket', async () => {
    // Reached through globalThis: this repo has no @types/node and takes
    // no new dependencies, and a bare `process` will not typecheck.
    const proc = (globalThis as unknown as {
      process: {
        on(event: string, handler: (reason: unknown) => void): void;
        off(event: string, handler: (reason: unknown) => void): void;
      };
    }).process;
    const rejections: unknown[] = [];
    const onRejection = (reason: unknown) => rejections.push(reason);
    proc.on('unhandledRejection', onRejection);
    try {
      const { hass } = fakeHass();
      hass.connection.subscribeMessage = vi.fn<SubscribeFn>(async () => async () => {
        throw new Error('Connection lost');
      });
      const el = await mount(hass);
      el.remove();
      await flush();
      await flush();
    } finally {
      proc.off('unhandledRejection', onRejection);
    }
    expect(rejections).toEqual([]);
  });

  // ---- hass changes the card renders from must re-render ----

  it('re-renders when Home Assistant switches language', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(state());
    await el.updateComplete;

    el.hass = { ...hass, locale: { language: 'he' } };
    await el.updateComplete;

    const header = el.shadowRoot!.querySelector('shabbat-block-header') as Card;
    expect(header.language).toBe('he');
  });

  it('enables the controls as soon as hass.user arrives', async () => {
    const { hass, send } = fakeHass({ user: undefined });
    const el = await mount(hass);
    send(state());
    await el.updateComplete;
    const before = el.shadowRoot!.querySelector('shabbat-block-header') as Card;
    expect(before.canWrite).toBe(false);

    el.hass = { ...hass, user: { is_admin: true } };
    await el.updateComplete;

    const header = el.shadowRoot!.querySelector('shabbat-block-header') as Card;
    expect(header.canWrite).toBe(true);
  });

  it('does not schedule a re-render for an unrelated hass assignment', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(state());
    await el.updateComplete;

    el.hass = { ...hass, states: { 'light.salon': { state: 'on' } } };

    expect(el.isUpdatePending).toBe(false);
  });

  // ---- a write that fails must say so ----

  it('surfaces a service call that the server rejected', async () => {
    const { hass, send, callService } = fakeHass();
    callService.mockRejectedValueOnce(new Error('boom'));
    const el = await mount(hass);
    send(state({ enabled: false }));
    await el.updateComplete;

    el.shadowRoot!
      .querySelector('shabbat-block-header')!
      .dispatchEvent(
        new CustomEvent('shabbat-master-toggle', { detail: { enabled: true } }),
      );
    await flush();
    await el.updateComplete;

    // The server was reachable and refused the call. Reporting that as
    // "connection lost" is a wrong diagnosis: it sends the household to
    // check the network instead of the appliance, on the one day nobody
    // can operate anything by hand.
    expect(el.shadowRoot!.textContent).toContain('did not go through');
    expect(el.shadowRoot!.textContent).not.toContain('Connection lost');
    // and the card is still a card - the failure is a notice, not a wipe
    expect(el.shadowRoot!.querySelector('shabbat-block-header')).not.toBeNull();
  });

  // ---- getCardSize ----

  it('sizes itself from the rules it renders, not every profile', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(
      state({
        rules: [
          rule({ id: 'shown', profile: 1, day: '1' }),
          rule({ id: 'chag-a', profile: 3, day: '1' }),
          rule({ id: 'chag-b', profile: 3, day: '2' }),
        ],
      }),
    );
    await el.updateComplete;

    expect(el.getCardSize()).toBe(4);
  });

  it('still returns a size for a payload with no rules', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    const { rules: _rules, ...withoutRules } = state();
    send(withoutRules as CardState);
    await el.updateComplete;

    expect(el.getCardSize()).toBe(3);
  });
});

describe('authoring', () => {
  const withRules = () => state({ rules: [rule({ id: 'r1', target: {} })] });

  it('opens the dialog when a row asks to be opened', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(withRules());
    await el.updateComplete;

    el.shadowRoot!.querySelector('shabbat-day-group')!.dispatchEvent(
      new CustomEvent('rule-open', {
        detail: { rule: withRules().rules[0] }, bubbles: true, composed: true,
      }),
    );
    await el.updateComplete;

    expect(el.shadowRoot!.querySelector('shabbat-rule-dialog')).not.toBeNull();
  });

  it('toggles a rule enabled/disabled from the row, non-optimistically', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(withRules());
    await el.updateComplete;

    const row = (await ruleRows(el))[0] as any;
    row.shadowRoot!.querySelector('ha-selector.row-toggle')!.dispatchEvent(
      new CustomEvent('value-changed', { detail: { value: false } }),
    );
    await flush();

    expect(hass.callWS).toHaveBeenCalledWith({
      type: 'shabbat_scheduler/rules/update',
      rule_id: withRules().rules[0].id,
      changes: { enabled: !withRules().rules[0].enabled },
    });
    // No optimistic update: the row still shows what the last push said.
    expect(row.rule.enabled).toBe(withRules().rules[0].enabled);
  });

  it('reports a rejected row toggle on the row, not the dialog', async () => {
    const { hass, send } = fakeHass();
    hass.callWS = vi.fn(async () => { throw { message: 'nope' }; });
    const el = await mount(hass);
    send(withRules());
    await el.updateComplete;

    const row = (await ruleRows(el))[0] as any;
    row.shadowRoot!.querySelector('ha-selector.row-toggle')!.dispatchEvent(
      new CustomEvent('value-changed', { detail: { value: false } }),
    );
    await flush();
    await el.updateComplete;

    const refreshedRow = (await ruleRows(el))[0] as any;
    expect(refreshedRow.toggleError).toBe('nope');
    expect(el.shadowRoot!.querySelector('shabbat-rule-dialog')).toBeNull();
  });

  it('sends rules/update with only the changed fields', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(withRules());
    await el.updateComplete;
    el._editing = withRules().rules[0];
    await el.updateComplete;

    el.shadowRoot!.querySelector('shabbat-rule-dialog')!.dispatchEvent(
      new CustomEvent('dialog-save', {
        detail: {
          rule: withRules().rules[0],
          form: { ...ruleToForm(withRules().rules[0]), time: '12:00:00' },
        },
      }),
    );
    await el.updateComplete;

    expect(hass.callWS).toHaveBeenCalledWith({
      type: 'shabbat_scheduler/rules/update',
      rule_id: 'r1',
      changes: { time: '12:00:00' },
    });
  });

  it('sends rules/create carrying the selected profile', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(state());
    el._selectedProfile = 3;
    el._creatingDay = '2';
    await el.updateComplete;

    el.shadowRoot!.querySelector('shabbat-rule-dialog')!.dispatchEvent(
      new CustomEvent('dialog-save', {
        detail: { rule: null, form: { ...EMPTY, day: '2', time: '11:00:00' } },
      }),
    );
    await el.updateComplete;

    const sent = hass.callWS.mock.calls[0][0];
    expect(sent.type).toBe('shabbat_scheduler/rules/create');
    expect(sent.rule.profile).toBe(3);
  });

  // ---- the per-day add chain, end to end ----
  //
  // Three separate links carried no guard at all: the card handing
  // `_creatingDay` to the dialog's `.day`, and the dialog stamping that
  // `day` onto both an empty form and a seeded (duplicate) one. Break any
  // one of them and EVERY rule added from EVERY day's button is created on
  // erev - an air conditioner acting on the wrong day of a three-day Chag -
  // while `day-group` still emits `{day: '1'}` and the card still sets
  // `_creatingDay` correctly, so both existing tests stay green.
  //
  // This one drives the whole chain through the real Save button rather
  // than a synthesised `dialog-save`, so the day it asserts is the day
  // that would actually be written.

  it('creates a rule on the day whose add button was pressed, all the way to the payload', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(state());
    el._selectedProfile = 3;
    await el.updateComplete;

    el.shadowRoot!.querySelector('shabbat-day-group')!.dispatchEvent(
      new CustomEvent('rule-add', {
        detail: { day: '2' }, bubbles: true, composed: true,
      }),
    );
    await el.updateComplete;

    const dialog = el.shadowRoot!.querySelector('shabbat-rule-dialog') as Card;
    expect(dialog).not.toBeNull();
    // The card must hand the target day down...
    expect(dialog.day).toBe('2');
    await dialog.updateComplete;

    (dialog.shadowRoot!.querySelector('.save') as HTMLElement).click();
    await flush();
    await el.updateComplete;

    // ...and the dialog must stamp it onto the form it emits.
    const sent = hass.callWS.mock.calls[0][0];
    expect(sent.type).toBe('shabbat_scheduler/rules/create');
    expect(sent.rule.day).toBe('2');
    expect(sent.rule.profile).toBe(3);
  });

  it('duplicates onto the day the duplicate was opened for, not the original\'s', async () => {
    // `_onDuplicate` reopens as a create carrying the original's values.
    // The seeded branch stamps `day` separately from the empty branch, so
    // it needs its own guard: a duplicate that ignored `this.day` would
    // silently move every duplicate to erev.
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(withRules());
    el._editing = withRules().rules[0];
    await el.updateComplete;

    el.shadowRoot!.querySelector('shabbat-rule-dialog')!.dispatchEvent(
      new CustomEvent('dialog-duplicate', {
        detail: {
          rule: withRules().rules[0],
          form: { ...ruleToForm(withRules().rules[0]), day: '1' },
        },
      }),
    );
    await el.updateComplete;

    // The user then moves the duplicate to day 2 before saving it.
    // Deliberately not erev: erev is what every fallback in this chain
    // falls back to, so expecting it would pass whether or not the target
    // day was honoured at all.
    el._creatingDay = '2';
    await el.updateComplete;
    const dialog = el.shadowRoot!.querySelector('shabbat-rule-dialog') as Card;
    expect(dialog.day).toBe('2');
    await dialog.updateComplete;

    (dialog.shadowRoot!.querySelector('.save') as HTMLElement).click();
    await flush();
    await el.updateComplete;

    const sent = hass.callWS.mock.calls[0][0];
    expect(sent.rule.day).toBe('2');
    // ...still carrying the original's values, or it duplicates nothing.
    expect(sent.rule.time).toBe('11:00:00');
  });

  it('keeps the dialog open and shows the message when the server refuses', async () => {
    // The saved form must actually differ from the original: the server
    // validates and stores rule.time already, so it can never answer
    // "not a valid clock time" for an unchanged value - only for a value
    // the user just typed. An unchanged form here would test a rejection
    // the server cannot produce in production.
    const { hass, send } = fakeHass();
    hass.callWS = vi.fn(async () => { throw { code: 'invalid_format', message: 'time is not a valid clock time' }; });
    const el = await mount(hass);
    send(withRules());
    el._editing = withRules().rules[0];
    await el.updateComplete;

    el.shadowRoot!.querySelector('shabbat-rule-dialog')!.dispatchEvent(
      new CustomEvent('dialog-save', {
        detail: {
          rule: withRules().rules[0],
          form: { ...ruleToForm(withRules().rules[0]), time: '99:99:99' },
        },
      }),
    );
    // `flush`, not `updateComplete`. Both `await el.updateComplete` calls
    // resolve BEFORE `_onSave`'s continuation runs, so without a macrotask
    // flush the assertions below observe an intermediate state in which
    // `_send` has set `_dialogError` but the close has not happened yet -
    // and an optimistic `this._closeDialogs()` (the one thing the Global
    // Constraints forbid) passed this test unnoticed. One macrotask is the
    // whole difference between a guard and a decoration.
    await flush();
    await el.updateComplete;

    const dialog = el.shadowRoot!.querySelector('shabbat-rule-dialog') as any;
    expect(dialog).not.toBeNull();
    expect(dialog.error).toContain('not a valid clock time');
    // The rejected form is still in the card's hands, unchanged.
    expect(el._editing).not.toBeNull();
  });

  // ---- the close path, in BOTH directions ----
  //
  // Closing before the server answers is optimistic and forbidden. NOT
  // closing after the server accepts is its own bug: the user taps Save,
  // sees nothing happen, and taps again - which on the create path is a
  // second identical rule, i.e. exactly the double-fire `conflict_warnings`
  // exists to complain about. The test above pins the first direction;
  // these two pin the second, for update and for create.

  it('closes the rule dialog once the server accepts an update', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(withRules());
    el._editing = withRules().rules[0];
    await el.updateComplete;

    el.shadowRoot!.querySelector('shabbat-rule-dialog')!.dispatchEvent(
      new CustomEvent('dialog-save', {
        detail: {
          rule: withRules().rules[0],
          form: { ...ruleToForm(withRules().rules[0]), time: '12:00:00' },
        },
      }),
    );
    await flush();
    await el.updateComplete;

    expect(el.shadowRoot!.querySelector('shabbat-rule-dialog')).toBeNull();
    expect(el._editing).toBeNull();
  });

  it('closes the rule dialog once the server accepts a create, so a second tap cannot duplicate it', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(state());
    el._creatingDay = '1';
    await el.updateComplete;

    el.shadowRoot!.querySelector('shabbat-rule-dialog')!.dispatchEvent(
      new CustomEvent('dialog-save', {
        detail: { rule: null, form: { ...EMPTY, day: '1', time: '11:00:00' } },
      }),
    );
    await flush();
    await el.updateComplete;

    expect(hass.callWS).toHaveBeenCalledOnce();
    expect(el.shadowRoot!.querySelector('shabbat-rule-dialog')).toBeNull();
    expect(el._creatingDay).toBeNull();
  });

  it('keeps the rule dialog open when the server refuses a create', async () => {
    const { hass, send } = fakeHass();
    hass.callWS = vi.fn(async () => {
      throw { code: 'invalid_format', message: 'time is required' };
    });
    const el = await mount(hass);
    send(state());
    el._creatingDay = '1';
    await el.updateComplete;

    el.shadowRoot!.querySelector('shabbat-rule-dialog')!.dispatchEvent(
      new CustomEvent('dialog-save', {
        detail: { rule: null, form: { ...EMPTY, day: '1', time: '' } },
      }),
    );
    await flush();
    await el.updateComplete;

    const dialog = el.shadowRoot!.querySelector('shabbat-rule-dialog') as any;
    expect(dialog).not.toBeNull();
    expect(dialog.error).toContain('time is required');
    expect(el._creatingDay).toBe('1');
  });

  it('shows the preview banner and hides dates for a non-current profile', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(withRules());
    el._selectedProfile = 3;
    await el.updateComplete;

    expect(el.shadowRoot!.textContent).toContain('Preview');
    const groups = [...el.shadowRoot!.querySelectorAll('shabbat-day-group')];
    expect(groups.length).toBe(4);
    for (const group of groups) {
      expect((group as any).group.date).toBeNull();
    }
  });

  it('duplicating opens a create pre-filled from the original', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(withRules());
    el._editing = withRules().rules[0];
    await el.updateComplete;

    el.shadowRoot!.querySelector('shabbat-rule-dialog')!.dispatchEvent(
      new CustomEvent('dialog-duplicate', {
        detail: {
          rule: withRules().rules[0],
          form: ruleToForm(withRules().rules[0]),
        },
      }),
    );
    await el.updateComplete;

    const dialog = el.shadowRoot!.querySelector('shabbat-rule-dialog') as any;
    // A create, not an edit - saving must add a rule, not overwrite one.
    expect(dialog.rule).toBeNull();
    // ...but carrying the original's values, or it duplicates nothing.
    expect(dialog.seed.time).toBe('11:00:00');
  });

  // `_onDuplicate` also sets `_editing` and `_creatingDay` (both already
  // `@state`), which on their own would trigger the re-render that makes
  // the seed show up correctly even if `_duplicateSeed` itself were a
  // plain field - so a duplicate-then-check test proves nothing about the
  // decorator specifically. Force the case where those two fields do NOT
  // change value on a second duplicate (same day, still not editing) - the
  // only path where `_duplicateSeed` alone is what has to trigger the
  // render.
  it('reflects a second duplicate on the same day, because _duplicateSeed is itself reactive', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(withRules());
    el._editing = withRules().rules[0];
    await el.updateComplete;

    const dialog = () => el.shadowRoot!.querySelector('shabbat-rule-dialog') as any;
    dialog().dispatchEvent(
      new CustomEvent('dialog-duplicate', {
        detail: { rule: withRules().rules[0], form: ruleToForm(withRules().rules[0]) },
      }),
    );
    await el.updateComplete;
    // Both now hold values that will NOT change on the next duplicate.
    expect(el._editing).toBeNull();
    expect(el._creatingDay).toBe('1');

    const secondForm = { ...ruleToForm(withRules().rules[0]), time: '15:00:00' };
    dialog().dispatchEvent(
      new CustomEvent('dialog-duplicate', {
        detail: { rule: withRules().rules[0], form: secondForm },
      }),
    );
    await el.updateComplete;

    expect(dialog().seed.time).toBe('15:00:00');
  });

  it('offers no authoring at all to a read-only user', async () => {
    const { hass, send } = fakeHass({ user: { is_admin: false } });
    const el = await mount(hass);
    send(withRules());
    await el.updateComplete;
    const group = el.shadowRoot!.querySelector('shabbat-day-group') as any;
    expect(group.canWrite).toBe(false);
  });

  // ---- an unchanged save is still a decision, not an accident ----

  it('always sends rules/update, even with an empty diff, rather than assuming nothing could go wrong', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(withRules());
    await el.updateComplete;
    el._editing = withRules().rules[0];
    await el.updateComplete;

    el.shadowRoot!.querySelector('shabbat-rule-dialog')!.dispatchEvent(
      new CustomEvent('dialog-save', {
        detail: {
          rule: withRules().rules[0],
          form: ruleToForm(withRules().rules[0]),
        },
      }),
    );
    await el.updateComplete;

    expect(hass.callWS).toHaveBeenCalledWith({
      type: 'shabbat_scheduler/rules/update',
      rule_id: 'r1',
      changes: {},
    });
  });

  // ---- a push arriving while the dialog is open ----
  //
  // `_editing` is captured at open and never reconciled with later
  // pushes, so a rule edited by another client mid-dialog leaves the diff
  // basis stale. Assessed and deliberately kept: every key the diff emits
  // still carries exactly the value the form is showing, so the write can
  // never be wrong - it can only be smaller than the display implies.
  // Diffing against the fresh copy would send a field the user never
  // touched and silently overwrite the other client's save, on a system
  // with no undo. This test pins the conservative choice so a future
  // "fix" for the stale display cannot quietly introduce the clobber.

  it('does not overwrite a field another client changed while the dialog was open', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(withRules());
    el._editing = withRules().rules[0];
    await el.updateComplete;

    // Another client moves the same rule to 12:00 and the push lands.
    send(state({ rules: [{ ...withRules().rules[0], time: '12:00:00' }] }));
    await el.updateComplete;

    const dialog = el.shadowRoot!.querySelector('shabbat-rule-dialog') as Card;
    await dialog.updateComplete;
    const name = dialog.shadowRoot!.querySelector('.name') as HTMLInputElement;
    name.value = 'Morning';
    name.dispatchEvent(new Event('change'));
    (dialog.shadowRoot!.querySelector('.save') as HTMLElement).click();
    await flush();
    await el.updateComplete;

    const sent = hass.callWS.mock.calls[0][0];
    expect(sent.changes).toEqual({ name: 'Morning' });
    // The field the user never touched is not in the payload, so the
    // other client's 12:00 survives.
    expect('time' in sent.changes).toBe(false);
  });

  // ---- delete: the destructive command had no card-level test ----

  it('sends rules/delete with the rule id and closes only on success', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(withRules());
    el._editing = withRules().rules[0];
    await el.updateComplete;

    el.shadowRoot!.querySelector('shabbat-rule-dialog')!.dispatchEvent(
      new CustomEvent('dialog-delete', {
        detail: { rule: withRules().rules[0] },
      }),
    );
    await flush();
    await el.updateComplete;

    expect(hass.callWS).toHaveBeenCalledWith({
      type: 'shabbat_scheduler/rules/delete',
      rule_id: 'r1',
    });
    expect(el.shadowRoot!.querySelector('shabbat-rule-dialog')).toBeNull();
  });

  it('keeps the dialog open when the server refuses a delete', async () => {
    const { hass, send } = fakeHass();
    hass.callWS = vi.fn(async () => {
      throw { code: 'invalid_state', message: 'rule is referenced elsewhere' };
    });
    const el = await mount(hass);
    send(withRules());
    el._editing = withRules().rules[0];
    await el.updateComplete;

    el.shadowRoot!.querySelector('shabbat-rule-dialog')!.dispatchEvent(
      new CustomEvent('dialog-delete', {
        detail: { rule: withRules().rules[0] },
      }),
    );
    // Same reason as the refused-save test above: without a macrotask the
    // assertion lands before `_onDelete`'s continuation and would pass
    // against an unconditional close.
    await flush();
    await el.updateComplete;

    expect(el.shadowRoot!.querySelector('shabbat-rule-dialog')).not.toBeNull();
  });

  // ---- defaults: what every rule inherits ----

  // v1's editor wrote `{devices, settings}`, which `validate_defaults` now
  // rejects outright, so its save could only ever have failed - the button
  // was removed rather than left broken. This dialog composes the same
  // target/service editors the rule dialog uses, so what has to work here
  // is that the gear opens it, it seeds the real defaults into those
  // editors, and a save round-trips exactly `{target, data}`.
  it('opens the defaults dialog from the gear, seeding the real defaults', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(state({
      defaults: {
        target: { entity_id: ['climate.salon'] },
        data: { temperature: 26 },
      },
    }));
    await el.updateComplete;

    const header = el.shadowRoot!.querySelector('shabbat-block-header')!;
    const gear = header.shadowRoot!.querySelector('.gear') as HTMLElement;
    expect(gear).not.toBeNull();
    gear.click();
    await el.updateComplete;

    const dialog = el.shadowRoot!.querySelector('shabbat-defaults-dialog') as Card;
    expect(dialog).not.toBeNull();
    await dialog.updateComplete;
    expect(
      (dialog.shadowRoot!.querySelector('shabbat-target-editor') as any).value,
    ).toEqual({ entity_id: ['climate.salon'] });
    expect(
      (dialog.shadowRoot!.querySelector('shabbat-service-editor') as any).data,
    ).toEqual({ temperature: 26 });
  });

  it('sends defaults/update with exactly what the dialog emits, and closes on success', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(state());
    await el.updateComplete;
    (el.shadowRoot!.querySelector('shabbat-block-header')!
      .shadowRoot!.querySelector('.gear') as HTMLElement).click();
    await el.updateComplete;

    el.shadowRoot!.querySelector('shabbat-defaults-dialog')!.dispatchEvent(
      new CustomEvent('dialog-save', {
        detail: { defaults: { target: { entity_id: ['climate.salon'] }, data: {} } },
      }),
    );
    await flush();
    await el.updateComplete;

    expect(hass.callWS).toHaveBeenCalledWith({
      type: 'shabbat_scheduler/defaults/update',
      defaults: { target: { entity_id: ['climate.salon'] }, data: {} },
    });
    expect(el.shadowRoot!.querySelector('shabbat-defaults-dialog')).toBeNull();
  });

  it('opens the simulate dialog from the header icon', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(state());
    await el.updateComplete;

    el.shadowRoot!.querySelector('shabbat-block-header')!.dispatchEvent(
      new CustomEvent('simulate-open', { bubbles: true, composed: true }),
    );
    await el.updateComplete;

    expect(el.shadowRoot!.querySelector('shabbat-simulate-dialog')).not.toBeNull();
  });

  it('passes canWrite through to the simulate dialog for a read-only user', async () => {
    const { hass, send } = fakeHass({ user: { is_admin: false } });
    const el = await mount(hass);
    send(state());
    await el.updateComplete;

    el._simulateOpen = true;
    await el.updateComplete;

    const dialog = el.shadowRoot!.querySelector('shabbat-simulate-dialog') as any;
    expect(dialog.canWrite).toBe(false);
  });

  // ---- the block:null dead end this plan's headline fix removes ----

  it('renders day groups and the preview banner with no block, once a profile is selected', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(state({ block: null }));
    el._selectedProfile = 1;
    await el.updateComplete;

    expect(el.shadowRoot!.querySelectorAll('shabbat-day-group').length).toBe(2);
    expect(el.shadowRoot!.textContent).toContain('Preview');
  });

  // ---- the row tap: the sole entry point to authoring, for real ----

  it('opens the dialog from an actual tap on the rendered row, crossing both shadow roots', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(withRules());
    await el.updateComplete;

    // withRules() puts its one rule on day '1', not 'erev' - the day
    // groups render in calendar order, so the FIRST one is the empty erev
    // group. Find the group that actually holds a row rather than assume
    // position.
    const dayGroups = [...el.shadowRoot!.querySelectorAll('shabbat-day-group')] as (HTMLElement &
      Record<string, unknown> & { updateComplete: Promise<unknown> })[];
    await Promise.all(dayGroups.map((g) => g.updateComplete));
    const dayGroup = dayGroups.find(
      (g) => g.shadowRoot!.querySelector('shabbat-rule-row') !== null,
    )!;
    expect(dayGroup).not.toBeUndefined();
    const ruleRow = dayGroup.shadowRoot!.querySelector('shabbat-rule-row') as HTMLElement &
      Record<string, unknown> & { updateComplete: Promise<unknown> };
    await ruleRow.updateComplete;
    const row = ruleRow.shadowRoot!.querySelector('.row') as HTMLElement;
    expect(row).not.toBeNull();

    row.click();
    await el.updateComplete;

    const dialog = el.shadowRoot!.querySelector('shabbat-rule-dialog') as any;
    expect(dialog).not.toBeNull();
    expect(dialog.rule.id).toBe('r1');
  });

  // ---- a wall dashboard left on a preview must not stay stuck there ----

  it('resets the selected profile once the coming block\'s length changes', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(state());
    await el.updateComplete;
    el._selectedProfile = 3;
    await el.updateComplete;
    expect(el._profile).toBe(3);

    send(
      state({
        block: {
          length: 3,
          candle_lighting: '2026-08-14T18:44:00+03:00',
          havdalah: '2026-08-17T20:10:00+03:00',
          dates: {
            erev: '2026-08-14', '1': '2026-08-15', '2': '2026-08-16', '3': '2026-08-17',
          },
        },
      }),
    );
    await el.updateComplete;

    expect(el._selectedProfile).toBeNull();
    expect(el._profile).toBe(3);
  });

  it('keeps the selected profile across a push whose block length has not changed', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(state());
    await el.updateComplete;
    el._selectedProfile = 3;
    await el.updateComplete;

    send(state({ enabled: true }));
    await el.updateComplete;

    expect(el._selectedProfile).toBe(3);
  });

  // ---- hass must reach the HA elements the dialogs embed ----

  it('passes hass down to the rule dialog, so HA elements can render', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(state());
    await el.updateComplete;

    el.shadowRoot!.querySelector('shabbat-day-group')!.dispatchEvent(
      new CustomEvent('rule-add', {
        detail: { day: 'erev' }, bubbles: true, composed: true,
      }),
    );
    await el.updateComplete;

    const dialog = el.shadowRoot!.querySelector('shabbat-rule-dialog') as any;
    expect(dialog).not.toBeNull();
    expect(dialog.hass).toBe(el.hass);
  });

  it('passes hass down to the defaults dialog', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(state());
    await el.updateComplete;
    el._defaultsOpen = true;
    await el.updateComplete;

    const dialog = el.shadowRoot!.querySelector('shabbat-defaults-dialog') as any;
    expect(dialog).not.toBeNull();
    expect(dialog.hass).toBe(el.hass);
  });

  it('no longer offers a dry-run control at all', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(state());
    await el.updateComplete;
    expect(el.shadowRoot!.querySelector('shabbat-block-header')!
      .shadowRoot).toBeTruthy(); // sanity: header rendered
    const header = el.shadowRoot!.querySelector('shabbat-block-header') as any;
    await header.updateComplete;
    expect(header.shadowRoot!.querySelector('.dry-run')).toBeNull();
    expect('dryRun' in header).toBe(false);
  });

  it('sends run_now and shows the inline result, without closing the dialog', async () => {
    const { hass, send } = fakeHass();
    hass.callWS = vi.fn(async () => ({ results: [{ outcome: 'would_call' }] }));
    const el = await mount(hass);
    send(withRules());
    el._editing = withRules().rules[0];
    await el.updateComplete;

    el.shadowRoot!.querySelector('shabbat-rule-dialog')!.dispatchEvent(
      new CustomEvent('dialog-run-now', {
        detail: { rule: withRules().rules[0], simulate: true },
      }),
    );
    await flush();
    await el.updateComplete;

    expect(hass.callWS).toHaveBeenCalledWith({
      type: 'shabbat_scheduler/rules/run_now',
      rule_id: withRules().rules[0].id,
      simulate: true,
    });
    expect(el.shadowRoot!.querySelector('shabbat-rule-dialog')).not.toBeNull();
  });
});
