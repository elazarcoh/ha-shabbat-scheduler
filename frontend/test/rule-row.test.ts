import { describe, expect, it } from 'vitest';
import '../src/rule-row';
import type { RuleData } from '../src/types';

const rule = (over: Partial<RuleData>): RuleData => ({
  id: 'r', profile: 1, day: '1', time: '11:00:00',
  action: 'climate.turn_on',
  target: { entity_id: ['climate.salon'] },
  data: {}, condition: [], replay: { enabled: false },
  name: null, icon: null, enabled: true, color: null,
  last_outcome: null, ...over,
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
        { kind: 'conflict', targets: ['climate.salon'], profile: 1, day: '1', time: '11:00:00', rule_ids: ['a'] },
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
        { kind: 'conflict', targets: ['climate.salon'], profile: 1, day: '1', time: '11:00:00', rule_ids: ['a'] },
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
        { kind: 'conflict', targets: ['climate.salon'], profile: 1, day: '1', time: '11:00:00', rule_ids: ['a'] },
        { kind: 'conflict', targets: ['climate.bedroom'], profile: 1, day: '1', time: '11:00:00', rule_ids: ['a'] },
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
        { kind: 'conflict', targets: ['climate.salon'], profile: 1, day: '1', time: '11:00:00', rule_ids: ['b'] },
      ],
    });
    expect(el.shadowRoot!.querySelector('.conflict')).toBeNull();
  });

  // ---- what happened last time: the durable, per-rule outcome ----
  //
  // `last_run` was ONE value for the whole integration, overwritten by the
  // next rule to act, so the card could never say why *this* rule did
  // nothing. "A rule that does not fire must say why - in the logbook AND
  // on the card"; this is the card half.

  it('says a rule was blocked, and why', async () => {
    const el = await render({ rule: rule({ last_outcome: {
      outcome: 'blocked', at: '2026-08-25T18:00:00+00:00',
      detail: 'condition 1 of 1 (state on input_boolean.kids) not met',
    } }) });
    const text = el.shadowRoot!.querySelector('.last-outcome')!.textContent!;
    // The exact words the logbook shows, from `_condition_block_reason`.
    // Naming the entity is the whole actionable content: a rule carrying
    // three conditions and reporting a bare "blocked" leaves the reader
    // nothing to check, on the one day they cannot investigate.
    expect(text).toContain('input_boolean.kids');
    expect(text).toContain('condition 1 of 1');
    expect(text).not.toContain('undefined');
  });

  it('says a rule was skipped as too stale to replay', async () => {
    const el = await render({ rule: rule({ last_outcome: {
      outcome: 'skipped_stale', at: '2026-08-25T18:00:00+00:00',
      detail: '6:00:43 late, window 1:00:00',
    } }) });
    const text = el.shadowRoot!.querySelector('.last-outcome')!.textContent!;
    expect(text).toContain('1:00:00');
    expect(text).toContain('6:00:43');
  });

  it('says a rule failed, and names the error', async () => {
    const el = await render({ rule: rule({ last_outcome: {
      outcome: 'failed', at: '2026-08-25T18:00:00+00:00',
      detail: 'RuntimeError: cloud auth expired',
    } }) });
    const text = el.shadowRoot!.querySelector('.last-outcome')!.textContent!;
    expect(text).toContain('cloud auth expired');
  });

  /**
   * Each of the three non-firing outcomes must be DISTINGUISHABLE from a
   * rule that ran. A single "last outcome" line that read the same for
   * "fired" and "blocked" would satisfy every assertion above while
   * telling the reader nothing - the exact failure the empty-conflict bug
   * was.
   */
  it('does not describe a rule that did not run the way it describes one that did', async () => {
    const lineFor = async (outcome: string) => {
      const el = await render({ rule: rule({ last_outcome: {
        outcome, at: '2026-08-25T18:00:00+00:00', detail: null,
      } }) });
      return el.shadowRoot!.querySelector('.last-outcome')!.textContent!.trim();
    };
    const lines = await Promise.all(
      ['called', 'would_call', 'failed', 'blocked', 'skipped_stale'].map(lineFor),
    );
    expect(new Set(lines).size).toBe(5);
    for (const line of lines) expect(line).not.toBe('');
  });

  it('marks the three non-firing outcomes as bad and a plain success as not', async () => {
    const classFor = async (outcome: string) => {
      const el = await render({ rule: rule({ last_outcome: {
        outcome, at: '2026-08-25T18:00:00+00:00', detail: null,
      } }) });
      return [...el.shadowRoot!.querySelector('.last-outcome')!.classList];
    };
    for (const bad of ['failed', 'blocked', 'skipped_stale']) {
      expect(await classFor(bad), bad).toContain('bad');
    }
    expect(await classFor('called')).not.toContain('bad');
    expect(await classFor('would_call')).not.toContain('bad');
  });

  /**
   * `called` AND a diagnostic, at once. The call genuinely happened, so
   * the outcome is not `failed` - but one named entity silently did
   * nothing, and a row saying only "fired" is precisely the quiet failure
   * this integration exists to prevent. So the two compose rather than
   * one displacing the other.
   */
  it('says a rule fired and still names the entity that does not exist', async () => {
    const el = await render({ rule: rule({ last_outcome: {
      outcome: 'called', at: '2026-08-25T18:00:00+00:00', detail: null,
      unknown_targets: ['light.typo'],
    } }) });
    const line = el.shadowRoot!.querySelector('.last-outcome')!;
    expect(line.textContent).toContain('light.typo');
    // Not silently promoted to a failure, and not silently a plain success.
    expect([...line.classList]).toContain('bad');
  });

  it('says a rule fired and reached nothing, without calling it a failure', async () => {
    const el = await render({ rule: rule({ last_outcome: {
      outcome: 'called', at: '2026-08-25T18:00:00+00:00', detail: null,
      no_live_targets: true,
    } }) });
    const text = el.shadowRoot!.querySelector('.last-outcome')!.textContent!;
    expect(text).toContain('reached no entity that exists');
    // The wording the engine and the logbook already use for this - NOT
    // the word "failed", which would blame a typo that is not there.
    expect(text.toLowerCase()).not.toContain('failed');
  });

  /**
   * A total miss already reads "no such entity: ..." in `detail`, because
   * that is what the engine puts in the failed result's `error`. Saying it
   * twice on one line is how the logbook's own de-duplication earned its
   * comment; the card must not reintroduce it.
   */
  it('does not say "no such entity" twice when the detail already says it', async () => {
    const el = await render({ rule: rule({ last_outcome: {
      outcome: 'failed', at: '2026-08-25T18:00:00+00:00',
      detail: 'no such entity: light.typo',
      unknown_targets: ['light.typo'],
    } }) });
    const text = el.shadowRoot!.querySelector('.last-outcome')!.textContent!;
    expect(text.match(/no such entity/g)!).toHaveLength(1);
  });

  it('says WHEN it happened, so last week cannot pass for tonight', async () => {
    const el = await render({ rule: rule({ last_outcome: {
      outcome: 'blocked', at: '2026-08-25T18:00:00+00:00', detail: 'nope',
    } }) });
    const when = el.shadowRoot!.querySelector('.last-outcome-at');
    expect(when).not.toBeNull();
    expect(when!.textContent!.trim()).not.toBe('');
  });

  it('shows no timestamp at all rather than "Invalid Date"', async () => {
    const el = await render({ rule: rule({ last_outcome: {
      outcome: 'blocked', at: 'not-a-timestamp', detail: 'nope',
    } }) });
    expect(el.shadowRoot!.querySelector('.last-outcome-at')).toBeNull();
    // ...and the verdict itself still renders: a bad timestamp must not
    // take the reason down with it.
    expect(el.shadowRoot!.textContent).toContain('nope');
  });

  it('still says something for an outcome it does not recognise', async () => {
    const el = await render({ rule: rule({ last_outcome: {
      outcome: 'invented_by_a_newer_server',
      at: '2026-08-25T18:00:00+00:00', detail: null,
    } }) });
    const text = el.shadowRoot!.querySelector('.last-outcome')!.textContent!;
    expect(text.trim()).not.toBe('');
    expect(text).not.toContain('undefined');
  });

  it('says nothing at all for a rule that has never run', async () => {
    const el = await render({ rule: rule({ last_outcome: null }) });
    expect(el.shadowRoot!.querySelector('.last-outcome')).toBeNull();
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
