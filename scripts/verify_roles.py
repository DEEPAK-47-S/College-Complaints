import django, os, sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.test.utils import setup_test_environment; setup_test_environment()
from django.test import Client
from apps.accounts.models import User

client = Client()
users = [
    'admin', 'rb_head', 'pgrc_head', 'rb_officer', 
    'pgrc_officer', 'ro_north', 'senior_mgmt', 'competent_auth'
]

print(f"{'User':<15} {'Role':<17} {'Total':<6} {'Pending':<8} {'Overdue':<8} {'Role Custom KPI'}")
print('='*75)
for username in users:
    u = User.objects.get(username=username)
    client.force_login(u)
    resp = client.get('/dashboard/')
    ctx = resp.context
    tot = ctx.get('total')
    pnd = ctx.get('pending')
    ovd = ctx.get('overdue')
    
    role_kpi = ""
    if u.role == 'CASE_OFFICER':
        role_kpi = f"Assigned to Me: {ctx.get('my_assigned_count')}"
    elif u.role == 'BUREAU_HEAD':
        role_kpi = f"Pending Transfers: {ctx.get('pending_transfers_count')}"
    elif u.role == 'COMPETENT_AUTH':
        role_kpi = f"Escalated Cases: {ctx.get('escalated_cases_count')}"
    elif u.role == 'REGIONAL_OFFICER':
        role_kpi = f"Regional Inst: {ctx.get('regional_institutions_count')}"
    elif u.role == 'SENIOR_MGMT':
        role_kpi = f"Disposal Rate: {ctx.get('disposal_rate')}%"
    elif u.role == 'SUPER_ADMIN':
        role_kpi = f"National Overlaps: {ctx.get('pending_overlaps')}"

    print(f"{u.username:<15} {u.role:<17} {str(tot):<6} {str(pnd):<8} {str(ovd):<8} {role_kpi}")
