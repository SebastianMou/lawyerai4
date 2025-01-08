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
    path('contract/transfer/<int:pk>/', views.transfer_contract_to_project, name='transfer-contract-to-project'),

    # AI Chat for Contract
    path('create-ai-chat-contract/<int:contract_project_id>/', views.create_ai_chat_contract, name='create-ai-chat-contract'),
    path('get-chat-history-contract/<int:contract_project_id>/', views.get_chat_history_contract, name='get-chat-history-contract'),
    path('delete-chat-history-contract/<int:contract_project_id>/', views.delete_chat_history_contract, name='delete-chat-history-contract'),

    path('search/', views.search_api, name='api_search'),
    path('feed-back/', views.feed_back, name='feed-back'),
    
    # Steps for contract creation
    path('contract-steps/', views.contract_steps, name='contract-steps'),
    path('generate-suggestions/', views.generate_suggestions, name='generate-suggestions'),
    path('generate-ai-text/', views.generate_ai_text, name='generate-ai-text'),
    path('contract-check-basis/<int:pk>/', views.contract_check_basis, name='contract-check-basis'),
    path('contract/<int:pk>/test-legality-check/', views.legality_check_view, name='legality-check-view'),
    path('contract/<int:pk>/full-test-legality-check/', views.full_doc_ai_check_view, name='full-doc-ai-check-view'),

    path('contract-steps-project/', views.contract_steps_project, name='contract-steps-project'),
    path('contract-steps-project-detail/<int:pk>/', views.contract_steps_project_detail, name='contract-steps-project-detail'),
    path('contract-steps-project-update/<int:pk>/', views.contract_steps_project_update, name='contract-steps-project-update'),
    path('contract-steps-project-delete/<int:pk>/', views.contract_steps_project_delete, name='contract-steps-project-delete'),

    # Chat Session Lawyer URLs
    path('chatsessions/', views.list_chat_sessions, name='list_chat_sessions'),
    path('chatsessions/create/', views.create_chat_session, name='create_chat_session'),
    path('chatsessions/<int:session_id>/', views.retrieve_chat_session, name='retrieve_chat_session'),
    path('chatsessions/<int:session_id>/send_message/', views.send_message_to_chat_session, name='send_message_to_chat_session'),
    path('chatsessions/user/', views.list_user_chat_sessions, name='list_user_chat_sessions'),

    path('chatsessions/<int:session_id>/update/', views.update_chat_session, name='update_chat_session'),
    path('chatsessions/<int:session_id>/delete/', views.delete_chat_session, name='delete_chat_session'),
]
