from django.utils import timezone
from .models import Organization, OrganizationNotification, Player, PlayerNotification, BiddingSeason, BiddingSeasonLog
from django.utils.formats import date_format

def notifications(request):
    """
    Context processor to make notifications available in all templates 
    assigned to the logged-in organization.
    """
        
    # --- AUTOMATIC & MANUAL BIDDING SYSTEM (JAN 1-31 & JUL 1-31) ---
    now = timezone.now()
    year = now.year

    # Define the strict bounds for the current year
    jan_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    jan_end = now.replace(month=1, day=31, hour=23, minute=59, second=59, microsecond=999999)
    
    jul_start = now.replace(month=7, day=1, hour=0, minute=0, second=0, microsecond=0)
    jul_end = now.replace(month=7, day=31, hour=23, minute=59, second=59, microsecond=999999)

    bidding_status = {
        'is_active': False,
        'season_name': '',
        'start_date': None,
        'end_date': None,
        'next_season_start': None
    }
    
    # Check if there's a manually activated season taking precedence
    active_season = BiddingSeason.objects.filter(is_active=True).first()
    manual_override = False

    if active_season and not active_season.auto_start:
        # Admin manually triggered a season. Let's see if it has expired.
        if active_season.end_date and now >= active_season.end_date:
            active_season.is_active = False
            active_season.save()
            BiddingSeasonLog.objects.create(season=active_season, action='AUTO_END', message="Manual season ended based on end date.")
            active_season = None
        else:
            manual_override = True
            bidding_status['is_active'] = True
            bidding_status['season_name'] = active_season.name
            bidding_status['start_date'] = active_season.start_date or now
            bidding_status['end_date'] = active_season.end_date
            
            # Auto-End any automated seasons if manual is active
            BiddingSeason.objects.filter(is_active=True, auto_start=True).update(is_active=False)

    if not manual_override:
        # Fall back to strict schedule
        if jan_start <= now <= jan_end:
            bidding_status['is_active'] = True
            bidding_status['season_name'] = f"Winter Season {year}"
            bidding_status['start_date'] = jan_start
            bidding_status['end_date'] = jan_end
        elif jul_start <= now <= jul_end:
            bidding_status['is_active'] = True
            bidding_status['season_name'] = f"Summer Season {year}"
            bidding_status['start_date'] = jul_start
            bidding_status['end_date'] = jul_end
        else:
            # Bidding is closed. Calculate next season start.
            bidding_status['is_active'] = False
            if now < jan_start:
                bidding_status['next_season_start'] = jan_start
            elif now < jul_start:
                bidding_status['next_season_start'] = jul_start
            else:
                bidding_status['next_season_start'] = jan_start.replace(year=year + 1)

        # Sync Database State automatically for strict scheduled windows
        if bidding_status['is_active']:
            season, created = BiddingSeason.objects.get_or_create(
                name=bidding_status['season_name'],
                defaults={
                    'start_date': bidding_status['start_date'],
                    'end_date': bidding_status['end_date'],
                    'is_active': True,
                    'auto_start': True
                }
            )
            if not season.is_active:
                BiddingSeason.objects.filter(is_active=True).update(is_active=False)
                season.is_active = True
                season.save()
                BiddingSeasonLog.objects.create(season=season, action='AUTO_START', message="System auto-activated season based on Jan/Jul schedule.")
            active_season = season
        else:
            # If no manual override is active and we are outside the bounds, turn off any auto seasons.
            active_seasons = BiddingSeason.objects.filter(is_active=True, auto_start=True)
            for season in active_seasons:
                season.is_active = False
                season.save()
                BiddingSeasonLog.objects.create(season=season, action='AUTO_END', message="System auto-ended season based on Jan/Jul schedule.")
    
    base_context = {
        'active_season': active_season, # Legacy variable for DB compatibility
        'bidding_status': bidding_status # New strictly calculated UI statuses
    }

    if not hasattr(request, 'session'):
        return base_context
        
    org_id = request.session.get('organizer_id')
    if org_id:
        try:
            org = Organization.objects.get(id=org_id)
            notifs = OrganizationNotification.objects.filter(recipient=org, is_read=False).order_by('-created_at')
            base_context.update({'notifications': notifs, 'notifications_count': notifs.count()})
            return base_context
        except Organization.DoesNotExist:
            pass
    
    player_id = request.session.get('player_id')
    if player_id:
        try:
            player = Player.objects.get(id=player_id)
            player_notifs = PlayerNotification.objects.filter(recipient=player, is_read=False).order_by('-created_at')
            base_context.update({'player_notifications': player_notifs, 'player_notifications_count': player_notifs.count()})
            return base_context
        except Player.DoesNotExist:
            pass
            
    return base_context
