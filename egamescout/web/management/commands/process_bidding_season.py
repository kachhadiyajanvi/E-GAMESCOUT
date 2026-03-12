from django.core.management.base import BaseCommand
from django.utils import timezone
from web.models import BiddingSeason, Bid, Organization, Transaction, OrganizationNotification, PlayerNotification, Player
from django.db import transaction

class Command(BaseCommand):
    help = 'Process automatic starting and ending of bidding seasons based on dates.'

    def handle(self, *args, **options):
        now = timezone.now()
        
        # 1. Check for seasons that need to END
        active_season = BiddingSeason.objects.filter(is_active=True).first()
        if active_season and active_season.end_date and active_season.end_date <= now:
            self.end_season(active_season)
            
        # 2. Check for seasons that need to START
        # Only if no active season exists
        if not BiddingSeason.objects.filter(is_active=True).exists():
            pending_season = BiddingSeason.objects.filter(
                is_active=False,
                start_date__lte=now,
                end_date__gt=now,
                auto_start=True
            ).first()
            
            if pending_season:
                self.start_season(pending_season)

    def end_season(self, season):
        self.stdout.write(f"Ending season: {season.name}")
        
        with transaction.atomic():
            season.is_active = False
            season.save()
            
            # Process all PENDING and NEGOTIATION bids
            pending_bids = Bid.objects.filter(season=season, status__in=['Pending', 'Negotiation'])
            
            count = 0
            for bid in pending_bids:
                # Reject bid
                old_status = bid.status
                bid.status = 'Rejected'
                bid.save()
                
                # Refund Organization
                bid.organization.coins += bid.amount
                bid.organization.save()
                
                # Create Refund Transaction
                Transaction.objects.create(
                    recipient=bid.organization,
                    amount=bid.amount,
                    transaction_type='BID_REFUND',
                    description=f"Bid expired at end of season '{season.name}' (Was {old_status})"
                )
                
                # Notify Organization
                OrganizationNotification.objects.create(
                    recipient=bid.organization,
                    message=f"Bidding Season '{season.name}' has ended. Your pending bid for {bid.player.full_name} was cancelled and refunded.",
                    notification_type='BID_SEASON_ENDED'
                )
                
                # Notify Player
                PlayerNotification.objects.create(
                    recipient=bid.player,
                    message=f"Bidding Season '{season.name}' has ended. Unanswered bid from {bid.organization.Organization_Name} expired.",
                    notification_type='BID_SEASON_ENDED'
                )
                
                count += 1
            
            self.stdout.write(self.style.SUCCESS(f"Season '{season.name}' ended. {count} pending bids processed."))

    def start_season(self, season):
        self.stdout.write(f"Starting season: {season.name}")
        
        with transaction.atomic():
            season.is_active = True
            season.save()
            
            # Notify all active organizations
            orgs = Organization.objects.filter(is_active_account=True, is_archived=False)
            for org in orgs:
                OrganizationNotification.objects.create(
                    recipient=org,
                    message=f"Bidding Season '{season.name}' has started! You can now place bids on players.",
                    notification_type='BID_SEASON_STARTED',
                    link='/organization/bidding/'
                )
                
            # Notify all active players
            players = Player.objects.filter(is_active_account=True, is_archived=False, status='ACTIVE')
            for player in players:
                PlayerNotification.objects.create(
                    recipient=player,
                    message=f"Bidding Season '{season.name}' has started! Get ready for offers.",
                    notification_type='BID_SEASON_STARTED',
                    link='/player/bidding/'
                )
                
            self.stdout.write(self.style.SUCCESS(f"Season '{season.name}' started automatically."))
