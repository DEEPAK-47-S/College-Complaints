from django.urls import path
from . import views

app_name = 'institutions'

urlpatterns = [
    path('', views.institution_list_view, name='list'),
    path('new/', views.institution_create_view, name='create'),
    path('<uuid:pk>/', views.institution_detail_view, name='detail'),
    path('<uuid:pk>/edit/', views.institution_edit_view, name='edit'),
    path('<uuid:pk>/360/', views.institution_360_view, name='institution_360'),
]
