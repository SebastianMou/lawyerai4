from rest_framework import serializers
from django.contrib.auth.models import User
from .models import ContractProject, AIHighlightChat, ChatSession, Message

class AIHighlightChatSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIHighlightChat
        fields = '__all__'

class ContractProjectSerializer(serializers.ModelSerializer):
    ai_chats = AIHighlightChatSerializer(many=True, read_only=True)  # Add this line to include related AI chats

    class Meta:
        model = ContractProject
        fields = '__all__'

class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['id', 'chat_session', 'content', 'sender', 'created_at']

class ChatSessionSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)  # This will include all messages in the session
    
    class Meta:
        model = ChatSession
        fields = ['id', 'name', 'created_at', 'updated_at', 'owner', 'messages']