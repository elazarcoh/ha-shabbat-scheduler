import { describe, expect, it } from 'vitest';
import '../src/rule-row';
import type { RuleData } from '../src/types';

const rule = (over: Partial<RuleData>): RuleData => ({
  id: 'r', profile: 1, day: '1', time: '11:00:00', action: 'on',
  devices: ['climate.salon'], settings: {}, name: null, icon: null,
  enabled: true, script: null, variables: {}, replay_on_restart: false,
  color: null, ...over,
});

async function render(props: Record<string, unknown>) {
  const el = document.createElement('shabbat-rule-row') as HTMLElement &
    Record<string, unknown>;
  Object.assign(el, { defaults: {}, warnings: [], language: 'en', ...props });
  document.body.appendChild(el);
  await (el as unknown as { updateComplete: Promise<unknown> }).updateComplete;
  return el;
}

describe('shabbat-rule-row', () => {
  it('shows the time and the brief', async () => {
    const el = await render({ rule: rule({}) });
    const text = el.shadowRoot!.textContent!;
    expect(text).toContain('11:00');
    expect(text).toContain('climate.salon');
  });

  it('shows the name when there is one', async () => {
    const el = await render({ rule: rule({ name: 'Shabbat morning' }) });
    expect(el.shadowRoot!.textContent).toContain('Shabbat morning');
  });

  it('marks a disabled rule as disabled, not merely dim', async () => {
    const el = await render({ rule: rule({ enabled: false }) });
    expect(el.shadowRoot!.querySelector('.row')!.classList).toContain('disabled');
    expect(el.shadowRoot!.textContent).toContain('disabled');
  });

  it('shows a conflict badge when a warning names this rule', async () => {
    const el = await render({
      rule: rule({ id: 'a' }),
      warnings: [
        { kind: 'conflict', device: 'climate.salon', profile: 1, day: '1', time: '11:00:00', rule_ids: ['a'] },
      ],
    });
    expect(el.shadowRoot!.querySelector('.conflict')).not.toBeNull();
  });

  it('shows no conflict badge when no warning names it', async () => {
    const el = await render({
      rule: rule({ id: 'a' }),
      warnings: [
        { kind: 'conflict', device: 'climate.salon', profile: 1, day: '1', time: '11:00:00', rule_ids: ['b'] },
      ],
    });
    expect(el.shadowRoot!.querySelector('.conflict')).toBeNull();
  });
});
