# ChatApp API guide

All `/api/` endpoints below require an authenticated Django session. POST requests require the Django CSRF token. Send form data unless the endpoint explicitly accepts JSON.

## Existing endpoints
- `GET /api/users/search/?q=name` — search users
- `POST /api/profile/update/` — update display name, about and optional avatar
- `POST /api/groups/create/` — create a group (`name`, repeated `members` IDs, optional `description`)
- `POST /api/groups/<conversation_id>/members/` — admin action `add`, `remove` or `promote`, with `user_id`
- `POST /api/conversations/<conversation_id>/upload/` — upload `file` and optional `content` (max 25 MB)
- `POST /api/messages/<message_id>/action/` — `edit`, `delete`, `react` or `forward`
- `POST /api/privacy/block/` — `action=block|unblock`, `user_id`
- `POST /api/status/create/` — `text` and/or `media`
- `GET /api/status/` — active statuses from other users
- `POST /api/status/<status_id>/view/` — mark a status viewed
- `POST /api/preferences/update/` — theme, font size, notification preference
- `POST /api/conversations/<conversation_id>/calls/` — call signalling record actions; this is not a complete WebRTC call implementation

## Added essential controls
- `POST /api/conversations/<conversation_id>/settings/` — `action=archive|pin|mute`, `value=true|false`
- `POST /api/messages/<message_id>/hide/` — hide a message for the current user only
- `POST /api/conversations/<conversation_id>/read/` — create read receipt records; optional repeated `message_ids`
- `POST /api/reports/create/` — `report_type=user|message|group`, `reason`, optional `details`, and the matching `user_id`, `message_id` or `conversation_id`
- `GET /api/status/<status_id>/viewers/` — viewers of a status owned by the current user

## Important notes
- Use the browser's CSRF token for authenticated POST calls.
- Conversation IDs and message IDs are not authorization: every endpoint must still check membership/ownership server-side.
- The UI is not yet wired to every endpoint. See `FEATURE_STATUS.md`.
- The default channel layer is in-memory and suitable only for local development. Configure Redis for multi-process deployments.
