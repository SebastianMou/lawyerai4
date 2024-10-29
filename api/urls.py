from django.urls import path
from . import views

urlpatterns = [
    path('', views.apiOverview, name='api-overview'),
    
    # Contract Project URLs
    path('contract-project/', views.contract_project, name='contract-project'),
    path('contract-detail/<int:pk>/', views.contract_project_detail, name='contract-detail'),
    path('contract-create/', views.contract_project_create, name='contract-create'),
    path('contract-update/<int:pk>/', views.contract_project_update, name='contract-update'),
    path('contract-delete/<int:pk>/', views.contract_project_delete, name='contract-delete'),
    
    # AI Chat for Contract
    path('create-ai-chat-contract/<int:contract_project_id>/', views.create_ai_chat_contract, name='create-ai-chat-contract'),
    path('get-chat-history-contract/<int:contract_project_id>/', views.get_chat_history_contract, name='get-chat-history-contract'),
    
    # Chat Session Lawyer URLs
    path('chatsessions/', views.list_chat_sessions, name='list_chat_sessions'),
    path('chatsessions/create/', views.create_chat_session, name='create_chat_session'),
    path('chatsessions/<int:session_id>/', views.retrieve_chat_session, name='retrieve_chat_session'),
    path('chatsessions/<int:session_id>/send_message/', views.send_message_to_chat_session, name='send_message_to_chat_session'),
    path('chatsessions/user/', views.list_user_chat_sessions, name='list_user_chat_sessions'),

    path('chatsessions/<int:session_id>/update/', views.update_chat_session, name='update_chat_session'),
    path('chatsessions/<int:session_id>/delete/', views.delete_chat_session, name='delete_chat_session'),
]
