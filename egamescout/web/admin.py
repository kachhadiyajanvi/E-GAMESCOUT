from django.contrib import admin
from .models import Organization, ScorecardAnalysis, Tournament, Player, Transaction, PlayerBid, PlayerNotification, TournamentBidder, AdminNotification, PlayerTask, OrganizationNotification, GlobalSettings 

# Register your models here.
admin.site.register(Organization)
admin.site.register(ScorecardAnalysis)
admin.site.register(Tournament)
admin.site.register(Player)
admin.site.register(Transaction)
admin.site.register(PlayerBid)
admin.site.register(PlayerNotification)
admin.site.register(TournamentBidder)
admin.site.register(AdminNotification)
admin.site.register(PlayerTask)
admin.site.register(OrganizationNotification)
admin.site.register(GlobalSettings)
