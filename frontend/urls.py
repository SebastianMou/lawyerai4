from django.urls import path
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('hero/', views.hero, name='hero'),
    path('chats/', views.chats, name='chats'),
    path('contracts/', views.contracts, name='contracts'),
    path('contract/<int:pk>/', views.contract, name='contract'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    path('chat/<int:session_id>/', views.view_chat_session, name='chat'),
    path('pages/', views.pages, name='pages'),
    path('delete_account/', views.delete_account, name='delete_account'),
    path('contract_project/<int:pk>/download_pdf/', views.download_contract_pdf, name='download_contract_pdf'),

    path('search/', views.search, name='search'),
    path('feedback/', views.feedback, name='feedback'),

    path('create-checkout-session/', views.create_checkout_session, name='create_checkout_session'),
    path('success/', views.success_view, name='success'),
    path('cancel/', views.cancel_view, name='cancel'),
    path('cancel-subscription/', views.cancel_subscription, name='cancel_subscription'),
    path('stripe-webhook/', views.stripe_webhook, name='stripe_webhook'),

    path('signup/', views.signup, name='signup'),
    # activación de la cuenta de usuario por correo electrónico
    path('activate/<uidb64>/<token>', views.activate, name='activate'),
    path('check-email/', views.check_email, name='check_email'),
    path('paper/', views.paper, name='paper'),

    path('contract-stepbystep/', views.contract_stepbystep, name='contract_stepbystep'),
    path('contract-checklist-basis/', views.contract_checklist_basis, name='contract_checklist_basis'),
    path('contract-check-basis/<int:pk>/', views.contract_check_basis_view, name='contract_check_basis_view'),
    path('contract-step/<int:pk>/', views.contract_step, name='contract-step'),
    path('generate-contract-pdf/<int:contract_id>/', views.generate_contract_pdf, name='generate_contract_pdf'),
    path('generate-contract-pdf-full-doc/<int:contract_id>/', views.generate_contract_pdf_full_doc, name='generate_contract_pdf_full_doc'),
    path('full-doc-ai-check/<int:pk>/', views.full_doc_ai_check, name='full_doc_ai_check'),
    path('factura/', views.invoice, name='invoice'),

    # User change password from account 
    path('change_password/', login_required(auth_views.PasswordChangeView.as_view(template_name='authentication/password_change.html', success_url='/password_changed/')), name='password_change'),
    path('password_changed/', login_required(auth_views.PasswordChangeDoneView.as_view(template_name='authentication/password_changed.html')), name='password_changed'),  
    # Forgoten password
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='authentication/password_reset.html'), name="password_reset"),
    path('password_reset_sent/', auth_views.PasswordResetDoneView.as_view(template_name='authentication/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name="authentication/password_reset_confirm.html"), name='password_reset_confirm'),
    path('reset_password_complete/', auth_views.PasswordResetCompleteView.as_view(template_name='authentication/password_reset_complete.html'), name='password_reset_complete'),
]