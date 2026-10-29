from django.urls import path
from . import views

app_name = 'intelligence'

urlpatterns = [
    path('', views.intelligence_dashboard_view, name='dashboard'),
    path('candidate/<uuid:pk>/', views.candidate_detail_view, name='detail'),
    path('candidates/<uuid:pk>/', views.candidate_detail_view),
    path('candidate/<uuid:pk>/ai-analyze/', views.run_gemini_analysis_view, name='ai_analyze'),
    path('candidate/<uuid:pk>/review/', views.candidate_review_action_view, name='review_action'),
]
