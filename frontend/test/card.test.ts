import { describe, expect, it, vi } from 'vitest';
import '../src/card';
import type { CardState } from '../src/types';

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
      subscribeMessage: vi.fn(async (cb: (s: CardState) => void) => {
        push = cb;
        return unsubscribe;
      }),
    },
    ...over,
  };
  return { hass, send: (s: CardState) => push!(s), unsubscribe, callService };
}

async function mount(hass: unknown) {
  const el = document.createElement('shabbat-scheduler-card') as HTMLElement &
    Record<string, any>;
  el.setConfig({});
  document.body.appendChild(el);
  el.hass = hass;
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
});
