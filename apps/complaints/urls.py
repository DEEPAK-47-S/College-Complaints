from django.urls import path
from . import views

app_name = 'complaints'

urlpatterns = [
    path('', views.complaint_list_view, name='list'),
    path('new/', views.complaint_create_view, name='create'),
    path('<uuid:pk>/', views.complaint_detail_view, name='detail'),
    path('<uuid:pk>/assign/', views.complaint_assign_view, name='assign'),
    path('<uuid:pk>/transition/', views.complaint_transition_view, name='transition'),
    path('<uuid:pk>/transfer/', views.complaint_transfer_view, name='transfer'),
    path('<uuid:pk>/escalate/', views.complaint_escalate_view, name='escalate'),
    path('<uuid:pk>/documents/upload/', views.complaint_upload_document_view, name='upload_document'),
    path('<uuid:pk>/documents/<uuid:doc_id>/download/', views.complaint_download_document_view, name='download_document'),
]
