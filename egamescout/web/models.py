from django.db import models
from django.utils import timezone
import datetime

# Create your models here.

class Organization(models.Model):
    Organization_Email = models.CharField(max_length=50, unique=True, null=False)
    Organization_UserName = models.CharField(max_length=30, unique=True, null=False)
    Organization_Name = models.CharField(max_length=20, null=False)
    Organization_Contact = models.BigIntegerField(null=False)
    profile_photo = models.ImageField(upload_to='organization_profiles/', null=True, blank=True)
    instagram_username = models.CharField(max_length=50, null=True, blank=True)
    instagram_link = models.URLField(max_length=200, null=True, blank=True)
    coins = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Suspended', 'Suspended'),
        ('Pending', 'Pending'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Active')
    is_archived = models.BooleanField(default=False)
    CreatedAt = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.Organization_Name

class ScorecardAnalysis(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='scorecards/')
    summary_text = models.TextField()
    ai_provider = models.CharField(max_length=50) # 'gemini' or 'groq'
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Scorecard {self.id} - {self.organization.Organization_Name}"

class Tournament(models.Model):
    STATUS_CHOICES = [
        ('Scheduled', 'Scheduled'),
        ('Ongoing', 'Ongoing'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    ]
    
    Tournament_ID = models.AutoField(primary_key=True)
    Name = models.CharField(max_length=20, null=False)
    Organization_Name = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='tournaments')
    Status = models.CharField(max_length=10, choices=STATUS_CHOICES, null=False, default='Scheduled')
    PrizePool = models.DecimalField(max_digits=15, decimal_places=2, null=False)
    CreatedAt = models.DateTimeField(auto_now_add=True, null=False)
    UpdatedAt = models.DateTimeField(auto_now=True, null=False)
    is_published = models.BooleanField(default=False)
    is_published = models.BooleanField(default=False)
    
    # New Fields
    description = models.TextField(default='')
    max_teams = models.IntegerField(default=16)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    is_offline = models.BooleanField(default=False)
    venue = models.CharField(max_length=255, null=True, blank=True)
    show_roadmap = models.BooleanField(default=False)
    roadmap_content = models.TextField(null=True, blank=True)
    roadmap_content = models.TextField(null=True, blank=True)
    prize_distribution = models.JSONField(default=list, blank=True)
    is_archived = models.BooleanField(default=False)
    
    # Removed Bidding Fields
    
    def __str__(self):
        return f"{self.Name} - {self.Organization_Name.Organization_Name}"

class OrganizationNotification(models.Model):
    recipient = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    notification_type = models.CharField(max_length=50, default='INFO')  # INFO
    related_tournament = models.ForeignKey(Tournament, on_delete=models.SET_NULL, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def link(self):
        if self.related_tournament:
            return f"/organization/tournaments/{self.related_tournament.Tournament_ID}/"
        return "#"

    def __str__(self):
        return f"To {self.recipient.Organization_Name}: {self.message[:30]}"


class Player(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('ACTIVE', 'Active'),
        ('SUSPENDED', 'Suspended'),
    ]

    full_name = models.CharField(max_length=255)
    uid = models.CharField(max_length=50, unique=True, help_text="Unique Game ID or System ID")
    mobile_no = models.CharField(max_length=15)
    email = models.EmailField(unique=True)
    aadhar_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    username = models.CharField(max_length=50, unique=True, null=True, blank=True)
    profile_photo = models.ImageField(upload_to='player_profiles/', null=True, blank=True)
    age = models.IntegerField()
    coins = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank=True, related_name='players')
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # 2FA Fields
    totp_secret = models.CharField(max_length=32, null=True, blank=True)
    is_2fa_enabled = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.full_name} ({self.uid})"

class AdminNotification(models.Model):
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    link = models.CharField(max_length=255, null=True, blank=True)
    notification_type = models.CharField(max_length=50, default='INFO')  # PLAYER, ORG, TOURNAMENT, INFO

    def __str__(self):
        return f"{self.notification_type}: {self.message[:50]}"



class PlayerTask(models.Model):
    TASK_TYPES = [
        ('EVENT', 'Event'),
        ('TASK', 'Task'),
    ]
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    due_date = models.DateTimeField()
    is_completed = models.BooleanField(default=False)
    task_type = models.CharField(max_length=10, choices=TASK_TYPES, default='TASK')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.player.username})"
class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('DEPOSIT', 'Deposit'),
        ('WITHDRAWAL', 'Withdrawal'),
        ('OTHER', 'Other'),
    ]

    sender = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, related_name='sent_transactions')
    recipient = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, related_name='received_transactions')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_type = models.CharField(max_length=50, choices=TRANSACTION_TYPES, default='OTHER')
    related_tournament = models.ForeignKey(Tournament, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.transaction_type}: {self.amount} ({self.timestamp.strftime('%Y-%m-%d %H:%M')})"

class PlayerNotification(models.Model):
    recipient = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    link = models.CharField(max_length=255, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    notification_type = models.CharField(max_length=50, default='INFO')  # INFO

    def __str__(self):
        return f"To {self.recipient.username}: {self.message[:30]}"


