from django.core.management.base import BaseCommand
from django.utils import timezone
from web.models import ExternalPlayerInvite

class Command(BaseCommand):
    help = 'Cleans up expired external player invitation tokens'

    def handle(self, *args, **options):
        now = timezone.now()
        
        # Find invites where expires_at is in the past
        expired_invites = ExternalPlayerInvite.objects.filter(expires_at__lt=now)
        count = expired_invites.count()
        
        if count > 0:
            expired_invites.delete()
            self.stdout.write(self.style.SUCCESS(f'Successfully deleted {count} expired tokens.'))
        else:
            self.stdout.write(self.style.SUCCESS('No expired tokens found.'))
