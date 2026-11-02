# ChatApp feature status (expanded backend build)

Legend: **Backend present** means a Django model/view/API exists; it does not mean the feature is fully wired into the browser/Android UI or production tested.

## Working foundation
- Django registration, login/logout, session authentication
- One-to-one text conversations and chat history
- Conversation membership checks
- Unread count and read marking
- WebSocket consumer/routing foundation and HTTP polling fallback
- Group model and create/manage-members endpoints
- Upload endpoint for image/video/audio/other files (25 MB cap)
- Message edit, delete-for-everyone, forward and reaction endpoint
- Profile and avatar update endpoint
- Block/unblock endpoint
- Status create/list/view endpoint with 24-hour expiry
- User preferences endpoint
- Call signalling record endpoint (not WebRTC media calling)

## Newly added essential backend controls
- Per-user archive, pin and mute settings: `POST /api/conversations/<id>/settings/`
- Delete a message for only the current user: `POST /api/messages/<id>/hide/`
- Read receipt records: `POST /api/conversations/<id>/read/`
- Report a user, message or group: `POST /api/reports/create/`
- Viewers for your own status: `GET /api/status/<id>/viewers/`
- Message history omits messages hidden by the requesting user
- Admin moderation list for user reports

## Still requires frontend/mobile integration and/or external services
- UI controls for archive/pin/mute, hide message, reports and status viewers
- Full contact/address-book sync and contact invitations
- Complete message delivery acknowledgements across devices
- Robust typing/online presence lifecycle and last-seen privacy enforcement
- Group invitation links, group privacy/permissions and complete group UI
- Voice recording UI, upload previews, resumable uploads and storage quotas
- Browser/Android push notifications (Firebase project and credentials required)
- Native Android chat UI, background services and notification handling
- WebRTC peer connection, STUN/TURN infrastructure and call UI
- End-to-end encryption protocol and independent security review
- Production Redis, HTTPS, rate limiting, backups, monitoring and deployment

This is a development foundation, not a production-ready secure messenger. Do not use it for sensitive communications or public launch before security review and testing.
