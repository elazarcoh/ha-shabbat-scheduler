import { LitElement, css, html, nothing } from 'lit';
import { customElement, property, state } from 'lit/decorators.js';
import { dump, load } from 'js-yaml';
import { t } from './strings';

/** What "Add condition" inserts: the shortest thing that is still a condition. */
const NEW_CONDITION = { condition: 'state' };

/**
 * The rule's conditions, as a list of YAML documents.
 *
 * A Home Assistant condition config is an arbitrary nested mapping, and
 * this card has no business knowing their schemas - the whole point of v2
 * is that Home Assistant owns *what*. There is no dashboard-safe
 * structured condition editor to embed (see the spec's frontend
 * availability findings), and hand-writing one would mean duplicating
 * HA's condition schemas here, which is exactly what this plan removes
 * elsewhere. So this element owns the LIST - add, remove, per-row errors -
 * and each entry's body is text.
 *
 * A `<textarea>` rather than `ha-code-editor` for the same reason the
 * replay editor uses a plain input: element availability on a dashboard
 * is not something to depend on.
 *
 * UNPARSEABLE TEXT IS NEVER EMITTED. The alternative - emitting a partial
 * parse - would silently save a condition the user did not write, and a
 * condition that does not mean what it says is worse than one that is
 * visibly broken. `hasError` lets the dialog refuse to save.
 */
@customElement('shabbat-condition-editor')
export class ShabbatConditionEditor extends LitElement {
  @property({ attribute: false }) value: Record<string, unknown>[] = [];
  @property({ type: Boolean }) disabled = false;
  @property() language = 'en';

  /** Per-row parse errors, keyed by index. Read by the dialog via `hasError`. */
  @state() private _errors: Record<number, string> = {};

  get hasError(): boolean {
    return Object.keys(this._errors).length > 0;
  }

  static override styles = css`
    .condition-row {
      display: flex;
      gap: 8px;
      align-items: flex-start;
      margin-block: 8px;
    }
    textarea {
      font-family: var(--code-font-family, monospace);
      font-size: 0.85em;
      flex: 1;
      min-inline-size: 0;
      min-block-size: 4.5em;
      padding: 6px;
    }
    .row-error {
      color: var(--error-color, #d64545);
      font-size: 0.8em;
      margin-block-start: 2px;
    }
    .body { flex: 1; min-inline-size: 0; }
    .help { color: var(--secondary-text-color, #666); font-size: 0.85em; }
    button {
      font: inherit;
      padding-block: 4px;
      padding-inline: 8px;
      border-radius: 6px;
      border: 1px solid var(--divider-color, #e0e0e0);
      background: var(--card-background-color, #fff);
      color: inherit;
      cursor: pointer;
    }
    button[disabled] { opacity: 0.5; cursor: not-allowed; }
  `;

  override render() {
    return html`
      <div class="wrap">
        <div class="help">${t(this.language, 'conditions_help')}</div>
        ${this.value.map((item, index) => this._row(item, index))}
        <button
          class="add-condition"
          ?disabled=${this.disabled}
          @click=${this._onAdd}
        >
          ${t(this.language, 'add_condition')}
        </button>
      </div>
    `;
  }

  private _row(item: Record<string, unknown>, index: number) {
    const error = this._errors[index];
    return html`
      <div class="condition-row">
        <div class="body">
          <textarea
            .value=${dump(item).trimEnd()}
            ?disabled=${this.disabled}
            @change=${(event: Event) => this._onEdit(event, index)}
          ></textarea>
          ${error
            ? html`<div class="row-error">${error}</div>`
            : nothing}
        </div>
        <button
          class="remove-condition"
          ?disabled=${this.disabled}
          @click=${() => this._onRemove(index)}
        >
          ${t(this.language, 'remove_condition')}
        </button>
      </div>
    `;
  }

  private _emit(value: Record<string, unknown>[]) {
    this.dispatchEvent(
      new CustomEvent('condition-changed', { detail: { value } }),
    );
  }

  private _setError(index: number, message: string | null) {
    const errors = { ...this._errors };
    if (message === null) delete errors[index];
    else errors[index] = message;
    this._errors = errors;
  }

  private _onEdit(event: Event, index: number) {
    const text = (event.target as HTMLTextAreaElement).value;
    let parsed: unknown;
    try {
      parsed = load(text);
    } catch {
      this._setError(index, t(this.language, 'condition_unparseable'));
      return;
    }
    // A condition is a mapping. A list or a bare scalar parses fine and
    // would be accepted by `load` while being meaningless as a condition,
    // so it is rejected here rather than sent to the server to fail.
    if (
      parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)
    ) {
      this._setError(index, t(this.language, 'condition_not_a_mapping'));
      return;
    }
    this._setError(index, null);
    const next = [...this.value];
    next[index] = parsed as Record<string, unknown>;
    this._emit(next);
  }

  private _onAdd = () => {
    this._emit([...this.value, { ...NEW_CONDITION }]);
  };

  private _onRemove(index: number) {
    // Errors are keyed by index, so removing a row shifts every later row
    // up by one. Re-index rather than clear: clearing would silently drop
    // a genuine error on an untouched row (its broken text is still right
    // there in that row's textarea), and hasError would report "clean"
    // while a row still holds text that was never saved.
    const errors: Record<number, string> = {};
    for (const [key, message] of Object.entries(this._errors)) {
      const i = Number(key);
      if (i < index) errors[i] = message;
      else if (i > index) errors[i - 1] = message;
      // i === index: this row is being removed, so its error goes with it.
    }
    this._errors = errors;
    this._emit(this.value.filter((_, i) => i !== index));
  }
}
