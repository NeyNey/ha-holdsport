"""Constants for the Holdsport integration."""

from __future__ import annotations

DOMAIN = "holdsport"

CONF_UPDATE_INTERVAL = "update_interval"
DEFAULT_UPDATE_INTERVAL = 15

BASE_URL = "https://api.holdsport.dk"
API_PREFIX = "/v1"

PLATFORMS = ["button", "calendar", "sensor"]

# Values of "joined_status" used by Holdsport sign-up actions.
JOINED_STATUS_ATTENDING = 1
JOINED_STATUS_DECLINED = 2

SERVICE_EXECUTE_ACTIVITY_ACTION = "execute_activity_action"
SERVICE_ADD_ACTIVITY_COMMENT = "add_activity_comment"
SERVICE_ADD_ACTIVITY_RIDE = "add_activity_ride"
SERVICE_REMOVE_ACTIVITY_RIDE = "remove_activity_ride"
SERVICE_ASSIGN_ACTIVITY_TASK = "assign_activity_task"
SERVICE_REFRESH = "refresh"
MAX_TASK_ATTRIBUTES = 10
MAX_ACTIVITY_ATTRIBUTES = 20
MAX_NOTE_ATTRIBUTES = 10
MAX_NOTE_BODY_LENGTH = 1000

ATTR_ENTRY_ID = "entry_id"
ATTR_TEAM_ID = "team_id"
ATTR_ACTIVITY_ID = "activity_id"
ATTR_ACTION_INDEX = "action_index"
ATTR_COMMENT = "comment"
ATTR_SEATS = "seats"
ATTR_RIDE_ID = "ride_id"
ATTR_TASK_TYPE_ID = "task_type_id"
ATTR_USER_ID = "user_id"
