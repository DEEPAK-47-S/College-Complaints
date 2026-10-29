from django.urls import path
from . import views

app_name = 'coordination'

urlpatterns = [
    path('', views.coordination_list_view, name='list'),
    path('new/', views.coordination_create_view, name='create'),
    path('<uuid:pk>/', views.coordination_detail_view, name='detail'),
    path('<uuid:pk>/notes/add/', views.coordination_add_note_view, name='add_note'),
    path('<uuid:pk>/status-update/', views.coordination_status_update_view, name='update_status'),
]
