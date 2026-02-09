from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Player, Organization, AdminNotification

@receiver(post_save, sender=Player)
def notify_new_player(sender, instance, created, **kwargs):
    if created:
        AdminNotification.objects.create(
            message=f"New Player Registered: {instance.full_name} ({instance.email})",
            notification_type='PLAYER',
            link='/admin/players/' 
        )

@receiver(post_save, sender=Organization)
def notify_new_organization(sender, instance, created, **kwargs):
    if created:
        AdminNotification.objects.create(
            message=f"New Organization Registered: {instance.Organization_Name}",
            notification_type='ORG',
            link='/admin/organizations/'
        )
