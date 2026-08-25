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
import type { CardState } from '../src/types';

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
