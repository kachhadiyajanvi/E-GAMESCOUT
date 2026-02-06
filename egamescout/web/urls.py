from django.urls import path
from . import views, admin_views

urlpatterns = [
    path('', views.index, name='index'),
    
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
    
    # Tools
    path('organization/tools/scorecard/', views.scorecard_tool, name='scorecard_tool'),
    
    # Tournament Management
    path('organization/tournaments/', views.tournament_list, name='tournament_list'),
    path('organization/players/', views.my_players, name='my_players'),
    path('organization/tournaments/create/', views.tournament_create, name='tournament_create'),
    path('organization/tournaments/<int:tournament_id>/update/', views.tournament_update, name='tournament_update'),
    path('organization/tournaments/<int:tournament_id>/delete/', views.tournament_delete, name='tournament_delete'),
    
    # Utilities
    path('organization/resend-otp/', views.resend_otp, name='resend_otp'),
    path('auth/login/', views.auth_login, name='auth_login'),
    path('auth/verify/', views.auth_verify_otp, name='auth_verify_otp'),
    path('auth/register/', views.auth_register_details, name='auth_register_details'),
    path('player/dashboard/', views.player_dashboard, name='player_dashboard'),
    path('auth/logout/', views.auth_logout, name='auth_logout'),

    # Admin Portal
    path('admin/login/', admin_views.admin_login, name='admin_login'),
    path('admin/logout/', admin_views.admin_logout, name='admin_logout'),
    path('admin/dashboard/', admin_views.admin_dashboard, name='admin_dashboard'),
    path('admin/players/', admin_views.admin_players_detail, name='admin_players_detail'),
    path('admin/organizations/', admin_views.admin_organization_detail, name='admin_organization_detail'),
    path('admin/organizations/delete/<int:org_id>/', admin_views.admin_delete_organization, name='admin_delete_organization'),
    path('admin/organizations/edit/<int:org_id>/', admin_views.admin_edit_organization, name='admin_edit_organization'),
    path('admin/tournaments/', admin_views.admin_tournaments_detail, name='admin_tournaments_detail'),
    path('admin/profile/', admin_views.admin_profile, name='admin_profile'),
]
