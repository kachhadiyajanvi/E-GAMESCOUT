from .models import Organization, OrganizationNotification

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
            return {'notifications': notifs}
        except Organization.DoesNotExist:
            pass
    return {}
