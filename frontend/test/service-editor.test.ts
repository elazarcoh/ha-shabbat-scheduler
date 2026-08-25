import { describe, expect, it } from 'vitest';
import '../src/service-editor';

async function render(props: Record<string, unknown> = {}) {
  const el = document.createElement('shabbat-service-editor') as HTMLElement &
    Record<string, any>;
  Object.assign(el, {
    hass: { states: {} }, action: '', data: {},
    disabled: false, language: 'en', ...props,
  });
  document.body.appendChild(el);
  await el.updateComplete;
  return el;
}

function control(el: any) {
  return el.shadowRoot!.querySelector('ha-service-control');
}

describe('shabbat-service-editor', () => {
  it('hands ha-service-control the action and data as one value', async () => {
    const el = await render({
      action: 'climate.set_temperature', data: { temperature: 26 },
    });
    expect(control(el).value).toEqual({
      action: 'climate.set_temperature', data: { temperature: 26 },
    });
    expect(control(el).hass).toBe(el.hass);
  });

  it('never hands it a target, which this card owns separately', async () => {
    const el = await render({ action: 'switch.turn_on' });
    expect(control(el).value.target).toBeUndefined();
  });

  it('splits value-changed back into action and data', async () => {
    const el = await render();
    const seen: any[] = [];
    el.addEventListener('service-changed', (e: Event) => {
      seen.push((e as CustomEvent).detail);
    });
    control(el).dispatchEvent(new CustomEvent('value-changed', {
      detail: { value: {
        action: 'climate.set_temperature', data: { temperature: 24 },
      } },
    }));
    expect(seen).toEqual([{
      action: 'climate.set_temperature', data: { temperature: 24 },
    }]);
  });

  it('drops any target ha-service-control emits', async () => {
    const el = await render();
    const seen: any[] = [];
    el.addEventListener('service-changed', (e: Event) => {
      seen.push((e as CustomEvent).detail);
    });
    control(el).dispatchEvent(new CustomEvent('value-changed', {
      detail: { value: {
        action: 'switch.turn_on',
        target: { entity_id: ['switch.stray'] },
        data: {},
      } },
    }));
    expect(seen).toEqual([{ action: 'switch.turn_on', data: {} }]);
  });

  it('normalises a missing action or data rather than emitting undefined', async () => {
    const el = await render();
    const seen: any[] = [];
    el.addEventListener('service-changed', (e: Event) => {
      seen.push((e as CustomEvent).detail);
    });
    control(el).dispatchEvent(new CustomEvent('value-changed', {
      detail: { value: {} },
    }));
    expect(seen).toEqual([{ action: '', data: {} }]);
  });

  it('disables the control when the user cannot write', async () => {
    const el = await render({ disabled: true });
    expect(control(el).disabled).toBe(true);
  });

  it('shows advanced fields when the user has that HA preference set', async () => {
    const el = await render({
      hass: { states: {}, userData: { showAdvanced: true } },
    });
    expect(control(el).showAdvanced).toBe(true);
  });

  it('does not show advanced fields when there is no userData at all', async () => {
    const el = await render({ hass: { states: {} } });
    expect(control(el).showAdvanced).toBe(false);
  });

  it('does not show advanced fields when the user has explicitly turned them off', async () => {
    const el = await render({
      hass: { states: {}, userData: { showAdvanced: false } },
    });
    expect(control(el).showAdvanced).toBe(false);
  });
});
