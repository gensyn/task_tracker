// javascript
class TaskTracker extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  _t(key) {
    return this._hass.localize(`component.task_tracker.entity.ui.${key}`);
  }

  set hass(hass) {
    this._hass = hass;
    const root = this.shadowRoot;
    const entityId = this.config.entity;
    const entity = this._hass.states[entityId];
    const friendly_name = entity ? entity.attributes.friendly_name : entityId;

    if (!this.content) {
      root.innerHTML = `
        <style>
          ha-card {
            color: black;
            background-color: #ec7063;
            --ha-card-header-color: black;
          }
          ha-card.done {
            background-color: #7dcea0;
          }
          ha-card.inactive {
            background-color: #5dade2;
          }
          ha-icon {
            color: var(--state-icon-color);
            cursor: pointer;
            position: absolute;
            top: 28px;
            right: 18px;
          }
          td:nth-child(2) {
            width: 99%;
            text-align: right;
          }
        </style>
        <ha-card id="card" header="${friendly_name}">
          <ha-icon id="icon" icon="mdi:check"></ha-icon>
          <div class="card-content">
            <table id="task-table">
              <tr>
                <td>${this._t("status.name")}</td>
                <td id="status-cell"></td>
              </tr>
              <tr>
                <td>${this._t("interval.name")}</td>
                <td id="task-interval-cell"></td>
              </tr>
              <tr>
                <td>${this._t("last_done.name")}</td>
                <td id="last-done-cell"></td>
              </tr>
              <tr>
                <td>${this._t("due_date.name")}</td>
                <td id="due-date-cell"></td>
              </tr>
              <tr>
                <td id="due-label-cell"></td>
                <td id="due-cell"></td>
              </tr>
            </table>
          </div>
        </ha-card>
      `;

      const icon = root.querySelector("#icon");
      icon.addEventListener("click", () => this._markAsDone());

      this.content = root.querySelector("div");
    }

    if (this._entity !== entity || this._entity.attributes !== entity.attributes) {
      const stateStr = entity ? entity.state : "unavailable";
      root.querySelector("#status-cell").innerHTML = this._t(`status.${stateStr}`);

      const card = root.querySelector("#card");
      card.className = stateStr;

      const icon = root.querySelector("#icon");
      icon.title = this._t("mark_as_done.name");

      const taskIntervalVal = entity.attributes.task_interval_value;
      const taskIntervalType = entity.attributes.task_interval_type;
      const taskIntervalSingularPlural = taskIntervalVal === 1 ? 'singular' : 'plural';
      const taskIntervalTypeTranslated = this._t(`interval.${taskIntervalSingularPlural}.${taskIntervalType}`)
      const taskIntervalCell = root.querySelector("#task-interval-cell");
      taskIntervalCell.innerHTML = `${taskIntervalVal}&nbsp;${taskIntervalTypeTranslated}`;

      const haLocale = (this._hass && this._hass.locale && this._hass.locale.language) || undefined;

      const lastDoneVal = entity.attributes.last_done;
      const lastDoneCell = root.querySelector("#last-done-cell");
      lastDoneCell.innerHTML = new Date(lastDoneVal).toLocaleDateString(haLocale, { day: '2-digit', month: '2-digit', year: 'numeric' });

      const dueDateVal = entity.attributes.due_date;
      const dueDateCell = root.querySelector("#due-date-cell");
      dueDateCell.innerHTML = new Date(dueDateVal).toLocaleDateString(haLocale, { day: '2-digit', month: '2-digit', year: 'numeric' });

      const dueLabelCell = root.querySelector("#due-label-cell");
      const dueCell = root.querySelector("#due-cell");
        if (entity.attributes.due_in > 0) {
            dueLabelCell.innerHTML = this._t('due.due_in');
        } else {
            dueLabelCell.innerHTML = this._t('due.overdue_by');
        }
      const dueNum = entity.attributes.due_in > 0 ? entity.attributes.due_in : entity.attributes.overdue_by;
      const dueSingularPlural = dueNum === 1 ? 'singular' : 'plural';
      const dueDayTranslated = this._t(`interval.${dueSingularPlural}.day`)
      dueCell.innerHTML = `${dueNum}&nbsp;${dueDayTranslated}`;

      this._entity = entity;
    }
  }

  setConfig(config) {
    if (!config.entity) {
      throw new Error("You need to define an entity");
    }
    this.config = config;
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
    this._hass.callService('task_tracker', 'mark_as_done', {
      entity_id: this.config.entity
    });
  }
}

customElements.define("task-tracker-card", TaskTracker);
