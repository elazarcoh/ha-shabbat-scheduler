import { describe, expect, it, vi } from 'vitest';
import '../src/simulate-dialog';

function fakeHass(previewResult: unknown, runResult: unknown) {
  const callWS = vi.fn(async (message: any) => {
    if (message.type === 'shabbat_scheduler/preview') return previewResult;
    return runResult;
  });
  return { callWS };
}

async function render(hass: unknown, props: Record<string, unknown> = {}) {
  const el = document.createElement('shabbat-simulate-dialog') as HTMLElement &
    Record<string, any>;
  Object.assign(el, { hass, language: 'en', canWrite: true, ...props });
  document.body.appendChild(el);
  await el.updateComplete;
  await el.updateComplete; // second tick: the preview load is async
  return el;
}

describe('shabbat-simulate-dialog', () => {
  it('loads and renders the preview for the default 1-day profile on connect', async () => {
    const hass = fakeHass(
      { profile: 1, rules: [{ when: '2026-08-15T11:00:00+03:00', rule_id: 'r1', name: 'Morning', action: 'a.b', target: {}, data: {} }], conflicts: [], warnings: [] },
      { results: [] },
    );
    const el = await render(hass);
    expect(hass.callWS).toHaveBeenCalledWith({ type: 'shabbat_scheduler/preview', block_length: 1 });
    expect(el.shadowRoot!.textContent).toContain('Morning');
  });

  it('reloads the preview when the profile picker changes', async () => {
    const hass = fakeHass({ profile: 3, rules: [], conflicts: [], warnings: [] }, { results: [] });
    const el = await render(hass);
    const select = el.shadowRoot!.querySelector('select.profile') as HTMLSelectElement;
    select.value = '3';
    select.dispatchEvent(new Event('change'));
    await el.updateComplete;
    await el.updateComplete;
    expect(hass.callWS).toHaveBeenLastCalledWith({ type: 'shabbat_scheduler/preview', block_length: 3 });
  });

  it('offers a day picker scoped to the selected profile', async () => {
    const hass = fakeHass({ profile: 1, rules: [], conflicts: [], warnings: [] }, { results: [] });
    const el = await render(hass, {});
    const select = el.shadowRoot!.querySelector('select.profile') as HTMLSelectElement;
    select.value = '2';
    select.dispatchEvent(new Event('change'));
    await el.updateComplete;
    await el.updateComplete;
    const days = [...el.shadowRoot!.querySelectorAll('select.day option')].map(
      (o) => (o as HTMLOptionElement).value,
    );
    expect(days).toEqual(['erev', '1', '2']);
  });

  it('sends run_day with force_conditions from the toggle', async () => {
    const hass = fakeHass({ profile: 1, rules: [], conflicts: [], warnings: [] }, { results: [] });
    const el = await render(hass);
    (el.shadowRoot!.querySelector('ha-selector.force-conditions') as any).dispatchEvent(
      new CustomEvent('value-changed', { detail: { value: true } }),
    );
    (el.shadowRoot!.querySelector('button.run-simulate') as HTMLElement).click();
    await el.updateComplete;
    expect(hass.callWS).toHaveBeenCalledWith({
      type: 'shabbat_scheduler/rules/run_day',
      profile: 1, day: 'erev', simulate: true, force_conditions: true,
    });
  });

  it('renders one result row per rule, outcome formatted', async () => {
    const hass = fakeHass(
      { profile: 1, rules: [], conflicts: [], warnings: [] },
      { results: [{ rule_id: 'r1', results: [{ outcome: 'would_call' }] }] },
    );
    const el = await render(hass);
    (el.shadowRoot!.querySelector('button.run-simulate') as HTMLElement).click();
    await el.updateComplete;
    await el.updateComplete; // second tick: the run_day round trip is async
    expect(el.shadowRoot!.textContent).toContain('Would have fired');
  });

  it('hides the run buttons and disables the force-conditions toggle for a reader', async () => {
    const hass = fakeHass({ profile: 1, rules: [], conflicts: [], warnings: [] }, { results: [] });
    const el = await render(hass, { canWrite: false });
    expect(el.shadowRoot!.querySelector('button.run-simulate')).toBeNull();
    expect(el.shadowRoot!.querySelector('button.run-real')).toBeNull();
    expect(
      (el.shadowRoot!.querySelector('ha-selector.force-conditions') as any).disabled,
    ).toBe(true);
  });

  describe('the preview list is filtered to the selected day', () => {
    it('only shows rules whose `day` matches the currently-selected day', async () => {
      const hass = fakeHass(
        {
          profile: 1,
          rules: [
            { when: '2026-08-14T17:00:00+03:00', rule_id: 'erev-r', name: 'Erev rule', action: 'a.b', target: {}, data: {}, day: 'erev' },
            { when: '2026-08-15T11:00:00+03:00', rule_id: 'day1-r', name: 'Day1 rule', action: 'a.b', target: {}, data: {}, day: '1' },
          ],
          conflicts: [], warnings: [],
        },
        { results: [] },
      );
      const el = await render(hass);
      // Default day is 'erev'.
      expect(el.shadowRoot!.textContent).toContain('Erev rule');
      expect(el.shadowRoot!.textContent).not.toContain('Day1 rule');

      const select = el.shadowRoot!.querySelector('select.day') as HTMLSelectElement;
      select.value = '1';
      select.dispatchEvent(new Event('change'));
      await el.updateComplete;

      expect(el.shadowRoot!.textContent).not.toContain('Erev rule');
      expect(el.shadowRoot!.textContent).toContain('Day1 rule');
    });

    it('keeps a rule with no `day` at all, from a server too old to send it', async () => {
      const hass = fakeHass(
        {
          profile: 1,
          rules: [
            { when: '2026-08-14T17:00:00+03:00', rule_id: 'r1', name: 'Undated rule', action: 'a.b', target: {}, data: {} },
          ],
          conflicts: [], warnings: [],
        },
        { results: [] },
      );
      const el = await render(hass);
      expect(el.shadowRoot!.textContent).toContain('Undated rule');
    });
  });

  it('names results by the rule, not its raw id', async () => {
    const hass = fakeHass(
      {
        profile: 1,
        rules: [
          { when: '2026-08-14T17:00:00+03:00', rule_id: 'r1', name: 'Lights on', action: 'light.turn_on', target: {}, data: {}, day: 'erev' },
        ],
        conflicts: [], warnings: [],
      },
      { results: [{ rule_id: 'r1', results: [{ outcome: 'would_call' }] }] },
    );
    const el = await render(hass);
    (el.shadowRoot!.querySelector('button.run-simulate') as HTMLElement).click();
    await el.updateComplete;
    await el.updateComplete;
    const resultsText = el.shadowRoot!.querySelector('.results')!.textContent!;
    expect(resultsText).toContain('Lights on');
    expect(resultsText).not.toContain('r1:');
  });

  describe('running for real requires an explicit inline confirmation', () => {
    it('does not fire run_day on the first click of "Run this day for real"', async () => {
      const hass = fakeHass({ profile: 1, rules: [], conflicts: [], warnings: [] }, { results: [] });
      const el = await render(hass);
      (el.shadowRoot!.querySelector('button.run-real') as HTMLElement).click();
      await el.updateComplete;
      expect(hass.callWS).not.toHaveBeenCalledWith(
        expect.objectContaining({ type: 'shabbat_scheduler/rules/run_day', simulate: false }),
      );
      expect(el.shadowRoot!.querySelector('.run-real-confirm')).not.toBeNull();
    });

    it('fires a real run_day only after the inline confirm is also clicked', async () => {
      const hass = fakeHass({ profile: 1, rules: [], conflicts: [], warnings: [] }, { results: [] });
      const el = await render(hass);
      (el.shadowRoot!.querySelector('button.run-real') as HTMLElement).click();
      await el.updateComplete;
      (el.shadowRoot!.querySelector('button.run-real-confirmed') as HTMLElement).click();
      await el.updateComplete;
      expect(hass.callWS).toHaveBeenCalledWith(
        expect.objectContaining({ type: 'shabbat_scheduler/rules/run_day', simulate: false }),
      );
    });

    it('cancelling the inline confirm fires nothing', async () => {
      const hass = fakeHass({ profile: 1, rules: [], conflicts: [], warnings: [] }, { results: [] });
      const el = await render(hass);
      (el.shadowRoot!.querySelector('button.run-real') as HTMLElement).click();
      await el.updateComplete;
      (el.shadowRoot!.querySelector('button.run-real-cancel') as HTMLElement).click();
      await el.updateComplete;
      expect(el.shadowRoot!.querySelector('.run-real-confirm')).toBeNull();
      expect(hass.callWS).not.toHaveBeenCalledWith(
        expect.objectContaining({ type: 'shabbat_scheduler/rules/run_day' }),
      );
    });
  });
});
