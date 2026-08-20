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

  // ---- the row is the sole entry point to authoring - it must be
  // operable without a pointer, not just tappable ----

  it('is a focusable, announced control - not a bare div with a click handler', async () => {
    const el = await render({ rule: rule({}) });
    const row = el.shadowRoot!.querySelector('.row') as HTMLElement;
    expect(row.getAttribute('tabindex')).toBe('0');
    expect(row.getAttribute('role')).toBe('button');
  });

  it('opens on Enter as well as on a tap', async () => {
    const el = await render({ rule: rule({ id: 'a' }) });
    const row = el.shadowRoot!.querySelector('.row') as HTMLElement;

    let detail: { rule?: { id: string } } | null = null;
    el.addEventListener('rule-open', (event: Event) => {
      detail = (event as CustomEvent).detail;
    });

    row.dispatchEvent(
      new KeyboardEvent('keydown', { key: 'Enter', bubbles: true, composed: true }),
    );

    expect(detail).not.toBeNull();
    expect((detail as any).rule.id).toBe('a');
  });

  it('opens on Space as well', async () => {
    const el = await render({ rule: rule({ id: 'a' }) });
    const row = el.shadowRoot!.querySelector('.row') as HTMLElement;

    let count = 0;
    el.addEventListener('rule-open', () => { count += 1; });

    row.dispatchEvent(
      new KeyboardEvent('keydown', { key: ' ', bubbles: true, composed: true }),
    );

    expect(count).toBe(1);
  });

  it('does not open on an unrelated key', async () => {
    const el = await render({ rule: rule({ id: 'a' }) });
    const row = el.shadowRoot!.querySelector('.row') as HTMLElement;

    let count = 0;
    el.addEventListener('rule-open', () => { count += 1; });

    row.dispatchEvent(
      new KeyboardEvent('keydown', { key: 'Tab', bubbles: true, composed: true }),
    );

    expect(count).toBe(0);
  });
});
