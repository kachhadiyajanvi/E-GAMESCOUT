from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from .models import Organization, Player, Tournament
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import timedelta

# Helper to check if user is superuser
from django.core.paginator import Paginator

def is_superuser(user):
    return user.is_superuser

def admin_login(request):
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('admin_dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if user.is_superuser:
                login(request, user)
                return redirect('admin_dashboard')
            else:
                messages.error(request, "Access Denied: You are not an admin.")
        else:
            messages.error(request, "Invalid credentials.")
    
    return render(request, 'web/Admin/admin_login.html')

@user_passes_test(is_superuser, login_url='admin_login')
def admin_logout(request):
    logout(request)
    return redirect('admin_login')

@user_passes_test(is_superuser, login_url='admin_login')
def admin_dashboard(request):
    # Stats
    player_count = Player.objects.count()
    org_count = Organization.objects.count()
    tournament_count = Tournament.objects.count()
    
    # Recent Activity (Mock logic for now, or fetch latest created items)
    recent_players = Player.objects.order_by('-created_at')[:5]
    
    context = {
        'player_count': player_count,
        'org_count': org_count,
        'tournament_count': tournament_count,
        'recent_players': recent_players
    }
    return render(request, 'web/Admin/admin_dashboard.html', context)

@user_passes_test(is_superuser, login_url='admin_login')
def admin_players_detail(request):
    search_query = request.GET.get('q', '')
    if search_query:
        players_list = Player.objects.filter(
            Q(full_name__icontains=search_query) | 
            Q(username__icontains=search_query)
        ).order_by('-created_at')
    else:
        players_list = Player.objects.all().order_by('-created_at')
        
    paginator = Paginator(players_list, 10) # Show 10 players per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'web/Admin/admin_players_detail.html', {
        'players': page_obj, 
        'page_obj': page_obj,
        'search_query': search_query
    })

@user_passes_test(is_superuser, login_url='admin_login')
def admin_organization_detail(request):
    organizations_list = Organization.objects.all().order_by('-CreatedAt')
    paginator = Paginator(organizations_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'web/Admin/admin_organization_detail.html', {'page_obj': page_obj})

@user_passes_test(is_superuser, login_url='admin_login')
def admin_profile(request):
    return render(request, 'web/Admin/admin_profile.html')

@user_passes_test(is_superuser, login_url='admin_login')
def admin_tournaments_detail(request):
    tournaments_list = Tournament.objects.all().order_by('-CreatedAt')
    paginator = Paginator(tournaments_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'web/Admin/admin_tournaments_detail.html', {'tournaments': page_obj, 'page_obj': page_obj})

@user_passes_test(is_superuser, login_url='admin_login')
def admin_delete_organization(request, org_id):
    org = get_object_or_404(Organization, id=org_id)
    if request.method == 'POST':
        org.delete()
        messages.success(request, f'Organization "{org.Organization_Name}" has been deleted.')
        return redirect('admin_organization_detail')
    
    return render(request, 'web/Admin/admin_org_confirm_delete.html', {'org': org})

@user_passes_test(is_superuser, login_url='admin_login')
def admin_edit_organization(request, org_id):
    org = get_object_or_404(Organization, id=org_id)
    if request.method == 'POST':
        # Basic update logic
        # Only allow Status Update
        org.status = request.POST.get('status', 'Active')
            
        org.save()
        messages.success(request, f'Organization "{org.Organization_Name}" has been updated.')
        return redirect('admin_organization_detail')
    
    return render(request, 'web/Admin/admin_org_edit.html', {'org': org})

@user_passes_test(is_superuser, login_url='admin_login')
def admin_update_player_status(request, player_id):
    if request.method == 'POST':
        player = get_object_or_404(Player, id=player_id)
        new_status = request.POST.get('status')
        if new_status in dict(Player.STATUS_CHOICES):
            player.status = new_status
            player.save()
            messages.success(request, f'Status for {player.full_name} updated to {new_status}.')
        else:
            messages.error(request, 'Invalid status selected.')
    return redirect('admin_players_detail')

@user_passes_test(is_superuser, login_url='admin_login')
def admin_delete_player(request, player_id):
    if request.method == 'POST':
        player = get_object_or_404(Player, id=player_id)
        player_name = player.full_name
        player.delete()
        messages.success(request, f'Player {player_name} has been deleted.')
    return redirect('admin_players_detail')
