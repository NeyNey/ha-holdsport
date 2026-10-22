"""Sensor platform for Holdsport."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    MAX_ACTIVITY_ATTRIBUTES,
    MAX_NOTE_ATTRIBUTES,
    MAX_TASK_ATTRIBUTES,
)
from .coordinator import HoldsportDataUpdateCoordinator
from .helpers import (
    activity_summary,
    my_status,
    next_activity,
    note_summary,
    sorted_activities,
    sorted_notes,
)

TEAM_ROLES = {
    1: "player",
    2: "coach",
    3: "assistant_coach",
    4: "injured",
    5: "inactive",
    6: "team_leader",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Holdsport sensors based on a config entry."""
    coordinator: HoldsportDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = [HoldsportUserSensor(coordinator, entry)]
    for team in coordinator.data.get("teams", []):
        entities.extend(
            [
                HoldsportTeamNextActivitySensor(coordinator, entry, team),
                HoldsportTeamActivitiesSensor(coordinator, entry, team),
                HoldsportTeamMetricSensor(coordinator, entry, team, "members"),
                HoldsportTeamNotesSensor(coordinator, entry, team),
            ]
        )

    async_add_entities(entities)


class HoldsportBaseEntity(CoordinatorEntity[HoldsportDataUpdateCoordinator], SensorEntity):
    """Base entity for Holdsport sensors."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HoldsportDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry

    @property
    def device_info(self) -> DeviceInfo:
        """Return shared account device info."""
        user = self.coordinator.data.get("user", {})
        display_name = f"{user.get('firstname', '')} {user.get('lastname', '')}".strip()
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=display_name or self._entry.data[CONF_USERNAME],
            manufacturer="Holdsport",
            model="Account",
        )


class HoldsportUserSensor(HoldsportBaseEntity):
    """Sensor describing current authenticated profile."""

    def __init__(self, coordinator: HoldsportDataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_translation_key = "user_name"
        self._attr_unique_id = f"{entry.entry_id}_user"

    @property
    def native_value(self) -> str | None:
        """Return current user name."""
        user = self.coordinator.data.get("user", {})
        display_name = f"{user.get('firstname', '')} {user.get('lastname', '')}".strip()
        return display_name or None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return user attributes."""
        user = self.coordinator.data.get("user", {})
        return {
            "id": user.get("id"),
            "team_count": len(self.coordinator.data.get("teams", [])),
        }


class HoldsportTeamBaseEntity(HoldsportBaseEntity):
    """Base entity for team-specific sensors."""

    def __init__(
        self,
        coordinator: HoldsportDataUpdateCoordinator,
        entry: ConfigEntry,
        team: dict[str, Any],
    ) -> None:
        super().__init__(coordinator, entry)
        self._team = team
        self._team_id = str(team["id"])

    @property
    def device_info(self) -> DeviceInfo:
        """Return team device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self._entry.entry_id}_{self._team_id}")},
            name=self._team.get("name", f"Team {self._team_id}"),
            manufacturer="Holdsport",
            model="Team",
            via_device=(DOMAIN, self._entry.entry_id),
        )


class HoldsportTeamMetricSensor(HoldsportTeamBaseEntity):
    """Sensor exposing counts for team collections."""

    def __init__(
        self,
        coordinator: HoldsportDataUpdateCoordinator,
        entry: ConfigEntry,
        team: dict[str, Any],
        metric: str,
    ) -> None:
        super().__init__(coordinator, entry, team)
        self._metric = metric
        self._attr_translation_key = f"team_{metric}_count"
        self._attr_unique_id = f"{entry.entry_id}_{self._team_id}_{metric}_count"

    @property
    def native_value(self) -> int:
        """Return collection size."""
        return len(self.coordinator.data.get(self._metric, {}).get(self._team_id, []))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose team details."""
        return {
            "team_id": int(self._team_id),
            "team_name": self._team.get("name"),
            "role": self._team.get("role"),
            "role_name": TEAM_ROLES.get(self._team.get("role")),
        }


class HoldsportTeamActivitiesSensor(HoldsportTeamMetricSensor):
    """Number of upcoming activities, with the activities themselves as attributes."""

    # Lists can be large and change often; keep them out of the recorder database.
    _unrecorded_attributes = frozenset({"activities"})

    def __init__(
        self,
        coordinator: HoldsportDataUpdateCoordinator,
        entry: ConfigEntry,
        team: dict[str, Any],
    ) -> None:
        super().__init__(coordinator, entry, team, "activities")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose the upcoming activities, soonest first."""
        user_id = self.coordinator.data.get("user", {}).get("id")
        activities = sorted_activities(
            self.coordinator.data.get("activities", {}).get(self._team_id, [])
        )
        return {
            **super().extra_state_attributes,
            "count": len(activities),
            "activities": [
                activity_summary(a, user_id)
                for a in activities[:MAX_ACTIVITY_ATTRIBUTES]
            ],
        }


class HoldsportTeamNotesSensor(HoldsportTeamMetricSensor):
    """Latest team note title as state, with all recent notes as attributes."""

    _unrecorded_attributes = frozenset({"notes"})

    def __init__(
        self,
        coordinator: HoldsportDataUpdateCoordinator,
        entry: ConfigEntry,
        team: dict[str, Any],
    ) -> None:
        super().__init__(coordinator, entry, team, "notes")

    def _notes(self) -> list[dict[str, Any]]:
        return sorted_notes(self.coordinator.data.get("notes", {}).get(self._team_id, []))

    @property
    def native_value(self) -> str | None:
        """Return the title of the newest note (state is limited to 255 characters)."""
        notes = self._notes()
        if not notes:
            return None
        title = (notes[0].get("title") or "").strip()
        return title[:255] or None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose the newest notes, newest first."""
        notes = self._notes()
        return {
            **super().extra_state_attributes,
            "count": len(notes),
            "notes": [note_summary(n) for n in notes[:MAX_NOTE_ATTRIBUTES]],
        }


class HoldsportTeamNextActivitySensor(HoldsportTeamBaseEntity):
    """Sensor exposing next upcoming activity details for a team."""

    def __init__(
        self,
        coordinator: HoldsportDataUpdateCoordinator,
        entry: ConfigEntry,
        team: dict[str, Any],
    ) -> None:
        super().__init__(coordinator, entry, team)
        self._attr_translation_key = "team_next_activity"
        self._attr_unique_id = f"{entry.entry_id}_{self._team_id}_next_activity"

    def _next_activity(self) -> dict[str, Any] | None:
        activities = self.coordinator.data.get("activities", {}).get(self._team_id, [])
        return next_activity(activities)

    def _my_status(self, activity: dict[str, Any]) -> str | None:
        """Return the authenticated user's own response, if the API lists it."""
        return my_status(activity, self.coordinator.data.get("user", {}).get("id"))

    @property
    def native_value(self) -> str | None:
        """Return next activity name."""
        activity = self._next_activity()
        if not activity:
            return None
        return activity.get("name")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return details of the next activity plus snapshots."""
        activity = self._next_activity()
        tasks = self.coordinator.data.get("activity_tasks", {}).get(self._team_id, {})
        if not activity:
            return {
                "team_id": int(self._team_id),
                "team_name": self._team.get("name"),
                "team_role": self._team.get("role"),
                "activities_count": len(
                    self.coordinator.data.get("activities", {}).get(self._team_id, [])
                ),
                "members_count": len(self.coordinator.data.get("members", {}).get(self._team_id, [])),
                "notes_count": len(self.coordinator.data.get("notes", {}).get(self._team_id, [])),
            }

        activity_id = str(activity.get("id"))
        return {
            "team_id": int(self._team_id),
            "team_name": self._team.get("name"),
            "team_role": self._team.get("role"),
            "team_role_name": TEAM_ROLES.get(self._team.get("role")),
            "activity_id": activity.get("id"),
            "starttime": activity.get("starttime"),
            "endtime": activity.get("endtime"),
            "status": activity.get("status"),
            "place": activity.get("place"),
            "comment": activity.get("comment"),
            "no_rsvp_count": activity.get("no_rsvp_count"),
            "my_status": self._my_status(activity),
            "attending_count": sum(
                a.get("status_code") == 1 for a in activity.get("activities_users", [])
            ),
            "declined_count": sum(
                a.get("status_code") == 2 for a in activity.get("activities_users", [])
            ),
            "max_attendees": activity.get("max_attendees"),
            "pickup_place": activity.get("pickup_place"),
            "pickup_time": activity.get("pickup_time"),
            "registration_type": activity.get("registration_type"),
            "is_department_activity": activity.get("department"),
            "event_type": activity.get("event_type"),
            "event_type_id": activity.get("event_type_id"),
            "available_actions": activity.get("actions", []),
            "action_method": activity.get("action_method"),
            "action_path": activity.get("action_path"),
            "rides": activity.get("rides", []),
            "ride_comment": activity.get("ride_comment"),
            "tasks": tasks.get(activity_id, [])[:MAX_TASK_ATTRIBUTES],
            "tasks_count": len(tasks.get(activity_id, [])),
            "activities_count": len(
                self.coordinator.data.get("activities", {}).get(self._team_id, [])
            ),
            "members_count": len(self.coordinator.data.get("members", {}).get(self._team_id, [])),
            "notes_count": len(self.coordinator.data.get("notes", {}).get(self._team_id, [])),
        }
