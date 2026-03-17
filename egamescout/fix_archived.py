import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'egamescout.settings')
django.setup()

from web.models import Player, Organization
from django.utils import timezone
from django.db import transaction

def fix_archived():
    with transaction.atomic():
        # Fix Organizations
        orgs = Organization.objects.filter(is_archived=True)
        for org in orgs:
            if not org.Organization_Email.startswith('archived_'):
                timestamp_str = (org.archived_at or timezone.now()).strftime("%Y%m%d%H%M%S")
                org.Organization_Email = f"archived_{timestamp_str}_{org.Organization_Email}"[:50]
                org.Organization_UserName = f"archived_{timestamp_str}_{org.Organization_UserName}"[:30]
                org.save()
                print(f"Fixed Organization: {org.Organization_Name}")

        # Fix Players
        players = Player.objects.filter(is_archived=True)
        for player in players:
            if not player.email.startswith('archived_'):
                timestamp_str = (player.archived_at or timezone.now()).strftime("%Y%m%d%H%M%S")
                player.email = f"archived_{timestamp_str}_{player.email}"[:254]
                player.uid = f"archived_{timestamp_str}_{player.uid}"[:50]
                
                if player.username and not player.username.startswith('archived_'):
                    player.username = f"archived_{timestamp_str}_{player.username}"[:50]
                if player.aadhar_number and not player.aadhar_number.startswith('archived_'):
                    player.aadhar_number = f"archived_{timestamp_str}_{player.aadhar_number}"[:20]
                    
                player.save()
                print(f"Fixed Player: {player.full_name}")

if __name__ == '__main__':
    fix_archived()
