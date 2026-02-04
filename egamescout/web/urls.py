from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    
    # Organization Registration
    path('organization/register/', views.org_register_start, name='org_register_start'),
    path('organization/register/otp/', views.org_register_otp, name='org_register_otp'),
    path('organization/register/details/', views.org_register_details, name='org_register_details'),
    
    # Organization Login
    path('organization/login/', views.org_login_start, name='org_login_start'),
    path('organization/login/otp/', views.org_login_otp, name='org_login_otp'),
    
    # Dashboard
    # Dashboard
    path('dashboard/', views.organizer_dashboard, name='organizer_dashboard'),
    
    # Profile Management
    path('organization/profile/', views.manage_profile, name='manage_profile'),
    path('organization/profile/update/', views.update_profile, name='update_profile'),
    path('organization/profile/photo/update/', views.update_profile_photo, name='update_profile_photo'),
    
    # Tools
    path('organization/tools/scorecard/', views.scorecard_tool, name='scorecard_tool'),
    
    # Utilities
    path('organization/resend-otp/', views.resend_otp, name='resend_otp'),
]
