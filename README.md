# 📋 Task Tracker

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![GitHub release](https://img.shields.io/github/release/gensyn/task_tracker.svg)](https://github.com/gensyn/task_tracker/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A powerful Home Assistant custom component for managing recurring tasks with automatic tracking and todo list integration.

---

## ✨ Features

- ✅ **Recurring Task Management** - Create tasks with customizable intervals (days, weeks, months, years)
- 📅 **Automatic Due Date Tracking** - Never forget when a task needs to be done
- 📝 **Todo List Integration** - Automatically sync with Home Assistant's Local Todo lists
- 🎨 **Custom Lovelace Card** - Beautiful task display in Lovelace
- 🏷️ **Tagging System** - Organize tasks with custom tags for filtering and automation
- 🔔 **Notification Support** - Built-in attributes for creating smart notification automations
- ⏸️ **Task Activation Control** - Pause tasks when needed without deleting them

---

## 🚀 Installation

### HACS (Recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=gensyn&repository=task_tracker&category=integration)

1. Click the badge above or search for **Task Tracker** in HACS
2. Click **Download**
3. Restart Home Assistant
4. Add the integration via `Settings > Devices & Services > Add Integration`

### Manual Installation

1. Download or clone this repository
2. Copy the `task_tracker` folder to your Home Assistant `config/custom_components` directory
3. Restart Home Assistant
4. Add the integration via `Settings > Devices & Services > Add Integration`

---

## 📖 Documentation

### 🆕 Task Creation

To create a new task: 

1. Navigate to `Settings > Devices & Services`
2. Click `Add Integration`
3. Search for **Task Tracker**
4. Fill in the task details:
   - **Name** - Display name for your task
   - **Task Interval** - How often the task repeats (combined with interval unit)
   - **Task Interval Unit** - Day, week, month or year

![Create task](assets/1_create.png)

---

### ⚙️ Task Options

Access task settings through the cog icon ⚙️ on the integration page. 

![Integration page](assets/2_integration.png)

#### Available Options

![Task settings](assets/3_options.png)

| Option | Description                                                                               |
|--------|-------------------------------------------------------------------------------------------|
| **Active** | Pause tasks when disabled (sensor shows `inactive` state)                                 |
| **Task Interval & Unit** | Modify how often the task repeats                                                         |
| **Material Design Icon** | Choose an icon for the sensor (available as attribute for notifications)                  |
| **Tags** | Add keywords for filtering in automations/templates (e.g., assignees, notification times) |
| **Todo Lists** | Select Local Todo lists for automatic task addition when due                              |
| **Todo List Offset** | Add task to lists `n` days before due date                                                |
| **Notification Interval** | Reference value for automation/template notification timing                               |

> **Note:** Tags and notification intervals require you to implement filtering logic in your own automations. 

---

### 🎴 Lovelace Card

Display tasks beautifully with the included custom card.  Click the ✓ icon to mark tasks complete.

```yaml
- type: custom:task-tracker-card
  entity: sensor.task_tracker_mow_the_lawn
```

#### Card States

<table>
<tr>
<td><img src="assets/4_due.png" alt="Due card"/><br/><b>Due</b></td>
<td><img src="assets/5_inactive.png" alt="Inactive card"/><br/><b>Inactive</b></td>
<td><img src="assets/6_done.png" alt="Done card"/><br/><b>Done</b></td>
</tr>
</table>

---

### 🔄 Todo List Synchronization

Task Tracker seamlessly integrates with Home Assistant's Local Todo lists: 

- **Auto-Add**:  Tasks appear `n` days before due (based on todo list offset)
- **Auto-Remove**: Completed tasks are removed from todo lists
- **Bi-directional Sync**:  Completing a todo item marks the task done after 5 seconds (grace period for accidental clicks)
- **Smart Filtering**:  Inactive tasks won't be added to todo lists

---

### 🔧 Services

Task Tracker provides the following services in the `task_tracker` domain:

#### `task_tracker.mark_as_done`

Marks a task as completed by setting the last done date to today and recalculating the next due date.

**Example:**
```yaml
action: task_tracker.mark_as_done
target:
  entity_id: sensor.task_tracker_mow_the_lawn
```
<br />

#### `task_tracker.set_last_done_date`
Sets the last done date to a specific value. Useful for:
- Recording tasks completed outside Home Assistant
- Correcting mistakes
- Setting initial state when adding existing recurring tasks

**Parameters:**
- `date` (required) - The last done date in `YYYY-MM-DD` format

**Example:**
```yaml
action: task_tracker.set_last_done_date
target:
  entity_id: sensor.task_tracker_mow_the_lawn
data:
  date: "2026-01-01"
```

> **Note:** After setting the last done date, the task's next due date will be automatically recalculated based on your configured interval.

---

### 🤖 Example Automation

Daily notification at 8 AM for due tasks, with assignee-based routing:

```yaml
alias: Task Tracker
description: Notify about due tasks
triggers:
  - trigger: time
    at: "8:00:00"
conditions: []
actions:
  - variables:
      tasks: |-
        [  {%- for entity_id in integration_entities('task_tracker') %}
          {%- if "sensor." in entity_id and states[entity_id].state == "due" %}
            {%- set last_done = as_datetime(states[entity_id].attributes.last_done) if 'last_done' in states[entity_id].attributes else None %}
            {%- set overdue_by = states[entity_id].attributes.overdue_by if 'overdue_by' in states[entity_id].attributes else None %}
            {%- set notification_interval = states[entity_id].attributes.notification_interval if 'notification_interval' in states[entity_id].attributes else None %}
            {%- if last_done is not none and overdue_by is not none and notification_interval is not none %}
              {%- if overdue_by % notification_interval == 0 %}
                "{{ entity_id }}"{% if not loop.last %},{% endif %}
              {%- endif %}
            {%- endif %}
          {%- endif %}
        {%- endfor %}  ]
  - repeat:
      for_each: "{{ tasks }}"
      sequence:
        - alias: Notify User
          if:
            - condition: template
              value_template: "{{ 'user_tag' in states[repeat.item].attributes.tags }}"
          then:
            - action: notify.mobile_app_user
              data:
                title: "{{ states[repeat.item].attributes.friendly_name }}"
                message: >-
                  {%- set overdue_by = states[repeat.item].attributes.overdue_by
                  %} due since {{ 'today' if overdue_by == 0 else ('yesterday'
                  if overdue_by == 1 else overdue_by ~ ' days') }}
                data:
                  tag: "{{ repeat.item }}"
                  color: green
                  group: "{{ repeat.item }}"
                  notification_icon: "{{ states[repeat.item].attributes.icon }}"
mode: single
```

---

## 🚧 Future Development

Have ideas or feature requests? I'm open to suggestions!

- 💭 **Notification Interval Refinement** - Gather feedback on current implementation or explore alternatives
- 🌍 **Additional Translations** - Community contributions welcome for your language
- 🎯 **Your Ideas** - Open an issue to suggest new features! 

---

## 🤝 Contributing

Contributions are welcome! Feel free to: 
- 🐛 Report bugs via [Issues](https://github.com/gensyn/task_tracker/issues)
- 💡 Suggest features
- 🌐 Contribute translations
- 📝 Improve documentation

---

## 📄 License

This project is licensed under the terms specified in the [MIT License](https://mit-license.org/).

---

## ⭐ Support

If you find Task Tracker useful, please consider giving it a star on GitHub! It helps others discover the project. 