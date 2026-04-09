from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.cache import cache_control
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from web.models import Organization, Player, Tournament, BiddingSeason, BiddingSeasonLog, Bid, Negotiation, Transaction, UserSession
from django.db import transaction
from django.db.models import Count, Sum, Q, Max
from django.utils import timezone
from datetime import datetime, time, timedelta
from decimal import Decimal
from web.auth_services import handle_secure_login, handle_secure_logout
import csv
from django.http import HttpResponse
from django.core.exceptions import ValidationError
import json
from django.core.serializers.json import DjangoJSONEncoder
import random
import time as time_module
from django.core.mail import send_mail
from django.conf import settings

# Helper to check if user is superuser
from django.core.paginator import Paginator

def is_superuser(user):
    return user.is_superuser

def admin_login(request):
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('admin_dashboard')

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        user = User.objects.filter(email=email, is_superuser=True).first()
        
        if user is not None and user.check_password(password):
            # Generate 6-digit OTP
            otp = str(random.randint(100000, 999999))
            request.session['admin_login_otp'] = otp
            request.session['admin_login_user_id'] = user.id
            request.session['admin_login_otp_time'] = time_module.time()
            
            # Send Email
            try:
                from django.template.loader import render_to_string
                from django.utils.html import strip_tags
                
                html_message = render_to_string('web/emails/admin_otp.html', {'otp': otp, 'user': user})
                plain_message = strip_tags(html_message)
                
                send_mail(
                    'Admin Secure Login OTP - E-GameScout',
                    plain_message,
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    html_message=html_message
                )
                messages.success(request, "Secure Login OTP sent to your email.")
            except Exception as e:
                # If email fails, print it for development
                print(f"OTP SEND FAIL: {otp} - Error: {str(e)}")
                messages.success(request, "Secure Login OTP generated. Check console if testing.")
            
            return redirect('admin_verify_otp')
        else:
            messages.error(request, "Invalid credentials or access denied.")
    
    return render(request, 'web/Admin/admin_login.html')

def admin_verify_otp(request):
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('admin_dashboard')

    if 'admin_login_user_id' not in request.session:
        messages.error(request, "Session expired. Please login again.")
        return redirect('admin_login')

    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        stored_otp = request.session.get('admin_login_otp')
        otp_time = request.session.get('admin_login_otp_time', 0)
        
        # Check expiry (2 minutes)
        if time_module.time() - otp_time > 120:
            del request.session['admin_login_otp']
            messages.error(request, "OTP has expired. Please login again.")
            return redirect('admin_login')
            
        if entered_otp == stored_otp:
            user_id = request.session.get('admin_login_user_id')
            user = get_object_or_404(User, id=user_id)
            
            # Clear intermediate session variables
            del request.session['admin_login_otp']
            del request.session['admin_login_user_id']
            del request.session['admin_login_otp_time']
            
            # Clear conflicting custom sessions
            if 'organizer_id' in request.session: del request.session['organizer_id']
            if 'player_id' in request.session: del request.session['player_id']
            
            # Standard Django Login
            login(request, user)
            
            # Secure Tracking Login
            handle_secure_login(request, user_id=user.id, user_type='ADMIN')
            
            messages.success(request, "Admin access granted.")
            return redirect('admin_dashboard')
        else:
            messages.error(request, "Invalid OTP.")

    otp_time = request.session.get('admin_login_otp_time', 0)
    remaining_time = max(0, int(120 - (time_module.time() - float(otp_time)))) if otp_time else 0
    return render(request, 'web/Admin/admin_verify_otp.html', {'remaining_time': remaining_time})

def admin_resend_otp(request):
    if 'admin_login_user_id' not in request.session:
        messages.error(request, "Session expired. Please start over.")
        return redirect('admin_login')
        
    user_id = request.session.get('admin_login_user_id')
    user = get_object_or_404(User, id=user_id)
    
    # Generate new 6-digit OTP
    otp = str(random.randint(100000, 999999))
    request.session['admin_login_otp'] = otp
    request.session['admin_login_otp_time'] = time_module.time()
    
    try:
        from django.template.loader import render_to_string
        from django.utils.html import strip_tags
        
        html_message = render_to_string('web/emails/admin_otp.html', {'otp': otp, 'user': user})
        plain_message = strip_tags(html_message)
        
        send_mail(
            'Admin Secure Login OTP - E-GameScout',
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_message
        )
        messages.success(request, "A new OTP has been sent to your email.")
    except Exception as e:
        print(f"OTP SEND FAIL: {otp} - Error: {str(e)}")
        messages.error(request, "Failed to send email. Check console if testing.")
        
    return redirect('admin_verify_otp')

@user_passes_test(is_superuser, login_url='admin_login')
def admin_logout(request):
    # Call secure tracking cleanup first
    from .auth_services import handle_secure_logout
    handle_secure_logout(request)
    
    # Call native logout to cleanly remove user from request bindings
    logout(request)
    
    messages.success(request, "You have been logged out successfully.")
    return redirect('admin_login')

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

@user_passes_test(is_superuser, login_url='admin_login')
def admin_change_password_request(request):
    user = request.user
    
    # Generate 6-digit OTP
    otp = str(random.randint(100000, 999999))
    request.session['admin_password_otp'] = otp
    request.session['admin_password_otp_time'] = time_module.time()
    
    # Send Email
    try:
        from django.template.loader import render_to_string
        from django.utils.html import strip_tags
        
        html_message = render_to_string('web/emails/admin_otp.html', {'otp': otp, 'user': user, 'action': 'password_change'})
        plain_message = strip_tags(html_message)
        
        send_mail(
            'Admin Password Change OTP - E-GameScout',
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_message
        )
        # Message removed to prevent double-pop on the frontend JS redirect
    except Exception as e:
        print(f"OTP SEND FAIL: {otp} - Error: {str(e)}")
        messages.success(request, "OTP generated. Check console if testing.")
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        from django.http import JsonResponse
        from django.urls import reverse
        return JsonResponse({'status': 'success', 'redirect': reverse('admin_change_password_verify')})
        
    return redirect('admin_change_password_verify')

@user_passes_test(is_superuser, login_url='admin_login')
def admin_change_password_verify(request):
    if 'admin_password_otp' not in request.session:
        messages.error(request, "No pending password change request found.")
        return redirect('admin_profile')

    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        stored_otp = request.session.get('admin_password_otp')
        otp_time = request.session.get('admin_password_otp_time', 0)
        
        # Check expiry (2 minutes)
        if time_module.time() - otp_time > 120:
            del request.session['admin_password_otp']
            messages.error(request, "OTP has expired. Please initiate request again.")
            return redirect('admin_profile')
            
        if entered_otp == stored_otp:
            # OTP is correct, validate password
            if new_password != confirm_password:
                messages.error(request, "Passwords do not match.")
                return render(request, 'web/Admin/admin_change_password.html')
            
            try:
                validate_password(new_password, user=request.user)
            except ValidationError as e:
                for error in e.messages:
                    messages.error(request, error)
                return render(request, 'web/Admin/admin_change_password.html')
            
            # Secure update update
            user = request.user
            user.set_password(new_password)
            user.save()
            
            # Update session auth hash to keep user logged in after password change
            from django.contrib.auth import update_session_auth_hash
            update_session_auth_hash(request, user)
            
            # Cleanup
            del request.session['admin_password_otp']
            del request.session['admin_password_otp_time']
            
            messages.success(request, "Password changed successfully!")
            return redirect('admin_profile')
        else:
            messages.error(request, "Invalid OTP.")

    return render(request, 'web/Admin/admin_change_password.html')

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@user_passes_test(is_superuser, login_url='admin_login')
def admin_dashboard(request):
    from django.core.cache import cache
    context = cache.get('admin_dashboard_context')
    
    if not context:
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

        # Bids
        total_bids = Bid.objects.count()
        active_bids = Bid.objects.filter(status='Pending').count()

        # --- New Today Calculation ---
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        new_players_today = player_qs.filter(created_at__gte=today_start).count()
        new_orgs_today = org_qs.filter(CreatedAt__gte=today_start).count()
        
        # --- Chart Data (Last 7 Days) ---
        from django.db.models.functions import TruncDate
        days = 7
        chart_labels = []
        player_trend = []
        org_trend = []
        
        seven_days_ago = timezone.now().date() - timedelta(days=days-1)
        seven_days_ago_aware = timezone.make_aware(datetime.combine(seven_days_ago, time.min))
        
        player_counts = {
            item['date']: item['count'] for item in 
            player_qs.filter(created_at__gte=seven_days_ago_aware).annotate(date=TruncDate('created_at')).values('date').annotate(count=Count('id'))
        }
        
        org_counts = {
            item['date']: item['count'] for item in 
            org_qs.filter(CreatedAt__gte=seven_days_ago_aware).annotate(date=TruncDate('CreatedAt')).values('date').annotate(count=Count('id'))
        }
        
        for i in range(days):
            day_date = seven_days_ago + timedelta(days=i)
            chart_labels.append(day_date.strftime('%a')) # Mon, Tue...
            
            player_trend.append(player_counts.get(day_date, 0))
            org_trend.append(org_counts.get(day_date, 0))

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
            
            'total_bids': total_bids,
            'active_bids': active_bids,
            
            # Chart Data
            'chart_labels': chart_labels,
            'player_trend': player_trend,
            'org_trend': org_trend,
            
            # List
            'recent_activity': recent_activity
        }
        
        cache.set('admin_dashboard_context', context, 60)
        
    return render(request, 'web/Admin/admin_dashboard.html', context)

@user_passes_test(is_superuser, login_url='admin_login')
def admin_players_detail(request):
    search_query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    
    players_list = Player.objects.filter(is_archived=False).select_related('organization')

    if search_query:
        players_list = players_list.filter(
            Q(full_name__icontains=search_query) | 
            Q(username__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    if status_filter:
        if status_filter == 'active':
            players_list = players_list.filter(status='ACTIVE', is_active_account=True)
        elif status_filter == 'deactivated':
            players_list = players_list.filter(is_active_account=False)
        elif status_filter == 'pending':
            players_list = players_list.filter(status='PENDING')
        elif status_filter == 'suspended':
            players_list = players_list.filter(status='SUSPENDED')

    players_list = players_list.order_by('-created_at')
        
    paginator = Paginator(players_list, 10) # Show 10 players per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'web/Admin/admin_players_detail.html', {
        'players': page_obj, 
        'page_obj': page_obj, 
        'search_query': search_query,
        'status_filter': status_filter
    })

@user_passes_test(is_superuser, login_url='admin_login')
def admin_organization_detail(request):
    search_query = request.GET.get('q', '')
    status_filter = request.GET.get('status', '')
    
    organizations_list = Organization.objects.filter(is_archived=False)

    if search_query:
        organizations_list = organizations_list.filter(
            Q(Organization_Name__icontains=search_query) | 
            Q(Organization_UserName__icontains=search_query) | 
            Q(Organization_Email__icontains=search_query)
        )
        
    if status_filter:
        if status_filter == 'active':
            organizations_list = organizations_list.filter(status='Active', is_active_account=True)
        elif status_filter == 'deactivated':
            organizations_list = organizations_list.filter(is_active_account=False)
        elif status_filter == 'pending':
            organizations_list = organizations_list.filter(status='Pending')
        elif status_filter == 'suspended':
            organizations_list = organizations_list.filter(status='Suspended')

    organizations_list = organizations_list.order_by('-CreatedAt')

    paginator = Paginator(organizations_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'web/Admin/admin_organization_detail.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter
    })

@user_passes_test(is_superuser, login_url='admin_login')
def admin_profile(request):
    total_projects = Tournament.objects.count()
    joined_year = 2024
    if hasattr(request.user, 'date_joined') and request.user.date_joined:
        joined_year = request.user.date_joined.year
    
    context = {
        'total_projects': total_projects,
        'joined_year': joined_year,
    }
    return render(request, 'web/Admin/admin_profile.html', context)

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
        # Soft delete logic
        org.is_archived = True
        archived_time = timezone.now()
        org.archived_at = archived_time
        org.status = 'Suspended'
        org.is_active_account = False
        
        # Free up unique constraints
        org.Organization_Email = f"arc_{org.id}_{org.Organization_Email}"[:254]
        org.Organization_UserName = f"arc_{org.id}_{org.Organization_UserName}"[:50]
        
        org.save()
        messages.success(request, f'Organization "{org.Organization_Name}" has been deleted.')
        return redirect('admin_organization_detail')
    
    return render(request, 'web/Admin/admin_org_confirm_delete.html', {'org': org})

@user_passes_test(is_superuser, login_url='admin_login')
def admin_bulk_delete_organizations(request):
    """Archives multiple organizations simultaneously."""
    if request.method == 'POST':
        selected_ids = request.POST.getlist('selected_ids')
        if not selected_ids:
            messages.error(request, "No organizations selected for archiving.")
            return redirect('admin_organization_detail')
            
        success_count = 0
        from django.utils import timezone
        
        with transaction.atomic():
            orgs = Organization.objects.filter(id__in=selected_ids, is_archived=False)
            for org in orgs:
                org.is_archived = True
                archived_time = timezone.now()
                org.archived_at = archived_time
                org.status = 'Suspended'
                org.is_active_account = False
                
                # Free up unique constraints
                org.Organization_Email = f"arc_{org.id}_{org.Organization_Email}"[:254]
                org.Organization_UserName = f"arc_{org.id}_{org.Organization_UserName}"[:50]
                
                org.save()
                success_count += 1
                
        if success_count > 0:
            messages.success(request, f"Successfully archived {success_count} organization(s).")
            
    return redirect('admin_organization_detail')

@user_passes_test(is_superuser, login_url='admin_login')
def admin_edit_organization(request, org_id):
    org = get_object_or_404(Organization, id=org_id)
    if request.method == 'POST':
        # Basic update logic
        # Only allow Status Update
        org.status = request.POST.get('status', org.status)
        org.is_active_account = request.POST.get('is_active_account') == 'true'
        
        # Handle verification grant
        if request.POST.get('grant_verification') == 'true' and not org.is_verified:
            org.is_verified = True
            messages.success(request, f"{org.Organization_Name} has been verified.")
            
            # Send Email
            from django.core.mail import send_mail
            from django.template.loader import render_to_string
            from django.utils.html import strip_tags
            
            html_message = render_to_string('web/emails/org_verified.html', {'org': org})
            plain_message = strip_tags(html_message)
            try:
                send_mail(
                    'Verification Successful - E-GameScout',
                    plain_message,
                    None,
                    [org.Organization_Email],
                    html_message=html_message
                )
            except Exception as e:
                pass
        
        # Handle verification revoke
        if request.POST.get('revoke_verification') == 'true' and org.is_verified:
            org.is_verified = False
            messages.warning(request, f"Verification has been revoked for {org.Organization_Name}.")
                
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
        
        # Handle verification grant
        if request.POST.get('grant_verification') == 'true' and not player.is_verified:
            player.is_verified = True
            messages.success(request, f'{player.full_name} has been granted verification.')
        
        # Handle verification revoke
        if request.POST.get('revoke_verification') == 'true' and player.is_verified:
            player.is_verified = False
            messages.warning(request, f'Verification has been revoked for {player.full_name}.')
        
        player.save()
        messages.success(request, f'Player {player.full_name} updated successfully.')
    return redirect('admin_players_detail')

@user_passes_test(is_superuser, login_url='admin_login')
def admin_delete_player(request, player_id):
    player = get_object_or_404(Player, id=player_id)
    if request.method == 'POST':
        # Admin Archive Action
        # Just mark as archived, don't trigger full deactivation logic which is user-side
        # OR trigger full logic if Admin wants complete removal
        
        with transaction.atomic():
            player.is_archived = True
            archived_time = timezone.now()
            player.archived_at = archived_time
            player.is_active_account = False
            player.status = 'SUSPENDED'
            
            # Free up unique constraints
            player.email = f"arc_{player.id}_{player.email}"[:254]
            player.uid = f"arc_{player.id}_{player.uid}"[:50]
            if player.username:
                player.username = f"arc_{player.id}_{player.username}"[:50]
            if player.aadhar_number:
                player.aadhar_number = f"A{player.id}_{player.aadhar_number}"[:20]
                            
            # Handle Organization Removal (Admin Action)
            if player.organization:
                org = player.organization
                OrganizationPlayer.objects.filter(player=player, organization=org).delete()
                
                # Notify Organization
                OrganizationNotification.objects.create(
                    recipient=org,
                    message=f"Player {player.full_name} has been archived by Admin.",
                    notification_type='ADMIN_ACTION'
                )
                
                player.organization = None
                
            player.save()
            
            # Handle Active Bids (Refund)
            active_bids = Bid.objects.filter(player=player, status__in=['Pending', 'Negotiation'])
            for bid in active_bids:
                org = bid.organization
                org.coins += bid.amount
                org.save()
                
                Transaction.objects.create(
                    recipient=org,
                    amount=bid.amount,
                    transaction_type='BID_REFUND',
                    description=f"Bid cancelled by Admin Archive: {player.full_name}"
                )
                
                bid.status = 'Rejected'
                bid.save()

        messages.success(request, f"Player {player.full_name} has been archived.")
    return redirect('admin_players_detail')
    
    # Render confirmation page for GET request
    return render(request, 'web/Admin/admin_player_confirm_delete.html', {'player': player})

@user_passes_test(is_superuser, login_url='admin_login')
def admin_bulk_delete_players(request):
    """Archives multiple players simultaneously."""
    if request.method == 'POST':
        selected_ids = request.POST.getlist('selected_ids')
        if not selected_ids:
            messages.error(request, "No players selected for archiving.")
            return redirect('admin_players_detail')
            
        success_count = 0
        from django.utils import timezone
        
        with transaction.atomic():
            players = Player.objects.filter(id__in=selected_ids, is_archived=False)
            for player in players:
                player.is_archived = True
                archived_time = timezone.now()
                player.archived_at = archived_time
                player.is_active_account = False
                player.status = 'SUSPENDED'
                
                # Free up unique constraints
                player.email = f"arc_{player.id}_{player.email}"[:254]
                player.uid = f"arc_{player.id}_{player.uid}"[:50]
                if player.username:
                    player.username = f"arc_{player.id}_{player.username}"[:50]
                if player.aadhar_number:
                    player.aadhar_number = f"A{player.id}_{player.aadhar_number}"[:20]
                                
                # Handle Organization Removal (Admin Action)
                if player.organization:
                    org = player.organization
                    OrganizationPlayer.objects.filter(player=player, organization=org).delete()
                    
                    OrganizationNotification.objects.create(
                        recipient=org,
                        message=f"Player {player.full_name} has been archived by Admin.",
                        notification_type='ADMIN_ACTION'
                    )
                    
                    player.organization = None
                    
                player.save()
                
                # Handle Active Bids (Refund)
                active_bids = Bid.objects.filter(player=player, status__in=['Pending', 'Negotiation'])
                for bid in active_bids:
                    org = bid.organization
                    org.coins += bid.amount
                    org.save()
                    
                    Transaction.objects.create(
                        recipient=org,
                        amount=bid.amount,
                        transaction_type='BID_REFUND',
                        description=f"Bid cancelled by Admin Bulk Archive: {player.full_name}"
                    )
                    
                    bid.status = 'Rejected'
                    bid.save()
                    
                success_count += 1

        if success_count > 0:
            messages.success(request, f"Successfully archived {success_count} player(s).")
            
    return redirect('admin_players_detail')

@user_passes_test(is_superuser, login_url='admin_login')
def admin_edit_player(request, player_id):
    player = get_object_or_404(Player, id=player_id)
    if request.method == 'POST':
        player.status = request.POST.get('status', player.status)
        player.is_active_account = request.POST.get('is_active_account') == 'true'
        player.save()
        messages.success(request, f'Player "{player.full_name}" status updated.')
        return redirect('admin_players_detail')
    
    return render(request, 'web/Admin/admin_player_edit.html', {'player': player})


# --- Admin Bulk Notification Views ---

@user_passes_test(is_superuser, login_url='/admin/login/')
def admin_notify_players(request):
    """Send a notification to all active players or a specific player"""
    if request.method == 'POST':
        message = request.POST.get('message', '').strip()
        link = request.POST.get('link', '').strip() or None
        target_id = request.POST.get('target_id', 'all')

        if not message:
            messages.error(request, "Notification message cannot be empty.")
            return redirect('admin_players_detail')

        from web.models import PlayerNotification, Player
        
        if target_id == 'all':
            active_players = Player.objects.filter(is_active_account=True, is_archived=False)
            success_msg = f"Notification sent to {active_players.count()} active player(s)."
        else:
            ids = [i.strip() for i in target_id.split(',') if i.strip().isdigit()]
            active_players = Player.objects.filter(id__in=ids)
            if active_players.exists():
                success_msg = f"Notification sent to {active_players.count()} player(s)."
            else:
                messages.error(request, "Player(s) not found.")
                return redirect('admin_players_detail')
                
        notifs = [
            PlayerNotification(
                recipient=p,
                message=message,
                link=link,
                notification_type='ADMIN_MESSAGE',
            )
            for p in active_players
        ]
        PlayerNotification.objects.bulk_create(notifs)
        messages.success(request, success_msg)
    return redirect('admin_players_detail')


@user_passes_test(is_superuser, login_url='/admin/login/')
def admin_notify_orgs(request):
    """Send a notification to all active organizations or a specific organization"""
    if request.method == 'POST':
        message = request.POST.get('message', '').strip()
        link = request.POST.get('link', '').strip() or None
        target_id = request.POST.get('target_id', 'all')

        if not message:
            messages.error(request, "Notification message cannot be empty.")
            return redirect('admin_organization_detail')

        from web.models import OrganizationNotification, Organization
        
        if target_id == 'all':
            active_orgs = Organization.objects.filter(status='Active', is_archived=False)
            success_msg = f"Notification sent to {active_orgs.count()} active organization(s)."
        else:
            ids = [i.strip() for i in target_id.split(',') if i.strip().isdigit()]
            active_orgs = Organization.objects.filter(id__in=ids)
            if active_orgs.exists():
                success_msg = f"Notification sent to {active_orgs.count()} organization(s)."
            else:
                messages.error(request, "Organization(s) not found.")
                return redirect('admin_organization_detail')

        notifs = [
            OrganizationNotification(
                recipient=org,
                message=message,
                notification_type='ADMIN_MESSAGE',
            )
            for org in active_orgs
        ]
        OrganizationNotification.objects.bulk_create(notifs)
        messages.success(request, success_msg)
    return redirect('admin_organization_detail')

# --- Notification APIs ---
from django.http import JsonResponse
from web.models import AdminNotification

@user_passes_test(is_superuser, login_url='admin_login')
def get_notifications(request):
    """API to fetch unread notifications"""
    from django.core.cache import cache
    cache_key = f'admin_notifications_{request.user.id}'
    data_dict = cache.get(cache_key)
    
    if data_dict is None:
        notifications = AdminNotification.objects.filter(is_read=False).order_by('-created_at')[:10]
        data = [{
            'id': n.id,
            'message': n.message,
            'type': n.notification_type,
            'created_at': n.created_at.strftime('%Y-%m-%d %H:%M'),
            'link': n.link or '#'
        } for n in notifications]
        
        data_dict = {'notifications': data, 'count': len(data)}
        cache.set(cache_key, data_dict, 60)
        
    return JsonResponse(data_dict)

@user_passes_test(is_superuser, login_url='admin_login')
def mark_notification_read(request, notif_id):
    """API to mark a notification as read"""
    if request.method == 'POST':
        try:
            notif = AdminNotification.objects.get(id=notif_id)
            notif.is_read = True
            notif.save()
            from django.core.cache import cache
            cache.delete(f'admin_notifications_{request.user.id}')
            return JsonResponse({'success': True})
        except AdminNotification.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Not found'}, status=404)
    return JsonResponse({'success': False}, status=400)

@user_passes_test(is_superuser, login_url='admin_login')
def mark_all_notifications_read(request):
    """API to mark all notifications as read"""
    if request.method == 'POST':
        AdminNotification.objects.filter(is_read=False).update(is_read=True)
        from django.core.cache import cache
        cache.delete(f'admin_notifications_{request.user.id}')
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=400)

@user_passes_test(is_superuser, login_url='admin_login')
def admin_delete_tournament(request, tournament_id):
    tournament = get_object_or_404(Tournament, Tournament_ID=tournament_id)
    if request.method == 'POST':
        name = tournament.Name
        tournament.archived_at = timezone.now()
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
    from django.core.cache import cache
    context = cache.get('admin_analytics_context')
    
    if not context:
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
        cache.set('admin_analytics_context', context, 60)
        
    return render(request, 'web/Admin/admin_analytics.html', context)

@user_passes_test(is_superuser, login_url='admin_login')
def admin_bidding_dashboard(request):
    # 1. Active Bidding Season
    active_season = BiddingSeason.objects.filter(is_active=True).first()
    
    # 2. Total Players Registered for Auction
    # We will assume all active players or players with bids are in auction
    total_players_in_auction = Player.objects.filter(is_archived=False).count()
    
    # Base queryset for overall metrics to ensure the dashboard remains dynamic even when inactive
    bids = Bid.objects.all()
    
    total_bids = bids.count()
    accepted_bids = bids.filter(status='Accepted')
    players_sold = accepted_bids.count()
    total_coins_spent = accepted_bids.aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    
    # 3. MVP
    mvp_bid = accepted_bids.order_by('-amount').first()
    
    # 4. Top Organizations by Spending
    top_orgs = (
        accepted_bids
        .values('organization__Organization_Name')
        .annotate(
            spent=Sum('amount'), 
            players_acquired=Count('id')
        )
        .order_by('-spent')
    )
    
    top_organizations = []
    for rank, org_data in enumerate(top_orgs, start=1):
        top_organizations.append({
            'rank': rank,
            'name': org_data['organization__Organization_Name'],
            'players_acquired': org_data['players_acquired'],
            'total_spent': org_data['spent'],
            'average_bid': round(org_data['spent'] / org_data['players_acquired'], 2) if org_data['players_acquired'] > 0 else 0
        })
        
    # 5. Live Bid Activity Feed
    live_bids = bids.order_by('-created_at')[:10]
    
    # 6. Player Auction Status Summary
    negotiation_bids_count = bids.filter(status='Negotiation').values('player').distinct().count()
    sold_player_ids = set(accepted_bids.values_list('player_id', flat=True).distinct())
    available_players = total_players_in_auction - len(sold_player_ids)
    
    # 7. Auction Heatmap (Top 5 Most Wanted)
    heatmap = (
        bids
        .values('player__full_name')
        .annotate(total_bids=Count('id'), highest_bid=Max('amount'))
        .order_by('-total_bids')[:5]
    )
    
    context = {
        'active_season': active_season,
        'all_seasons': BiddingSeason.objects.all().order_by('start_date'),
        'season_logs': BiddingSeasonLog.objects.filter(season=active_season).order_by('-timestamp')[:5] if active_season else [],
        'total_players_in_auction': total_players_in_auction,
        'total_bids': total_bids,
        'players_sold': players_sold,
        'total_coins_spent': total_coins_spent,
        'mvp_bid': mvp_bid,
        'top_organizations': top_organizations,
        'live_bids': live_bids,
        'auction_status': {
            'available': available_players if available_players > 0 else 0,
            'negotiation': negotiation_bids_count,
            'sold': players_sold,
            'unsold': available_players - negotiation_bids_count if available_players > 0 else 0
        },
        'heatmap': heatmap,
    }
    
    return render(request, 'web/Admin/admin_bidding_dashboard.html', context)

@user_passes_test(is_superuser, login_url='admin_login')
def admin_bidding_details(request):
    from decimal import Decimal
    
    if request.method == 'POST':
        if 'add_manual_bid' in request.POST:
            player_id = request.POST.get('player_id')
            organization_id = request.POST.get('organization_id')
            season_id = request.POST.get('season_id')
            amount = request.POST.get('amount')
            status = request.POST.get('status', 'Accepted')
            
            try:
                player = Player.objects.get(id=player_id)
                organization = Organization.objects.get(id=organization_id)
                season = BiddingSeason.objects.get(id=season_id)
                
                # Create the manual Bid
                bid = Bid(
                    season=season,
                    player=player,
                    organization=organization,
                    amount=Decimal(amount),
                    status=status,
                    is_manual=True
                )
                
                # Skipping full_clean here if season is inactive, to allow Admin override
                bid.save()
                
                # If Accepted, also add player to OrganizationPlayer (simulate actual bid acceptance logic)
                if status == 'Accepted':
                    from .models import OrganizationPlayer
                    player.organization = organization
                    player.save()
                    OrganizationPlayer.objects.get_or_create(
                        organization=organization,
                        player=player,
                        defaults={
                            'name': player.full_name,
                            'email': player.email,
                            'game_id': player.uid,
                            'status_label': 'Purchased via Manual Bid'
                        }
                    )
                
                messages.success(request, f"Manual bid for {player.full_name} added successfully.")
            except Exception as e:
                messages.error(request, f"Failed to add manual bid: {str(e)}")
            return redirect('admin_bidding_details')

    active_season = BiddingSeason.objects.filter(is_active=True).first()
    bids = Bid.objects.filter(season=active_season) if active_season else Bid.objects.none()
    
    # 1. All Bids (Regular Bids Only)
    all_bids = bids.filter(is_manual=False).select_related('player', 'organization').order_by('-created_at')
    
    # 2. Manual Bids
    manual_bids = bids.filter(is_manual=True).select_related('player', 'organization').order_by('-created_at')
    
    # 3. Top Organizations by Spending
    top_orgs = (
        bids.filter(status='Accepted')
        .values('organization__Organization_Name')
        .annotate(
            spent=Sum('amount'), 
            players_acquired=Count('id')
        )
        .order_by('-spent')
    )
    
    context = {
        'active_season': active_season,
        'all_bids': all_bids,
        'manual_bids': manual_bids,
        'top_orgs': top_orgs,
        'players': Player.objects.filter(status='ACTIVE', is_archived=False),
        'organizations': Organization.objects.filter(status='Active', is_archived=False),
        'seasons': BiddingSeason.objects.all().order_by('-start_date'),
    }
    return render(request, 'web/Admin/admin_bidding_details.html', context)

@user_passes_test(is_superuser, login_url='admin_login')
def admin_bidding_export(request, report_type):
    import csv
    from django.http import HttpResponse
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{report_type}_report.csv"'
    writer = csv.writer(response)
    
    if report_type == 'bidding_activity':
        writer.writerow(['Player Name', 'Organization Name', 'Bid Amount', 'Bid Status', 'Bid Date', 'Season'])
        for bid in Bid.objects.select_related('player', 'organization', 'season').all():
            writer.writerow([
                bid.player.full_name if bid.player else 'N/A',
                bid.organization.Organization_Name if bid.organization else 'N/A',
                bid.amount,
                bid.status,
                bid.created_at.strftime('%Y-%m-%d %H:%M'),
                bid.season.name if bid.season else 'N/A'
            ])
            
    elif report_type == 'transaction':
        writer.writerow(['Organization', 'Transaction Type', 'Coins', 'Date', 'Description'])
        for txn in Transaction.objects.select_related('sender').all():
            writer.writerow([
                txn.sender.Organization_Name if txn.sender else 'System',
                txn.transaction_type,
                txn.amount,
                txn.timestamp.strftime('%Y-%m-%d %H:%M'),
                txn.description
            ])
            
    elif report_type == 'organization_spending':
        writer.writerow(['Rank', 'Organization', 'Players Acquired', 'Total Coins Spent', 'Average Bid'])
        top_orgs = Bid.objects.filter(status='Accepted').values('organization__Organization_Name').annotate(spent=Sum('amount'), players=Count('id')).order_by('-spent')
        for rank, org in enumerate(top_orgs, 1):
            writer.writerow([
                rank,
                org['organization__Organization_Name'],
                org['players'],
                org['spent'],
                round(org['spent'] / org['players'], 2) if org['players'] > 0 else 0
            ])
            
    elif report_type == 'heatmap':
        writer.writerow(['Player', 'Total Bids', 'Highest Bid'])
        heatmap = Bid.objects.values('player__full_name').annotate(total_bids=Count('id'), highest_bid=Max('amount')).order_by('-total_bids')
        for row in heatmap:
            writer.writerow([
                row['player__full_name'],
                row['total_bids'],
                row['highest_bid']
            ])
            
    return response

@user_passes_test(is_superuser, login_url='admin_login')
def admin_update_bid_status(request, bid_id):
    """Update bid status and handle wallet refunds on rejection (Issue #5)."""
    if request.method != 'POST':
        return redirect('admin_bidding_dashboard')
    
    bid = get_object_or_404(Bid, id=bid_id)
    old_status = bid.status
    new_status = request.POST.get('status')
    
    valid_statuses = [s[0] for s in Bid.STATUS_CHOICES]
    if new_status not in valid_statuses:
        messages.error(request, 'Invalid bid status.')
        return redirect('admin_bidding_dashboard')
    
    # Handle Rejected → refund coins to organization wallet
    if new_status == 'Rejected' and old_status == 'Pending':
        org = bid.organization
        org.coins += bid.amount
        org.save()
        # Log the refund transaction
        Transaction.objects.create(
            sender=None,
            recipient=org,
            amount=bid.amount,
            transaction_type='BID_REFUND',
            description=f'Refund for rejected bid on {bid.player.full_name}'
        )
        messages.success(request, f'Bid rejected and ₹{bid.amount:,} refunded to {org.Organization_Name}.')
    elif new_status == 'Accepted' and old_status != 'Accepted':
        # Assign player to org
        from .models import OrganizationPlayer
        
        # 1. Update the player's direct organization reference (legacy)
        bid.player.organization = bid.organization
        bid.player.save()
        
        # 2. Create the unified OrganizationPlayer record
        # Note: We use get_or_create to prevent duplicate entries if the action is somehow re-run
        OrganizationPlayer.objects.get_or_create(
            organization=bid.organization,
            player=bid.player,
            defaults={
                'name': bid.player.full_name,
                'email': bid.player.email,
                'game_id': bid.player.uid,
                'status_label': 'Purchased via Bidding'
            }
        )
        
        messages.success(request, f'Bid for {bid.player.full_name} accepted successfully. Player added to {bid.organization.Organization_Name}.')
    else:
        messages.success(request, f'Bid status updated to {new_status}.')
    
    bid.status = new_status
    # Use update() to skip model's full_clean season.is_active check
    Bid.objects.filter(id=bid.id).update(status=new_status)
    
    return redirect('admin_bidding_dashboard')

@user_passes_test(is_superuser, login_url='admin_login')
def admin_start_bidding_season(request):
    if request.method == 'POST':
        name = request.POST.get('name', f"Manual Season {timezone.now().strftime('%Y-%m-%d')}")
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')
        
        # Admin Wallet Distribution (Feature #1)
        bidding_budget = request.POST.get('bidding_budget')
        
        # Check if there's already an active season
        if BiddingSeason.objects.filter(is_active=True).exists():
            messages.error(request, "A bidding season is already active. Please end or pause it before starting a new one.")
            return redirect('admin_bidding_dashboard')

        start_dt = timezone.now()
        if start_date_str:
            try:
                naive_dt = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M')
                start_dt = timezone.make_aware(naive_dt)
            except ValueError:
                pass

        try:
            season = BiddingSeason.objects.create(
                name=name,
                auto_start=False,
                is_active=True,
                start_date=start_dt
            )
            
            if end_date_str:
                try:
                    naive_dt = datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M')
                    season.end_date = timezone.make_aware(naive_dt)
                    season.save()
                except ValueError:
                    pass
                    
            # Distribute Coins Logic
            if bidding_budget:
                try:
                    budget_amount = Decimal(bidding_budget)
                    if budget_amount > 0:
                        orgs = Organization.objects.filter(status='Active', is_active_account=True)
                        count = 0
                        for org in orgs:
                            org.coins += budget_amount  # Fixed: Add to existing balance
                            org.save()
                            
                            # create transaction record for history
                            Transaction.objects.create(
                                recipient=org,
                                amount=budget_amount,
                                transaction_type='ADMIN_GRANT',
                                description=f"Initial Bidding Budget for {season.name}"
                            )
                            count += 1
                        BiddingSeasonLog.objects.create(season=season, action='START', message=f"Bidding Started with Budget: {budget_amount} added to {count} organizations.")
                    else:
                         BiddingSeasonLog.objects.create(season=season, action='START', message="Bidding Manually Started by Admin (Zero Budget)")
                except Exception as e:
                    season.delete() # Rollback creation if budget distribution fails
                    messages.error(request, f"Error distributing budget: {str(e)}")
                    return redirect('admin_bidding_dashboard')
            else:
                BiddingSeasonLog.objects.create(season=season, action='START', message="Bidding Manually Started by Admin")
                
            messages.success(request, f"Bidding Season '{season.name}' started successfully.")
        except ValidationError as e:
            messages.error(request, f"Validation Error: {', '.join(e.messages)}")
        except Exception as e:
            messages.error(request, f"Error starting bidding season: {str(e)}")
    return redirect('admin_bidding_dashboard')

@user_passes_test(is_superuser, login_url='admin_login')
def admin_pause_bidding_season(request):
    if request.method == 'POST':
        active_season = BiddingSeason.objects.filter(is_active=True).first()
        if active_season:
            active_season.is_active = False
            active_season.save()
            BiddingSeasonLog.objects.create(season=active_season, action='PAUSE', message="Bidding Paused by Admin")
            messages.success(request, f"Bidding Season '{active_season.name}' paused successfully.")
        else:
            messages.error(request, "No active bidding season to pause.")
    return redirect('admin_bidding_dashboard')

@user_passes_test(is_superuser, login_url='admin_login')
def admin_end_bidding_season(request):
    if request.method == 'POST':
        season_id = request.POST.get('season_id')
        if season_id:
            season = get_object_or_404(BiddingSeason, id=season_id)
        else:
            season = BiddingSeason.objects.filter(is_active=True).first()
        if season:
            season.is_active = False
            now = timezone.now()
            if season.start_date and season.start_date >= now:
                season.start_date = now - timedelta(seconds=1)
            season.end_date = now
            season.save()
            BiddingSeasonLog.objects.create(season=season, action='END', message="Bidding Ended by Admin")
            
            # Feature #3: Wallet Reset After Auction
            orgs_with_coins = Organization.objects.filter(coins__gt=0)
            for org in orgs_with_coins:
                Transaction.objects.create(
                    recipient=org,
                    amount=org.coins,
                    transaction_type='WITHDRAWAL',
                    description=f"Wallet reset upon bidding close - Season: {season.name}"
                )
            Organization.objects.all().update(coins=0)
            BiddingSeasonLog.objects.create(season=season, action='RESET', message="Organization Wallets Reset to 0")

            messages.success(request, f"Bidding Season '{season.name}' ended successfully.")
    return redirect('admin_bidding_dashboard')

@user_passes_test(is_superuser, login_url='admin_login')
def admin_update_bidding_season(request):
    if request.method == 'POST':
        season_id = request.POST.get('season_id')
        name = request.POST.get('name')
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')
        
        auto_start = request.POST.get('auto_start') == 'on'

        if season_id:
            season = get_object_or_404(BiddingSeason, id=season_id)
        else:
            season = BiddingSeason()

        season.name = name
        season.auto_start = auto_start
        
        if start_date_str:
            naive_dt = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M')
            season.start_date = timezone.make_aware(naive_dt)
        
        if end_date_str:
            naive_dt = datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M')
            season.end_date = timezone.make_aware(naive_dt)
        else:
            season.end_date = None
            
        season.save()
        messages.success(request, f"Bidding Season '{season.name}' updated successfully.")
    return redirect('admin_bidding_dashboard')


@user_passes_test(is_superuser, login_url='/admin/login/')
def api_admin_live_bidding_stats(request):
    """Returns live JSON stats for the admin bidding dashboard."""
    from django.http import JsonResponse
    from django.db.models import Sum
    from decimal import Decimal
    
    bids = Bid.objects.all()
    total_bids = bids.count()
    accepted_bids = bids.filter(status='Accepted')
    players_sold = accepted_bids.count()
    total_coins_spent = accepted_bids.aggregate(Sum('amount'))['amount__sum'] or Decimal('0')
    mvp_bid = accepted_bids.order_by('-amount').first()

    return JsonResponse({
        'total_bids': total_bids,
        'players_sold': players_sold,
        'total_coins_spent': f"₹{int(total_coins_spent):,}",
        'mvp_amount': f"₹{int(mvp_bid.amount):,}" if mvp_bid else "---",
        'mvp_player': mvp_bid.player.username if mvp_bid else "",
    })


@user_passes_test(is_superuser, login_url='/admin/login/')
def admin_bids_report(request):
    """Shows a directory of reports grouped by season and manual bids."""
    from django.db.models import Sum, Count
    
    # 1. Calculate Manual Bids Summary
    manual_bids = Bid.objects.filter(is_manual=True)
    manual_summary = {
        'name': 'Manual Bids Report',
        'is_manual': True,
        'total_bids': manual_bids.count(),
        'total_spent': manual_bids.filter(status='Accepted').aggregate(Sum('amount'))['amount__sum'] or 0,
    }
    
    # 2. Calculate Season Summaries
    seasons = BiddingSeason.objects.all().order_by('-start_date')
    season_summaries = []
    
    for season in seasons:
        season_bids = Bid.objects.filter(season=season, is_manual=False)
        total_bids = season_bids.count()
        total_spent = season_bids.filter(status='Accepted').aggregate(Sum('amount'))['amount__sum'] or 0
        status_label = "Active" if season.is_active else "Completed"
        
        season_summaries.append({
            'season_id': season.id,
            'name': season.name,
            'status': status_label,
            'total_bids': total_bids,
            'total_spent': total_spent,
        })
        
    context = {
        'manual_summary': manual_summary,
        'season_summaries': season_summaries,
    }
    return render(request, 'web/Admin/admin_bids_report.html', context)


@user_passes_test(is_superuser, login_url='/admin/login/')
def admin_report_detail_manual(request):
    """Shows specific report for manual bids."""
    from django.db.models import Sum, Count
    all_bids = Bid.objects.filter(is_manual=True).select_related('player', 'organization', 'season').order_by('-created_at')
    
    top_orgs = Bid.objects.filter(is_manual=True, status='Accepted').values(
        'organization__Organization_Name'
    ).annotate(
        spent=Sum('amount'),
        players_acquired=Count('id')
    ).order_by('-spent')

    context = {
        'report_title': 'MANUAL BIDS REPORT',
        'report_desc': 'Detailed ledger of all manually placed bids by administrators.',
        'all_bids': all_bids,
        'top_orgs': top_orgs,
    }
    return render(request, 'web/Admin/admin_bids_report_detail.html', context)


@user_passes_test(is_superuser, login_url='/admin/login/')
def admin_report_detail_season(request, season_id):
    """Shows specific report for a particular season."""
    from django.db.models import Sum, Count
    from django.shortcuts import get_object_or_404
    
    season = get_object_or_404(BiddingSeason, id=season_id)
    all_bids = Bid.objects.filter(season=season, is_manual=False).select_related('player', 'organization').order_by('-created_at')
    
    top_orgs = Bid.objects.filter(season=season, is_manual=False, status='Accepted').values(
        'organization__Organization_Name'
    ).annotate(
        spent=Sum('amount'),
        players_acquired=Count('id')
    ).order_by('-spent')

    context = {
        'report_title': f"{season.name} REPORT",
        'report_desc': f"Detailed ledger and spending analytics for {season.name}.",
        'all_bids': all_bids,
        'top_orgs': top_orgs,
    }
    return render(request, 'web/Admin/admin_bids_report_detail.html', context)



@user_passes_test(is_superuser, login_url='/admin/login/')
def admin_settings(request):
    from .models import SystemSettings
    settings = SystemSettings.get_settings()
    
    if request.method == 'POST':
        # Maintenance
        settings.is_maintenance_mode = request.POST.get('is_maintenance_mode') == 'on'
        settings.maintenance_message = request.POST.get('maintenance_message', '')

        # Site Identity
        settings.site_name = request.POST.get('site_name', 'EGAMESCOUT')
        settings.contact_email = request.POST.get('contact_email', '')

        # Registration Controls
        settings.allow_player_registration = request.POST.get('allow_player_registration') == 'on'
        settings.allow_org_registration = request.POST.get('allow_org_registration') == 'on'

        # Coin / Economy
        try:
            settings.default_org_coins = float(request.POST.get('default_org_coins', 1000))
            settings.default_player_coins = float(request.POST.get('default_player_coins', 0))
        except (ValueError, TypeError):
            pass

        # Announcement Banner
        settings.show_announcement = request.POST.get('show_announcement') == 'on'
        settings.announcement_text = request.POST.get('announcement_text', '')

        settings.save()
        messages.success(request, 'System settings saved successfully.')
        return redirect('admin_settings')
        
    return render(request, 'web/Admin/admin_settings.html', {'settings': settings})


# --- Verification & Approvals ---
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

@user_passes_test(is_superuser, login_url='/admin/login/')
def admin_grant_verification(request, entity_type, entity_id):
    if request.method == 'POST':
        if entity_type == 'organization':
            org = get_object_or_404(Organization, id=entity_id)
            org.is_verified = True
            org.save()
            messages.success(request, f"{org.Organization_Name} has been verified.")
            
            # Send Email
            html_message = render_to_string('web/emails/org_verified.html', {'org': org})
            plain_message = strip_tags(html_message)
            send_mail(
                'Verification Successful - E-GameScout',
                plain_message,
                None,
                [org.Organization_Email],
                html_message=html_message
            )
            return redirect('admin_organization_detail')
            
        elif entity_type == 'player':
            player = get_object_or_404(Player, id=entity_id)
            player.is_verified = True
            player.save()
            messages.success(request, f"{player.full_name} has been verified.")
            
            # Send Email
            html_message = render_to_string('web/emails/player_verified.html', {'player': player})
            plain_message = strip_tags(html_message)
            send_mail(
                'Verification Successful - E-GameScout',
                plain_message,
                None,
                [player.email],
                html_message=html_message
            )
            return redirect('admin_players_detail')

    return redirect('admin_dashboard')

@user_passes_test(is_superuser, login_url='/admin/login/')
def admin_tournament_approvals(request):
    tab = request.GET.get('tab', 'pending')
    
    if tab == 'history':
        tournaments_list = Tournament.objects.filter(approval_status__in=['APPROVED', 'REJECTED']).order_by('-UpdatedAt')
    else:
        tournaments_list = Tournament.objects.filter(approval_status='PENDING').order_by('-CreatedAt')
    
    paginator = Paginator(tournaments_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'tournaments': page_obj,
        'current_tab': tab,
    }
    return render(request, 'web/Admin/admin_tournament_approvals.html', context)

@user_passes_test(is_superuser, login_url='/admin/login/')
def admin_approve_tournament(request, tournament_id):
    if request.method == 'POST':
        tournament = get_object_or_404(Tournament, Tournament_ID=tournament_id)
        tournament.approval_status = 'APPROVED'
        tournament.save()

        # Notify Organizer
        from .models import OrganizationNotification
        OrganizationNotification.objects.create(
            recipient=tournament.Organization_Name,
            message=f"Your tournament '{tournament.Name}' has been approved by Admin! You can now publish it.",
            notification_type='TOURNAMENT',
            related_tournament=tournament,
        )

        messages.success(request, f"Tournament {tournament.Name} has been approved.")
        
    return redirect('admin_tournament_approvals')

@user_passes_test(is_superuser, login_url='/admin/login/')
def admin_reject_tournament(request, tournament_id):
    if request.method == 'POST':
        tournament = get_object_or_404(Tournament, Tournament_ID=tournament_id)
        reason = request.POST.get('rejection_reason', '')
        tournament.approval_status = 'REJECTED'
        tournament.admin_rejection_reason = reason
        tournament.is_published = False
        tournament.save()

        # Notify Organizer
        from .models import OrganizationNotification
        OrganizationNotification.objects.create(
            recipient=tournament.Organization_Name,
            message=f"Your tournament '{tournament.Name}' has been rejected by Admin. Reason: {reason}",
            notification_type='TOURNAMENT',
            related_tournament=tournament,
        )

        messages.warning(request, f"Tournament {tournament.Name} has been rejected.")
        
    return redirect('admin_tournament_approvals')

@user_passes_test(is_superuser, login_url='/admin/login/')
def admin_tournament_approvals_history(request):
    history = Tournament.objects.filter(approval_status__in=['APPROVED', 'REJECTED']).order_by('-UpdatedAt')
    
    paginator = Paginator(history, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'tournaments': page_obj,
    }
    return render(request, 'web/Admin/admin_tournament_approvals_history.html', context)

# --- Archive Actions ---
@user_passes_test(is_superuser, login_url='/admin/login/')
def admin_archive_actions(request):
    if request.method == 'POST':
        action_type = request.POST.get('action_type')
        selected_ids = request.POST.getlist('selected_ids')
        
        if not selected_ids:
             messages.warning(request, "No items selected.")
             return redirect('admin_archive_actions')
             
        if action_type == 'delete_players':
            deleted_count, _ = Player.objects.filter(id__in=selected_ids, is_archived=True).delete()
            messages.success(request, f"{deleted_count} archived players permanently deleted.")
        elif action_type == 'delete_orgs':
            deleted_count, _ = Organization.objects.filter(id__in=selected_ids, is_archived=True).delete()
            messages.success(request, f"{deleted_count} archived organizations permanently deleted.")
        elif action_type == 'delete_tournaments':
            deleted_count, _ = Tournament.objects.filter(Tournament_ID__in=selected_ids, is_archived=True).delete()
            messages.success(request, f"{deleted_count} archived tournaments permanently deleted.")
            
        return redirect('admin_archive_actions')

    # Get search queries
    player_q = request.GET.get('player_q', '')
    org_q = request.GET.get('org_q', '')
    tour_q = request.GET.get('tour_q', '')

    # Base Querysets
    players_qs = Player.objects.filter(is_archived=True).order_by('-created_at')
    orgs_qs = Organization.objects.filter(is_archived=True).order_by('-CreatedAt')
    tours_qs = Tournament.objects.filter(is_archived=True).order_by('-CreatedAt')

    # Counts for Dashboard
    total_players = players_qs.count()
    total_orgs = orgs_qs.count()
    total_tours = tours_qs.count()

    # --- Export Functionality ---
    export_type = request.GET.get('export')
    if export_type:
        response = HttpResponse(content_type='text/csv')
        writer = csv.writer(response)
        
        if export_type == 'players':
            response['Content-Disposition'] = 'attachment; filename="archived_players.csv"'
            writer.writerow(['ID', 'Full Name', 'Email', 'Mobile', 'UID', 'Created At', 'Archived At'])
            for p in players_qs:
                archived_at = p.archived_at.strftime("%Y-%m-%d %H:%M:%S") if p.archived_at else "Unknown"
                writer.writerow([p.id, p.full_name, p.email, p.mobile_no, p.uid, p.created_at, archived_at])
                
        elif export_type == 'orgs':
            response['Content-Disposition'] = 'attachment; filename="archived_organizations.csv"'
            writer.writerow(['ID', 'Organization Name', 'Email', 'Contact', 'Created At', 'Archived At'])
            for o in orgs_qs:
                archived_at = o.archived_at.strftime("%Y-%m-%d %H:%M:%S") if o.archived_at else "Unknown"
                writer.writerow([o.id, o.Organization_Name, o.Organization_Email, o.Organization_Contact, o.CreatedAt, archived_at])
                
        elif export_type == 'tournaments':
            response['Content-Disposition'] = 'attachment; filename="archived_tournaments.csv"'
            writer.writerow(['ID', 'Tournament Name', 'Organization', 'Status', 'Created At', 'Archived At'])
            for t in tours_qs:
                org_name = t.Organization_Name.Organization_Name if t.Organization_Name else 'N/A'
                archived_at = t.archived_at.strftime("%Y-%m-%d %H:%M:%S") if t.archived_at else "Unknown"
                writer.writerow([t.Tournament_ID, t.Name, org_name, t.Status, t.CreatedAt, archived_at])
                
        return response

    # Apply Filters for Display
    if player_q:
        players_qs = players_qs.filter(
            Q(full_name__icontains=player_q) | 
            Q(email__icontains=player_q) | 
            Q(uid__icontains=player_q)
        )

    if org_q:
        orgs_qs = orgs_qs.filter(
            Q(Organization_Name__icontains=org_q) |
            Q(Organization_Email__icontains=org_q)
        )

    if tour_q:
        tours_qs = tours_qs.filter(
            Q(Name__icontains=tour_q) |
            Q(Organization_Name__Organization_Name__icontains=tour_q)
        )

    # --- Chart Data Preparation ---
    # Distribution Data (Pie Chart)
    distribution_data = {
        'labels': ['Players', 'Organizations', 'Tournaments'],
        'data': [total_players, total_orgs, total_tours]
    }

    # Activity Data (Line Chart) - Using created_at as proxy for "activity" or timeframe
    # Grouping by date (last 30 days or general distribution)
    # Since we don't have 'archived_at', we'll show 'Creation Date' distribution or 'Last Updated'
    # Let's use UpdatedAt (approximating archive time)
    
    # helper for date grouping
    def get_date_counts(queryset, date_field):
        return (queryset
                .extra(select={'day': f"date({date_field})"})
                .values('day')
                .annotate(count=Count('id' if date_field != 'Tournament_ID' else 'Tournament_ID'))
                .order_by('day'))

    # Since SQLite/MySQL syntax differs for date extraction, keeping it simple:
    # Just passing counts for now. Logic for complex date grouping might need DB specific functions.
    # We will pass simple total counts for now to ensure robustness.
    
    context = {
        # Lists
        'archived_players': players_qs,
        'archived_orgs': orgs_qs,
        'archived_tournaments': tours_qs,
        
        # Search Params
        'player_q': player_q,
        'org_q': org_q,
        'tour_q': tour_q,
        
        # Dashboard Counts
        'total_players': total_players,
        'total_orgs': total_orgs,
        'total_tours': total_tours,
        
        # Charts
        'distribution_chart_data': json.dumps(distribution_data),
    }
    return render(request, 'web/Admin/admin_archive_actions.html', context)

@user_passes_test(is_superuser, login_url='/admin/login/')
def admin_delete_archived_player(request, player_id):
    player = get_object_or_404(Player, id=player_id, is_archived=True)
    if request.method == 'POST':
        name = player.username or player.full_name
        player.delete()
        messages.success(request, f"Player '{name}' has been permanently deleted.")
    return redirect('admin_archive_actions')

@user_passes_test(is_superuser, login_url='/admin/login/')
def admin_delete_archived_organization(request, org_id):
    org = get_object_or_404(Organization, id=org_id, is_archived=True)
    if request.method == 'POST':
        name = org.Organization_Name
        org.delete()
        messages.success(request, f"Organization '{name}' has been permanently deleted.")
    return redirect('admin_archive_actions')

@user_passes_test(is_superuser, login_url='/admin/login/')
def admin_delete_archived_tournament(request, tournament_id):
    tournament = get_object_or_404(Tournament, Tournament_ID=tournament_id, is_archived=True)
    if request.method == 'POST':
        name = tournament.Name
        tournament.delete()
        messages.success(request, f"Tournament '{name}' has been permanently deleted.")
    return redirect('admin_archive_actions')


@user_passes_test(is_superuser, login_url='admin_login')
def admin_transaction_history(request):
    """Admin view: Shows Bidding Seasons by default. Passing ?season_id shows transactions for that season."""
    season_id = request.GET.get('season_id')
    view_mode = 'transactions' if season_id else 'seasons'

    if view_mode == 'transactions':
        season = get_object_or_404(BiddingSeason, id=season_id)
        search_query = request.GET.get('q', '').strip()
        type_filter  = request.GET.get('type', '').strip()

        start = season.start_date
        end = season.end_date or timezone.now()
        
        if start:
            txn_qs = Transaction.objects.select_related(
                'sender', 'recipient', 'recipient_player'
            ).filter(
                timestamp__gte=start, 
                timestamp__lte=end
            ).order_by('-timestamp')
        else:
            txn_qs = Transaction.objects.none()

        if search_query:
            txn_qs = txn_qs.filter(
                Q(sender__Organization_Name__icontains=search_query)     |
                Q(recipient__Organization_Name__icontains=search_query)  |
                Q(recipient_player__full_name__icontains=search_query)   |
                Q(description__icontains=search_query)
            )

        if type_filter:
            txn_qs = txn_qs.filter(transaction_type=type_filter)

        total_volume = txn_qs.aggregate(total=Sum('amount'))['total'] or 0

        paginator   = Paginator(txn_qs, 20)
        page_number = request.GET.get('page')
        page_obj    = paginator.get_page(page_number)

        transaction_types = Transaction.objects.values_list(
            'transaction_type', flat=True
        ).distinct().order_by('transaction_type')

        return render(request, 'web/Admin/admin_transactions.html', {
            'view_mode':          view_mode,
            'season':             season,
            'transactions':       page_obj,
            'page_obj':           page_obj,
            'total_volume':       total_volume,
            'search_query':       search_query,
            'type_filter':        type_filter,
            'transaction_types':  transaction_types,
        })
    
    else:
        # Bidding Seasons View
        search_query = request.GET.get('q', '').strip()
        seasons_qs = BiddingSeason.objects.all().order_by('-created_at')
        if search_query:
            seasons_qs = seasons_qs.filter(name__icontains=search_query)
            
        paginator   = Paginator(seasons_qs, 20)
        page_number = request.GET.get('page')
        page_obj    = paginator.get_page(page_number)
        
        return render(request, 'web/Admin/admin_transactions.html', {
            'view_mode':          view_mode,
            'seasons':            page_obj,
            'page_obj':           page_obj,
            'search_query':       search_query,
        })
