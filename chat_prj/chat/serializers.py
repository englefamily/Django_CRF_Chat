from rest_framework import serializers
from .models import User, Room, Message


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        exclude = ["password"]


class MessageSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    created_at_formatted = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = "__all__"

    def get_created_at_formatted(self, obj):
        return obj.created_at.strftime("%d-%m-%Y %H:%M:%S")


class RoomSerializer(serializers.ModelSerializer):
    last_message = MessageSerializer()
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Room
        fields = ["pk", "name", "host", "messages", "current_users", "last_message"]
        read_only_fields = ["messages", "last_message"]
