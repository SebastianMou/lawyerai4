from django.db import models
from django.contrib.auth.models import User
from tinymce.models import HTMLField
from django.db.models.signals import pre_save
from django.conf import settings
from django.dispatch import receiver

# Create your models here.
class ContractProject(models.Model):
    check_completed = models.BooleanField(default=False)  
    name = models.CharField(max_length=100, null=True)
    description = HTMLField(blank=True, null=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contract_project', null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    contract_steps = models.OneToOneField(
        'ContractSteps',  # Reference to the ContractSteps model
        on_delete=models.SET_NULL,  # If the ContractSteps is deleted, set this field to null
        null=True,
        blank=True,
        related_name='contract_project'  # Allows reverse lookup: contract_steps.contract_project
    )
    has_changes = models.BooleanField(default=False)

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
    check_completed = models.BooleanField(default=False)
    title = models.CharField(max_length=255)  # Contract Title (Required)
    party_one_name = models.CharField(max_length=255, blank=True, null=True)  # First party's name 
    party_one_role = models.CharField(max_length=255, blank=True, null=True)  # First party's role 
    party_two_name = models.CharField(max_length=255, blank=True, null=True)  # Second party's name 
    party_two_role = models.CharField(max_length=255, blank=True, null=True)  # Second party's role
    effective_date = models.DateField(blank=True, null=True)  # Start date of the contract
    purpose = HTMLField(blank=True, null=True)  # Brief description of the contract 
    obligations = HTMLField(blank=True, null=True)  # Responsibilities/Obligations 
    payment_terms = HTMLField(blank=True, null=True)  # Payment terms 
    duration = models.CharField(max_length=255, blank=True, null=True)  # Contract duration 
    termination_clause = HTMLField(blank=True, null=True)  # Conditions for termination 

    # Optional Fields
    confidentiality_clause = HTMLField(blank=True, null=True)  # Confidentiality clause (Optional)
    dispute_resolution = HTMLField(blank=True, null=True)  # Dispute resolution terms (Optional)
    penalties_for_breach = HTMLField(blank=True, null=True)  # Penalty clause (Optional)
    
    notary_required = models.BooleanField(default=False)  # Whether a notary is required (Optional)
    notarization = HTMLField(blank=True, null=True)
    # attachments = models.FileField(upload_to="contract_attachments/", blank=True, null=True)  # Additional documents (Optional)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)  # When the contract was created
    updated_at = models.DateTimeField(auto_now=True)  # When the contract was last updated

    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        text_fields = ['purpose', 'obligations', 'payment_terms', 'termination_clause', 
                       'confidentiality_clause', 'dispute_resolution', 'penalties_for_breach', 'notarization']
        
        for field in text_fields:
            if getattr(self, field) is None:
                setattr(self, field, '')  # Set empty fields to ''

        super().save(*args, **kwargs)

class ValidationResult(models.Model):
    contract = models.ForeignKey('ContractSteps', on_delete=models.CASCADE, related_name='validation_results', null=True, blank=True) # Allow null valuesblank=True  # Allow blank values in forms
    contract_project = models.ForeignKey('ContractProject', on_delete=models.CASCADE, related_name='validation_results', null=True, blank=True)
    check_type = models.CharField(max_length=255)  # Type of check (e.g., "Legal Check", "Spelling Check")
    passed = models.BooleanField()  # Whether the check passed or failed
    issues = models.TextField(blank=True, null=True)  # Details of the issues if the check failed
    created_at = models.DateTimeField(auto_now_add=True)  # Timestamp of the result

    def __str__(self):
        return f"{self.check_type} - {'Passed' if self.passed else 'Failed'}"

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

class Subscription(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    stripe_customer_id = models.CharField(max_length=255, null=True, blank=True)
    stripe_subscription_id = models.CharField(max_length=255, null=True, blank=True)
    subscription_status = models.CharField(max_length=50, choices=[
        ('active', 'Active'),
        ('canceled', 'Canceled'),
        ('past_due', 'Past Due'),
        ('incomplete', 'Incomplete'),
    ], default='incomplete')
    current_period_end = models.DateTimeField(null=True, blank=True)
    product_name = models.CharField(max_length=255, null=True, blank=True)  # Add this field

    def __str__(self):
        return f"Subscription for {self.user.username}"

class PaymentRecord(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    stripe_session_id = models.CharField(max_length=255)
    product_name = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10)
    status = models.CharField(max_length=50)  # e.g., "paid", "failed"
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product_name} - {self.amount} {self.currency} ({self.status})"
