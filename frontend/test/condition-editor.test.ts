import { describe, expect, it } from 'vitest';
import '../src/condition-editor';

async function render(props: Record<string, unknown> = {}) {
  const el = document.createElement('shabbat-condition-editor') as HTMLElement &
    Record<string, any>;
  Object.assign(el, {
    value: [], disabled: false, language: 'en', ...props,
  });
  document.body.appendChild(el);
  await el.updateComplete;
  return el;
}

const rows = (el: any) => el.shadowRoot!.querySelectorAll('.condition-row');
const areaFor = (el: any, i: number) =>
  rows(el)[i].querySelector('textarea') as HTMLTextAreaElement;

const stateCondition = { condition: 'state', entity_id: 'input_boolean.a', state: 'on' };

describe('shabbat-condition-editor', () => {
  it('shows nothing but an add button when there are no conditions', async () => {
    const el = await render();
    expect(rows(el).length).toBe(0);
    expect(el.shadowRoot!.querySelector('button.add-condition')).not.toBeNull();
  });

  it('renders one row per condition, as YAML', async () => {
    const el = await render({ value: [stateCondition] });
    expect(rows(el).length).toBe(1);
    expect(areaFor(el, 0).value).toContain('condition: state');
    expect(areaFor(el, 0).value).toContain('input_boolean.a');
  });

  it('emits the parsed condition when a row is edited', async () => {
    const el = await render({ value: [stateCondition] });
    const seen: any[] = [];
    el.addEventListener('condition-changed', (e: Event) => {
      seen.push((e as CustomEvent).detail.value);
    });
    const area = areaFor(el, 0);
    area.value = 'condition: state\nentity_id: input_boolean.b\nstate: "off"';
    area.dispatchEvent(new Event('change'));
    expect(seen).toEqual([[
      { condition: 'state', entity_id: 'input_boolean.b', state: 'off' },
    ]]);
  });

  it('does not emit while the YAML is unparseable, and says so', async () => {
    const el = await render({ value: [stateCondition] });
    const seen: any[] = [];
    el.addEventListener('condition-changed', (e: Event) => {
      seen.push((e as CustomEvent).detail.value);
    });
    const area = areaFor(el, 0);
    area.value = 'condition: [state';
    area.dispatchEvent(new Event('change'));
    await el.updateComplete;
    expect(seen).toEqual([]);
    expect(el.hasError).toBe(true);
    expect(rows(el)[0].querySelector('.row-error')).not.toBeNull();
  });

  it('clears the error once the YAML parses again', async () => {
    const el = await render({ value: [stateCondition] });
    const area = areaFor(el, 0);
    area.value = 'condition: [state';
    area.dispatchEvent(new Event('change'));
    await el.updateComplete;
    expect(el.hasError).toBe(true);
    area.value = 'condition: state\nentity_id: input_boolean.a\nstate: "on"';
    area.dispatchEvent(new Event('change'));
    await el.updateComplete;
    expect(el.hasError).toBe(false);
  });

  it('rejects YAML that is valid but is not a mapping', async () => {
    const el = await render({ value: [stateCondition] });
    const seen: any[] = [];
    el.addEventListener('condition-changed', (e: Event) => {
      seen.push((e as CustomEvent).detail.value);
    });
    const area = areaFor(el, 0);
    area.value = '- one\n- two';
    area.dispatchEvent(new Event('change'));
    await el.updateComplete;
    expect(seen).toEqual([]);
    expect(el.hasError).toBe(true);
  });

  it('adds an empty condition row', async () => {
    const el = await render();
    const seen: any[] = [];
    el.addEventListener('condition-changed', (e: Event) => {
      seen.push((e as CustomEvent).detail.value);
    });
    (el.shadowRoot!.querySelector('button.add-condition') as HTMLButtonElement).click();
    expect(seen).toEqual([[{ condition: 'state' }]]);
  });

  it('removes the row that was pressed, not the first', async () => {
    const second = { condition: 'time', after: '20:00:00' };
    const el = await render({ value: [stateCondition, second] });
    const seen: any[] = [];
    el.addEventListener('condition-changed', (e: Event) => {
      seen.push((e as CustomEvent).detail.value);
    });
    (rows(el)[1].querySelector('button.remove-condition') as HTMLButtonElement).click();
    expect(seen).toEqual([[stateCondition]]);
  });

  it('disables every control when the user cannot write', async () => {
    const el = await render({ value: [stateCondition], disabled: true });
    expect(areaFor(el, 0).disabled).toBe(true);
    expect(
      (el.shadowRoot!.querySelector('button.add-condition') as HTMLButtonElement).disabled,
    ).toBe(true);
  });
});
