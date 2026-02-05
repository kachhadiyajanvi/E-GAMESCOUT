from django.contrib import admin
from .models import Organization, ScorecardAnalysis, Tournament

# Register your models here.
admin.site.register(Organization)
admin.site.register(ScorecardAnalysis)
admin.site.register(Tournament)
