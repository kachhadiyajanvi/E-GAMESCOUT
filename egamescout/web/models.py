from django.db import models

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
