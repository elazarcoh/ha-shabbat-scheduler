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

  it('normalises a missing action to the empty string, never undefined', async () => {
    const el = await render();
    const seen: any[] = [];
    el.addEventListener('service-changed', (e: Event) => {
      seen.push((e as CustomEvent).detail);
    });
    control(el).dispatchEvent(new CustomEvent('value-changed', {
      detail: { value: { data: { temperature: 24 } } },
    }));
    expect(seen).toStrictEqual([{ action: '', data: { temperature: 24 } }]);
  });

  /**
   * The mechanism of the blocker this suite could not see.
   *
   * `ha-service-control._serviceChanged` fires `{action, target}` with no
   * `data` key at all - read off HA 2026.8.2's shipped bundle - so this is
   * not a defensive corner, it is EVERY service change. Flattening it to
   * `{}` here is what silently wiped `defaults.data`, because the defaults
   * dialog could not then tell "HA said nothing about data" from "the user
   * emptied it".
   *
   * Asserts key ABSENCE explicitly, not by comparing whole objects:
   * Vitest's `toEqual` treats an omitted key as equal to `undefined`, so a
   * version of this that emitted `data: undefined` would pass a `toEqual`
   * against `{action: 'x'}`. This suite has been caught by that once
   * already.
   */
  it('omits data entirely when ha-service-control sends none', async () => {
    const el = await render();
    const seen: any[] = [];
    el.addEventListener('service-changed', (e: Event) => {
      seen.push((e as CustomEvent).detail);
    });
    control(el).dispatchEvent(new CustomEvent('value-changed', {
      // Byte-for-byte the shape HA emits on a service pick.
      detail: { value: {
        action: 'climate.set_temperature',
        target: { entity_id: ['climate.salon'] },
      } },
    }));
    expect(seen).toHaveLength(1);
    expect('data' in seen[0]).toBe(false);
    expect(seen[0]).toStrictEqual({ action: 'climate.set_temperature' });
  });

  /**
   * The other half, and the reason "omitted" has to be its own signal: an
   * explicitly empty `data` is a real edit (the user cleared every field)
   * and MUST come through, or nothing could ever empty a payload. Driven
   * in the direction where absent and empty differ, since a fix that
   * omitted the key in both cases would satisfy the test above alone.
   */
  it('emits an explicitly empty data as an empty object', async () => {
    const el = await render();
    const seen: any[] = [];
    el.addEventListener('service-changed', (e: Event) => {
      seen.push((e as CustomEvent).detail);
    });
    control(el).dispatchEvent(new CustomEvent('value-changed', {
      detail: { value: { action: 'switch.turn_on', data: {} } },
    }));
    expect('data' in seen[0]).toBe(true);
    expect(seen[0]).toStrictEqual({ action: 'switch.turn_on', data: {} });
  });

  /**
   * The branch the ledger recorded as "not reachable from what
   * ha-service-control actually emits" - a claim that turned out to be
   * wrong about the ABSENT case and is now covered for both. A `data` that
   * is not a container cannot mean "the user wants an empty payload", so
   * it is reported the same way silence is, and the stored value survives.
   * Guessing "empty" from garbage destroys data just as thoroughly as
   * guessing it from silence.
   */
  it('treats a non-object data as nothing said, not as empty', async () => {
    const el = await render();
    const seen: any[] = [];
    el.addEventListener('service-changed', (e: Event) => {
      seen.push((e as CustomEvent).detail);
    });
    for (const data of ['not_a_dict', 42, null]) {
      control(el).dispatchEvent(new CustomEvent('value-changed', {
        detail: { value: { action: 'switch.turn_on', data } },
      }));
    }
    expect(seen).toHaveLength(3);
    for (const detail of seen) {
      expect('data' in detail).toBe(false);
      expect(detail).toStrictEqual({ action: 'switch.turn_on' });
    }
  });

  it('disables the control when the user cannot write', async () => {
    const el = await render({ disabled: true });
    expect(control(el).disabled).toBe(true);
  });

  // Three tests asserting `showAdvanced` was forwarded lived here, and
  // they were deleted rather than repaired. `ha-service-control` has no
  // such property in this Home Assistant version - its full property list
  // is `hass, value, disabled, narrow, showServiceId, hidePicker,
  // hideDescription` - so nothing ever read what they proved was passed.
  // They passed only because happy-dom accepts any property on an element
  // it has never heard of, which makes them the exact shape this suite
  // spent a whole plan learning to distrust: a test that agrees with the
  // code and would agree just as readily with code that does nothing.
  //
  // Which advanced fields render is HA's decision, inside its own element.
  it('does not forward a property Home Assistant has no use for', async () => {
    const el = await render({
      hass: { states: {}, userData: { showAdvanced: true } },
    });
    expect('showAdvanced' in control(el)).toBe(false);
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
