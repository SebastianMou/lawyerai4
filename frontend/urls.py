from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('chats/', views.chats, name='chats'),
    path('contracts/', views.contracts, name='contracts'),
    path('contract/<int:pk>/', views.contract, name='contract'),
    path('contract/<int:pk>/', views.contract, name='contract'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    path('signup/', views.signup, name='signup'),
    # activación de la cuenta de usuario por correo electrónico
    path('activate/<uidb64>/<token>', views.activate, name='activate'),
    path('check-email/', views.check_email, name='check_email'),


]