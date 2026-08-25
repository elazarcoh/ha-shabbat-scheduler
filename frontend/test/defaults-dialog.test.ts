import { describe, expect, it } from 'vitest';
import '../src/defaults-dialog';

async function render(props: Record<string, unknown> = {}) {
  const el = document.createElement('shabbat-defaults-dialog') as HTMLElement &
    Record<string, any>;
  Object.assign(el, {
    defaults: {
      target: { entity_id: ['climate.salon'] },
      data: { temperature: 26 },
    },
    canWrite: true, busy: false, error: null, language: 'en', ...props,
  });
  document.body.appendChild(el);
  await el.updateComplete;
  return el;
}

/**
 * This dialog is READ-ONLY until Plan 2 builds a target/data editor.
 *
 * v1's editor wrote `{devices, settings}`; `validate_defaults`
 * (rule_schema.py) now accepts exactly `{target, data}`, so every press of
 * the old save button would be rejected by the server. A save button that
 * cannot succeed is worse than none, and a form that quietly rewrote the
 * defaults into a v1 shape would be worse still - so the button is gone
 * and the truth is shown instead. The tests below pin BOTH halves: what it
 * shows, and that it offers no way to save.
 */
describe('shabbat-defaults-dialog', () => {
  it('shows the shared defaults as they actually are', async () => {
    const el = await render();
    const text = el.shadowRoot!.textContent!;
    expect(text).toContain('Shared defaults');
    expect(text).toContain('climate.salon');
    expect(text).toContain('temperature');
    expect(text).toContain('26');
  });

  it('offers no save button at all, to anyone', async () => {
    expect((await render()).shadowRoot!.querySelector('.save')).toBeNull();
    expect((await render({ canWrite: false })).shadowRoot!.querySelector('.save'))
      .toBeNull();
  });

  it('says the defaults are not editable here rather than looking broken', async () => {
    const el = await render();
    expect(el.shadowRoot!.textContent).toContain('Not editable here');
  });

  it('says so when there are no defaults, rather than showing a blank', async () => {
    const el = await render({ defaults: {} });
    expect((el.shadowRoot!.querySelector('.ro-target') as HTMLElement).textContent)
      .toContain('none');
    expect((el.shadowRoot!.querySelector('.ro-data') as HTMLElement).textContent)
      .toContain('none');
  });

  it('shows a server rejection and stays open', async () => {
    const el = await render({ error: "unknown field(s): ['temperature']" });
    expect(el.shadowRoot!.textContent).toContain('unknown field');
    expect(el.shadowRoot!.querySelector('.ro-target')).not.toBeNull();
  });

  it('closes on cancel', async () => {
    const el = await render();
    let closed = false;
    el.addEventListener('dialog-close', () => { closed = true; });
    (el.shadowRoot!.querySelector('button') as HTMLElement).click();
    expect(closed).toBe(true);
  });

  // The card must not keep a listener for an event this component can
  // never emit - that reads as a working feature. See card.ts.
  it('emits no defaults-save event when it is clicked through', async () => {
    const el = await render();
    let saved = false;
    el.addEventListener('defaults-save', () => { saved = true; });
    for (const button of el.shadowRoot!.querySelectorAll('button')) {
      (button as HTMLElement).click();
    }
    expect(saved).toBe(false);
  });
});
