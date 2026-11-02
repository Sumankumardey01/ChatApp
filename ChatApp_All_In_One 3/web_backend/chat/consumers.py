from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Conversation, Profile
from django.utils import timezone


class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope["url_route"]["kwargs"]["conversation_id"]
        user = self.scope.get("user")
        if not user or user.is_anonymous:
            await self.close(code=4401)
            return
        if not await self.user_is_participant(user.id, self.conversation_id):
            await self.close(code=4403)
            return
        self.room_group_name = f"chat_{self.conversation_id}"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        await self.set_presence(True)

    async def disconnect(self, close_code):
        if hasattr(self, "room_group_name"):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        user = self.scope.get("user")
        if user and user.is_authenticated:
            await self.set_presence(False)

    async def receive_json(self, content, **kwargs):
        event = content.get("event")
        if event in {"typing", "stop_typing"}:
            await self.channel_layer.group_send(self.room_group_name, {
                "type": "chat.typing",
                "event": event,
                "username": self.scope["user"].username,
                "user_id": self.scope["user"].id,
            })

    async def chat_typing(self, event):
        if event.get("user_id") != self.scope["user"].id:
            await self.send_json({
                "event": event["event"],
                "username": event["username"],
            })

    async def chat_message(self, event):
        # The view only publishes messages after checking conversation membership
        # and saving the message to the database.
        await self.send_json({"event": "message", "message": event["message"]})

    @database_sync_to_async
    def user_is_participant(self, user_id, conversation_id):
        return Conversation.objects.filter(
            pk=conversation_id, participants__id=user_id
        ).exists()

    @database_sync_to_async
    def set_presence(self, online):
        profile, _ = Profile.objects.get_or_create(user_id=self.scope["user"].id)
        profile.is_online = online
        if not online:
            profile.last_seen = timezone.now()
        profile.save(update_fields=["is_online", "last_seen"] if not online else ["is_online"])
