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
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Suspended', 'Suspended'),
        ('Pending', 'Pending'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Active')
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
    
    # New Fields
    description = models.TextField(default='')
    max_teams = models.IntegerField(default=16)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    is_offline = models.BooleanField(default=False)
    venue = models.CharField(max_length=255, null=True, blank=True)
    show_roadmap = models.BooleanField(default=False)
    roadmap_content = models.TextField(null=True, blank=True)
    prize_distribution = models.JSONField(default=list, blank=True)
    
    def __str__(self):
        return f"{self.Name} - {self.Organization_Name.Organization_Name}"

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
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    organization = models.ForeignKey(Organization, on_delete=models.SET_NULL, null=True, blank=True, related_name='players')
    created_at = models.DateTimeField(auto_now_add=True)

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
