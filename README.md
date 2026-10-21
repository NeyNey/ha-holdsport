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
  - Per team: *Next activity*, *Activities*, *Members* and *Notes* (the last three are counts).
- **Services** for acting on activities from automations and dashboards (sign up, decline,
  comment, rides, tasks).
- Works with managed profiles (see [Setup](#setup)).
- Configurable update interval.

## Installation

### HACS

1. In HACS, open the menu and choose **Custom repositories**.
2. Add this repository's URL and set the type to **Integration** (not *Dashboard*).
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

### Dashboard example

Add a **Calendar** card (not the Entities card), for example:

```yaml
type: calendar
initial_view: listWeek
entities:
  - calendar.myteam_traening
  - calendar.myteam_kamp
```

To avoid duplicates, use either the "all activities" calendar or a selection of the per-type ones in
the same card.

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

**Activities / Members / Notes** are number sensors per team. The *Activities* count only covers
upcoming activities, because that is all the API returns.

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

Example: answer the next activity with its first available action (check `available_actions`
first, because the action list depends on your current status):

```yaml
action: holdsport.execute_activity_action
data:
  team_id: "{{ state_attr('sensor.myteam_next_activity', 'team_id') }}"
  activity_id: "{{ state_attr('sensor.myteam_next_activity', 'activity_id') }}"
  action_index: 0
```

Example: remind yourself when you haven't answered an activity happening soon:

```yaml
trigger:
  - platform: time
    at: "17:00:00"
condition:
  - condition: template
    value_template: >
      {{ state_attr('sensor.myteam_next_activity', 'my_status') is none }}
action:
  - action: notify.notify
    data:
      message: "Remember to answer Holdsport: {{ states('sensor.myteam_next_activity') }}"
```

## Good to know

- **Only upcoming activities** are available. Holdsport's API returns activities from today onwards,
  so there is no history.
- Data is polled from `https://api.holdsport.dk/v1`; nothing is pushed. Use `holdsport.refresh`
  for an immediate update.
- Members' contact details are never exposed by this integration; only the member count is.
- If your password changes, remove and re-add the integration.

## Troubleshooting

- **No events in a calendar**: run **Developer Tools → Actions → `calendar.get_events`** on the
  calendar entity with `duration: {days: 30}` to see what the integration produces. If that
  list is empty, check the logs under **Settings → System → Logs**.
- **HACS says the repository structure is not compliant**: make sure the repository was added as
  type **Integration**.
- **A calendar for a type is missing**: type calendars are created from the activities currently
  returned by Holdsport, so a type with no upcoming activities has no calendar yet.

Please include relevant log lines (with personal details removed) when opening an issue.

## Development

- The integration lives in `custom_components/holdsport/`.
- `hacs.json` and the GitHub Actions workflows validate the repository with HACS and hassfest.
- Pushing a tag such as `v0.1.1` creates a GitHub release with a zip of the integration.
- Keep the keys in `manifest.json` ordered as hassfest requires: `domain`, `name`, then the rest
  alphabetically.

## Credits

Original integration by [MrMEEE](https://github.com/MrMEEE/ha-holdsport).
