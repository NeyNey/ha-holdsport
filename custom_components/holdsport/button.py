"""Button platform for Holdsport: answer the next activity."""

from __future__ import annotations

from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, JOINED_STATUS_ATTENDING, JOINED_STATUS_DECLINED
from .coordinator import HoldsportDataUpdateCoordinator
from .helpers import find_action_index, next_activity, team_device_info
from .holdsport_api import HoldsportApiError

# (translation key, joined_status, icon)
NEXT_ACTIVITY_BUTTONS = (
    ("sign_up_next_activity", JOINED_STATUS_ATTENDING, "mdi:check-circle"),
    ("decline_next_activity", JOINED_STATUS_DECLINED, "mdi:close-circle"),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Holdsport buttons."""
    coordinator: HoldsportDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        HoldsportNextActivityButton(
            coordinator, entry, team, translation_key, joined_status, icon
        )
        for team in coordinator.data.get("teams", [])
        for translation_key, joined_status, icon in NEXT_ACTIVITY_BUTTONS
    )


class HoldsportNextActivityButton(
    CoordinatorEntity[HoldsportDataUpdateCoordinator], ButtonEntity
):
    """Button that signs up for / declines the team's next activity.

    The button is only available while Holdsport offers that answer for the
    next activity.
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HoldsportDataUpdateCoordinator,
        entry: ConfigEntry,
        team: dict[str, Any],
        translation_key: str,
        joined_status: int,
        icon: str,
    ) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._entry = entry
        self._team = team
        self._team_id = str(team["id"])
        self._joined_status = joined_status
        self._attr_translation_key = translation_key
        self._attr_icon = icon
        self._attr_unique_id = f"{entry.entry_id}_{self._team_id}_{translation_key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Attach the button to the team device."""
        return team_device_info(
            self.coordinator, self._entry.entry_id, self._team_id, self._team
        )

    def _target(self) -> tuple[dict[str, Any], int] | None:
        """Return (next activity, action index) if the answer is available."""
        activities = self.coordinator.data.get("activities", {}).get(self._team_id, [])
        activity = next_activity(activities)
        if activity is None:
            return None
        index = find_action_index(activity, self._joined_status)
        if index is None:
            return None
        return activity, index

    @property
    def available(self) -> bool:
        """Only available when Holdsport offers this answer for the next activity."""
        return super().available and self._target() is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Show which activity the button will answer."""
        target = self._target()
        if target is None:
            return None
        activity, _ = target
        return {
            "activity_id": activity.get("id"),
            "activity_name": (activity.get("name") or "").strip(),
            "starttime": activity.get("starttime"),
        }

    async def async_press(self) -> None:
        """Send the answer to Holdsport."""
        target = self._target()
        if target is None:
            raise HomeAssistantError(
                "This answer is not available for the next activity"
            )
        activity, index = target
        try:
            await self.coordinator.client.async_execute_activity_action(activity, index)
        except HoldsportApiError as err:
            raise HomeAssistantError(f"Failed to answer activity: {err}") from err
        await self.coordinator.async_request_refresh()
