// javascript
class TaskTrackerPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._filter = "all";
    this._nameFilter = "";
    this._sortBy = "name";
    this._sortDir = "asc";
    this._narrow = false;
    // Pre-render sort controls immediately so they are present in the
    // shadow DOM as soon as the element is created, even before HA calls
    // set hass().  Full render (with live task data) happens once hass
    // is available.
    this._render();
    this.shadowRoot.addEventListener("click", (e) => {
      const filterBtn = e.target.closest(".filter-btn");
      if (filterBtn) { this._setFilter(filterBtn.dataset.filter); return; }
      const sortBtn = e.target.closest(".sort-btn");
      if (sortBtn) { this._setSort(sortBtn.dataset.sort); return; }
      const doneBtn = e.target.closest(".mark-done-btn");
      if (doneBtn) { this._markAsDone(doneBtn.dataset.entityId); return; }
    });
    this.shadowRoot.addEventListener("input", (e) => {
      const nameInput = e.target.closest(".name-filter-input");
      if (nameInput) { this._nameFilter = nameInput.value; this._render(); return; }
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
        let cmp = 0;
        if (this._sortBy === "due_date") {
          // Tasks without a due_date are placed at the end (Infinity) for ascending sort.
          const dateA = a.attributes.due_date ? new Date(a.attributes.due_date).getTime() : Infinity;
          const dateB = b.attributes.due_date ? new Date(b.attributes.due_date).getTime() : Infinity;
          cmp = dateA - dateB;
        } else {
          const nameA = (a.attributes.friendly_name || a.entity_id).toLowerCase();
          const nameB = (b.attributes.friendly_name || b.entity_id).toLowerCase();
          cmp = nameA.localeCompare(nameB);
        }
        return this._sortDir === "asc" ? cmp : -cmp;
      });
  }

  _setSort(sortBy) {
    if (this._sortBy === sortBy) {
      this._sortDir = this._sortDir === "asc" ? "desc" : "asc";
    } else {
      this._sortBy = sortBy;
      this._sortDir = "asc";
    }
    this._render();
  }

  _sortIndicator(sortBy) {
    if (this._sortBy !== sortBy) return "";
    return this._sortDir === "asc" ? " ↑" : " ↓";
  }

  _getFilteredTasks() {
    let tasks = this._getAllTasks();
    if (this._filter !== "all") {
      tasks = tasks.filter((t) => t.state === this._filter);
    }
    if (this._nameFilter) {
      const needle = this._nameFilter.toLowerCase();
      tasks = tasks.filter((t) => {
        const name = (t.attributes.friendly_name || t.entity_id).toLowerCase();
        return name.includes(needle);
      });
    }
    return tasks;
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

  _renderTaskCard(entity) {
    const state = entity.state;
    const attrs = entity.attributes;
    const name = attrs.friendly_name || entity.entity_id;

    const [scheduleLabel, scheduleValue] = this._scheduleStr(attrs);

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

    // "Mark as done" is a no-op for repeat_every tasks that are already done.
    const showMarkDone = !(attrs.repeat_mode === "repeat_every" && state === "done");

    return `
      <div class="task-card">
        <div class="task-card-header" style="background:${this._stateColor(state)}">
          <span class="task-name">${name}</span>
          <span class="state-badge">${this._t(state) || state}</span>
        </div>
        <div class="task-card-content">
          <table>
            <tr><td>${scheduleLabel}</td><td>${scheduleValue}</td></tr>
            <tr><td>${this._t("last_done")}</td><td>${lastDoneStr}</td></tr>
            <tr><td>${this._t("due_date")}</td><td>${dueDateStr}</td></tr>
            <tr><td>${dueLabel}</td><td>${dueValue}</td></tr>
          </table>
          ${showMarkDone ? `
          <div class="action-buttons">
            <button class="action-btn mark-done-btn"
                    data-entity-id="${entity.entity_id}"
                    title="${this._t("mark_as_done")}">
              &#10003; ${this._t("mark_as_done")}
            </button>
          </div>` : ""}
        </div>
      </div>
    `;
  }

  _css() {
    return `
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
          position: sticky;
          top: 0;
          z-index: 10;
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
        .sort-controls {
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          gap: 8px;
          margin-bottom: 16px;
        }
        .sort-label {
          font-size: 0.875rem;
          color: var(--secondary-text-color, #727272);
        }
        .sort-btn {
          padding: 6px 14px;
          border: 2px solid var(--secondary-color, #727272);
          background: transparent;
          color: var(--secondary-text-color, #727272);
          border-radius: 20px;
          cursor: pointer;
          font-size: 0.875rem;
          font-family: inherit;
          transition: background 0.2s, color 0.2s;
        }
        .sort-btn.active {
          border-color: var(--primary-color, #03a9f4);
          background: var(--primary-color, #03a9f4);
          color: var(--text-primary-color, white);
        }
        .sort-btn:hover:not(.active) {
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
        .name-filter-wrap {
          margin-bottom: 12px;
        }
        .name-filter-input {
          width: 100%;
          box-sizing: border-box;
          padding: 8px 12px;
          border: 1px solid var(--divider-color, #e0e0e0);
          border-radius: 20px;
          font-size: 0.9rem;
          font-family: inherit;
          background: var(--card-background-color, white);
          color: var(--primary-text-color, #212121);
          outline: none;
          transition: border-color 0.2s;
        }
        .name-filter-input:focus {
          border-color: var(--primary-color, #03a9f4);
        }
        .no-tasks {
          color: var(--secondary-text-color, #727272);
          font-style: italic;
        }
    `;
  }

  _render() {
    if (!this._hass) {
      // hass is not yet set; render a skeleton with the toolbar and sort
      // controls so they are present in the shadow DOM immediately after
      // the element is created.  Full render with live task data runs once
      // HA calls set hass().
      this.shadowRoot.innerHTML = `
        <style>${this._css()}</style>
        <div class="toolbar">
          <div class="toolbar-title">Task Tracker</div>
        </div>
        <div class="content">
          <div class="sort-controls">
            <span class="sort-label">Sort by:</span>
            <button class="sort-btn${this._sortBy === "name" ? " active" : ""}" data-sort="name">
              Name${this._sortIndicator("name")}
            </button>
            <button class="sort-btn${this._sortBy === "due_date" ? " active" : ""}" data-sort="due_date">
              Due date${this._sortIndicator("due_date")}
            </button>
          </div>
        </div>
      `;
      return;
    }

    // Preserve name-filter input focus and cursor position across re-renders.
    const prevInput = this.shadowRoot.querySelector(".name-filter-input");
    const nameInputFocused = prevInput && this.shadowRoot.activeElement === prevInput;
    const nameInputSelStart = nameInputFocused ? prevInput.selectionStart : null;
    const nameInputSelEnd   = nameInputFocused ? prevInput.selectionEnd   : null;

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

    const placeholder = this._t("name_filter_placeholder") || "Filter tasks…";

    this.shadowRoot.innerHTML = `
      <style>${this._css()}</style>
      <div class="toolbar">
        ${this._narrow ? "<ha-menu-button></ha-menu-button>" : ""}
        <div class="toolbar-title">Task Tracker</div>
      </div>
      <div class="content">
        ${showFilters ? `<div class="filters">${filterButtons}</div>` : ""}
        <div class="sort-controls">
          <span class="sort-label">${this._t("sort_by") || "Sort by"}:</span>
          <button class="sort-btn${this._sortBy === "name" ? " active" : ""}" data-sort="name">
            ${this._t("sort_name") || "Name"}${this._sortIndicator("name")}
          </button>
          <button class="sort-btn${this._sortBy === "due_date" ? " active" : ""}" data-sort="due_date">
            ${this._t("sort_due_date") || "Due date"}${this._sortIndicator("due_date")}
          </button>
        </div>
        <div class="name-filter-wrap">
          <input class="name-filter-input"
                 type="text"
                 placeholder="${placeholder}"
                 value="${this._nameFilter.replace(/"/g, "&quot;")}">
        </div>
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

    // Restore focus and cursor to the name filter input if it was focused before re-render.
    if (nameInputFocused) {
      const newInput = this.shadowRoot.querySelector(".name-filter-input");
      if (newInput) {
        newInput.focus();
        if (nameInputSelStart !== null) {
          newInput.setSelectionRange(nameInputSelStart, nameInputSelEnd);
        }
      }
    }
  }
}

customElements.define("task-tracker-panel", TaskTrackerPanel);
