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

/**
 * The target-row suppression. See service-editor.ts's class docstring for
 * why the row exists at all and why hiding it is not optional.
 *
 * happy-dom has no real `ha-service-control`, so these build a stand-in
 * with its own shadow root holding the two kinds of `ha-selector` HA puts
 * there: the target row, and a per-field selector. That is exactly the
 * discrimination the production code has to get right, and it is testable
 * without HA.
 */
function fakeControl(el: any, selectors: unknown[]) {
  const control = control_(el);
  const root = control.attachShadow({ mode: 'open' });
  const made: any[] = [];
  for (const selector of selectors) {
    const node = document.createElement('ha-selector');
    (node as any).selector = selector;
    root.appendChild(node);
    made.push(node);
  }
  return made;
}

function control_(el: any) {
  return el.shadowRoot!.querySelector('ha-service-control');
}

function hidden(node: any) {
  return node.style.getPropertyValue('display') === 'none';
}

describe('shabbat-service-editor target-row suppression', () => {
  it("hides HA's own target row, which the card would otherwise discard", async () => {
    const el = await render({ action: 'switch.turn_on' });
    const [target] = fakeControl(el, [{ target: { entity: [] } }]);
    expect(el.suppressTargetRows()).toBe(1);
    expect(hidden(target)).toBe(true);
  });

  it('leaves per-field selectors alone', async () => {
    const el = await render({ action: 'climate.set_temperature' });
    const [target, hvac, temperature] = fakeControl(el, [
      { target: { entity: [] } },
      { state: { hide_states: [] } },
      { number: { min: 16, max: 32 } },
    ]);
    expect(el.suppressTargetRows()).toBe(1);
    expect(hidden(target)).toBe(true);
    // Stated as absences: hiding the schema-derived form would delete the
    // entire point of v2 on the frontend, and a filter that matched
    // everything would pass the assertion above.
    expect(hidden(hvac)).toBe(false);
    expect(hidden(temperature)).toBe(false);
  });

  it('matches on the selector shape, not on HA’s class name', async () => {
    const el = await render({ action: 'switch.turn_on' });
    const [target] = fakeControl(el, [{ target: {} }]);
    // No `class` attribute at all: HA calls this row `.target-selector`
    // today, and keying on that name would make a rename silently
    // reintroduce the duplicate picker.
    expect(target.getAttribute('class')).toBe(null);
    expect(el.suppressTargetRows()).toBe(1);
    expect(hidden(target)).toBe(true);
  });

  it('reports the count it found, so a shape change is observable', async () => {
    const el = await render({ action: 'switch.turn_on' });
    fakeControl(el, [{ target: {} }]);
    el.suppressTargetRows();
    expect(el.getAttribute('data-target-rows-suppressed')).toBe('1');
  });

  it('reports zero rather than throwing when there is no target row', async () => {
    const el = await render({ action: 'script.dev_beep' });
    const [field] = fakeControl(el, [{ object: {} }]);
    expect(el.suppressTargetRows()).toBe(0);
    expect(hidden(field)).toBe(false);
    // Zero, not absent: "we looked and found none" and "we never looked"
    // are different states, and only one of them is a bug.
    expect(el.getAttribute('data-target-rows-suppressed')).toBe('0');
  });

  it('survives ha-service-control having no shadow root at all', async () => {
    const el = await render();
    expect(el.suppressTargetRows()).toBe(0);
  });
});
