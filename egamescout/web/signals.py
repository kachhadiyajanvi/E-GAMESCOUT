from django.db.models.signals import post_save
from django.dispatch import receiver
from web.models import Player, Organization, AdminNotification

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

from web.models import Contract, Transaction, Bid, ExternalPlayerInvite, SystemLog, PlayerNotification, OrganizationNotification

@receiver(post_save, sender=Contract)
def notify_contract_updates(sender, instance, created, **kwargs):
    if created:
        PlayerNotification.objects.create(
            recipient=instance.player,
            message=f"{instance.organization.Organization_Name} has sent you an official contract. Please review and sign it.",
            link='/player/contract/'
        )
        SystemLog.objects.create(
            user_id=instance.organization.id,
            user_type='ORGANIZATION',
            action='Sent Contract',
            details=f"Sent contract to {instance.player.full_name}"
        )

@receiver(post_save, sender=Transaction)
def notify_transaction_updates(sender, instance, created, **kwargs):
    if created:
        SystemLog.objects.create(
            user_id=instance.recipient.id if instance.recipient else 0,
            user_type='ORGANIZATION',
            action='Transaction',
            details=f"{instance.transaction_type}: {instance.amount} coins"
        )
