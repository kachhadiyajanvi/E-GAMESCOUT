from django.test import TestCase, Client
from django.urls import reverse
from .models import Organization, Tournament

class OrganizationAuthTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.org = Organization.objects.create(
            Organization_Name="Test Org",
            Organization_Email="test@org.com",
            Organization_UserName="test_org",
            Organization_Contact=1234567890,
            status='Active'
        )

    def test_unauthenticated_dashboard_access(self):
        """Accessing dashboard without session should redirect to login"""
        response = self.client.get(reverse('organizer_dashboard'))
        self.assertRedirects(response, reverse('org_login_start'))

    def test_authenticated_dashboard_access(self):
        """Accessing dashboard with valid session should succeed"""
        # Simulate login
        session = self.client.session
        session['organizer_id'] = self.org.id
        session.save()
        
        response = self.client.get(reverse('organizer_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_manage_profile_access(self):
        """Accessing manage profile with valid session should succeed"""
        session = self.client.session
        session['organizer_id'] = self.org.id
        session.save()
        
        response = self.client.get(reverse('manage_profile'))
        self.assertEqual(response.status_code, 200)

    def test_authenticated_login_redirect(self):
        """Accessing login page with valid session should redirect to dashboard"""
        session = self.client.session
        session['organizer_id'] = self.org.id
        session.save()
        
        response = self.client.get(reverse('org_login_start'))
        self.assertRedirects(response, reverse('organizer_dashboard'))

    def test_soft_delete_tournament(self):
        """Deleting a tournament should mark it as archived, not remove it"""
        # Create tournament
        tournament = Tournament.objects.create(
            Name="Test Tourney",
            Organization_Name=self.org,
            PrizePool=100.00,
            Status='Scheduled'
        )
        
        # Login
        session = self.client.session
        session['organizer_id'] = self.org.id
        session.save()
        
        # Post delete
        response = self.client.post(reverse('tournament_delete', args=[tournament.Tournament_ID]))
        self.assertRedirects(response, reverse('tournament_list'))
        
        # Verify
        tournament.refresh_from_db()
        self.assertTrue(tournament.is_archived)
        
        # Check list view excludes it
        response = self.client.get(reverse('tournament_list'))
        self.assertNotContains(response, "Test Tourney")

    def test_logout(self):
        """Logout should clear session"""
        session = self.client.session
        session['organizer_id'] = self.org.id
        session.save()
        
        response = self.client.get(reverse('org_logout'))
        self.assertRedirects(response, reverse('index'))
        
        # Verify session flushed
        self.assertIsNone(self.client.session.get('organizer_id'))
