from .models import Organization, OrganizationNotification, Player, PlayerNotification

def notifications(request):
    """
    Context processor to make notifications available in all templates 
    assigned to the logged-in organization.
    """
    org_id = request.session.get('organizer_id')
    if org_id:
        try:
            org = Organization.objects.get(id=org_id)
            notifs = OrganizationNotification.objects.filter(recipient=org, is_read=False).order_by('-created_at')
            return {'notifications': notifs, 'notifications_count': notifs.count()}
        except Organization.DoesNotExist:
            pass
    
    player_id = request.session.get('player_id')
    if player_id:
        try:
            player = Player.objects.get(id=player_id)
            player_notifs = PlayerNotification.objects.filter(recipient=player, is_read=False).order_by('-created_at')
            return {'player_notifications': player_notifs, 'player_notifications_count': player_notifs.count()}
        except Player.DoesNotExist:
            pass
            
    return {}
