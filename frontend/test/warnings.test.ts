import { describe, expect, it } from 'vitest';
import '../src/warnings';
import type { WarningData } from '../src/types';

async function render(warnings: WarningData[], displayedRuleIds: string[] = []) {
  const el = document.createElement('shabbat-warnings') as HTMLElement &
    Record<string, unknown>;
  Object.assign(el, { warnings, displayedRuleIds, language: 'en' });
  document.body.appendChild(el);
  await (el as unknown as { updateComplete: Promise<unknown> }).updateComplete;
  return el;
}

describe('shabbat-warnings', () => {
  it('renders nothing at all when there are none', async () => {
    const el = await render([]);
    expect(el.shadowRoot!.querySelector('.banner')).toBeNull();
  });

  it('shows a warning that names no rule at all', async () => {
    const el = await render([
      { kind: 'no_profile', message: 'nothing enabled' },
    ]);
    expect(el.shadowRoot!.textContent).toContain('nothing enabled');
  });

  it('hides a conflict whose rule is displayed - it already shows on that row', async () => {
    const el = await render(
      [
        {
          kind: 'conflict', device: 'climate.salon', profile: 1, day: '1',
          time: '11:00:00', rule_ids: ['a'],
        },
      ],
      ['a'],
    );
    expect(el.shadowRoot!.querySelector('.banner')).toBeNull();
  });

  // CONFIRMED DEFECT: a conflict belonging to a rule that is not on screen
  // (e.g. it names a rule from a profile the current block doesn't show)
  // must still surface in the banner. Otherwise it is rendered nowhere,
  // and conflicts are never auto-resolved - only a person can act on one.
  it('shows a conflict whose rule is not displayed, instead of dropping it', async () => {
    const el = await render(
      [
        {
          kind: 'conflict', device: 'climate.salon', profile: 3, day: '1',
          time: '11:00:00', rule_ids: ['not-shown'],
        },
      ],
      [],
    );
    const text = el.shadowRoot!.textContent!;
    expect(text).toContain('climate.salon');
    expect(text).toContain('11:00:00');
  });
});
