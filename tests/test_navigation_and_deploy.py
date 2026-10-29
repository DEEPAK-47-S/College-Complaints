from django.test import TestCase, Client
from django.urls import reverse
from django.core.management import call_command
from apps.accounts.models import User
from apps.bureaus.models import Bureau
from apps.institutions.models import Institution
from apps.complaints.models import ComplaintCategory
from apps.complaints.forms import ComplaintCreateForm

class NavigationAndDeploymentTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.bureau = Bureau.objects.create(code='RB', name='Regulation Bureau')
        self.admin = User.objects.create_user(
            username='admin_nav',
            email='admin_nav@test.gov.in',
            password='TestPassword@123',
            role=User.Role.SUPER_ADMIN,
            display_name='Nav Admin'
        )
        self.client.login(username='admin_nav', password='TestPassword@123')

        self.inst = Institution.objects.create(
            aicte_permanent_id='1-AICTE-NAV-01',
            name='Nav Test College',
            institution_type='ENGINEERING',
            address='Road 1',
            district='Bhopal',
            state='Madhya Pradesh',
            region='CENTRAL',
            pincode='462001'
        )

        self.cat = ComplaintCategory.objects.create(code='NAV_CAT', name='Nav Category')

    def test_t27_responsive_layout_assets_render(self):
        """T27: Layout and responsive design CSS assets are served properly."""
        response = self.client.get(reverse('dashboard:index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'augis.css')
        self.assertContains(response, 'augis.js')
        self.assertContains(response, 'app-sidebar')

    def test_t28_all_primary_navigation_links_resolve(self):
        """T28: All primary navigation links resolve successfully without 404 or 500 errors."""
        routes = [
            reverse('dashboard:index'),
            reverse('institutions:list'),
            reverse('institutions:create'),
            reverse('institutions:detail', args=[self.inst.id]),
            reverse('institutions:institution_360', args=[self.inst.id]),
            reverse('complaints:list'),
            reverse('complaints:create'),
            reverse('intelligence:dashboard'),
            reverse('coordination:list'),
            reverse('notifications:list'),
            reverse('reports:index'),
            reverse('admin_panel:audit_list'),
            reverse('accounts:profile'),
        ]

        for route in routes:
            with self.subTest(route=route):
                resp = self.client.get(route)
                self.assertEqual(resp.status_code, 200)

    def test_t29_forms_show_meaningful_validation_messages(self):
        """T29: Forms display clear server-side validation error messages on invalid input."""
        # Empty title and missing description
        form = ComplaintCreateForm(data={
            'institution': self.inst.id,
            'currently_assigned_bureau': self.bureau.id,
            'category': self.cat.id,
            'title': '',
            'description': '',
            'source_channel': 'PORTAL',
            'priority': 'MEDIUM'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('title', form.errors)
        self.assertIn('description', form.errors)

    def test_t30_production_deployment_configuration_check(self):
        """T30: Django check passes cleanly for core and settings."""
        # Run system check
        call_command('check')
        # Check passes without raising SystemCheckError
        self.assertTrue(True)
