# Holdsport for Home Assistant

A custom integration that brings your [Holdsport](https://www.holdsport.dk) (SportMember) teams into
Home Assistant: upcoming activities as calendars, a "next activity" sensor per team, and services for
answering sign-ups, adding comments, offering rides and picking tasks.

> This is an unofficial integration. It uses Holdsport's public REST API
> ([documentation](https://github.com/Holdsport/holdsport-api)) and is not affiliated with Holdsport.

## Features

- **Calendars** for every team you belong to:
  - one calendar with **all** upcoming activities, and
  - one calendar **per activity type** (e.g. *Træning*, *Kamp*, *Social aktivitet*), so you can show
    or hide types on a dashboard the same way you can on holdsport.dk. New types get their own
    calendar automatically the first time they appear.
- **Sensors**:
  - *User*: your Holdsport profile and number of teams.
  - Per team: *Next activity*, *Activities* (all upcoming activities as attributes), *Notes* (the
    newest note as state, all recent notes as attributes) and *Members* (a count).
- **Buttons** per team to **sign up for** or **decline** the next activity with one press.
- **Services** for acting on any activity from automations and dashboards (sign up, decline,
  comment, rides, tasks).
- Works with managed profiles (see [Setup](#setup)).
- Configurable update interval.

## Installation

### HACS

1. In HACS, open the menu and choose **Custom repositories**.
2. Add `https://github.com/NeyNey/ha-holdsport` and set the type to **Integration** (not *Dashboard*).
3. Install **Holdsport** and restart Home Assistant.

### Manual

1. Download this repository (green **Code** button → **Download ZIP**, or a release).
2. Copy the `custom_components/holdsport` folder into your Home Assistant `custom_components`
   directory.
3. Restart Home Assistant.

## Setup

1. Go to **Settings → Devices & services → Add integration** and search for **Holdsport**.
2. Enter your Holdsport **username** and **password**.
   - To access a managed profile (for example a child's account), use the **profile ID** as
     username and the **administrator's password**.
3. Optionally set the update interval (1–360 minutes, default 15). You can change it later under
   the integration's **Configure** button.

Each team becomes a device, and your account is the parent device.

## Calendars

| Entity | Contains |
| --- | --- |
| `calendar.<team>_calendar` | All upcoming activities of the team |
| `calendar.<team>_<type>` | Only activities of that type, e.g. `…_traening`, `…_kamp` |

Each event has the activity name as title, the place as location, and a description with the
activity type, your own response, attendance counts and any comment. Activities without an end
time in Holdsport are shown as one-hour events. Calendars are read-only.

Exact entity IDs are chosen by Home Assistant, so check **Settings → Devices & services → Holdsport**.

See [Examples](#examples) for dashboard cards and automations.

## Sensors

**Next activity** (`sensor.<team>_next_activity`) has the name of the next upcoming activity as its
state. Useful attributes:

| Attribute | Meaning |
| --- | --- |
| `starttime`, `endtime`, `place`, `comment` | Basic details |
| `event_type`, `event_type_id` | Activity type (Træning, Kamp, …) |
| `my_status` | Your own response (e.g. *Tilmeldt*), if Holdsport lists one |
| `attending_count`, `declined_count`, `no_rsvp_count` | Response counts |
| `max_attendees`, `registration_type`, `is_department_activity` | Sign-up details |
| `pickup_place`, `pickup_time` | Pickup details |
| `available_actions`, `action_path`, `action_method` | What you can currently do (e.g. *Afmeld*) |
| `rides`, `ride_comment` | Offered rides |
| `tasks`, `tasks_count` | Tasks (up to 10 shown) |
| `team_id`, `team_name`, `team_role_name` | Team info (role: player, coach, assistant_coach, injured, inactive, team_leader) |

**Activities** (`sensor.<team>_activities`) has the number of upcoming activities as its state and
the activities themselves, soonest first (max 20), in the `activities` attribute. Each item has:
`id`, `name`, `event_type`, `starttime`, `endtime`, `place`, `comment`, `my_status`,
`attending_count`, `declined_count`, `no_rsvp_count`, `max_attendees`, `is_department_activity`,
`pickup_place` and `pickup_time`. The list only covers upcoming activities, because that is all
the API returns.

**Notes** (`sensor.<team>_notes`) has the **title of the newest note** as its state, and the
attributes `count` and `notes`: the 10 newest notes, newest first. Each note has `title`, `body`
(shortened to 1000 characters), `created_by`, `created_at` and `attachment_url`.

**Members** (`sensor.<team>_members`) is the number of team members. Member contact details are not
exposed.

The `activities` and `notes` lists are excluded from the Home Assistant database (recorder), so
they don't bloat your history, but they are available for dashboards and automations.

Lists of items are best shown with a **Markdown** card, see [Examples](#examples).

## Buttons

Each team has two buttons for answering its **next activity**:

| Entity | Does |
| --- | --- |
| `button.<team>_sign_up_for_next_activity` | Signs you up (Tilmeld) |
| `button.<team>_decline_next_activity` | Declines (Afmeld) |

A button is only **available** while Holdsport offers that answer for the next activity. If you have
already signed up, the sign-up button is unavailable and the decline button works, and the other
way around. Activities without sign-up (for example some club matches) leave both unavailable.
The button's attributes show which activity it will answer. After pressing, Home Assistant
refreshes the data within a few seconds.

Use them in a dashboard (`tile` or `button` card) or in automations:

```yaml
action: button.press
target:
  entity_id: button.myteam_decline_next_activity
```

To answer an activity that is **not** the next one, use `holdsport.execute_activity_action`
(see below).

## Services

All services accept an optional `entry_id` if you have more than one Holdsport account configured.

| Service | Purpose |
| --- | --- |
| `holdsport.refresh` | Fetch fresh data immediately |
| `holdsport.execute_activity_action` | Run one of the activity's available actions (sign up, decline, …). Fields: `team_id`, `activity_id`, `action_index` (default 0) |
| `holdsport.add_activity_comment` | Post a comment. Fields: `activity_id`, `comment` |
| `holdsport.add_activity_ride` | Offer seats. Fields: `activity_id`, `seats`, `comment` |
| `holdsport.remove_activity_ride` | Remove a ride offer. Fields: `activity_id`, `ride_id` |
| `holdsport.assign_activity_task` | Take a task (or assign someone, if you are coach/admin). Fields: `activity_id`, `task_type_id`, optional `user_id` |

Example: answer a specific activity with its first available action (check the sensor's
`available_actions` first, because the action list depends on your current status). For the next
activity, the buttons above are simpler:

```yaml
action: holdsport.execute_activity_action
data:
  team_id: "{{ state_attr('sensor.myteam_next_activity', 'team_id') }}"
  activity_id: "{{ state_attr('sensor.myteam_next_activity', 'activity_id') }}"
  action_index: 0
```

## Examples

Replace `myteam` in the entity IDs with your team's name. Exact entity IDs are shown under
**Settings → Devices & services → Holdsport**.

### Dashboard: calendar

```yaml
type: calendar
initial_view: listWeek
entities:
  - calendar.myteam_traening
  - calendar.myteam_kamp
```

If you use the HACS card *Calendar Card Pro*, `type: custom:calendar-card-pro` with the same
`entities` works too.

### Dashboard: next activity with answer buttons

A Markdown card with the details, followed by buttons that only appear when they can be used:

```yaml
type: vertical-stack
cards:
  - type: markdown
    title: Next activity
    content: |-
      {% set s = 'sensor.myteam_next_activity' %}
      {% if states(s) in ['unknown', 'unavailable'] %}
      No upcoming activities.
      {% else %}
      **{{ states(s) }}** ({{ state_attr(s, 'event_type') }})

      {{ (state_attr(s, 'starttime') | as_datetime | as_local).strftime('%d/%m at %H:%M') }}{% if state_attr(s, 'place') %} – {{ state_attr(s, 'place') }}{% endif %}

      Your response: **{{ state_attr(s, 'my_status') or 'not answered' }}**
      · {{ state_attr(s, 'attending_count') }} attending
      · {{ state_attr(s, 'declined_count') }} declined
      {% endif %}
  - type: horizontal-stack
    cards:
      - type: conditional
        conditions:
          - condition: state
            entity: button.myteam_sign_up_for_next_activity
            state_not: unavailable
        card:
          type: button
          name: Sign up
          icon: mdi:check-circle
          tap_action:
            action: perform-action
            perform_action: button.press
            target:
              entity_id: button.myteam_sign_up_for_next_activity
            confirmation: true
      - type: conditional
        conditions:
          - condition: state
            entity: button.myteam_decline_next_activity
            state_not: unavailable
        card:
          type: button
          name: Decline
          icon: mdi:close-circle
          tap_action:
            action: perform-action
            perform_action: button.press
            target:
              entity_id: button.myteam_decline_next_activity
            confirmation: true
```

### Dashboard: upcoming activities

All upcoming activities from the *Activities* sensor, with your own response:

```yaml
type: markdown
title: Upcoming activities
content: |-
  {% for a in state_attr('sensor.myteam_activities', 'activities') or [] -%}
  - **{{ (a.starttime | as_datetime | as_local).strftime('%a %d/%m %H:%M') }}** {{ a.name }}{% if a.place %} – {{ a.place }}{% endif %} ({{ a.my_status or 'not answered' }})
  {% endfor %}
```

To show only one activity type, add `{% if a.event_type == 'Kamp' %}` … `{% endif %}` inside the loop.

### Dashboard: notes

The newest notes with author, date and text:

```yaml
type: markdown
title: Team notes
content: |-
  {% for n in state_attr('sensor.myteam_notes', 'notes') or [] %}
  ### {{ n.title }}
  *{{ n.created_by }}, {{ (n.created_at | as_datetime | as_local).strftime('%d/%m/%Y') }}*

  {{ n.body }}
  {% if n.attachment_url %}[Attachment]({{ n.attachment_url }}){% endif %}

  {% endfor %}
```

For a compact view, an **Entity** card on `sensor.myteam_notes` shows the title of the newest note.

### Automation: reminder if you haven't answered

```yaml
triggers:
  - trigger: time
    at: "17:00:00"
conditions:
  - condition: template
    value_template: >
      {{ states('sensor.myteam_next_activity') not in ['unknown', 'unavailable']
         and state_attr('sensor.myteam_next_activity', 'my_status') is none }}
actions:
  - action: notify.notify
    data:
      message: "Remember to answer Holdsport: {{ states('sensor.myteam_next_activity') }}"
```

Because the sign-up button is unavailable once you have signed up, you can also use
`{{ is_state('button.myteam_sign_up_for_next_activity', 'unavailable') }}` to check that you have
already signed up (or that there is nothing to answer).

### Automation: notify when a new note is posted

```yaml
triggers:
  - trigger: state
    entity_id: sensor.myteam_notes
    attribute: count
conditions:
  - condition: template
    value_template: >
      {{ trigger.from_state is not none
         and trigger.from_state.attributes.count is defined
         and trigger.to_state.attributes.count | int(0) > trigger.from_state.attributes.count | int(0) }}
actions:
  - action: notify.notify
    data:
      title: "New note: {{ states('sensor.myteam_notes') }}"
      message: "{{ state_attr('sensor.myteam_notes', 'notes')[0].body | truncate(200) }}"
```

### Automation: morning summary of today's activities

```yaml
triggers:
  - trigger: time
    at: "07:30:00"
actions:
  - variables:
      today: >
        {% set ns = namespace(items=[]) %}
        {% for a in state_attr('sensor.myteam_activities', 'activities') or [] %}
          {% set start = a.starttime | as_datetime | as_local %}
          {% if start.date() == now().date() %}
            {% set ns.items = ns.items + [start.strftime('%H:%M') ~ ' ' ~ a.name] %}
          {% endif %}
        {% endfor %}
        {{ ns.items | join(', ') }}
  - if:
      - condition: template
        value_template: "{{ today | length > 0 }}"
    then:
      - action: notify.notify
        data:
          message: "Today: {{ today }}"
```

### Automation: answer from a button or voice assistant

```yaml
action: button.press
target:
  entity_id: button.myteam_decline_next_activity
```

## Good to know

- **Only upcoming activities** are available. Holdsport's API returns activities from today onwards,
  so there is no history.
- Data is polled from `https://api.holdsport.dk/v1`; nothing is pushed. Use `holdsport.refresh`
  for an immediate update.
- Members' contact details are never exposed by this integration; only the member count is.
- If your password changes, remove and re-add the integration.

## Troubleshooting

**Step 1: look at the raw data.** Open **Developer tools → Template** and paste this (replace
`myteam`). In recent Home Assistant versions Developer tools is no longer in the sidebar: go to
**Settings**, scroll to the bottom and open **Developer tools**, or press `Ctrl+K` (`Cmd+K` on Mac)
and type "developer":

```
next activity: {{ states('sensor.myteam_next_activity') }}
  starts: {{ state_attr('sensor.myteam_next_activity', 'starttime') }}
activities: {{ states('sensor.myteam_activities') }}
  first: {{ (state_attr('sensor.myteam_activities', 'activities') or [])[:2] }}
notes: {{ states('sensor.myteam_notes') }} (count {{ state_attr('sensor.myteam_notes', 'count') }})
now: {{ now() }}
```

- If a sensor shows `unknown`, the integration got no data. Check the logs (step 2).
- If the values look right but a dashboard card doesn't, the problem is in the card, not the
  integration. Paste the card's template into the same Template tool to see the error.

**Step 2: logs.** Failed requests are logged as warnings ("Unable to fetch notes for team …") under
**Settings → System → Logs**. For more detail, enable debug logging in `configuration.yaml` and restart:

```yaml
logger:
  logs:
    custom_components.holdsport: debug
```

The debug log shows how many activities, members and notes were fetched for each team on every update.

**Common problems**

- **No events in a calendar**: run **Developer tools → Actions → `calendar.get_events`** on the
  calendar entity with `duration: {days: 30}` to see what the integration produces.
- **Notes are empty**: the team may simply have no notes. Holdsport returns an empty list in that
  case, and the debug log will say "Fetched 0 notes".
- **HACS says the repository structure is not compliant**: make sure the repository was added as
  type **Integration**.
- **A calendar for a type is missing**: type calendars are created from the activities currently
  returned by Holdsport, so a type with no upcoming activities has no calendar yet.

Please include relevant log lines (with personal details removed) when opening an issue.

## Development

- The integration lives in `custom_components/holdsport/`.
- `hacs.json` and the GitHub Actions workflows validate the repository with HACS and hassfest.
- **Releasing:** change `version` in `manifest.json`, add an entry to `CHANGELOG.md`, commit, and
  run `./release.sh` (or push a tag `vX.Y.Z` yourself). The release workflow checks that the tag
  matches the manifest version and then creates the GitHub release with a zip of the integration.
- Work on a branch and open a pull request; the Validate workflow must be green before merging.
- Team devices are linked to the account device with `via_device_id` on Home Assistant 2026.8
  and newer, and with the older `via_device` on earlier versions (`via_device` is deprecated and
  breaks in 2027.8).
- Sign-up buttons rely on the `joined_status` of the actions Holdsport returns for an activity
  (1 = attending, 2 = declined).
- Keep the keys in `manifest.json` ordered as hassfest requires: `domain`, `name`, then the rest
  alphabetically.

## Credits

Originally created by [MrMEEE](https://github.com/MrMEEE/ha-holdsport). This version is maintained
by [NeyNey](https://github.com/NeyNey/ha-holdsport). Licensed under the GNU GPL v3, see `LICENSE`.
