from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    path('audit/', views.audit_log_list_view, name='audit_list'),
    path('users/', views.user_management_list_view, name='user_list'),
    path('bureaus/', views.bureau_management_list_view, name='bureau_list'),
]
