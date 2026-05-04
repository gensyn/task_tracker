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

  /** Escape text for safe HTML interpolation. */
  _esc(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  /** Return a safe CSS color value (hex only) or a fallback. */
  _safeColor(color, fallback) {
    if (!color) return fallback;
    // Accept only hex colors: #rgb, #rrggbb, #rrggbbaa
    return /^#[0-9a-fA-F]{3,8}$/.test(color) ? color : fallback;
  }

  set hass(hass) {
    this._hass = hass;
    const entity = hass.states[this.config?.entity];
    const entityEntry = hass.entities && hass.entities[this.config?.entity];
    if (entity === this._entity && entityEntry === this._entityEntry) return;
    this._entity = entity;
    this._entityEntry = entityEntry;
    this._render();
  }

  setConfig(config) {
    if (!config.entity) {
      throw new Error("You need to define an entity");
    }
    this.config = config;
    // show_area, show_tags, show_labels default to false when omitted
    this._showArea   = config.show_area   === true;
    this._showTags   = config.show_tags   === true;
    this._showLabels = config.show_labels === true;
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

  _monthIntervalSuffix(n) {
    if (!n || n <= 1) return "";
    const sp = n === 1 ? "singular" : "plural";
    return `,\u00a0${this._t("every")}\u00a0${n}\u00a0${this._t(`month_${sp}`)}`;
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
        `${this._t("day_of_month_prefix")}\u00a0${attrs.repeat_month_day}\u00a0${this._t("of_month")}${this._monthIntervalSuffix(attrs.repeat_months_interval)}`];
    }
    if (t === "repeat_every_weekday_of_month") {
      const nth = this._t(`occurrence_${attrs.repeat_nth_occurrence}`);
      const weekday = this._t(attrs.repeat_weekday);
      return [this._t("schedule"),
        `${nth}\u00a0${weekday}\u00a0${this._t("of_month")}${this._monthIntervalSuffix(attrs.repeat_months_interval)}`];
    }
    if (t === "repeat_every_days_before_end_of_month") {
      const n = attrs.repeat_days_before_end ?? 0;
      const base = n === 0 ? this._t("last_day_of_month") : (() => {
        const sp = n === 1 ? "singular" : "plural";
        return `${n}\u00a0${this._t(`days_before_end_of_month_${sp}`)}`;
      })();
      return [this._t("schedule"), `${base}${this._monthIntervalSuffix(attrs.repeat_months_interval)}`];
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

    // "Mark as done" is a no-op for repeat_every tasks that are already done.
    const showMarkDone = !(attrs.repeat_mode === "repeat_every" && stateStr === "done");

    // --- optional area / tags / labels ---
    const entityEntry = this._entityEntry;

    let areaName = null;
    if (this._showArea) {
      const areaId = entityEntry && entityEntry.area_id;
      if (areaId) {
        const areaEntry = this._hass.areas && this._hass.areas[areaId];
        areaName = (areaEntry && areaEntry.name) || null;
      }
    }

    const tagsArr = this._showTags ? (attrs.tags || []) : [];

    let labelItems = [];
    if (this._showLabels) {
      const labelIds = (entityEntry && entityEntry.labels) || [];
      labelItems = labelIds.map((id) => {
        const le = this._hass.labels && this._hass.labels[id];
        return le || { name: id, color: null };
      });
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
        .chips-cell { text-align: right; }
        .tag-chip {
          display: inline-block;
          padding: 1px 8px;
          border-radius: 10px;
          font-size: 0.75em;
          background: var(--primary-color, #03a9f4);
          color: white;
          margin: 1px;
        }
        .label-chip {
          display: inline-block;
          padding: 1px 8px;
          border-radius: 10px;
          font-size: 0.75em;
          color: white;
          margin: 1px;
        }
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
            ${areaName ? `
            <tr>
              <td>${this._t("area")}</td>
              <td>${this._esc(areaName)}</td>
            </tr>` : ""}
            ${tagsArr.length ? `
            <tr>
              <td>${this._t("tags")}</td>
              <td class="chips-cell">${tagsArr.map((t) => `<span class="tag-chip">${this._esc(t)}</span>`).join(" ")}</td>
            </tr>` : ""}
            ${labelItems.length ? `
            <tr>
              <td>${this._t("labels")}</td>
              <td class="chips-cell">${labelItems.map((l) => `<span class="label-chip" style="background:${this._safeColor(l.color, "#616161")}">${this._esc(l.name)}</span>`).join(" ")}</td>
            </tr>` : ""}
          </table>
          ${showMarkDone ? `
          <div class="action-buttons">
            <button class="action-btn mark-done-btn"
                    title="${this._t("mark_as_done")}"
                    aria-label="${this._t("mark_as_done")}">
              &#10003; ${this._t("mark_as_done")}
            </button>
          </div>` : ""}
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
