from django.db import models
from django.utils import timezone
import datetime
from django.core.exceptions import ValidationError

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
        ('Rejected', 'Rejected'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Active')
    is_active_account = models.BooleanField(default=True)
    is_archived = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True)
    has_seen_player_setup_popup = models.BooleanField(default=False)
    last_player_reminder_date = models.DateField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    organization_signature = models.ImageField(upload_to='organization_signatures/', null=True, blank=True)
    CreatedAt = models.DateTimeField(auto_now_add=True)
    
    # 2FA Fields
    totp_secret = models.CharField(max_length=32, null=True, blank=True)
    is_2fa_enabled = models.BooleanField(default=False)

    def __str__(self):
        return self.Organization_Name

class ScorecardAnalysis(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    tournament = models.ForeignKey('PreviousTournament', on_delete=models.SET_NULL, null=True, blank=True, related_name='ai_analyses')
    image = models.ImageField(upload_to='scorecards/')
    summary_text = models.TextField()
    raw_data = models.JSONField(null=True, blank=True, help_text="Stored JSON data from AI")
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
    
    APPROVAL_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    approval_status = models.CharField(max_length=15, choices=APPROVAL_CHOICES, default='DRAFT')
    admin_rejection_reason = models.TextField(null=True, blank=True)
    
    # New Fields
    description = models.TextField(default='')
    max_teams = models.IntegerField(default=16)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    is_offline = models.BooleanField(default=False)
    venue = models.CharField(max_length=255, null=True, blank=True)
    show_roadmap = models.BooleanField(default=False)
    roadmap_content = models.TextField(null=True, blank=True)
    prize_distribution = models.JSONField(default=list, blank=True)
    is_archived = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True)
    
    # Removed Bidding Fields
    
    def __str__(self):
        return f"{self.Name} - {self.Organization_Name.Organization_Name}"

class TournamentBidder(models.Model):
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='bidders')
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE, related_name='participating_tournaments')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('tournament', 'organization')

    def __str__(self):
        return f"{self.organization.Organization_Name} - {self.tournament.Name}"

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
        ('REJECTED', 'Rejected'),
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
    is_active_account = models.BooleanField(default=True)
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank=True, related_name='players')
    address = models.CharField(max_length=500, null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    is_archived = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # 2FA Fields
    totp_secret = models.CharField(max_length=32, null=True, blank=True)
    is_2fa_enabled = models.BooleanField(default=False)

    SKILL_ROLE_CHOICES = [
        ('IGL(In Game Leader)', 'IGL(In Game Leader)'),
        ('Fragger', 'Fragger'),
        ('Assaulter', 'Assaulter'),
        ('Freeman', 'Freeman'),
        ('Support', 'Support'),
    ]
    skill_role = models.CharField(max_length=50, choices=SKILL_ROLE_CHOICES, null=True, blank=True, help_text="Select your primary in-game role")

    # Social Fields
    instagram_username = models.CharField(max_length=150, null=True, blank=True)
    instagram_link = models.URLField(max_length=200, null=True, blank=True)
    youtube_username = models.CharField(max_length=150, null=True, blank=True)
    youtube_link = models.URLField(max_length=200, null=True, blank=True)
    discord_username = models.CharField(max_length=150, null=True, blank=True)
    discord_link = models.URLField(max_length=200, null=True, blank=True)

    def __str__(self):
        return f"{self.full_name} ({self.uid})"

class OrganizationPlayer(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='roster_players')
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='org_affiliations', null=True, blank=True)
    name = models.CharField(max_length=255)
    email = models.EmailField()
    game_id = models.CharField(max_length=50)
    position = models.CharField(max_length=50, default='Player')
    status_label = models.CharField(max_length=50, default='Added Manually') # e.g., 'Added Manually', 'Purchased via Bidding', 'External (Verified)'
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.organization.Organization_Name}"

import uuid
import datetime as dt

class ExternalPlayerInvite(models.Model):
    """Pending invitation for a player not registered in the system.
    They must verify their email before being added to the organization's roster."""
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('ACCEPTED', 'Accepted'),
        ('EXPIRED', 'Expired'),
    ]
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='external_invites')
    name = models.CharField(max_length=255)
    email = models.EmailField()
    game_id = models.CharField(max_length=100)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def save(self, *args, **kwargs):
        if not self.pk:
            self.expires_at = timezone.now() + datetime.timedelta(days=3)
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"Invite: {self.email} → {self.organization.Organization_Name}"

class AdminNotification(models.Model):
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    link = models.CharField(max_length=255, null=True, blank=True)
    notification_type = models.CharField(max_length=50, default='INFO')  # PLAYER, ORG, TOURNAMENT, INFO

    def __str__(self):
        return f"{self.notification_type}: {self.message[:50]}"

# --- Tournament History Models ---

class PreviousTournament(models.Model):
    """Stores history of past tournaments for the Index page."""
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='previous_tournaments', null=True, blank=True)
    tournament_name = models.CharField(max_length=255)
    date = models.DateField(default=timezone.now)
    game_name = models.CharField(max_length=100, blank=True, null=True)
    cover_image = models.ImageField(upload_to='previous_tournaments/covers/', null=True, blank=True)
    winner_team = models.CharField(max_length=255, blank=True, null=True)
    runner_up_team = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    published = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.tournament_name} ({self.date.year})"

class TournamentTeam(models.Model):
    tournament = models.ForeignKey(PreviousTournament, on_delete=models.CASCADE, related_name='participating_teams')
    team_name = models.CharField(max_length=255)
    organization = models.CharField(max_length=255, blank=True, null=True)
    placement = models.IntegerField(null=True, blank=True)
    points = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.team_name} - {self.tournament.tournament_name}"

class TournamentScorecard(models.Model):
    tournament = models.ForeignKey(PreviousTournament, on_delete=models.CASCADE, related_name='scorecards')
    match_number = models.IntegerField()
    match_data = models.JSONField(help_text="Raw JSON data of the match scoreboard")
    ai_analysis = models.TextField(help_text="AI generated summary for this match")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Match {self.match_number} - {self.tournament.tournament_name}"

class PlayerTask(models.Model):
    TASK_TYPES = [
        ('EVENT', 'Event'),
        ('TASK', 'Task'),
    ]
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    due_date = models.DateTimeField(null=True, blank=True)
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
        ('BID_LOCKED', 'Bid Locked'),
        ('BID_ACCEPTED', 'Bid Accepted'),
        ('BID_REFUND', 'Bid Refund'),
        ('ADMIN_GRANT', 'Admin Grant'),
        ('BID_PAYMENT', 'Bid Payment'),
    ]

    sender = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, related_name='sent_transactions')
    recipient = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, related_name='received_transactions')
    recipient_player = models.ForeignKey(Player, on_delete=models.SET_NULL, null=True, related_name='received_transactions')
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

class BiddingSeason(models.Model):
    name = models.CharField(max_length=100)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    auto_start = models.BooleanField(default=True)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def clean(self):
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValidationError("End date must be after start date.")
        if self.is_active:
            active_seasons = BiddingSeason.objects.filter(is_active=True).exclude(pk=self.pk)
            if active_seasons.exists():
                raise ValidationError("Only one bidding season can be active at a time.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

class BiddingSeasonLog(models.Model):
    season = models.ForeignKey(BiddingSeason, on_delete=models.CASCADE, related_name='logs')
    action = models.CharField(max_length=50) # 'START', 'PAUSE', 'END', 'AUTO_START', 'AUTO_END'
    message = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.season.name} - {self.action} at {self.timestamp}"

class Bid(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Accepted', 'Accepted'),
        ('Rejected', 'Rejected'),
        ('Negotiation', 'Negotiation'),
    ]
    season = models.ForeignKey(BiddingSeason, on_delete=models.CASCADE, related_name='bids')
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='bids')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='bids')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    is_manual = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if not self.pk and not self.season.is_active:
            raise ValidationError("Bids can only be placed during an active bidding season.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.organization.Organization_Name} bid {self.amount} for {self.player.username}"

class Negotiation(models.Model):
    bid = models.ForeignKey(Bid, on_delete=models.CASCADE, related_name='negotiations')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    counter_amount = models.DecimalField(max_digits=12, decimal_places=2)
    message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Negotiation for Bid {self.bid.id}"

class SystemSettings(models.Model):
    # --- Maintenance ---
    is_maintenance_mode = models.BooleanField(default=False)
    maintenance_message = models.TextField(
        default="We are currently performing scheduled maintenance. Please check back soon!"
    )

    # --- Site Identity ---
    site_name = models.CharField(max_length=100, default="EGAMESCOUT")
    contact_email = models.EmailField(default="admin@egamescout.com", blank=True)

    # --- Registration Controls ---
    allow_player_registration = models.BooleanField(default=True)
    allow_org_registration = models.BooleanField(default=True)

    # --- Coin / Economy ---
    default_org_coins = models.DecimalField(max_digits=10, decimal_places=2, default=1000.00)
    default_player_coins = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    # --- Announcement Banner ---
    show_announcement = models.BooleanField(default=False)
    announcement_text = models.TextField(blank=True, default="")

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "System Settings"

    @classmethod
    def get_settings(cls):
        settings, created = cls.objects.get_or_create(id=1)
        return settings
    # ... (Add UserSession to models.py)
from django.contrib.sessions.models import Session

class UserSession(models.Model):
    user_type = models.CharField(max_length=20, choices=[('ADMIN', 'Admin'), ('ORG', 'Organization'), ('PLAYER', 'Player')])
    user_id = models.IntegerField()
    
    session = models.OneToOneField(Session, on_delete=models.CASCADE)
    session_key = models.CharField(max_length=40, unique=True)
    
    login_time = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_info = models.CharField(max_length=255, null=True, blank=True)
    
    is_active = models.BooleanField(default=True)
    is_remember_me = models.BooleanField(default=False)

    class Meta:
        db_table = 'secure_user_sessions'
        indexes = [
            models.Index(fields=['user_type', 'user_id', 'is_active']),
        ]

    def expire_session(self):
        self.is_active = False
        self.save()
        try:
            self.session.delete()
        except:
            pass
        
    def __str__(self):
        return f"{self.user_type} session ({self.user_id})"



class Contract(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='contracts')
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='contracts')
    salary = models.DecimalField(max_digits=12, decimal_places=2)
    responsibilities = models.TextField()
    sponsor_promotion = models.TextField()
    duration = models.CharField(max_length=100) # e.g., "1 Year", "6 Months"
    termination_rules = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_saved = models.BooleanField(default=False)

    def __str__(self):
        return f"Contract: {self.organization.Organization_Name} - {self.player.full_name}"

class SystemLog(models.Model):
    USER_TYPES = [
        ('PLAYER', 'Player'),
        ('ORGANIZATION', 'Organization'),
        ('ADMIN', 'Admin'),
        ('SYSTEM', 'System'),
    ]
    user_type = models.CharField(max_length=20, choices=USER_TYPES)
    user_id = models.IntegerField(null=True, blank=True)
    action = models.CharField(max_length=100)
    details = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user_type} - {self.action} at {self.timestamp}"
