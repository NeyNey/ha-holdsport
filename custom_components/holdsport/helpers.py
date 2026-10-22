"""Shared helpers for the Holdsport integration."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.util import dt as dt_util

from .const import BASE_URL, DOMAIN, MAX_NOTE_BODY_LENGTH


def next_activity(activities: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Return the earliest activity that has not started yet."""
    best: tuple[datetime, dict[str, Any]] | None = None
    now = dt_util.utcnow()

    for activity in activities:
        start = activity.get("starttime")
        if not start:
            continue
        start_time = dt_util.parse_datetime(start)
        if start_time is None:
            continue
        start_time = dt_util.as_utc(start_time)
        if start_time < now:
            continue
        if best is None or start_time < best[0]:
            best = (start_time, activity)

    return best[1] if best else None


def find_action_index(activity: dict[str, Any], joined_status: int) -> int | None:
    """Return the index of the sign-up action with the given joined_status.

    Holdsport only offers the actions that are currently possible, so the
    result is None when the answer is not available (for example because the
    user already gave it, or the activity has no sign-up).
    """
    for index, action in enumerate(activity.get("actions") or []):
        user_action = action.get("activities_user") if isinstance(action, dict) else None
        if isinstance(user_action, dict) and user_action.get("joined_status") == joined_status:
            return index
    return None


def activity_start(activity: dict[str, Any]) -> datetime | None:
    """Return the activity start time as an aware UTC datetime."""
    start = dt_util.parse_datetime(activity.get("starttime") or "")
    return dt_util.as_utc(start) if start else None


def sorted_activities(activities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return activities sorted by start time (activities without one last)."""
    far_future = datetime.max.replace(tzinfo=timezone.utc)
    return sorted(activities, key=lambda a: activity_start(a) or far_future)


def my_status(activity: dict[str, Any], user_id: Any) -> str | None:
    """Return the user's own response to an activity, if Holdsport lists it."""
    for attendee in activity.get("activities_users") or []:
        if attendee.get("user_id") == user_id:
            return attendee.get("status")
    return None


def activity_summary(activity: dict[str, Any], user_id: Any) -> dict[str, Any]:
    """Return a compact, dashboard-friendly view of an activity."""
    attendees = activity.get("activities_users") or []
    return {
        "id": activity.get("id"),
        "name": (activity.get("name") or "").strip(),
        "event_type": activity.get("event_type"),
        "starttime": activity.get("starttime"),
        "endtime": activity.get("endtime") or None,
        "place": activity.get("place") or None,
        "comment": activity.get("comment") or None,
        "my_status": my_status(activity, user_id),
        "attending_count": sum(a.get("status_code") == 1 for a in attendees),
        "declined_count": sum(a.get("status_code") == 2 for a in attendees),
        "no_rsvp_count": activity.get("no_rsvp_count"),
        "max_attendees": activity.get("max_attendees"),
        "is_department_activity": activity.get("department"),
        "pickup_place": activity.get("pickup_place") or None,
        "pickup_time": activity.get("pickup_time") or None,
    }


def sorted_notes(notes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return notes newest first (API order is kept for equal/missing dates)."""
    def created(note: dict[str, Any]) -> datetime:
        parsed = dt_util.parse_datetime(note.get("created_at") or "")
        return dt_util.as_utc(parsed) if parsed else datetime.min.replace(tzinfo=timezone.utc)

    return sorted(notes, key=created, reverse=True)


def note_summary(note: dict[str, Any]) -> dict[str, Any]:
    """Return a compact view of a team note with a length-limited body."""
    body = (note.get("body") or "").strip()
    if len(body) > MAX_NOTE_BODY_LENGTH:
        body = body[: MAX_NOTE_BODY_LENGTH - 1].rstrip() + "…"
    attachment = note.get("attachment_path")
    return {
        "title": (note.get("title") or "").strip(),
        "body": body,
        "created_by": note.get("created_by"),
        "created_at": note.get("created_at"),
        "attachment_url": f"{BASE_URL}{attachment}" if attachment else None,
    }


def team_device_info(
    coordinator: Any, entry_id: str, team_id: str, team: dict[str, Any]
) -> DeviceInfo:
    """Return device info for a team device, linked to the account device.

    Home Assistant 2026.8+ wants the parent's device registry id in
    ``via_device_id``; older versions only know the ``via_device`` identifier
    tuple (which newer versions deprecate and eventually remove).
    """
    info = DeviceInfo(
        identifiers={(DOMAIN, f"{entry_id}_{team_id}")},
        name=team.get("name", f"Team {team_id}"),
        manufacturer="Holdsport",
        model="Team",
    )
    parent_id = getattr(coordinator, "account_device_id", None)
    if parent_id and "via_device_id" in getattr(DeviceInfo, "__optional_keys__", ()):
        info["via_device_id"] = parent_id  # type: ignore[typeddict-unknown-key]
    else:
        info["via_device"] = (DOMAIN, entry_id)  # type: ignore[typeddict-unknown-key]
    return info
