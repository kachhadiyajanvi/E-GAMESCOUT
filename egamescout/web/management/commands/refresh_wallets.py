from django.core.management.base import BaseCommand
from web.models import Organization, Player

class Command(BaseCommand):
    help = 'Refreshes all wallets: Orgs to 100,000, Players to 0'

    def handle(self, *args, **options):
        # Reset Organizations
        orgs_count = Organization.objects.update(coins=0.00)
        self.stdout.write(self.style.SUCCESS(f'Successfully reset {orgs_count} Organizations to 0 coins.'))

        # Reset Players
        # Assuming players start with 0 or a nominal amount. The prompt said "wallet will settel ad zero".
        # Let's set to 0 as a baseline for "fresh" state before being bought.
        players_count = Player.objects.update(coins=0.00)
        self.stdout.write(self.style.SUCCESS(f'Successfully reset {players_count} Players to 0 coins.'))
