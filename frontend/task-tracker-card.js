// javascript
class TaskTracker extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this.shadowRoot.addEventListener("click", (e) => {
      if (e.target.closest(".mark-done-btn")) this._markAsDone();
    });
  }

  _t(key) {
    return this._hass.localize(`component.task_tracker.entity.ui.${key}.name`);
  }

  set hass(hass) {
    this._hass = hass;
    const entity = hass.states[this.config?.entity];
    if (entity === this._entity) return;
    this._entity = entity;
    this._render();
  }

  setConfig(config) {
    if (!config.entity) {
      throw new Error("You need to define an entity");
    }
    this.config = config;
  }

  _stateColor(state) {
    switch (state) {
      case "due":      return "#e74c3c";
      case "due_soon": return "#e67e22";
      case "done":     return "#27ae60";
      case "inactive": return "#3498db";
      default:         return "#95a5a6";
    }
  }

  _scheduleStr(attrs) {
    const repeatMode = attrs.repeat_mode;
    if (repeatMode !== "repeat_every") {
      const val = attrs.task_interval_value;
      const type = attrs.task_interval_type;
      const sp = val === 1 ? "singular" : "plural";
      return [this._t("interval"), `${val}\u00a0${this._t(`${type}_${sp}`)}`];
    }
    const t = attrs.repeat_every_type;
    if (t === "repeat_every_weekday") {
      const n = attrs.repeat_weeks_interval || 1;
      const sp = n === 1 ? "singular" : "plural";
      const weekday = this._t(attrs.repeat_weekday);
      const nStr = n === 1 ? "" : `\u00a0${n}`;
      return [this._t("schedule"),
        `${this._t("every")}${nStr}\u00a0${this._t(`week_${sp}`)}\u00a0${this._t("on")}\u00a0${weekday}`];
    }
    if (t === "repeat_every_day_of_month") {
      return [this._t("schedule"),
        `${this._t("day_of_month_prefix")}\u00a0${attrs.repeat_month_day}\u00a0${this._t("of_month")}`];
    }
    if (t === "repeat_every_weekday_of_month") {
      const nth = this._t(`occurrence_${attrs.repeat_nth_occurrence}`);
      const weekday = this._t(attrs.repeat_weekday);
      return [this._t("schedule"),
        `${nth}\u00a0${weekday}\u00a0${this._t("of_month")}`];
    }
    if (t === "repeat_every_days_before_end_of_month") {
      const n = attrs.repeat_days_before_end ?? 0;
      if (n === 0) return [this._t("schedule"), this._t("last_day_of_month")];
      const sp = n === 1 ? "singular" : "plural";
      return [this._t("schedule"), `${n}\u00a0${this._t(`days_before_end_of_month_${sp}`)}`];
    }
    return [this._t("schedule"), "—"];
  }

  _render() {
    if (!this._hass || !this.config) return;

    const entityId = this.config.entity;
    const entity = this._hass.states[entityId];
    const attrs = (entity && entity.attributes) || {};
    const stateStr = (entity && entity.state) || "unavailable";
    const name = attrs.friendly_name || entityId;

    const haLocale =
      (this._hass && this._hass.locale && this._hass.locale.language) ||
      undefined;

    const formatDate = (dateStr) =>
      new Date(dateStr).toLocaleDateString(haLocale, {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
      });

    const [scheduleLabel, scheduleValue] = this._scheduleStr(attrs);

    const lastDoneStr = formatDate(attrs.last_done);
    const dueDateStr = formatDate(attrs.due_date);

    let dueLabel, dueValue;
    if (attrs.due_in > 0) {
      dueLabel = this._t("due_in");
      const sp = attrs.due_in === 1 ? "singular" : "plural";
      dueValue = `${attrs.due_in}\u00a0${this._t(`day_${sp}`)}`;
    } else {
      dueLabel = this._t("overdue_by");
      const sp = attrs.overdue_by === 1 ? "singular" : "plural";
      dueValue = `${attrs.overdue_by}\u00a0${this._t(`day_${sp}`)}`;
    }

    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; }
        ha-card { color: var(--primary-text-color); }
        .card-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 12px 16px;
          font-size: 1.1rem;
          font-weight: 600;
          border-bottom: 1px solid rgba(0,0,0,0.1);
          background: ${this._stateColor(stateStr)};
          color: white;
          border-radius: 8px 8px 0 0;
        }
        .task-name {
          flex: 1;
          margin-right: 8px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .badge {
          display: inline-block;
          padding: 2px 10px;
          border-radius: 12px;
          font-size: 0.78em;
          background: rgba(255,255,255,0.3);
          text-transform: capitalize;
          flex-shrink: 0;
        }
        .card-content {
          padding: 10px 16px 14px;
        }
        table { width: 100%; border-collapse: collapse; }
        td { padding: 4px 0; font-size: 1em; color: var(--primary-text-color); }
        td:last-child { text-align: right; color: var(--secondary-text-color); }
        .action-buttons {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
          margin-top: 10px;
          padding-top: 8px;
          border-top: 1px solid var(--divider-color, #e0e0e0);
        }
        .action-btn {
          padding: 4px 10px;
          border: none;
          border-radius: 12px;
          cursor: pointer;
          font-size: 0.78em;
          font-family: inherit;
          font-weight: 500;
          transition: opacity 0.2s;
          color: white;
        }
        .action-btn:hover { opacity: 0.85; }
        .mark-done-btn { background: #27ae60; }
      </style>
      <ha-card>
        <div class="card-header">
          <span class="task-name">${name}</span>
          <span class="badge">${this._t(stateStr) || stateStr}</span>
        </div>
        <div class="card-content">
          <table>
            <tr>
              <td>${scheduleLabel}</td>
              <td>${scheduleValue}</td>
            </tr>
            <tr>
              <td>${this._t("last_done")}</td>
              <td>${lastDoneStr}</td>
            </tr>
            <tr>
              <td>${this._t("due_date")}</td>
              <td>${dueDateStr}</td>
            </tr>
            <tr>
              <td>${dueLabel}</td>
              <td>${dueValue}</td>
            </tr>
          </table>
          <div class="action-buttons">
            <button class="action-btn mark-done-btn"
                    title="${this._t("mark_as_done")}"
                    aria-label="${this._t("mark_as_done")}">
              &#10003; ${this._t("mark_as_done")}
            </button>
          </div>
        </div>
      </ha-card>
    `;
  }

  getCardSize() {
    return 3;
  }

  getGridOptions() {
    return {
      rows: 3,
      columns: 6,
      min_rows: 3,
      max_rows: 3,
    };
  }

  _markAsDone() {
    this._hass.callService("task_tracker", "mark_as_done", {
      entity_id: this.config.entity,
    });
  }
}

customElements.define("task-tracker-card", TaskTracker);
