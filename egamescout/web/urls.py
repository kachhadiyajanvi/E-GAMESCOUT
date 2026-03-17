from django.urls import path
from django.views.generic import RedirectView
from web import views, admin_views

urlpatterns = [
    path('', views.index, name='index'),
    path('maintenance/', views.maintenance_page, name='maintenance_page'),
    path('tournaments/', views.public_tournaments, name='public_tournaments'),
    path('previous-tournaments/', views.public_previous_tournaments, name='public_previous_tournaments'),
    path('tournament-history/<int:tournament_id>/', views.tournament_history_detail, name='tournament_history_detail'),
    
    # Organization Registration
    path('organization/register/', views.org_register_start, name='org_register_start'),

    path('organization/register/otp/', views.org_register_otp, name='org_register_otp'),
    path('organization/register/details/', views.org_register_details, name='org_register_details'),
    
    # Organization Login
    path('organization/login/', views.org_login_start, name='org_login_start'),
    path('organization/login/otp/', views.org_login_otp, name='org_login_otp'),
    path('organization/logout/', views.org_logout, name='org_logout'),
    
    # Organization Dashboard
    path('organization/dashboard/', views.organizer_dashboard, name='organizer_dashboard'),
    
    # Profile Management
    path('organization/profile/', views.manage_profile, name='manage_profile'),
    path('organization/profile/update/', views.update_profile, name='update_profile'),
    path('organization/profile/photo/update/', views.update_profile_photo, name='update_profile_photo'),
    path('organization/deactivate/', views.org_deactivate_account, name='org_deactivate_account'),
    path('organization/activate/', views.org_activate_account, name='org_activate_account'),
    path('organization/delete/', views.org_delete_account, name='org_delete_account'),
    
    # Tools
    path('organization/tools/scorecard/', views.scorecard_tool, name='scorecard_tool'),
    
    # Tournament Management
    path('organization/tournaments/', views.tournament_list, name='tournament_list'),

    path('organization/tournaments/history/', views.tournament_history, name='tournament_history'),
    path('organization/players/', views.my_players, name='my_players'),
    path('organization/scout/', views.org_scout_players, name='org_scout_players'),
    path('organization/players/<int:player_id>/profile/', views.org_view_player_profile, name='org_view_player_profile'),
    path('organization/players/<int:player_id>/remove/', views.org_remove_player, name='org_remove_player'),
    path('organization/tournaments/create/', views.tournament_create, name='tournament_create'),
    path('organization/tournaments/<int:tournament_id>/', views.tournament_detail, name='tournament_detail'),
    path('organization/tournaments/<int:tournament_id>/cancel/', views.cancel_tournament, name='cancel_tournament'),
    path('organization/tournaments/<int:tournament_id>/edit/', views.tournament_update, name='tournament_update'),
    path('organization/tournaments/<int:tournament_id>/delete/', views.tournament_delete, name='tournament_delete'),
    path('organization/tournaments/<int:tournament_id>/participants/', views.tournament_participants, name='tournament_participants'),
    # Utilities
    path('organization/resend-otp/', views.resend_otp, name='resend_otp'),
    path('auth/login/', views.auth_login, name='auth_login'),
    # API Authentication Setup
    path('api/login/send-otp', views.api_send_otp, name='api_send_otp'),
    path('api/login/verify-otp', views.api_verify_otp, name='api_verify_otp'),
    path('api/register/send-otp', views.api_register_send_otp, name='api_register_send_otp'),
    path('api/register/verify-otp', views.api_register_verify_otp, name='api_register_verify_otp'),
    path('api/register/step1/', views.api_register_step1, name='api_register_step1'),
    path('api/register/step2/', views.api_register_step2, name='api_register_step2'),
    path('api/check-username/', views.check_username, name='check_username'),
    
    # Organization API
    path('api/organization/dismiss_player_setup/', views.dismiss_player_setup_popup, name='dismiss_player_setup_popup'),
    
    # --- Profile & Common ---
    path('auth/verify/', views.auth_verify_otp, name='auth_verify_otp'),
    path('auth/register/upload/', views.auth_register_upload, name='auth_register_upload'),
    path('auth/register/details/', views.auth_register_details, name='auth_register_details'),

    path('auth/register/cancel/', views.cancel_register, name='cancel_register'),
    
    # Backward compatibility redirect for old invite emails
    path('player/register/', RedirectView.as_view(pattern_name='auth_register_upload', permanent=True)),
    
    # Organization Player Management Routing
    path('organization/my-players/', views.my_players, name='my_players_legacy'),
    path('organization/add-player/', views.org_add_player, name='org_add_player'),
    path('organization/player/<int:player_id>/', views.org_view_player_profile, name='org_view_player_profile_legacy'),
    path('organization/player/<int:player_id>/remove/', views.org_remove_player, name='org_remove_player_legacy'),
    
    path('player/dashboard/', views.player_dashboard, name='player_dashboard'),
    path('player/profile/', views.player_profile, name='player_profile'),
    
    path('player/deactivate/', views.player_deactivate_account, name='player_deactivate_account'),
    path('player/reactivate-confirm/', views.player_reactivate_confirm, name='player_reactivate_confirm'),
    path('player/activate/', views.player_activate_account, name='player_activate_account'),
    path('player/delete/', views.player_delete_account, name='player_delete_account'),
    path('auth/logout/', views.auth_logout, name='auth_logout'),

    # Admin Portal
    path('admin/login/', admin_views.admin_login, name='admin_login'),
    path('admin/logout/', admin_views.admin_logout, name='admin_logout'),
    path('admin/', admin_views.admin_dashboard, name='admin_dashboard'),
    path('admin/players/', admin_views.admin_players_detail, name='admin_players_detail'),
    path('admin/organizations/', admin_views.admin_organization_detail, name='admin_organization_detail'),
    path('admin/organizations/delete/<int:org_id>/', admin_views.admin_delete_organization, name='admin_delete_organization'),
    path('admin/organizations/edit/<int:org_id>/', admin_views.admin_edit_organization, name='admin_edit_organization'),
    path('admin/players/update-status/<int:player_id>/', admin_views.admin_update_player_status, name='admin_update_player_status'),
    path('admin/players/delete/<int:player_id>/', admin_views.admin_delete_player, name='admin_delete_player'),
    path('admin/players/edit/<int:player_id>/', admin_views.admin_edit_player, name='admin_edit_player'),
    path('admin/tournaments/', admin_views.admin_tournaments_detail, name='admin_tournaments_detail'),
    path('admin/tournaments/delete/<int:tournament_id>/', admin_views.admin_delete_tournament, name='admin_delete_tournament'),
    path('admin/tournaments/edit/<int:tournament_id>/', admin_views.admin_edit_tournament, name='admin_edit_tournament'),
    path('admin/profile/', admin_views.admin_profile, name='admin_profile'),
    path('admin/analytics/', admin_views.admin_analytics, name='admin_analytics'),
    path('admin/settings/', admin_views.admin_settings, name='admin_settings'),
    
    # Bidding Analytics
    path('admin/bidding/dashboard/', admin_views.admin_bidding_dashboard, name='admin_bidding_dashboard'),
    path('admin/bidding/details/', admin_views.admin_bidding_details, name='admin_bidding_details'),
    path('admin/bidding/export/<str:report_type>/', admin_views.admin_bidding_export, name='admin_bidding_export'),
    path('admin/bidding/season/start/', admin_views.admin_start_bidding_season, name='admin_start_bidding_season'),
    path('admin/bidding/season/pause/', admin_views.admin_pause_bidding_season, name='admin_pause_bidding_season'),
    path('admin/bidding/season/end/', admin_views.admin_end_bidding_season, name='admin_end_bidding_season'),
    path('admin/bidding/season/update/', admin_views.admin_update_bidding_season, name='admin_update_bidding_season'),
    path('admin/bidding/bid/<int:bid_id>/status/', admin_views.admin_update_bid_status, name='admin_update_bid_status'),

    # Organization & Player Bidding
    path('organization/bidding/', views.org_bidding_dashboard, name='org_bidding_dashboard'),
    path('organization/bidding/place/<int:player_id>/', views.place_bid, name='place_bid'),
    path('organization/bidding/negotiation/<int:negotiation_id>/<str:action>/', views.org_respond_negotiation, name='org_respond_negotiation'),
    path('organization/transactions/', views.org_transaction_history, name='org_transaction_history'),
    path('player/bidding/', views.player_bidding_dashboard, name='player_bidding_dashboard'),
    path('player/bidding/<int:bid_id>/accept/', views.player_accept_bid, name='player_accept_bid'),
    path('player/bidding/<int:bid_id>/reject/', views.player_reject_bid, name='player_reject_bid'),
    path('player/bidding/<int:bid_id>/negotiate/', views.player_negotiate_bid, name='player_negotiate_bid'),
    
    # Admin Transactions
    path('admin/transactions/', views.admin_transaction_history, name='admin_transaction_history'),

    # Tournament Publishing & Participation
    path('organization/tournaments/<int:tournament_id>/publish/', views.publish_tournament, name='publish_tournament'),
    path('organization/tournaments/history/<int:history_id>/publish/', views.publish_previous_tournament, name='publish_previous_tournament'),
    path('organization/tournaments/upcoming/', views.org_upcoming_tournaments, name='org_upcoming_tournaments'),
    path('organization/tournaments/<int:tournament_id>/join/', views.org_join_tournament, name='org_join_tournament'),
    path('organization/player/accept-invite/<uuid:token>/', views.accept_player_invite, name='accept_player_invite'),
    path('player/tournaments/upcoming/', views.player_upcoming_tournaments, name='player_upcoming_tournaments'),
    
    # Notifications
    path('organization/notifications/mark-all-read/', views.org_mark_all_notifications_read, name='org_mark_all_notifications_read'),
    path('organization/notifications/delete/<int:notification_id>/', views.delete_notification, name='delete_notification'),
    path('organization/notifications/', views.org_notifications, name='org_notifications'),

    # Admin Notifications API
    path('admin/api/notifications/', admin_views.get_notifications, name='get_notifications'),
    path('admin/api/notifications/read/<int:notif_id>/', admin_views.mark_notification_read, name='mark_notification_read'),
    path('admin/api/notifications/read-all/', admin_views.mark_all_notifications_read, name='mark_all_notifications_read'),
    
    # Generic Pages
    path('terms/', views.terms_and_conditions, name='terms'),
    
    # Admin Verification
    path('admin/verify/<str:entity_type>/<int:entity_id>/', admin_views.admin_grant_verification, name='admin_grant_verification'),
    
    # Admin Tournament Approvals
    path('admin/tournament/approvals/', admin_views.admin_tournament_approvals, name='admin_tournament_approvals'),
    path('admin/tournament/approvals/history/', admin_views.admin_tournament_approvals_history, name='admin_tournament_approvals_history'),
    path('admin/tournament/approvals/approve/<int:tournament_id>/', admin_views.admin_approve_tournament, name='admin_approve_tournament'),
    path('admin/tournament/approvals/reject/<int:tournament_id>/', admin_views.admin_reject_tournament, name='admin_reject_tournament'),
    
    # Admin Archive Actions
    path('admin/archive/', admin_views.admin_archive_actions, name='admin_archive_actions'),
    path('admin/archive/player/<int:player_id>/delete/', admin_views.admin_delete_archived_player, name='admin_delete_archived_player'),
    path('admin/archive/org/<int:org_id>/delete/', admin_views.admin_delete_archived_organization, name='admin_delete_archived_organization'),
    path('admin/archive/tournament/<int:tournament_id>/delete/', admin_views.admin_delete_archived_tournament, name='admin_delete_archived_tournament'),
    
    # Admin Role Conflicts
    path('admin/role-conflicts/', admin_views.admin_role_conflicts, name='admin_role_conflicts'),
    path('admin/role-conflicts/approve/<int:request_id>/', admin_views.admin_approve_conflict, name='admin_approve_conflict'),
    path('admin/role-conflicts/reject/<int:request_id>/', admin_views.admin_reject_conflict, name='admin_reject_conflict'),
]
