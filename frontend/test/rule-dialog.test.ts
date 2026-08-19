import { describe, expect, it, vi } from 'vitest';
import '../src/rule-dialog';
import { ruleToForm } from '../src/format';
import type { RuleData } from '../src/types';

const existing: RuleData = {
  id: 'r1', profile: 1, day: '1', time: '11:00:00', action: 'on',
  devices: ['climate.salon'], settings: { temperature: 26 }, name: 'Morning',
  icon: null, enabled: true, script: null, variables: {},
  replay_on_restart: false, color: null,
};

async function render(props: Record<string, unknown> = {}) {
  const el = document.createElement('shabbat-rule-dialog') as HTMLElement &
    Record<string, any>;
  Object.assign(el, {
    rule: existing, day: '1', profile: 1, defaults: {}, states: {},
    canWrite: true, language: 'en', error: null, busy: false, ...props,
  });
  document.body.appendChild(el);
  await el.updateComplete;
  return el;
}

describe('shabbat-rule-dialog', () => {
  it('opens an existing rule with its values filled in', async () => {
    const el = await render();
    expect((el.shadowRoot!.querySelector('.time') as HTMLInputElement).value)
      .toBe('11:00:00');
    expect((el.shadowRoot!.querySelector('.name') as HTMLInputElement).value)
      .toBe('Morning');
    expect(el.shadowRoot!.textContent).toContain('Edit rule');
  });

  it('opens empty for a new rule, and offers no delete', async () => {
    const el = await render({ rule: null });
    expect(el.shadowRoot!.textContent).toContain('Add rule');
    expect(el.shadowRoot!.querySelector('.delete')).toBeNull();
    expect(el.shadowRoot!.querySelector('.duplicate')).toBeNull();
  });

  it('reports a save with the edited form, not the original rule', async () => {
    const el = await render();
    const listener = vi.fn();
    el.addEventListener('dialog-save', listener);

    const time = el.shadowRoot!.querySelector('.time') as HTMLInputElement;
    time.value = '12:30:00';
    time.dispatchEvent(new Event('change'));
    (el.shadowRoot!.querySelector('.save') as HTMLElement).click();

    const detail = (listener.mock.calls[0][0] as CustomEvent).detail;
    expect(detail.form.time).toBe('12:30:00');
    expect(detail.rule.id).toBe('r1');
  });

  it('shows the server error and stays open, keeping the input', async () => {
    const el = await render({ error: 'time is not a valid clock time' });
    expect(el.shadowRoot!.textContent).toContain('not a valid clock time');
    expect(el.shadowRoot!.querySelector('.form')).not.toBeNull();
  });

  it('disables everything and hides the actions for a read-only user', async () => {
    const el = await render({ canWrite: false });
    expect(el.shadowRoot!.textContent).toContain('do not have permission');
    expect(el.shadowRoot!.querySelector('.save')).toBeNull();
    expect(el.shadowRoot!.querySelector('.delete')).toBeNull();
    expect((el.shadowRoot!.querySelector('.time') as HTMLInputElement).disabled)
      .toBe(true);
  });

  it('disables the actions while a command is in flight', async () => {
    const el = await render({ busy: true });
    expect((el.shadowRoot!.querySelector('.save') as HTMLButtonElement).disabled)
      .toBe(true);
  });

  it('shows the advanced fields only once asked for', async () => {
    const el = await render();
    expect(el.shadowRoot!.querySelector('.icon')).toBeNull();
    (el.shadowRoot!.querySelector('.advanced-toggle') as HTMLElement).click();
    await el.updateComplete;
    expect(el.shadowRoot!.querySelector('.icon')).not.toBeNull();
  });

  it('asks for a script when the action is custom', async () => {
    const el = await render({
      rule: { ...existing, action: 'custom', script: 'script.boiler' },
    });
    expect((el.shadowRoot!.querySelector('.script') as HTMLInputElement).value)
      .toBe('script.boiler');
  });

  it('starts a seeded create from the seed, which is what makes duplicate duplicate', async () => {
    const el = await render({
      rule: null,
      seed: { ...ruleToForm(existing), time: '11:00:00' },
    });
    expect(el.shadowRoot!.textContent).toContain('Add rule');
    expect((el.shadowRoot!.querySelector('.name') as HTMLInputElement).value)
      .toBe('Morning');
    expect((el.shadowRoot!.querySelector('.time') as HTMLInputElement).value)
      .toBe('11:00:00');
    // Still a create - a duplicate that offered delete would delete the
    // rule it was copied from.
    expect(el.shadowRoot!.querySelector('.delete')).toBeNull();
  });
});
