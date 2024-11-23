from django.db import models
from django.contrib.auth.models import User
from tinymce.models import HTMLField
from django.db.models.signals import pre_save
from django.conf import settings
from django.dispatch import receiver

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

class ContractSteps(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="contracts")  # Related to User model
    # Core Elements
    title = models.CharField(max_length=255)  # Contract Title (Required)
    party_one_name = models.CharField(max_length=255, blank=True, null=True)  # First party's name (Optional)
    party_one_role = models.CharField(max_length=255, blank=True, null=True)  # First party's role (Optional)
    party_two_name = models.CharField(max_length=255, blank=True, null=True)  # Second party's name (Optional)
    party_two_role = models.CharField(max_length=255, blank=True, null=True)  # Second party's role (Optional)
    effective_date = models.DateField(blank=True, null=True)  # Start date of the contract (Optional)
    purpose = HTMLField(blank=True, null=True)  # Brief description of the contract (Optional)
    obligations = HTMLField(blank=True, null=True)  # Responsibilities/Obligations (Optional)
    payment_terms = HTMLField(blank=True, null=True)  # Payment terms (Optional)
    duration = models.CharField(max_length=255, blank=True, null=True)  # Contract duration (Optional)
    termination_clause = models.TextField(blank=True, null=True)  # Conditions for termination (Optional)

    # Optional Fields
    confidentiality_clause = HTMLField(blank=True, null=True)  # Confidentiality clause (Optional)
    dispute_resolution = HTMLField(blank=True, null=True)  # Dispute resolution terms (Optional)
    penalties_for_breach = HTMLField(blank=True, null=True)  # Penalty clause (Optional)
    notary_required = models.BooleanField(default=False)  # Whether a notary is required (Optional)
    attachments = models.FileField(upload_to="contract_attachments/", blank=True, null=True)  # Additional documents (Optional)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)  # When the contract was created
    updated_at = models.DateTimeField(auto_now=True)  # When the contract was last updated

    def __str__(self):
        return self.title


class Feedback(models.Model):
    FEEDBACK_TYPE_CHOICES = [
        ('bug', 'Error'),
        ('complaint', 'Queja'),
        ('suggestion', 'Sugerencia'),
        ('other', 'Otro'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    feedback_type = models.CharField(max_length=20, choices=FEEDBACK_TYPE_CHOICES)
    message = models.TextField()
    email = models.EmailField(blank=True, null=True)  # Optional email field
    phone_number = models.CharField(max_length=15, blank=True, null=True)  # Optional phone number field
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.feedback_type} - {self.created_at}"