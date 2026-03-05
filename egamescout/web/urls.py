from django.urls import path
from . import views, admin_views

urlpatterns = [
    path('', views.index, name='index'),
    path('tournaments/', views.public_tournaments, name='public_tournaments'),
    
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
    path('organization/delete/', views.org_delete_account, name='org_delete_account'),
    
    # Tools
    path('organization/tools/scorecard/', views.scorecard_tool, name='scorecard_tool'),
    
    # Tournament Management
    path('organization/tournaments/', views.tournament_list, name='tournament_list'),

    path('organization/tournaments/history/', views.tournament_history, name='tournament_history'),
    path('organization/players/', views.my_players, name='my_players'),
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
    path('api/register/step1', views.api_register_step1, name='api_register_step1'),
    path('api/register/step2', views.api_register_step2, name='api_register_step2'),
    path('auth/verify/', views.auth_verify_otp, name='auth_verify_otp'),
    path('auth/register/upload/', views.auth_register_upload, name='auth_register_upload'),
    path('auth/register/details/', views.auth_register_details, name='auth_register_details'),
    path('player/dashboard/', views.player_dashboard, name='player_dashboard'),
    path('player/profile/', views.player_profile, name='player_profile'),
    

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


    # Tournament Publishing
    path('organization/tournaments/<int:tournament_id>/publish/', views.publish_tournament, name='publish_tournament'),
    path('organization/tournaments/upcoming/', views.org_upcoming_tournaments, name='org_upcoming_tournaments'),
    path('player/tournaments/upcoming/', views.player_upcoming_tournaments, name='player_upcoming_tournaments'),
    
    # Bidding
    path('organization/notifications/mark-all-read/', views.org_mark_all_notifications_read, name='org_mark_all_notifications_read'),
    path('organization/notifications/delete/<int:notification_id>/', views.delete_notification, name='delete_notification'),
    path('organization/notifications/', views.org_notifications, name='org_notifications'),

    # Admin Notifications API
    path('admin/api/notifications/', admin_views.get_notifications, name='get_notifications'),
    path('admin/api/notifications/read/<int:notif_id>/', admin_views.mark_notification_read, name='mark_notification_read'),
    path('admin/api/notifications/read-all/', admin_views.mark_all_notifications_read, name='mark_all_notifications_read'),
]
