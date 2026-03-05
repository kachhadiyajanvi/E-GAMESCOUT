from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from .models import Organization, Player, Tournament
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import datetime, time, timedelta
from decimal import Decimal

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
                # Clear conflicting sessions
                if 'organizer_id' in request.session: del request.session['organizer_id']
                if 'player_id' in request.session: del request.session['player_id']
                
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
    player_qs = Player.objects.filter(is_archived=False)
    player_count = player_qs.count()
    active_players = player_qs.filter(status='ACTIVE').count()
    
    # Organizations
    org_qs = Organization.objects.filter(is_archived=False)
    org_count = org_qs.count()
    active_orgs = org_qs.filter(status='Active').count()
    
    # Tournaments
    tournament_qs = Tournament.objects.filter(is_archived=False)
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
        day_date = timezone.now().date() - timedelta(days=6-i)
        chart_labels.append(day_date.strftime('%a')) # Mon, Tue...
        
        # Create aware start/end times
        day_start = timezone.make_aware(datetime.combine(day_date, time.min))
        day_end = timezone.make_aware(datetime.combine(day_date, time.max))
        
        # Count for specific day
        p_count = player_qs.filter(created_at__range=(day_start, day_end)).count()
        o_count = org_qs.filter(CreatedAt__range=(day_start, day_end)).count()
        
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
            Q(email__icontains=search_query),
            is_archived=False
        ).order_by('-created_at')
    else:
        players_list = Player.objects.filter(is_archived=False).order_by('-created_at')
        
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
            Q(Organization_Email__icontains=search_query),
            is_archived=False
        ).order_by('-CreatedAt')
    else:
        organizations_list = Organization.objects.filter(is_archived=False).order_by('-CreatedAt')

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
    tournaments_list = Tournament.objects.filter(is_archived=False).order_by('-CreatedAt')
    paginator = Paginator(tournaments_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'web/Admin/admin_tournaments_detail.html', {'tournaments': page_obj, 'page_obj': page_obj})



@user_passes_test(is_superuser, login_url='admin_login')
def admin_delete_organization(request, org_id):
    org = get_object_or_404(Organization, id=org_id)
    if request.method == 'POST':
        org.is_archived = True
        org.save()
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
        player.is_archived = True
        player.save()
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
        tournament.is_archived = True
        tournament.save()
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

@user_passes_test(is_superuser, login_url='admin_login')
def admin_analytics(request):
    # Time ranges
    now = timezone.now()
    week_start = now - timedelta(days=7)
    month_start = now - timedelta(days=30)
    year_start = now - timedelta(days=365)
    
    # 1. Total Counts
    total_players = Player.objects.filter(is_archived=False).count()
    total_orgs = Organization.objects.filter(is_archived=False).count()
    total_tournaments = Tournament.objects.filter(is_archived=False).count()
    
    # 2. Status Breakdown
    active_players = Player.objects.filter(status='ACTIVE', is_archived=False).count()
    pending_players = Player.objects.filter(status='PENDING', is_archived=False).count()
    suspended_players = Player.objects.filter(status='SUSPENDED', is_archived=False).count()
    
    active_orgs = Organization.objects.filter(status='Active', is_archived=False).count()
    pending_orgs = Organization.objects.filter(status='Pending', is_archived=False).count()
    suspended_orgs = Organization.objects.filter(status='Suspended', is_archived=False).count()
    
    # 3. Growth (Weekly)
    new_players_week = Player.objects.filter(created_at__gte=week_start).count()
    new_orgs_week = Organization.objects.filter(CreatedAt__gte=week_start).count()
    new_tournaments_week = Tournament.objects.filter(CreatedAt__gte=week_start).count()
    
    # 4. Growth (Monthly)
    new_players_month = Player.objects.filter(created_at__gte=month_start).count()
    new_orgs_month = Organization.objects.filter(CreatedAt__gte=month_start).count()
    new_tournaments_month = Tournament.objects.filter(CreatedAt__gte=month_start).count()
    
    # 5. Growth (Yearly)
    new_players_year = Player.objects.filter(created_at__gte=year_start).count()
    new_orgs_year = Organization.objects.filter(CreatedAt__gte=year_start).count()
    new_tournaments_year = Tournament.objects.filter(CreatedAt__gte=year_start).count()
    
    # 6. Financials
    total_prize_pool = Tournament.objects.aggregate(Sum('PrizePool'))['PrizePool__sum'] or Decimal('0')
    total_coins = Organization.objects.aggregate(Sum('coins'))['coins__sum'] or Decimal('0')
    

    # 8. Tournament Status Breakdown
    scheduled_tournaments = Tournament.objects.filter(Status='Scheduled', is_archived=False).count()
    ongoing_tournaments = Tournament.objects.filter(Status='Ongoing', is_archived=False).count()
    completed_tournaments = Tournament.objects.filter(Status='Completed', is_archived=False).count()
    cancelled_tournaments = Tournament.objects.filter(Status='Cancelled', is_archived=False).count()
    
    # Calculate conversion rates
    player_conversion = (active_players / total_players * 100) if total_players > 0 else 0
    org_conversion = (active_orgs / total_orgs * 100) if total_orgs > 0 else 0
    
    # 5. Charts Logic
    # ---------------------------------------------------------
    # WEEKLY DATA (Last 7 Days - Daily)
    # ---------------------------------------------------------
    week_labels = []
    player_data_week = []
    org_data_week = []
    
    # Helper for range queries
    from datetime import datetime, time
    
    for i in range(7):
        day_date = now.date() - timedelta(days=6-i)
        week_labels.append(day_date.strftime('%a')) # Mon, Tue
        
        # Create aware start/end times
        day_start = timezone.make_aware(datetime.combine(day_date, time.min))
        day_end = timezone.make_aware(datetime.combine(day_date, time.max))
        
        p_count = Player.objects.filter(created_at__range=(day_start, day_end)).count()
        o_count = Organization.objects.filter(CreatedAt__range=(day_start, day_end)).count()
        
        player_data_week.append(p_count)
        org_data_week.append(o_count)

    # ---------------------------------------------------------
    # MONTHLY DATA (Last 30 Days - Daily)
    # ---------------------------------------------------------
    month_labels = []
    player_data_month = []
    org_data_month = []
    tournament_data_month = []
    
    for i in range(30):
        day_date = now.date() - timedelta(days=29-i)
        month_labels.append(day_date.strftime('%d %b')) # 10 Feb
        
        # Create aware start/end times
        day_start = timezone.make_aware(datetime.combine(day_date, time.min))
        day_end = timezone.make_aware(datetime.combine(day_date, time.max))
        
        p_count = Player.objects.filter(created_at__range=(day_start, day_end), is_archived=False).count()
        o_count = Organization.objects.filter(CreatedAt__range=(day_start, day_end), is_archived=False).count()
        t_count = Tournament.objects.filter(CreatedAt__range=(day_start, day_end), is_archived=False).count()
        
        player_data_month.append(p_count)
        org_data_month.append(o_count)
        tournament_data_month.append(t_count)

    # ---------------------------------------------------------
    # YEARLY DATA (Last 12 Months - Monthly)
    # ---------------------------------------------------------
    year_labels = []
    player_data_year = []
    org_data_year = []
    
    for i in range(12):
        this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_offset = 11 - i
        target_year = this_month_start.year
        target_month = this_month_start.month - month_offset
        
        while target_month <= 0:
            target_month += 12
            target_year -= 1
            
        loop_month_start = this_month_start.replace(year=target_year, month=target_month)
        
        if target_month == 12:
            loop_month_end = loop_month_start.replace(year=target_year + 1, month=1)
        else:
            loop_month_end = loop_month_start.replace(month=target_month + 1)
            
        year_labels.append(loop_month_start.strftime('%b %Y'))
        
        p_count = Player.objects.filter(created_at__gte=loop_month_start, created_at__lt=loop_month_end).count()
        o_count = Organization.objects.filter(CreatedAt__gte=loop_month_start, CreatedAt__lt=loop_month_end).count()
        
        player_data_year.append(p_count)
        org_data_year.append(o_count)
    
    # Account Status
    deactivated_players = Player.objects.filter(status='SUSPENDED', is_archived=False).count()
    deleted_players = Player.objects.filter(is_archived=True).count()
    deactivated_orgs = Organization.objects.filter(status='Suspended', is_archived=False).count()
    deleted_orgs = Organization.objects.filter(is_archived=True).count()
        
    context = {
        # Counts
        'total_players': total_players,
        'active_players': active_players,
        'pending_players': pending_players,
        'suspended_players': suspended_players,
        'player_conversion': round(player_conversion, 1),
        
        'total_orgs': total_orgs,
        'active_orgs': active_orgs,
        'pending_orgs': pending_orgs,
        'suspended_orgs': suspended_orgs,
        'org_conversion': round(org_conversion, 1),
        
        'total_tournaments': total_tournaments,
        'scheduled_tournaments': scheduled_tournaments,
        'ongoing_tournaments': ongoing_tournaments,
        'completed_tournaments': completed_tournaments,
        'cancelled_tournaments': cancelled_tournaments,
        
        # Growth Metrics
        'new_players_week': new_players_week,
        'new_orgs_week': new_orgs_week,
        'new_tournaments_week': new_tournaments_week,
        'new_players_month': new_players_month,
        'new_orgs_month': new_orgs_month,
        'new_tournaments_month': new_tournaments_month,
        'new_players_year': new_players_year,
        'new_orgs_year': new_orgs_year,
        'new_tournaments_year': new_tournaments_year,
        

        # Financials
        'total_prize_pool': total_prize_pool,
        'total_coins': total_coins,
        
        # Account Status Metrics
        'deactivated_players': deactivated_players,
        'deleted_players': deleted_players,
        'deactivated_orgs': deactivated_orgs,
        'deleted_orgs': deleted_orgs,
        
        # Charts - Multi-period
        'week_labels': week_labels,
        'player_data_week': player_data_week,
        'org_data_week': org_data_week,
        
        'month_labels': month_labels,
        'player_data_month': player_data_month,
        'org_data_month': org_data_month,
        
        'year_labels': year_labels,
        'player_data_year': player_data_year,
        'org_data_year': org_data_year,
        
        'tournament_growth_data': tournament_data_month,
        'tournament_data_month': tournament_data_month,
        
        'chart_labels': month_labels,
        'player_growth_data': player_data_month,
        'org_growth_data': org_data_month,
    }
    return render(request, 'web/Admin/admin_analytics.html', context)
