import { describe, expect, it } from 'vitest';
import '../src/target-editor';

async function render(props: Record<string, unknown> = {}) {
  const el = document.createElement('shabbat-target-editor') as HTMLElement &
    Record<string, any>;
  Object.assign(el, {
    hass: { states: {} }, value: {}, inherited: {},
    disabled: false, language: 'en', ...props,
  });
  document.body.appendChild(el);
  await el.updateComplete;
  return el;
}

function selector(el: any) {
  return el.shadowRoot.querySelector('ha-selector');
}

describe('shabbat-target-editor', () => {
  it('hands ha-selector a target selector and the current value', async () => {
    const el = await render({ value: { entity_id: ['switch.a'] } });
    const sel = selector(el);
    expect(sel).not.toBeNull();
    expect(sel.selector).toEqual({ target: {} });
    expect(sel.value).toEqual({ entity_id: ['switch.a'] });
    expect(sel.hass).toBe(el.hass);
  });

  it('re-emits ha-selector value-changed as target-changed', async () => {
    const el = await render();
    const seen: unknown[] = [];
    el.addEventListener('target-changed', (e: Event) => {
      seen.push((e as CustomEvent).detail.value);
    });
    selector(el).dispatchEvent(new CustomEvent('value-changed', {
      detail: { value: { area_id: ['salon'] } },
    }));
    expect(seen).toEqual([{ area_id: ['salon'] }]);
  });

  it('normalises a cleared target to an empty object, never undefined', async () => {
    const el = await render({ value: { entity_id: ['switch.a'] } });
    const seen: unknown[] = [];
    el.addEventListener('target-changed', (e: Event) => {
      seen.push((e as CustomEvent).detail.value);
    });
    selector(el).dispatchEvent(new CustomEvent('value-changed', {
      detail: { value: undefined },
    }));
    expect(seen).toEqual([{}]);
  });

  it('says the target is inherited when it has none of its own', async () => {
    const el = await render({
      value: {}, inherited: { entity_id: ['switch.shared'] },
    });
    expect(el.shadowRoot!.textContent).toContain('switch.shared');
  });

  it('does not mention inheritance once the rule has its own target', async () => {
    const el = await render({
      value: { entity_id: ['switch.a'] },
      inherited: { entity_id: ['switch.shared'] },
    });
    expect(el.shadowRoot!.textContent).not.toContain('switch.shared');
  });

  it('disables the selector when the user cannot write', async () => {
    const el = await render({ disabled: true });
    expect(selector(el).disabled).toBe(true);
  });
});
