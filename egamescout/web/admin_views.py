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
    messages.success(request, "You have been logged out successfully.")
    return redirect('admin_login')

@user_passes_test(is_superuser, login_url='admin_login')
def admin_dashboard(request):
    # --- Real-time Counters ---
    # Players
    player_qs = Player.objects.all()
    player_count = player_qs.count()
    active_players = player_qs.filter(status='ACTIVE').count()
    
    # Organizations
    org_qs = Organization.objects.all()
    org_count = org_qs.count()
    active_orgs = org_qs.filter(status='Active').count()
    
    # Tournaments
    tournament_qs = Tournament.objects.all()
    tournament_count = tournament_qs.count()
    active_tournaments = tournament_qs.filter(Status='Ongoing').count()

    # --- New Today Calculation ---
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    new_players_today = player_qs.filter(created_at__gte=today_start).count()
    new_orgs_today = org_qs.filter(CreatedAt__gte=today_start).count()
    
    # --- Chart Data (Last 7 Days) ---
    days = 7
    chart_labels = []
    player_trend = []
    org_trend = []
    
    for i in range(days):
        day = timezone.now().date() - timedelta(days=6-i)
        chart_labels.append(day.strftime('%a')) # Mon, Tue...
        
        # Count for specific day
        p_count = player_qs.filter(created_at__date=day).count()
        o_count = org_qs.filter(CreatedAt__date=day).count()
        
        player_trend.append(p_count)
        org_trend.append(o_count)

    # --- Unified Recent Activity ---
    # Fetch top 5 from both, combine and sort
    recent_p = list(player_qs.order_by('-created_at')[:5])
    recent_o = list(org_qs.order_by('-CreatedAt')[:5])
    
    recent_activity = []
    for p in recent_p:
        recent_activity.append({
            'type': 'PLAYER',
            'name': p.full_name,
            'uid': p.uid,
            'time': p.created_at,
            'initial': p.full_name[:2].upper()
        })
    for o in recent_o:
        recent_activity.append({
            'type': 'ORG',
            'name': o.Organization_Name,
            'uid': o.Organization_UserName,
            'time': o.CreatedAt,
            'initial': o.Organization_Name[:2].upper()
        })
    
    # Sort by time desc and take top 10
    recent_activity.sort(key=lambda x: x['time'], reverse=True)
    recent_activity = recent_activity[:10]

    context = {
        # Counts
        'player_count': player_count,
        'active_players': active_players,
        'new_players_today': new_players_today,
        
        'org_count': org_count,
        'active_orgs': active_orgs,
        'new_orgs_today': new_orgs_today,
        
        'tournament_count': tournament_count,
        'active_tournaments': active_tournaments,
        
        # Chart Data
        'chart_labels': chart_labels,
        'player_trend': player_trend,
        'org_trend': org_trend,
        
        # List
        'recent_activity': recent_activity
    }
    return render(request, 'web/Admin/admin_dashboard.html', context)

@user_passes_test(is_superuser, login_url='admin_login')
def admin_players_detail(request):
    search_query = request.GET.get('q', '')
    if search_query:
        players_list = Player.objects.filter(
            Q(full_name__icontains=search_query) | 
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query)
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
    search_query = request.GET.get('q', '')
    if search_query:
        organizations_list = Organization.objects.filter(
            Q(Organization_Name__icontains=search_query) | 
            Q(Organization_UserName__icontains=search_query) | 
            Q(Organization_Email__icontains=search_query)
        ).order_by('-CreatedAt')
    else:
        organizations_list = Organization.objects.all().order_by('-CreatedAt')

    paginator = Paginator(organizations_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'web/Admin/admin_organization_detail.html', {
        'page_obj': page_obj,
        'search_query': search_query
    })

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
    player = get_object_or_404(Player, id=player_id)
    if request.method == 'POST':
        player_name = player.full_name
        player.delete()
        messages.success(request, f'Player {player_name} has been deleted.')
        return redirect('admin_players_detail')
    
    # Render confirmation page for GET request
    return render(request, 'web/Admin/admin_player_confirm_delete.html', {'player': player})

@user_passes_test(is_superuser, login_url='admin_login')
def admin_edit_player(request, player_id):
    player = get_object_or_404(Player, id=player_id)
    if request.method == 'POST':
        player.status = request.POST.get('status', 'PENDING')
        player.save()
        messages.success(request, f'Player "{player.full_name}" status updated.')
        return redirect('admin_players_detail')
    
    return render(request, 'web/Admin/admin_player_edit.html', {'player': player})

# --- Notification APIs ---
from django.http import JsonResponse
from .models import AdminNotification

@user_passes_test(is_superuser, login_url='admin_login')
def get_notifications(request):
    """API to fetch unread notifications"""
    notifications = AdminNotification.objects.filter(is_read=False).order_by('-created_at')
    data = [{
        'id': n.id,
        'message': n.message,
        'type': n.notification_type,
        'created_at': n.created_at.strftime('%Y-%m-%d %H:%M'),
        'link': n.link or '#'
    } for n in notifications]
    
    return JsonResponse({'notifications': data, 'count': len(data)})

@user_passes_test(is_superuser, login_url='admin_login')
def mark_notification_read(request, notif_id):
    """API to mark a notification as read"""
    if request.method == 'POST':
        try:
            notif = AdminNotification.objects.get(id=notif_id)
            notif.is_read = True
            notif.save()
            return JsonResponse({'success': True})
        except AdminNotification.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Not found'}, status=404)
    return JsonResponse({'success': False}, status=400)

@user_passes_test(is_superuser, login_url='admin_login')
def mark_all_notifications_read(request):
    """API to mark all notifications as read"""
    if request.method == 'POST':
        AdminNotification.objects.filter(is_read=False).update(is_read=True)
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=400)

@user_passes_test(is_superuser, login_url='admin_login')
def admin_delete_tournament(request, tournament_id):
    tournament = get_object_or_404(Tournament, Tournament_ID=tournament_id)
    if request.method == 'POST':
        name = tournament.Name
        tournament.delete()
        messages.success(request, f'Tournament "{name}" has been deleted.')
        return redirect('admin_tournaments_detail')
    
    return redirect('admin_tournaments_detail')

@user_passes_test(is_superuser, login_url='admin_login')
def admin_edit_tournament(request, tournament_id):
    tournament = get_object_or_404(Tournament, Tournament_ID=tournament_id)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in ['Scheduled', 'Ongoing', 'Completed', 'Cancelled']:
            tournament.Status = new_status
            tournament.save()
            messages.success(request, f'Tournament "{tournament.Name}" status updated to {new_status}.')
        else:
            messages.error(request, 'Invalid status selected.')
            
    return redirect('admin_tournaments_detail')
