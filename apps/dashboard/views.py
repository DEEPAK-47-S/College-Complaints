from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .services import DashboardMetricsService

@login_required
def index_view(request):
    """
    Main operational and intelligence dashboard for AUGIS.
    All figures originate directly from the database and respect role scoping.
    """
    metrics = DashboardMetricsService.get_dashboard_kpis(request.user)
    return render(request, 'dashboard/index.html', metrics)
