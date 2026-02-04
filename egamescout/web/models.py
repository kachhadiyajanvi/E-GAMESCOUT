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
    age = models.IntegerField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} ({self.uid})"

class OTP(models.Model):
    email = models.EmailField()
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_valid(self):
        # Valid for 10 minutes
        return self.created_at >= timezone.now() - datetime.timedelta(minutes=10)

    def __str__(self):
        return f"{self.email} - {self.otp_code}"
