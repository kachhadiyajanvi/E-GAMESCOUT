from django.contrib import admin
from .models import Organization, ScorecardAnalysis, Tournament, Player, Transaction, PlayerBid, PlayerNotification, TournamentBidder, AdminNotification, PlayerTask, OrganizationNotification, GlobalSettings 

class ArchivedFilter(admin.SimpleListFilter):
    title = 'Archived Status'
    parameter_name = 'is_archived'

    def lookups(self, request, model_admin):
        return (
            ('active', 'Active (Default)'),
            ('archived', 'Archived'),
            ('all', 'All'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'archived':
            return queryset.filter(is_archived=True)
        elif self.value() == 'all':
            return queryset
        else:
            return queryset.filter(is_archived=False)

class SoftDeleteAdmin(admin.ModelAdmin):
    list_filter = (ArchivedFilter,)
    actions = ['unarchive_selected', 'soft_delete_selected']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Check if filter is applied. If not, default to showing active only
        if 'is_archived' not in request.GET:
             return qs.filter(is_archived=False)
        return qs

    def delete_model(self, request, obj):
        # Soft delete instead of hard delete
        obj.is_archived = True
        obj.save()

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    @admin.action(description='Unarchive selected items')
    def unarchive_selected(self, request, queryset):
        queryset.update(is_archived=False)
        self.message_user(request, f"{queryset.count()} items were successfully unarchived.")

    @admin.action(description='Archive (Soft Delete) selected items')
    def soft_delete_selected(self, request, queryset):
        queryset.update(is_archived=True)
        self.message_user(request, f"{queryset.count()} items were successfully archived.")

@admin.register(Organization)
class OrganizationAdmin(SoftDeleteAdmin):
    list_display = ('Organization_Name', 'Organization_Email', 'status', 'is_archived')
    search_fields = ('Organization_Name', 'Organization_Email')

@admin.register(Tournament)
class TournamentAdmin(SoftDeleteAdmin):
    list_display = ('Name', 'Organization_Name', 'Status', 'is_archived')
    search_fields = ('Name', 'Organization_Name__Organization_Name')

@admin.register(Player)
class PlayerAdmin(SoftDeleteAdmin):
    list_display = ('full_name', 'username', 'email', 'status', 'is_archived')
    search_fields = ('full_name', 'username', 'email')
    list_filter = (ArchivedFilter, 'status')

admin.site.register(ScorecardAnalysis)
admin.site.register(Transaction)
admin.site.register(PlayerBid)
admin.site.register(PlayerNotification)
admin.site.register(TournamentBidder)
admin.site.register(AdminNotification)
admin.site.register(PlayerTask)
admin.site.register(OrganizationNotification)
admin.site.register(GlobalSettings)
