import { describe, expect, it, vi } from 'vitest';
import '../src/card';
import type { CardState, RuleData } from '../src/types';

/** Lets pending promise chains (subscribe, unsubscribe, callService) settle. */
const flush = () => new Promise((resolve) => setTimeout(resolve, 0));

const rule = (over: Partial<RuleData> = {}): RuleData => ({
  id: 'a', profile: 1, day: '1', time: '11:00:00', action: 'on',
  devices: ['climate.salon'], settings: {}, name: null, icon: null,
  enabled: true, script: null, variables: {}, replay_on_restart: false,
  color: null,
  ...over,
});

const state = (over: Partial<CardState> = {}): CardState => ({
  defaults: {}, rules: [], enabled: false, dry_run: false, warnings: [],
  master_entity_id: 'switch.master',
  block: {
    length: 1,
    candle_lighting: '2026-08-14T18:44:00+03:00',
    havdalah: '2026-08-15T20:01:00+03:00',
    dates: { erev: '2026-08-14', '1': '2026-08-15' },
  },
  ...over,
});

type Unsubscribe = () => Promise<void>;
type SubscribeFn = (
  cb: (s: CardState) => void,
  msg?: unknown,
) => Promise<Unsubscribe>;

/** A fake hass whose subscription we drive by hand. */
function fakeHass(over: Record<string, unknown> = {}) {
  let push: ((s: CardState) => void) | null = null;
  const unsubscribe = vi.fn(async () => {});
  const callService = vi.fn(async () => {});
  const hass = {
    locale: { language: 'en' },
    user: { is_admin: true },
    callService,
    connection: {
      subscribeMessage: vi.fn<SubscribeFn>(async (cb) => {
        push = cb;
        return unsubscribe;
      }),
    },
    ...over,
  };
  return { hass, send: (s: CardState) => push!(s), unsubscribe, callService };
}

type Card = HTMLElement & Record<string, any>;

/** Attaches a card without waiting for anything - for mid-flight probes. */
function attach(hass: unknown): Card {
  const el = document.createElement('shabbat-scheduler-card') as Card;
  el.setConfig({});
  document.body.appendChild(el);
  el.hass = hass;
  return el;
}

async function mount(hass: unknown) {
  const el = attach(hass);
  await el.updateComplete;
  return el;
}

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
          {
            id: 'a', profile: 1, day: '1', time: '11:00:00', action: 'on',
            devices: ['climate.salon'], settings: {}, name: null, icon: null,
            enabled: true, script: null, variables: {}, replay_on_restart: false,
            color: null,
          },
        ],
        warnings: [
          {
            kind: 'conflict', device: 'climate.salon', profile: 1, day: '1',
            time: '11:00:00', rule_ids: ['a'],
          },
        ],
      }),
    );
    await el.updateComplete;

    expect(el.shadowRoot!.querySelector('shabbat-warnings')!.shadowRoot!.querySelector('.banner')).toBeNull();
    const dayGroups = [...el.shadowRoot!.querySelectorAll('shabbat-day-group')] as (HTMLElement &
      Record<string, unknown>)[];
    await Promise.all(
      dayGroups.map((g) => (g as unknown as { updateComplete: Promise<unknown> }).updateComplete),
    );
    const hasRuleRow = dayGroups.some(
      (g) => g.shadowRoot!.querySelector('shabbat-rule-row') !== null,
    );
    expect(hasRuleRow).toBe(true);
  });

  it('shows a conflict on a non-displayed rule in the banner', async () => {
    const { hass, send } = fakeHass();
    const el = await mount(hass);
    send(
      state({
        rules: [],
        warnings: [
          {
            kind: 'conflict', device: 'climate.salon', profile: 3, day: '1',
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
                 devices: ['climate.mamad'] }),
        ],
        warnings: [
          {
            kind: 'conflict', device: 'climate.mamad', profile: 3, day: '2',
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
