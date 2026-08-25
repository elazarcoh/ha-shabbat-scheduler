import { LitElement, css, html } from 'lit';
import { customElement, property } from 'lit/decorators.js';
import type { Hass } from './types';

/**
 * The rule's action and its data, on Home Assistant's own service control.
 *
 * This is the whole point of v2 on the frontend: the form for every
 * service comes from Home Assistant's own schema for that service, so
 * this card carries no per-domain form code and gains support for new
 * services without changing.
 *
 * `<ha-service-control>` speaks a single `{action, target, data}` value,
 * and it HAS internal target logic. This card owns the target separately
 * (see `target-editor.ts`), so this element neither passes a target down
 * nor lets one back up. Dropping it on the way out is not defensive
 * coding: without it, a stray target from HA's element would silently
 * overwrite what the user chose in the target editor.
 *
 * WHY THE TARGET ROW IS HIDDEN, AND WHY THAT IS NOT OPTIONAL.
 *
 * The spec recorded that `ha-service-control` "does not render its own
 * target row on a dashboard", because its target UI needs
 * `ha-target-picker` and that element is not pre-registered outside the
 * automation editor. That was true in isolation and is FALSE in this
 * card, for a reason worth stating: HA's target row is itself an
 * `<ha-selector>` with a `{target: ...}` selector, and `ha-selector`
 * dynamically imports whatever it is handed. `target-editor.ts` renders
 * one of those in the same dialog - which is the whole reason it exists -
 * so by the time HA's row renders, the picker IS defined and HA's row
 * works. Verified in real Chromium against HA 2026.8.2 / frontend
 * 20260729.7, including with the card's own target editor removed
 * entirely: HA's row still loads its own picker. We created the duplicate
 * by solving the availability problem.
 *
 * That left two target pickers in the rule dialog, of which this element
 * silently discarded one - a user could pick a target in HA's row, watch
 * it be accepted, save, and lose it. Silent, and the discard was
 * deliberate, which makes it worse than an ordinary bug. In the DEFAULTS
 * dialog it was worse still: there the action is a throwaway used only to
 * shape the data form and is never saved, so HA's target row appeared
 * under a heading reading "Data" and anything set in it was dropped.
 *
 * There is no supported way to ask for that row to go away.
 * `ha-service-control`'s entire property list in this version is `hass`,
 * `value`, `disabled`, `narrow`, `showServiceId`, `hidePicker` and
 * `hideDescription` - read off the shipped bundle, and `hideTarget`
 * appears nowhere in the whole frontend - and the row renders
 * unconditionally whenever the service's schema has a `target` key. No
 * `::part` and no CSS custom property reaches it either. So it is hidden
 * by hand.
 *
 * The row is found by THE SHAPE OF ITS SELECTOR (`'target' in selector`)
 * rather than by HA's `.target-selector` class name, so a rename does not
 * break it, and per-field selectors - whose selectors are `{state: ...}`,
 * `{number: ...}` and so on - can never be caught by it. It is
 * unconditional rather than a property: "the action and its data, never
 * the target" is this element's contract, and a caller that could forget
 * to pass the flag would reintroduce exactly the bug this prevents.
 *
 * A `MutationObserver` rather than only `updated()`: HA's element owns its
 * own `_value` state and re-renders itself when the action changes, which
 * does not run our update cycle. The observer fires before paint, so the
 * row never flashes into view. `data-target-rows-suppressed` records how
 * many rows were found, so "HA changed shape and we no longer match" is
 * observable rather than silent - and e2e pins exactly one VISIBLE target
 * picker per dialog, so a fix that quietly stopped working fails a test
 * rather than costing someone their target.
 */
@customElement('shabbat-service-editor')
export class ShabbatServiceEditor extends LitElement {
  @property({ attribute: false }) hass: Hass | null = null;
  @property() action = '';
  @property({ attribute: false }) data: Record<string, unknown> = {};
  @property({ type: Boolean }) disabled = false;

  static override styles = css`
    :host { display: block; }
  `;

  override render() {
    return html`
      <div class="wrap">
        <ha-service-control
          .hass=${this.hass}
          .value=${{ action: this.action, data: this.data }}
          .disabled=${this.disabled}
          .showAdvanced=${this.hass?.userData?.showAdvanced === true}
          @value-changed=${this._onChange}
        ></ha-service-control>
      </div>
    `;
  }

  /**
   * Kept even though the row it defends against is now hidden. Hiding the
   * UI is what stops a user losing a target; dropping the value is what
   * makes "this element never speaks for the target" true regardless.
   * If the suppression ever stops matching, this is what still prevents
   * HA's row from overwriting the target editor's value.
   */
  private _onChange = (event: CustomEvent) => {
    const value = (event.detail?.value ?? {}) as Record<string, unknown>;
    this.dispatchEvent(new CustomEvent('service-changed', {
      detail: {
        action: typeof value.action === 'string' ? value.action : '',
        data: (typeof value.data === 'object' && value.data !== null
          ? value.data
          : {}) as Record<string, unknown>,
      },
    }));
  };

  private _observer: MutationObserver | null = null;

  private get _control(): (Element & { updateComplete?: Promise<unknown> }) | null {
    return this.shadowRoot?.querySelector('ha-service-control') ?? null;
  }

  override async updated() {
    // HA's element renders on its own cycle, so its shadow root may not
    // exist yet when ours has just finished. Nothing to await when
    // `ha-service-control` is not a defined element at all, which is the
    // case under happy-dom.
    const control = this._control;
    if (control?.updateComplete) await control.updateComplete;
    this.suppressTargetRows();
    this._watch();
  }

  override disconnectedCallback() {
    super.disconnectedCallback();
    this._observer?.disconnect();
    this._observer = null;
  }

  private _watch() {
    const root = this._control?.shadowRoot;
    if (this._observer || !root) return;
    // childList only, and not subtree: the target row is a direct child of
    // HA's shadow root, and watching the subtree would fire on every
    // keystroke inside every field for nothing.
    this._observer = new MutationObserver(() => this.suppressTargetRows());
    this._observer.observe(root, { childList: true });
  }

  /**
   * Hide every target row inside HA's element. See the class docstring.
   *
   * Public so a test can call it directly; also reflected onto
   * `data-target-rows-suppressed` so the count is inspectable from a
   * browser without reaching into this class.
   */
  suppressTargetRows(): number {
    const root = this._control?.shadowRoot;
    if (!root) return 0;
    const rows = [...root.querySelectorAll('ha-selector')].filter((element) => {
      const selector = (element as Element & { selector?: unknown }).selector;
      return (
        typeof selector === 'object' &&
        selector !== null &&
        'target' in (selector as Record<string, unknown>)
      );
    });
    for (const row of rows) {
      // `important`, because HA's own stylesheet sets `display: block` on
      // this row and a future `!important` there would otherwise win.
      (row as HTMLElement).style.setProperty('display', 'none', 'important');
    }
    this.setAttribute('data-target-rows-suppressed', String(rows.length));
    return rows.length;
  }
}
