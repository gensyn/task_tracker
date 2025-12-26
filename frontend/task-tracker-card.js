class TaskTracker extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
  }

  set hass(hass) {
    const config = this._config;

    const entity = hass.states[config.entity];

    if (typeof entity === 'undefined') {
      return;
    }

    const card = this.shadowRoot.getElementById('do-card');
    card.style.color = "#000";
    
    if (entity.state == "done") {
      card.style.backgroundColor = "#7dcea0";
    } else if (entity.state == "inactive") {
        card.style.backgroundColor = "#5dade2";
    } else {
      card.style.backgroundColor = "#ec7063";
    }

    this.style.setProperty('--ha-card-header-color', 'black');

    const header = entity.attributes.friendly_name.replace(" State", "");
    card.title = header;
    card.header = header.length >= 18 ? header.slice(0, 15) + "..." : header;

    if (this._entity !== entity || this._entity.attributes !== entity.attributes) {
      const cellIconStatus = this.shadowRoot.getElementById('do-iconStatus');
      cellIconStatus.icon = entity.attributes.icon;

      const cellValueStatus = this.shadowRoot.getElementById('do-cellValueStatus');
      cellValueStatus.innerHTML = entity.state;

      const cellValueTaskFrequency = this.shadowRoot.getElementById('do-cellValueTaskFrequency');
      cellValueTaskFrequency.innerHTML = entity.attributes.task_frequency_value;
      const singular_plural_string = cellValueTaskFrequency.innerHTML === "1" ? '' : 's';
      cellValueTaskFrequency.innerHTML = cellValueTaskFrequency.innerHTML + ' ' + entity.attributes.task_frequency_type + singular_plural_string;

      const cellValueNotificationFrequency = this.shadowRoot.getElementById('do-cellValueNotificationFrequency');
      cellValueNotificationFrequency.innerHTML = entity.attributes.notification_frequency;
      const notification_days_string = cellValueNotificationFrequency.innerHTML === "1" ? ' day' : ' days';
      cellValueNotificationFrequency.innerHTML = cellValueNotificationFrequency.innerHTML + notification_days_string;;

      const cellDescriptionDue = this.shadowRoot.getElementById('do-cellDescriptionDue');
      cellDescriptionDue.innerHTML = (entity.attributes.due_in > 0 ? 'Due in' : 'Overdue by');

      const cellValueDue = this.shadowRoot.getElementById('do-cellValueDue');
      cellValueDue.innerHTML = entity.attributes.due_in > 0 ? entity.attributes.due_in : entity.attributes.overdue_by;
      const due_days_string = cellValueDue.innerHTML === "1" ? ' day' : ' days';
      cellValueDue.innerHTML = cellValueDue.innerHTML + due_days_string;

      const cellValueLastDone = this.shadowRoot.getElementById('do-cellValueLastDone');
      cellValueLastDone.innerHTML = new Date(entity.attributes.last_done).toLocaleDateString(undefined, { day: '2-digit', month: '2-digit', year: 'numeric' });

      const cellValueDueDate = this.shadowRoot.getElementById('do-cellValueDueDate');
      cellValueDueDate.innerHTML = new Date(entity.attributes.due_date).toLocaleDateString(undefined, { day: '2-digit', month: '2-digit', year: 'numeric' });

      const cellValueTags = this.shadowRoot.getElementById('do-cellValueTags');
      cellValueTags.innerHTML = entity.attributes.tags.join(', ');

      this._entity = entity;
    }

    this._hass = hass;
  }

  setConfig(config) {
    if (!config.entity) {
      throw new Error('You need to define an entity');
    }

    const root = this.shadowRoot;
    if (root.lastChild) root.removeChild(root.lastChild);

    // 1. row "status"
    const iconStatus = document.createElement('ha-icon');
    iconStatus.style.color = 'var(--state-icon-color)';
    iconStatus.id = 'do-iconStatus';

    const cellIconStatus = document.createElement('td');
    cellIconStatus.appendChild(iconStatus);

    const cellDescriptionStatus = document.createElement('td');
    cellDescriptionStatus.innerHTML = 'Status';
    cellDescriptionStatus.style.paddingLeft = '10px';

    const cellValueStatus = document.createElement('td');
    cellValueStatus.style.width = '99%';
    cellValueStatus.style.textAlign = 'right';
    cellValueStatus.id = 'do-cellValueStatus';

    const rowStatus = document.createElement('tr');
    rowStatus.appendChild(cellIconStatus);
    rowStatus.appendChild(cellDescriptionStatus);
    rowStatus.appendChild(cellValueStatus);

    // 2. row "task frequency"
    const iconTaskFrequency = document.createElement('ha-icon');
    iconTaskFrequency.icon = 'mdi:sine-wave';
    iconTaskFrequency.style.color = 'var(--state-icon-color)';

    const cellIconTaskFrequency = document.createElement('td');
    cellIconTaskFrequency.appendChild(iconTaskFrequency);

    const cellDescriptionTaskFrequency = document.createElement('td');
    cellDescriptionTaskFrequency.innerHTML = 'Task&nbsp;Frequency';
    cellDescriptionTaskFrequency.style.paddingLeft = '10px';

    const cellValueTaskFrequency = document.createElement('td');
    cellValueTaskFrequency.style.width = '99%';
    cellValueTaskFrequency.style.textAlign = 'right';
    cellValueTaskFrequency.id = 'do-cellValueTaskFrequency';

    const rowTaskFrequency = document.createElement('tr');
    rowTaskFrequency.appendChild(cellIconTaskFrequency);
    rowTaskFrequency.appendChild(cellDescriptionTaskFrequency);
    rowTaskFrequency.appendChild(cellValueTaskFrequency);

    // 3. row "notification frequency"
    const iconNotificationFrequency = document.createElement('ha-icon');
    iconNotificationFrequency.icon = 'mdi:cosine-wave';
    iconNotificationFrequency.style.color = 'var(--state-icon-color)';

    const cellIconNotificationFrequency = document.createElement('td');
    cellIconNotificationFrequency.appendChild(iconNotificationFrequency);

    const cellDescriptionNotificationFrequency = document.createElement('td');
    cellDescriptionNotificationFrequency.innerHTML = 'Notification&nbsp;Frequency';
    cellDescriptionNotificationFrequency.style.paddingLeft = '10px';

    const cellValueNotificationFrequency = document.createElement('td');
    cellValueNotificationFrequency.style.width = '99%';
    cellValueNotificationFrequency.style.textAlign = 'right';
    cellValueNotificationFrequency.id = 'do-cellValueNotificationFrequency';

    const rowNotificationFrequency = document.createElement('tr');
    rowNotificationFrequency.appendChild(cellIconNotificationFrequency);
    rowNotificationFrequency.appendChild(cellDescriptionNotificationFrequency);
    rowNotificationFrequency.appendChild(cellValueNotificationFrequency);

    // 4. row "last done"
    const iconLastDone = document.createElement('ha-icon');
    iconLastDone.icon = 'mdi:calendar-check';
    iconLastDone.style.color = 'var(--state-icon-color)';

    const cellIconLastDone = document.createElement('td');
    cellIconLastDone.appendChild(iconLastDone);

    const cellDescriptionLastDone = document.createElement('td');
    cellDescriptionLastDone.innerHTML = 'Last&nbsp;Done';
    cellDescriptionLastDone.style.paddingLeft = '10px';

    const cellValueLastDone = document.createElement('td');
    cellValueLastDone.style.width = '99%';
    cellValueLastDone.style.textAlign = 'right';
    cellValueLastDone.id = 'do-cellValueLastDone';

    const rowLastDone = document.createElement('tr');
    rowLastDone.appendChild(cellIconLastDone);
    rowLastDone.appendChild(cellDescriptionLastDone);
    rowLastDone.appendChild(cellValueLastDone);

    // 5. row "due date"
    const iconDueDate = document.createElement('ha-icon');
    iconDueDate.icon = 'mdi:calendar-alert';
    iconDueDate.style.color = 'var(--state-icon-color)';

    const cellIconDueDate = document.createElement('td');
    cellIconDueDate.appendChild(iconDueDate);

    const cellDescriptionDueDate = document.createElement('td');
    cellDescriptionDueDate.innerHTML = 'Due&nbsp;Date';
    cellDescriptionDueDate.style.paddingLeft = '10px';

    const cellValueDueDate = document.createElement('td');
    cellValueDueDate.style.width = '99%';
    cellValueDueDate.style.textAlign = 'right';
    cellValueDueDate.id = 'do-cellValueDueDate';

    const rowDueDate = document.createElement('tr');
    rowDueDate.appendChild(cellIconDueDate);
    rowDueDate.appendChild(cellDescriptionDueDate);
    rowDueDate.appendChild(cellValueDueDate);

    // 6. row "due"
    const iconDue = document.createElement('ha-icon');
    iconDue.icon = 'mdi:counter';
    iconDue.style.color = 'var(--state-icon-color)';

    const cellIconDue = document.createElement('td');
    cellIconDue.appendChild(iconDue);

    const cellDescriptionDue = document.createElement('td');
    cellDescriptionDue.style.paddingLeft = '10px';
    cellDescriptionDue.id = 'do-cellDescriptionDue';

    const cellValueDue = document.createElement('td');
    cellValueDue.style.width = '99%';
    cellValueDue.style.textAlign = 'right';
    cellValueDue.id = 'do-cellValueDue';

    const rowDue = document.createElement('tr');
    rowDue.appendChild(cellIconDue);
    rowDue.appendChild(cellDescriptionDue);
    rowDue.appendChild(cellValueDue);

    // 7. row "tags"
    const iconTags = document.createElement('ha-icon');
    iconTags.icon = 'mdi:clipboard-account-outline';
    iconTags.style.color = 'var(--state-icon-color)';

    const cellIconTags = document.createElement('td');
    cellIconTags.appendChild(iconTags);

    const cellDescriptionTags = document.createElement('td');
    cellDescriptionTags.innerHTML = 'Tags';
    cellDescriptionTags.style.paddingLeft = '10px';

    const cellValueTags = document.createElement('td');
    cellValueTags.style.width = '99%';
    cellValueTags.style.textAlign = 'right';
    cellValueTags.id = 'do-cellValueTags';

    const rowTags = document.createElement('tr');
    rowTags.appendChild(cellIconTags);
    rowTags.appendChild(cellDescriptionTags);
    rowTags.appendChild(cellValueTags);


    const tableInfo = document.createElement('table');
    tableInfo.style.borderBottom = '1px solid var(--divider-color)';
    tableInfo.style.paddingBottom = '5px';
    tableInfo.appendChild(rowStatus);
    tableInfo.appendChild(rowTaskFrequency);
    tableInfo.appendChild(rowNotificationFrequency);
    tableInfo.appendChild(rowLastDone);
    tableInfo.appendChild(rowDueDate);
    tableInfo.appendChild(rowDue);
    tableInfo.appendChild(rowTags);

    const iconMarkAsDone = document.createElement('ha-icon');
    iconMarkAsDone.icon = 'mdi:check';
    iconMarkAsDone.title = 'Mark task as done';
    iconMarkAsDone.style.color = 'var(--state-icon-color)';
    iconMarkAsDone.style.cursor = 'pointer';
    iconMarkAsDone.addEventListener('click', event => {
      this._markAsDone();
    });

    const cellMarkAsDone = document.createElement('td');
    cellMarkAsDone.style.textAlign = 'center';
    cellMarkAsDone.appendChild(iconMarkAsDone);


    const rowButtons = document.createElement('tr');
    rowButtons.appendChild(cellMarkAsDone);

    const tableButtons = document.createElement('table');
    tableButtons.style.tableLayout = 'fixed';
    tableButtons.style.width = '100%';
    tableButtons.style.paddingTop = '5px';
    tableButtons.appendChild(rowButtons);


    const content = document.createElement('div');
    content.appendChild(tableInfo);
    content.appendChild(tableButtons);
    content.style.paddingLeft = '10px';
    content.style.paddingRight = '10px';
    content.style.paddingBottom = '10px';

    const card = document.createElement('ha-card');
    card.id = 'do-card';
    card.appendChild(content);

    root.appendChild(card);

    this._config = config;
  }

  _markAsDone() {
    this._hass.callService('task_tracker', 'mark_as_done', {
      entity_id: this._config.entity
    });
  }
}

customElements.define("task-tracker-card", TaskTracker);