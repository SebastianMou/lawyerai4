from django.db import models
from django.contrib.auth.models import User
from tinymce.models import HTMLField
from django.db.models.signals import pre_save
from django.conf import settings
from django.dispatch import receiver
import openai

# Create your models here.
class ContractProject(models.Model):
    name = models.CharField(max_length=100, null=True)
    description = HTMLField(blank=True, null=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contract_project', null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        # Return a default string if name is None
        return self.name if self.name else "Unnamed Contract Project"

    class Meta:
        verbose_name_plural = 'Contract Projects'
        ordering = ('-created_at',)

class AIHighlightChat(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    highlighted_text = models.TextField()
    instruction = models.TextField()
    ai_response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    contract_project = models.ForeignKey(ContractProject, on_delete=models.CASCADE, related_name='ai_chats')

    class Meta:
        verbose_name_plural = 'AI Highlight Chats'
        ordering = ('-created_at',)

class ChatSession(models.Model):
    name = models.CharField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.name

class Message(models.Model):
    chat_session = models.ForeignKey(ChatSession, related_name='messages', on_delete=models.CASCADE)
    content = models.TextField()  # This stores both user input and AI output
    sender = models.CharField(max_length=255)  # 'user' or 'AI'
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender}: {self.content[:80]}..."