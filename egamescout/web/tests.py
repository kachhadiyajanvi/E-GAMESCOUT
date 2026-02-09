from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Organization, Player, AdminNotification

class LoginStatusCheckTest(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Create Organizations
        self.active_org = Organization.objects.create(
            Organization_Name="Active Org",
            Organization_Email="active@org.com",
            Organization_UserName="active_org",
            Organization_Contact=1234567890,
            status='Active'
        )
        self.suspended_org = Organization.objects.create(
            Organization_Name="Suspended Org",
            Organization_Email="suspended@org.com",
            Organization_UserName="suspended_org",
            Organization_Contact=1234567890,
            status='Suspended'
        )
        
        # Create Players
        self.active_player = Player.objects.create(
            full_name="Active Player",
            uid="active123",
            mobile_no="1234567890",
            email="active@player.com",
            age=20,
            status='ACTIVE'
        )
        self.suspended_player = Player.objects.create(
            full_name="Suspended Player",
            uid="suspended123",
            mobile_no="1234567890",
            email="suspended@player.com",
            age=20,
            status='SUSPENDED'
        )

    def test_active_org_login(self):
        response = self.client.post(reverse('org_login_start'), {
            'organization_email': 'active@org.com'
        })
        # Should redirect to OTP page
        self.assertRedirects(response, reverse('org_login_otp'))
        # Check if OTP was sent (mock or check session, here checking flow is enough)

    def test_suspended_org_login(self):
        response = self.client.post(reverse('org_login_start'), {
            'organization_email': 'suspended@org.com'
        })
        # Should stay on login start or redirect back to it with error
        # Implementation redirects to 'org_login_start' on error
        self.assertRedirects(response, reverse('org_login_start'))
        
        # Check for error message
        messages = list(response.wsgi_request._messages)
        self.assertTrue(any("Your account has been suspended" in str(m) for m in messages))

    def test_active_player_login(self):
        # Login flow (not register)
        response = self.client.post(reverse('auth_login'), {
            'email': 'active@player.com'
        })
        # Should redirect to OTP verification
        self.assertRedirects(response, reverse('auth_verify_otp'))

    def test_suspended_player_login(self):
        response = self.client.post(reverse('auth_login'), {
            'email': 'suspended@player.com'
        })
        # Should redirect back to auth_login
        self.assertRedirects(response, reverse('auth_login'))
        
        # Check for error message
        messages = list(response.wsgi_request._messages)
        self.assertTrue(any("Your account has been suspended" in str(m) for m in messages))

class NotificationAPITest(TestCase):
    def setUp(self):
        self.client = Client()
        self.superuser = User.objects.create_superuser('admin', 'admin@test.com', 'password')
        self.client.login(username='admin', password='password')
        
        self.notif = AdminNotification.objects.create(
            message="Test Notification",
            notification_type='INFO'
        )

    def test_get_notifications(self):
        response = self.client.get(reverse('get_notifications'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['notifications'][0]['message'], "Test Notification")

    def test_mark_read(self):
        response = self.client.post(reverse('mark_notification_read', args=[self.notif.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        
        # Verify db
        self.notif.refresh_from_db()
        self.assertTrue(self.notif.is_read)

    def test_mark_read_invalid(self):
        response = self.client.post(reverse('mark_notification_read', args=[9999]))
        self.assertEqual(response.status_code, 404)

import time
class OTPExpiryTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.player = Player.objects.create(
            full_name="Test Player", email="test@player.com", status='ACTIVE', age=20, mobile_no="1234567890", uid="test"
        )

    def test_expired_otp(self):
        # 1. Start Login to set session
        self.client.post(reverse('auth_login'), {'email': 'test@player.com'})
        
        # 2. Manipulate session to expire OTP
        session = self.client.session
        session['auth_otp_created_at'] = time.time() - 600 # 10 mins ago
        session.save()
        
        # 3. Try to verify
        otp = session['auth_otp']
        response = self.client.post(reverse('auth_verify_otp'), {'otp_code': otp})
        
        # 4. Should redirect to login (expiry behavior)
        self.assertRedirects(response, reverse('auth_login'))
        
        # 5. Check message
        messages = list(response.wsgi_request._messages)
        self.assertTrue(any("OTP Expired" in str(m) for m in messages))



from django.utils import timezone
from datetime import timedelta
from .models import Organization, Player, AdminNotification, Tournament

class AdminDashboardStatsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.superuser = User.objects.create_superuser('admin', 'admin@test.com', 'password')
        self.client.login(username='admin', password='password')

        # Create Data
        today = timezone.now()
        yesterday = today - timedelta(days=1)
        
        # Player (1 active, 1 new today)
        Player.objects.create(full_name="Old Player", uid="old", age=20, mobile_no="1", email="old@p.com", status='ACTIVE', created_at=yesterday)
        Player.objects.create(full_name="New Player", uid="new", age=20, mobile_no="2", email="new@p.com", status='PENDING', created_at=today)
        
        # Org (1 active, 0 new today)
        Organization.objects.create(Organization_Name="Old Org", Organization_Email="old@o.com", Organization_UserName="old_org", Organization_Contact=1, status='Active', CreatedAt=yesterday)
        
        # Tournament (1 active)
        org = Organization.objects.first()
        Tournament.objects.create(Name="Tourney 1", Organization_Name=org, PrizePool=100.00, Status='Ongoing')

    def test_dashboard_context(self):
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 200)
        
        context = response.context
        # Check Counts
        self.assertEqual(context['player_count'], 2)
        self.assertEqual(context['active_players'], 1)
        
        # Recalculate yesterday for test logic
        today = timezone.now()
        yesterday = today - timedelta(days=1)
        
        p_old = Player.objects.get(uid="old")
        p_old.created_at = yesterday
        p_old.save()
        
        o_old = Organization.objects.get(Organization_UserName="old_org")
        o_old.CreatedAt = yesterday
        o_old.save()
        
        # Re-fetch to test correct date logic
        response = self.client.get(reverse('admin_dashboard'))
        context = response.context
        
        self.assertEqual(context['new_players_today'], 1) # Only "New Player"
        self.assertEqual(context['new_orgs_today'], 0) # "Old Org" moved to yesterday
        self.assertEqual(context['active_tournaments'], 1)
        
        # Check Chart Data
        self.assertEqual(len(context['chart_labels']), 7)
        self.assertEqual(len(context['player_trend']), 7)
        
        # Check Recent Activity
        self.assertTrue(len(context['recent_activity']) > 0)
        self.assertEqual(context['recent_activity'][0]['name'], "New Player") # Newest first
