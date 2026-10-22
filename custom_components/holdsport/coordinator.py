"""Data coordinator for Holdsport."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import DEFAULT_UPDATE_INTERVAL, DOMAIN
from .holdsport_api import HoldsportApiClient, HoldsportApiError, HoldsportAuthError

_LOGGER = logging.getLogger(__name__)

# Number of upcoming activities per team for which tasks are fetched.
TASK_LOOKAHEAD = 3


class HoldsportDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinate Holdsport API data updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: HoldsportApiClient,
        *,
        update_interval_minutes: int = DEFAULT_UPDATE_INTERVAL,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=update_interval_minutes),
        )
        self.client = client
        # Registry id of the account device; set during integration setup.
        self.account_device_id: str | None = None

    async def _async_team_payload(self, team_id: int) -> dict[str, list[dict[str, Any]]]:
        """Fetch team scoped payload."""

        async def _safe(call_name: str, coro: Any) -> list[dict[str, Any]]:
            try:
                result = await coro
                if isinstance(result, list):
                    _LOGGER.debug(
                        "Fetched %s %s for team %s", len(result), call_name, team_id
                    )
                    return result
                _LOGGER.warning(
                    "Unexpected response type %s for %s of team %s",
                    type(result).__name__,
                    call_name,
                    team_id,
                )
                return []
            except HoldsportApiError as err:
                _LOGGER.warning("Unable to fetch %s for team %s: %s", call_name, team_id, err)
                return []

        activities, members, notes = await asyncio.gather(
            _safe("activities", self.client.async_get_all_activities(team_id)),
            _safe("members", self.client.async_get_members(team_id)),
            _safe("notes", self.client.async_get_notes(team_id)),
        )

        # Tasks are only shown for the next activity, so don't hammer the API
        # with one request per upcoming activity on every refresh.
        now = dt_util.utcnow()
        upcoming: list[tuple[Any, dict[str, Any]]] = []
        for activity in activities:
            if activity.get("id") is None:
                continue
            start_time = dt_util.parse_datetime(activity.get("starttime") or "")
            if start_time is None:
                continue
            start_time = dt_util.as_utc(start_time)
            if start_time >= now:
                upcoming.append((start_time, activity))
        upcoming.sort(key=lambda item: item[0])
        next_ids = [str(a["id"]) for _, a in upcoming[:TASK_LOOKAHEAD]]

        tasks_map: dict[str, list[dict[str, Any]]] = {}
        if next_ids:
            task_results = await asyncio.gather(
                *(
                    _safe("activity_tasks", self.client.async_get_activity_tasks(int(i)))
                    for i in next_ids
                )
            )
            tasks_map = dict(zip(next_ids, task_results, strict=True))

        return {
            "activities": activities,
            "members": members,
            "notes": notes,
            "activity_tasks": tasks_map,
        }

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch all account data from Holdsport."""
        try:
            user = await self.client.async_get_user()
            teams = await self.client.async_get_teams()

            activities: dict[str, list[dict[str, Any]]] = {}
            members: dict[str, list[dict[str, Any]]] = {}
            notes: dict[str, list[dict[str, Any]]] = {}
            activity_tasks: dict[str, dict[str, list[dict[str, Any]]]] = {}

            team_ids: list[int] = []
            team_coroutines: list[Any] = []
            for team in teams:
                team_id = int(team["id"])
                team_ids.append(team_id)
                team_coroutines.append(self._async_team_payload(team_id))

            team_payloads = await asyncio.gather(*team_coroutines)

            for team_id, payload in zip(team_ids, team_payloads, strict=True):
                team_key = str(team_id)
                activities[team_key] = payload["activities"]
                members[team_key] = payload["members"]
                notes[team_key] = payload["notes"]
                activity_tasks[team_key] = payload["activity_tasks"]

            return {
                "user": user,
                "teams": teams,
                "activities": activities,
                "members": members,
                "notes": notes,
                "activity_tasks": activity_tasks,
            }
        except HoldsportAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except HoldsportApiError as err:
            raise UpdateFailed(f"Error communicating with Holdsport API: {err}") from err
