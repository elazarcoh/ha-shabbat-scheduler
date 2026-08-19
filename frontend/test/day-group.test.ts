import { describe, expect, it } from 'vitest';
import '../src/day-group';
import type { DayGroup } from '../src/types';

const group = (over: Partial<DayGroup>): DayGroup => ({
  day: '1', date: '2026-08-15', rules: [], marker: null, ...over,
});

async function render(props: Record<string, unknown>) {
  const el = document.createElement('shabbat-day-group') as HTMLElement &
    Record<string, unknown>;
  Object.assign(el, { defaults: {}, warnings: [], language: 'en', ...props });
  document.body.appendChild(el);
  await (el as unknown as { updateComplete: Promise<unknown> }).updateComplete;
  return el;
}

describe('shabbat-day-group', () => {
  it('shows the date in its heading', async () => {
    const el = await render({ group: group({}) });
    expect(el.shadowRoot!.textContent).toContain('2026-08-15');
  });

  it('renders a row per rule', async () => {
    const el = await render({
      group: group({
        rules: [
          { id: 'a', profile: 1, day: '1', time: '11:00:00', action: 'on',
            devices: [], settings: {}, name: null, icon: null, enabled: true,
            script: null, variables: {}, replay_on_restart: false, color: null },
          { id: 'b', profile: 1, day: '1', time: '18:00:00', action: 'off',
            devices: [], settings: {}, name: null, icon: null, enabled: true,
            script: null, variables: {}, replay_on_restart: false, color: null },
        ],
      }),
    });
    expect(el.shadowRoot!.querySelectorAll('shabbat-rule-row').length).toBe(2);
  });

  it('says so when a day has no rules rather than rendering nothing', async () => {
    const el = await render({ group: group({ rules: [] }) });
    expect(el.shadowRoot!.textContent).toContain('No rules');
  });

  it('shows the havdalah marker with its time', async () => {
    const el = await render({
      group: group({ marker: { kind: 'havdalah', at: '2026-08-15T20:01:00+03:00' } }),
    });
    const text = el.shadowRoot!.textContent!;
    expect(text).toContain('Havdalah');
    expect(text).toContain('20:01');
  });

  it('shows the raw value when a marker timestamp cannot be parsed, rather than a blank', async () => {
    const el = await render({
      group: group({ marker: { kind: 'havdalah', at: 'not-a-timestamp' } }),
    });
    const text = el.shadowRoot!.textContent!;
    expect(text).toContain('Havdalah');
    expect(text).toContain('not-a-timestamp');
  });
});
