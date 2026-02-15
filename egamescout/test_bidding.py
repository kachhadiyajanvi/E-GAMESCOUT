import pymysql
pymysql.install_as_MySQLdb()
import MySQLdb
setattr(MySQLdb, 'version_info', (2, 2, 7, 'final', 0))
setattr(pymysql, 'version_info', (2, 2, 7, 'final', 0))

# Bypass MariaDB version check
try:
    from django.db.backends.mysql.base import DatabaseWrapper
    DatabaseWrapper.check_database_version_supported = lambda self: None
    from django.db.backends.mysql.features import DatabaseFeatures
    DatabaseFeatures.can_return_columns_from_insert = False
except ImportError:
    pass

import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'egamescout.settings')
django.setup()

from web.models import Organization, Tournament, OrganizationNotification, TournamentBidder
from django.test import RequestFactory
from web.views import open_bidding, handle_bidding_invite

# Setup Test Data
print("Setting up test data...")
org_a, _ = Organization.objects.get_or_create(
    Organization_Email='owner@test.com',
    defaults={'Organization_Name': 'Owner Org', 'Organization_UserName': 'owner', 'Organization_Contact': 1234567890}
)
org_b, _ = Organization.objects.get_or_create(
    Organization_Email='bidder@test.com',
    defaults={'Organization_Name': 'Bidder Org', 'Organization_UserName': 'bidder', 'Organization_Contact': 9876543210}
)

tournament = Tournament.objects.create(
    Name='Bidding Test Tourney',
    Organization_Name=org_a,
    Status='Scheduled',
    PrizePool=1000,
    bidding_open=False
)

print(f"Tournament created: {tournament.Name} (ID: {tournament.Tournament_ID})")

# 1. Test Open Bidding
print("\n--- Testing Open Bidding ---")
factory = RequestFactory()
request = factory.post(f'/organization/tournaments/bidding/open/{tournament.Tournament_ID}/')
from django.contrib.sessions.middleware import SessionMiddleware
middleware = SessionMiddleware(lambda x: None)
middleware.process_request(request)
request.session['organizer_id'] = org_a.id
request.session.save()

# Add message support
from django.contrib.messages.storage.fallback import FallbackStorage
setattr(request, 'session', request.session)
messages = FallbackStorage(request)
setattr(request, '_messages', messages)

open_bidding(request, tournament.Tournament_ID)

tournament.refresh_from_db()
print(f"Bidding Open: {tournament.bidding_open}")

# Check Notifications
notifs = OrganizationNotification.objects.filter(recipient=org_b, related_tournament=tournament)
print(f"Notifications for Org B: {notifs.count()}")
if notifs.exists():
    n = notifs.first()
    print(f"Notification: {n.message} (Type: {n.notification_type})")
    
    # 2. Test Accept Bid
    print("\n--- Testing Accept Invite ---")
    request_accept = factory.get(f'/organization/notifications/invite/{n.id}/accept/')
    middleware.process_request(request_accept)
    request_accept.session['organizer_id'] = org_b.id # Login as Bidder
    request_accept.session.save()
    setattr(request_accept, 'session', request_accept.session)
    messages = FallbackStorage(request_accept)
    setattr(request_accept, '_messages', messages)

    handle_bidding_invite(request_accept, n.id, 'accept')
    
    # Verify Bidder
    is_bidder = TournamentBidder.objects.filter(tournament=tournament, organization=org_b).exists()
    print(f"Org B is Bidder: {is_bidder}")
    
    # Verify Notification Deleted
    notif_exists = OrganizationNotification.objects.filter(id=n.id).exists()
    print(f"Notification Exists: {notif_exists}")

# Cleanup
print("\nCleaning up...")
tournament.delete()
OrganizationNotification.objects.filter(recipient=org_b).delete()
# Orgs are kept for future tests
