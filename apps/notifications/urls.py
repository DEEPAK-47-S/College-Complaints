from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.notification_list_view, name='list'),
    path('<uuid:pk>/read/', views.mark_notification_read_view, name='mark_read'),
    path('mark-all-read/', views.mark_all_read_view, name='mark_all_read'),
    path('unread-count/', views.unread_count_api_view, name='unread_count'),
]
