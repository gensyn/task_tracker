// javascript
class TaskTrackerPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._filter = "all";
    this._narrow = false;
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  set narrow(value) {
    this._narrow = value;
    this._render();
  }

  set header(value) {
    this._header = value;
  }

  set panel(panel) {
    this._panel = panel;
  }

  _t(key) {
    return (
      this._hass.localize(`component.task_tracker.entity.ui.${key}.name`) || key
    );
  }

  _getAllTasks() {
    return Object.values(this._hass.states)
      .filter((entity) => entity.entity_id.startsWith("sensor.task_tracker_"))
      .sort((a, b) => {
        const nameA = (a.attributes.friendly_name || a.entity_id).toLowerCase();
        const nameB = (b.attributes.friendly_name || b.entity_id).toLowerCase();
        return nameA.localeCompare(nameB);
      });
  }

  _getFilteredTasks() {
    const tasks = this._getAllTasks();
    if (this._filter === "all") return tasks;
    return tasks.filter((t) => t.state === this._filter);
  }

  _setFilter(filter) {
    this._filter = filter;
    this._render();
  }

  _markAsDone(entityId) {
    this._hass.callService("task_tracker", "mark_as_done", {
      entity_id: entityId,
    });
  }

  _formatDate(dateStr) {
    const locale =
      (this._hass && this._hass.locale && this._hass.locale.language) ||
      undefined;
    return new Date(dateStr).toLocaleDateString(locale, {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
    });
  }

  _renderTaskCard(entity) {
    const state = entity.state;
    const attrs = entity.attributes;
    const name = attrs.friendly_name || entity.entity_id;

    const taskIntervalVal = attrs.task_interval_value;
    const taskIntervalType = attrs.task_interval_type;
    const singularPlural = taskIntervalVal === 1 ? "singular" : "plural";
    const intervalTypeStr = this._t(`${taskIntervalType}_${singularPlural}`);
    const intervalStr = `${taskIntervalVal}\u00a0${intervalTypeStr}`;

    const lastDoneStr = this._formatDate(attrs.last_done);
    const dueDateStr = this._formatDate(attrs.due_date);

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

    return `
      <div class="task-card ${state}">
        <div class="task-card-header">
          <span class="task-name">${name}</span>
          <button class="mark-done-btn"
                  data-entity-id="${entity.entity_id}"
                  title="${this._t("mark_as_done")}">&#10003;</button>
        </div>
        <div class="task-card-content">
          <table>
            <tr><td>${this._t("status")}</td><td>${this._t(state)}</td></tr>
            <tr><td>${this._t("interval")}</td><td>${intervalStr}</td></tr>
            <tr><td>${this._t("last_done")}</td><td>${lastDoneStr}</td></tr>
            <tr><td>${this._t("due_date")}</td><td>${dueDateStr}</td></tr>
            <tr><td>${dueLabel}</td><td>${dueValue}</td></tr>
          </table>
        </div>
      </div>
    `;
  }

  _render() {
    if (!this._hass) return;

    const allTasks = this._getAllTasks();

    const counts = {
      due: allTasks.filter((t) => t.state === "due").length,
      done: allTasks.filter((t) => t.state === "done").length,
      inactive: allTasks.filter((t) => t.state === "inactive").length,
    };

    const activeStates = ["due", "done", "inactive"].filter(
      (s) => counts[s] > 0
    );

    // Reset filter if the currently selected state has no tasks
    if (this._filter !== "all" && counts[this._filter] === 0) {
      this._filter = "all";
    }

    const filteredTasks = this._getFilteredTasks();

    // Only show filters when tasks span more than one state
    const showFilters = activeStates.length > 1;
    const filterButtons = showFilters
      ? ["all", ...activeStates]
          .map(
            (f) =>
              `<button class="filter-btn${this._filter === f ? " active" : ""}"
                       data-filter="${f}">
                ${this._t(f)}${f !== "all" ? ` (${counts[f]})` : ""}
               </button>`
          )
          .join("")
      : "";

    const taskGrid = filteredTasks.length
      ? filteredTasks.map((t) => this._renderTaskCard(t)).join("")
      : `<p class="no-tasks">${this._t("no_tasks_found")}</p>`;

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
        }
        .toolbar {
          display: flex;
          align-items: center;
          background-color: var(--app-header-background-color, var(--primary-color));
          color: var(--app-header-text-color, white);
          height: var(--header-height, 56px);
          padding: 0 16px;
        }
        .toolbar-title {
          font-size: 1.25rem;
          font-weight: 500;
          flex: 1;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .content {
          padding: 16px;
        }
        .filters {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          margin-bottom: 16px;
        }
        .filter-btn {
          padding: 6px 14px;
          border: 2px solid var(--primary-color, #03a9f4);
          background: transparent;
          color: var(--primary-color, #03a9f4);
          border-radius: 20px;
          cursor: pointer;
          font-size: 0.875rem;
          font-family: inherit;
          transition: background 0.2s, color 0.2s;
        }
        .filter-btn.active {
          background: var(--primary-color, #03a9f4);
          color: var(--text-primary-color, white);
        }
        .filter-btn:hover:not(.active) {
          background: rgba(3, 169, 244, 0.1);
        }
        .task-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
          gap: 16px;
        }
        .task-card {
          border-radius: 8px;
          overflow: hidden;
          color: black;
          background-color: #ec7063;
          box-shadow: var(--ha-card-box-shadow, 0 2px 6px rgba(0,0,0,0.2));
        }
        .task-card.done {
          background-color: #7dcea0;
        }
        .task-card.inactive {
          background-color: #5dade2;
        }
        .task-card-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 12px 16px;
          font-size: 1rem;
          font-weight: 600;
          border-bottom: 1px solid rgba(0,0,0,0.1);
        }
        .task-name {
          flex: 1;
          margin-right: 8px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .mark-done-btn {
          background: rgba(255,255,255,0.35);
          border: none;
          border-radius: 50%;
          width: 32px;
          height: 32px;
          font-size: 1.1rem;
          cursor: pointer;
          flex-shrink: 0;
          display: inline-flex;
          align-items: center;
          justify-content: center;
          transition: background 0.2s;
        }
        .mark-done-btn:hover {
          background: rgba(255,255,255,0.55);
        }
        .task-card-content {
          padding: 8px 16px 12px;
        }
        table {
          width: 100%;
          border-collapse: collapse;
        }
        td {
          padding: 3px 0;
          font-size: 0.875rem;
        }
        td:last-child {
          text-align: right;
          padding-left: 8px;
        }
        .no-tasks {
          color: var(--secondary-text-color, #727272);
          font-style: italic;
        }
      </style>
      <div class="toolbar">
        ${this._narrow ? "<ha-menu-button></ha-menu-button>" : ""}
        <div class="toolbar-title">Task Tracker</div>
      </div>
      <div class="content">
        ${showFilters ? `<div class="filters">${filterButtons}</div>` : ""}
        <div class="task-grid">${taskGrid}</div>
      </div>
    `;

    if (this._narrow) {
      const menuButton = this.shadowRoot.querySelector("ha-menu-button");
      if (menuButton) {
        menuButton.hass = this._hass;
        menuButton.narrow = this._narrow;
      }
    }

    this.shadowRoot.querySelectorAll(".filter-btn").forEach((btn) => {
      btn.addEventListener("click", () => this._setFilter(btn.dataset.filter));
    });

    this.shadowRoot.querySelectorAll(".mark-done-btn").forEach((btn) => {
      btn.addEventListener("click", () =>
        this._markAsDone(btn.dataset.entityId)
      );
    });
  }
}

customElements.define("task-tracker-panel", TaskTrackerPanel);
