// javascript
class TaskTrackerPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._filter = "all";
    this._narrow = false;
    this.shadowRoot.addEventListener("click", (e) => {
      const filterBtn = e.target.closest(".filter-btn");
      if (filterBtn) { this._setFilter(filterBtn.dataset.filter); return; }
      const doneBtn = e.target.closest(".mark-done-btn");
      if (doneBtn) { this._markAsDone(doneBtn.dataset.entityId); return; }
    });
  }

  set hass(hass) {
    const oldHass = this._hass;
    this._hass = hass;
    if (!oldHass || this._tasksChanged(oldHass.states, hass.states)) {
      this._render();
    }
  }

  _tasksChanged(oldStates, newStates) {
    const isTask = (id) => id.startsWith("sensor.task_tracker_");
    const oldTaskIds = Object.keys(oldStates).filter(isTask);
    const newTaskIds = Object.keys(newStates).filter(isTask);
    if (oldTaskIds.length !== newTaskIds.length) return true;
    return (
      newTaskIds.some((id) => oldStates[id] !== newStates[id]) ||
      oldTaskIds.some((id) => oldStates[id] !== newStates[id])
    );
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

  _stateColor(state) {
    switch (state) {
      case "due":      return "#e74c3c";
      case "due_soon": return "#e67e22";
      case "done":     return "#27ae60";
      case "inactive": return "#3498db";
      default:         return "#95a5a6";
    }
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
      <div class="task-card">
        <div class="task-card-header" style="background:${this._stateColor(state)}">
          <span class="task-name">${name}</span>
          <span class="state-badge">${this._t(state) || state}</span>
        </div>
        <div class="task-card-content">
          <table>
            <tr><td>${this._t("interval")}</td><td>${intervalStr}</td></tr>
            <tr><td>${this._t("last_done")}</td><td>${lastDoneStr}</td></tr>
            <tr><td>${this._t("due_date")}</td><td>${dueDateStr}</td></tr>
            <tr><td>${dueLabel}</td><td>${dueValue}</td></tr>
          </table>
          <div class="action-buttons">
            <button class="action-btn mark-done-btn"
                    data-entity-id="${entity.entity_id}"
                    title="${this._t("mark_as_done")}">
              &#10003; ${this._t("mark_as_done")}
            </button>
          </div>
        </div>
      </div>
    `;
  }

  _render() {
    if (!this._hass) return;

    const allTasks = this._getAllTasks();

    const counts = {
      due: allTasks.filter((t) => t.state === "due").length,
      due_soon: allTasks.filter((t) => t.state === "due_soon").length,
      done: allTasks.filter((t) => t.state === "done").length,
      inactive: allTasks.filter((t) => t.state === "inactive").length,
    };

    const activeStates = ["due", "due_soon", "done", "inactive"].filter(
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
                ${this._t(f)} (${f === "all" ? allTasks.length : counts[f]})
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
          box-shadow: var(--ha-card-box-shadow, 0 2px 6px rgba(0,0,0,0.2));
          background: var(--card-background-color, white);
        }
        .task-card-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 12px 16px;
          color: white;
        }
        .task-name {
          flex: 1;
          margin-right: 8px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          font-size: 1.1rem;
          font-weight: 600;
        }
        .state-badge {
          background: rgba(255,255,255,0.3);
          padding: 2px 10px;
          border-radius: 12px;
          font-size: 0.78em;
          flex-shrink: 0;
          text-transform: capitalize;
        }
        .task-card-content {
          padding: 8px 16px 12px;
        }
        table {
          width: 100%;
          border-collapse: collapse;
        }
        td {
          padding: 4px 0;
          font-size: 1rem;
          color: var(--primary-text-color, #212121);
        }
        td:last-child {
          text-align: right;
          color: var(--secondary-text-color, #727272);
        }
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
  }
}

customElements.define("task-tracker-panel", TaskTrackerPanel);
