from django.contrib import admin
from django.contrib.auth.models import User

from .models import ContractProject, AIHighlightChat, ChatSession, Message, Feedback, ContractSteps, ValidationResult, Subscription, PaymentRecord

# Register your models here.
admin.site.register(ContractProject)
admin.site.register(AIHighlightChat)

admin.site.register(ChatSession)
admin.site.register(Message)
admin.site.register(Feedback)
admin.site.register(ContractSteps)
admin.site.register(ValidationResult)
admin.site.register(Subscription)
admin.site.register(PaymentRecord)