from rest_framework import serializers
from django.contrib.auth.models import User
from .models import ContractProject, AIHighlightChat, ChatSession, Message, Feedback, ContractSteps, ValidationResult, Subscription

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

class ValidationResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = ValidationResult
        fields = '__all__'

class ContractStepsSerializer(serializers.ModelSerializer):
    validation_results = ValidationResultSerializer(many=True, read_only=True)  # Add nested serializer

    class Meta:
        model = ContractSteps
        fields = '__all__'
        extra_kwargs = {
            'user': {'required': False}  # Make `user` optional during validation
        }
    def validate(self, data):
        text_fields = ['purpose', 'obligations', 'payment_terms', 'termination_clause', 
                       'confidentiality_clause', 'dispute_resolution', 'penalties_for_breach', 'notarization']
        for field in text_fields:
            if field in data and data[field] == '':
                data[field] = ''  # Ensure blank fields are explicitly empty
        return data

class FeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = Feedback
        fields = ['id', 'user', 'feedback_type', 'message', 'email', 'phone_number', 'created_at']


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = '__all__'
