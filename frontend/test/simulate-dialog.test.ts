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
  Object.assign(el, { hass, language: 'en', ...props });
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
});
