from django.urls import path
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required

from . import views

urlpatterns = [
    path('', views.index, name='index'),
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
    path('contract-stepbystep/', views.contract_stepbystep, name='contract_stepbystep'),

    path('signup/', views.signup, name='signup'),
    # activación de la cuenta de usuario por correo electrónico
    path('activate/<uidb64>/<token>', views.activate, name='activate'),
    path('check-email/', views.check_email, name='check_email'),
    
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