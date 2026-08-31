/**
 * The one way this suite puts a card on screen and drives its subscription.
 *
 * Shared rather than copied, deliberately. `payload-contract.test.ts`
 * renders the card from a payload the PYTHON side generated, and it is only
 * worth anything if it reaches the card through exactly the same door
 * `card.test.ts` uses - a second, slightly different mount would make the
 * two files test two different cards, which is the same failure (tests
 * agreeing with each other and with nothing else) that Gap A exists to
 * close.
 */
import { vi } from 'vitest';
import type { CardState, RuleData } from '../src/types';

export type Unsubscribe = () => Promise<void>;
export type SubscribeFn = (
  cb: (s: CardState) => void,
  msg?: unknown,
) => Promise<Unsubscribe>;

export type Card = HTMLElement & Record<string, any>;

/** Lets pending promise chains (subscribe, unsubscribe, callService) settle. */
export const flush = () => new Promise((resolve) => setTimeout(resolve, 0));

/** A fake hass whose subscription we drive by hand. */
export function fakeHass(over: Record<string, unknown> = {}) {
  let push: ((s: CardState) => void) | null = null;
  const unsubscribe = vi.fn(async () => {});
  const callService = vi.fn(async () => {});
  const callWS = vi.fn(async (_message: any) => ({}) as any);
  const hass = {
    locale: { language: 'en' },
    user: { is_admin: true },
    callService,
    callWS,
    connection: {
      subscribeMessage: vi.fn<SubscribeFn>(async (cb) => {
        push = cb;
        return unsubscribe;
      }),
    },
    ...over,
  };
  return { hass, send: (s: CardState) => push!(s), unsubscribe, callService, callWS };
}

/**
 * A fake `hass` whose `callWS` genuinely mutates its own rule list and
 * pushes a fresh state after every `rules/create`/`rules/delete` - unlike
 * `fakeHass` above, whose `callWS` is a bare mock that never touches
 * `_state` at all.
 *
 * That gap is right for a test that only cares what got SENT, and it is
 * exactly the blind spot that let the critical overwrite-onto-self clone
 * bug hide behind a fully green suite: production pushes a new `_state`
 * mid-operation (`ws_delete` -> `store.async_delete` -> `_notify_change`
 * -> the subscribed push, all before `send_result`), so a card function
 * that re-reads `this._state` between two awaited `callWS` calls sees
 * ITS OWN prior call's effect - but `fakeHass`'s `_state` stays frozen for
 * the whole test, so that re-read always finds the stale, still-correct
 * copy no matter what the function under test actually did. Any test that
 * needs the card to observe its own in-flight side effects - overwrite
 * mode's delete-then-recreate chief among them - needs THIS helper
 * instead.
 */
export function fakeServerHass(initialRules: RuleData[]) {
  let rules = [...initialRules];
  let nextId = 0;
  let push: ((s: CardState) => void) | null = null;

  const buildState = (): CardState => ({
    defaults: {}, rules: [...rules], enabled: false, warnings: [],
    master_entity_id: 'switch.master', language: null,
    block: {
      length: 1, candle_lighting: '2026-08-14T18:44:00+03:00',
      havdalah: '2026-08-15T20:01:00+03:00',
      dates: { erev: '2026-08-14', '1': '2026-08-15' },
    },
  }) as CardState;

  const pushState = () => { if (push) push(buildState()); };

  const callWS = vi.fn(async (message: any) => {
    if (message.type === 'shabbat_scheduler/rules/create') {
      nextId += 1;
      const id = `srv-${nextId}`;
      const r = message.rule;
      const created: RuleData = {
        id,
        day: r.day, profile: r.profile, time: r.time, action: r.action,
        target: r.target ?? {}, data: r.data ?? {},
        condition: r.condition ?? [],
        replay: r.replay ?? { enabled: false },
        name: r.name ?? null, icon: r.icon ?? null, color: r.color ?? null,
        enabled: r.enabled ?? true, last_outcome: null,
      };
      rules = [...rules, created];
      pushState();
      return { rule_id: id };
    }
    if (message.type === 'shabbat_scheduler/rules/delete') {
      rules = rules.filter((rule) => rule.id !== message.rule_id);
      pushState();
      return {};
    }
    return {};
  });

  const hass = {
    locale: { language: 'en' },
    user: { is_admin: true },
    callService: vi.fn(async () => {}),
    callWS,
    connection: {
      subscribeMessage: vi.fn<SubscribeFn>(async (cb) => {
        push = cb;
        pushState();
        return async () => {};
      }),
    },
  };

  return { hass, callWS, rules: () => rules };
}

/** Attaches a card without waiting for anything - for mid-flight probes. */
export function attach(hass: unknown): Card {
  const el = document.createElement('shabbat-scheduler-card') as Card;
  el.setConfig({});
  document.body.appendChild(el);
  el.hass = hass;
  return el;
}

export async function mount(hass: unknown) {
  const el = attach(hass);
  await el.updateComplete;
  return el;
}

/**
 * A card showing exactly this state, and nothing else pending.
 *
 * The card only ever renders what the server pushed (nothing is
 * optimistic), so this is the whole of "render the card with this state".
 */
export async function renderCardWithState(state: CardState): Promise<Card> {
  const { hass, send } = fakeHass();
  const el = await mount(hass);
  send(state);
  await el.updateComplete;
  return el;
}

/**
 * The day groups on screen, each already rendered.
 *
 * Awaiting each group's `updateComplete` rather than sleeping is what makes
 * this reliable: the groups render one microtask behind their parent, and
 * probing them before that reads as "the card drew nothing".
 */
export async function dayGroups(el: Card): Promise<Card[]> {
  const groups = [...el.shadowRoot!.querySelectorAll('shabbat-day-group')] as Card[];
  await Promise.all(groups.map((group) => group.updateComplete));
  return groups;
}

/**
 * Every rule row actually on screen, across every day group.
 *
 * Rows do NOT live in the card's own shadow root - the card renders
 * `<shabbat-day-group>` per day and each group renders its own rows - so
 * `card.shadowRoot.querySelectorAll('shabbat-rule-row')` finds nothing at
 * all and reads as "no rules rendered".
 */
export async function ruleRows(el: Card): Promise<Card[]> {
  return (await dayGroups(el)).flatMap(
    (group) => [...group.shadowRoot!.querySelectorAll('shabbat-rule-row')] as Card[],
  );
}
