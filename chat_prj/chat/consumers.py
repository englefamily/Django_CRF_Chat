# import json
# # Converting app to be asynchronous. So following import is not needed anymore:
# # from asgiref.sync import async_to_sync
# from channels.generic.websocket import AsyncWebsocketConsumer # WebsocketConsumer
#
#
# # Converting to asynchronous. WebsocketConsumer -> AsyncWebsocketConsumer
# class ChatConsumer(AsyncWebsocketConsumer):
#     async def connect(self):
#         self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
#         self.room_group_name = "chat_%s" % self.room_name
#
#         # Join room group
#         await self.channel_layer.group_add(
#             self.room_group_name, self.channel_name
#         )
#
#         await self.accept()
#
#     async def disconnect(self, close_code):
#         # Leave room group
#         await self.channel_layer.group_discard(
#             self.room_group_name, self.channel_name
#         )
#
#     # Receive message from WebSocket
#     async def receive(self, text_data):
#         text_data_json = json.loads(text_data)
#         message = text_data_json["message"]
#
#         # Send message to room group
#         await self.channel_layer.group_send(
#             self.room_group_name, {"type": "chat_message", "message": message}
#         )
#
#     # Receive message from room group
#     async def chat_message(self, event):
#         message = event["message"]
#
#         # Send message to WebSocket
#         await self.send(text_data=json.dumps({"message": message}))


import json
from django.shortcuts import get_object_or_404
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils.timezone import now
from django.conf import settings
from typing import Generator
from djangochannelsrestframework.generics import GenericAsyncAPIConsumer, AsyncAPIConsumer
from djangochannelsrestframework.observer.generics import (ObserverModelInstanceMixin, action)
from djangochannelsrestframework.observer import model_observer

from .models import Room, Message, User
from .serializers import MessageSerializer, RoomSerializer, UserSerializer


class RoomConsumer(ObserverModelInstanceMixin, GenericAsyncAPIConsumer):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    lookup_field = "pk"

    async def disconnect(self, code):
        if hasattr(self, "room_subscribe"):
            await self.remove_user_from_room(self.room_subscribe)
            await self.notify_users()
        await super().disconnect(code)

    # @action()
    # async def join_room(self, pk, **kwargs):
    #     self.room_subscribe = pk
    #     await self.add_user_to_room(pk)
    #     await self.notify_users()

    @action()
    async def join_room(self, pk, **kwargs):
        if self.scope["user"].is_authenticated:
            self.room_subscribe = pk
            await self.add_user_to_room(pk)
            await self.notify_users()
        else:
            raise ValueError("The user is not authenticated.")

    # @action()
    # async def leave_room(self, pk, **kwargs):
    #     await self.remove_user_from_room(pk)

    @action()
    async def leave_room(self, pk, **kwargs):
        if self.scope["user"].is_authenticated:
            await self.remove_user_from_room(pk)
        else:
            raise ValueError("The user is not authenticated.")

    # @action()
    # async def create_message(self, message, **kwargs):
    #     room: Room = await self.get_room(pk=self.room_subscribe)
    #     await database_sync_to_async(Message.objects.create)(
    #         room=room,
    #         user=self.scope["user"],
    #         text=message
    #     )

    @action()
    async def create_message(self, message, **kwargs):
        user = self.scope["user"]
        if user.is_authenticated:
            room: Room = await self.get_room(pk=self.room_subscribe)
            await database_sync_to_async(Message.objects.create)(
                room=room,
                user=user,
                text=message
            )
        else:
            raise ValueError("The user is not authenticated.")

    @action()
    async def subscribe_to_messages_in_room(self, pk, request_id, **kwargs):
        await self.message_activity.subscribe(room=pk, request_id=request_id)

    @model_observer(Message)
    async def message_activity(
        self,
        message,
        observer=None,
        subscribing_request_ids = [],
        **kwargs
    ):
        """
        This is evaluated once for each subscribed consumer.
        The result of `@message_activity.serializer` is provided here as the message.
        """
        # since we provide the request_id when subscribing we can just loop over them here.
        for request_id in subscribing_request_ids:
            message_body = dict(request_id=request_id)
            message_body.update(message)
            await self.send_json(message_body)

    @message_activity.groups_for_signal
    def message_activity(self, instance: Message, **kwargs):
        yield 'room__{instance.room_id}'
        yield f'pk__{instance.pk}'

    @message_activity.groups_for_consumer
    def message_activity(self, room=None, **kwargs):
        if room is not None:
            yield f'room__{room}'

    @message_activity.serializer
    def message_activity(self, instance:Message, action, **kwargs):
        """
        This is evaluated before the update is sent
        out to all the subscribing consumers.
        """
        return dict(data=MessageSerializer(instance).data, action=action.value, pk=instance.pk)

    async def notify_users(self):
        room: Room = await self.get_room(self.room_subscribe)
        for group in self.groups:
            await self.channel_layer.group_send(
                group,
                {
                    'type':'update_users',
                    'usuarios':await self.current_users(room)
                }
            )

    async def update_users(self, event: dict):
        await self.send(text_data=json.dumps({'usuarios': event["usuarios"]}))

    @database_sync_to_async
    def get_room(self, pk: int) -> Room:
        return Room.objects.get(pk=pk)

    @database_sync_to_async
    def current_users(self, room: Room):
        return [UserSerializer(user).data for user in room.current_users.all()]

    # @database_sync_to_async
    # def remove_user_from_room(self, room):
    #     user:User = self.scope["user"]
    #     user.current_rooms.remove(room)

    @database_sync_to_async
    def remove_user_from_room(self, room):
        if self.scope["user"].is_authenticated:
            user: User = self.scope["user"]
            user.current_rooms.remove(room)
        else:
            raise ValueError("The user is not authenticated.")

    # @database_sync_to_async
    # def add_user_to_room(self, pk):
    #     user:User = self.scope["user"]
    #     if not user.current_rooms.filter(pk=self.room_subscribe).exists():
    #         user.current_rooms.add(Room.objects.get(pk=pk))

    @database_sync_to_async
    def add_user_to_room(self, pk):
        if self.scope["user"].is_authenticated:
            user: User = self.scope["user"]
            if not user.current_rooms.filter(pk=self.room_subscribe).exists():
                user.current_rooms.add(Room.objects.get(pk=pk))
        else:
            raise ValueError("The user is not authenticated.")

    async def disconnect(self, clean_close, code):
        if self.scope['user'].is_active and self.scope['user'].is_authenticated:
            if hasattr(self, "room_subscribe"):
                await self.remove_user_from_room(self.room_subscribe)
                await self.notify_users()
            await super().disconnect(clean_close, code)
        elif hasattr(self, "room_subscribe"):
            await self.remove_user_from_room(self.room_subscribe)
            await self.notify_users()
            await super().disconnect(clean_close, code)
        else:
            await super().disconnect(clean_close, code)