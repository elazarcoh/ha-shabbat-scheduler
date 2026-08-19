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

  /**
   * The badge's existence is not the thing that matters - its text is.
   * Conflicts are warned and never auto-resolved, so the only way anyone
   * fixes one is by reading which device and which time clash. The
   * payload this card receives carries no `message` field, so a row
   * built from `warning.message` renders the literal string "undefined":
   * a badge that says a conflict exists and refuses to say what it is.
   * Asserting only that `.conflict` exists passes either way, which is
   * how that defect survived once already.
   */
  it('says which device and time conflict, in the badge and on the row', async () => {
    const el = await render({
      rule: rule({ id: 'a' }),
      warnings: [
        { kind: 'conflict', device: 'climate.salon', profile: 1, day: '1', time: '11:00:00', rule_ids: ['a'] },
      ],
    });

    const badge = el.shadowRoot!.querySelector('.conflict')!;
    const tooltip = badge.getAttribute('title')!;
    expect(tooltip).toContain('climate.salon');
    expect(tooltip).toContain('11:00');
    expect(tooltip).not.toContain('undefined');

    // And reachable without hovering - see the .conflict-detail line.
    const detail = el.shadowRoot!.querySelector('.conflict-detail')!;
    expect(detail).not.toBeNull();
    expect(detail.textContent).toContain('climate.salon');
    expect(detail.textContent).toContain('11:00');
    expect(detail.textContent).not.toContain('undefined');
  });

  /** Every conflict, not just the first: `unattachedWarnings` treats a
   * warning as handled the moment it names a displayed rule, so a second
   * conflict on the same row that this did not render would appear
   * nowhere at all - neither here nor in the banner. */
  it('shows every conflict naming this rule, not only the first', async () => {
    const el = await render({
      rule: rule({ id: 'a' }),
      warnings: [
        { kind: 'conflict', device: 'climate.salon', profile: 1, day: '1', time: '11:00:00', rule_ids: ['a'] },
        { kind: 'conflict', device: 'climate.bedroom', profile: 1, day: '1', time: '11:00:00', rule_ids: ['a'] },
      ],
    });
    const detail = el.shadowRoot!.querySelector('.conflict-detail')!.textContent!;
    expect(detail).toContain('climate.salon');
    expect(detail).toContain('climate.bedroom');
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
