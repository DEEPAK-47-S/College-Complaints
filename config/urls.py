from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(pattern_name='dashboard:index', permanent=False)),
    path('accounts/', include('apps.accounts.urls', namespace='accounts')),
    path('institutions/', include('apps.institutions.urls', namespace='institutions')),
    path('complaints/', include('apps.complaints.urls', namespace='complaints')),
    path('intelligence/', include('apps.intelligence.urls', namespace='intelligence')),
    path('coordination/', include('apps.coordination.urls', namespace='coordination')),
    path('notifications/', include('apps.notifications.urls', namespace='notifications')),
    path('dashboard/', include('apps.dashboard.urls', namespace='dashboard')),
    path('reports/', include('apps.reports.urls', namespace='reports')),
    path('admin-panel/', include('apps.audit.urls', namespace='admin_panel')),
]
