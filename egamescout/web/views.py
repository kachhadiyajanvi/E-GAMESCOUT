from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from django.conf import settings
from django.views.decorators.cache import cache_control
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.core.cache import cache
from django.db import models
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from django.core.serializers.json import DjangoJSONEncoder
from decimal import Decimal
import random
import time
import json

from web.forms import (
    OrganizationEmailForm, OTPForm, OrganizationDetailsForm,
    OrganizationLoginForm, OrganizationPhotoForm, TournamentForm,
    EmailLoginForm, OTPVerifyForm, AadharUploadForm,
    PlayerRegistrationForm, PlayerProfileForm
)
from web.models import (
    Organization, Tournament, TournamentBidder, Player, 
    Transaction, OrganizationPlayer, ExternalPlayerInvite, PlayerNotification,
    AdminNotification, BiddingSeason, BiddingSeasonLog, Bid, Negotiation,
    SystemSettings, PlayerTask, OrganizationNotification, UserSession, ScorecardAnalysis,
    PreviousTournament, TournamentTeam, TournamentScorecard
)
from web.decorators import login_required_organization
from web.auth_services import handle_secure_login, handle_secure_logout
from web.helpers import extract_aadhar_details


def terms_and_conditions(request):
    return render(request, 'web/terms.html')

@csrf_exempt
def api_send_otp(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email')
            role = data.get('role')
            
            if not email or not role:
                return JsonResponse({'status': 'error', 'message': 'Email and role are required'}, status=400)
                
            player_exists = False
            org_exists = False
            
            if role.lower() == 'player':
                try:
                    player = Player.objects.get(email__iexact=email)
                    if player.status == 'SUSPENDED':
                         return JsonResponse({'status': 'error', 'message': 'Account is suspended'}, status=403)
                    player_exists = True
                except Player.DoesNotExist:
                    return JsonResponse({'status': 'error', 'message': 'Player not found'}, status=404)
            elif role.lower() == 'organization':
                try:
                    org = Organization.objects.get(Organization_Email__iexact=email)
                    if org.status == 'Suspended':
                         return JsonResponse({'status': 'error', 'message': 'Account is suspended'}, status=403)
                    org_exists = True
                except Organization.DoesNotExist:
                    return JsonResponse({'status': 'error', 'message': 'Organization not found'}, status=404)
            else:
                return JsonResponse({'status': 'error', 'message': 'Unsupported role'}, status=400)
                
            if player_exists or org_exists:
                # Generate OTP
                otp_code = str(random.randint(100000, 999999))
                
                # Store OTP in cache for 5 minutes (300 seconds)
                cache_key = f"api_otp_{email}"
                cache.set(cache_key, otp_code, timeout=300)
                
                # Send Email
                html_message = render_to_string('web/emails/otp_verification.html', {'otp': otp_code, 'email': email, 'logo_url': request.build_absolute_uri('/static/web/images/logo.png')})
                plain_message = strip_tags(html_message)
                
                send_mail(
                    'Your E-Game Scout Code',
                    plain_message,
                    settings.DEFAULT_FROM_EMAIL or 'noreply@egamescout.com',
                    [email],
                    fail_silently=False,
                    html_message=html_message
                )
                
                print(f"DEBUG: API Post OTP for {email}: {otp_code}")
                return JsonResponse({'status': 'success', 'message': 'OTP sent successfully'})
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

@csrf_exempt
def api_verify_otp(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email')
            otp_input = data.get('otp')
            role = data.get('role')
            
            if not email or not otp_input or not role:
                 return JsonResponse({'status': 'error', 'message': 'Email, OTP, and role are required'}, status=400)
                 
            # Retrieve OTP from cache
            cache_key = f"api_otp_{email}"
            stored_otp = cache.get(cache_key)
            
            if not stored_otp:
                return JsonResponse({'status': 'error', 'message': 'OTP expired or invalid. Please request a new one.'}, status=400)
                
            if str(otp_input).strip() == str(stored_otp).strip():
                # OTP is correct, clear it
                cache.delete(cache_key)
                
                # Fetch user data to return
                if role.lower() == 'player':
                    try:
                        player = Player.objects.get(email__iexact=email)
                        return JsonResponse({'status': 'success', 'message': 'Login successful', 'data': {
                            'id': player.id, 
                            'name': player.full_name,
                            'email': player.email,
                            'aadhar_number': player.aadhar_number,
                            'uid': player.uid,
                            'mobile_no': player.mobile_no,
                            'age': player.age,
                            'role': 'player'
                        }})
                    except Player.DoesNotExist:
                        return JsonResponse({'status': 'error', 'message': 'Player not found'}, status=404)
                elif role.lower() == 'organization':
                    try:
                        org = Organization.objects.get(Organization_Email__iexact=email)
                        return JsonResponse({'status': 'success', 'message': 'Login successful', 'data': {'id': org.id, 'name': org.Organization_Name}})
                    except Organization.DoesNotExist:
                        return JsonResponse({'status': 'error', 'message': 'Organization not found'}, status=404)
            else:
                return JsonResponse({'status': 'error', 'message': 'Invalid OTP'}, status=400)
                
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

@csrf_exempt
def api_register_send_otp(request):
    """Sends OTP for registration, ensuring player does NOT exist."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email')
            role = data.get('role')
            
            if not email or not role:
                 return JsonResponse({'status': 'error', 'message': 'Email and role are required'}, status=400)
                 
            if role.lower() == 'player':
                if Player.objects.filter(email__iexact=email).exists():
                     return JsonResponse({'status': 'error', 'message': 'Player already exists. Please login.'}, status=409)
            elif role.lower() == 'organization':
                 if Organization.objects.filter(Organization_Email__iexact=email).exists():
                     return JsonResponse({'status': 'error', 'message': 'Organization already exists. Please login.'}, status=409)
            else:
                return JsonResponse({'status': 'error', 'message': 'Unsupported role'}, status=400)
                
            # Generate OTP
            otp_code = str(random.randint(100000, 999999))
            
            # Store OTP in cache for 5 minutes (300 seconds)
            cache_key = f"api_register_otp_{email}"
            cache.set(cache_key, otp_code, timeout=300)
            
            # Send Email
            html_message = render_to_string('web/emails/otp_verification.html', {'otp': otp_code, 'email': email, 'logo_url': request.build_absolute_uri('/static/web/images/logo.png')})
            plain_message = strip_tags(html_message)
            
            send_mail(
                'Your E-Game Scout Code',
                plain_message,
                settings.DEFAULT_FROM_EMAIL or 'noreply@egamescout.com',
                [email],
                fail_silently=False,
                html_message=html_message
            )
            
            print(f"DEBUG: API Post Register OTP for {email}: {otp_code}")
            return JsonResponse({'status': 'success', 'message': 'OTP sent successfully'})
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

@csrf_exempt
def api_register_verify_otp(request):
    """Verifies OTP for registration."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email')
            otp_input = data.get('otp')
            role = data.get('role')
            
            if not email or not otp_input or not role:
                 return JsonResponse({'status': 'error', 'message': 'Email, OTP, and role are required'}, status=400)
                 
            # Retrieve OTP from cache
            cache_key = f"api_register_otp_{email}"
            stored_otp = cache.get(cache_key)
            
            if not stored_otp:
                return JsonResponse({'status': 'error', 'message': 'OTP expired or invalid. Please request a new one.'}, status=400)
                
            if str(otp_input).strip() == str(stored_otp).strip():
                # OTP is correct, clear it
                cache.delete(cache_key)
                # Registration step 1 verified (email is good), proceed to next steps
                return JsonResponse({'status': 'success', 'message': 'OTP verified successfully'})
            else:
                return JsonResponse({'status': 'error', 'message': 'Invalid OTP'}, status=400)
                
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)


@csrf_exempt
def api_register_step1(request):
    """Handles Aadhar upload and AI extraction for the API."""
    if request.method == 'POST':
        email = request.POST.get('email')
        aadhar_image = request.FILES.get('aadhar_card')
        
        if not email or not aadhar_image:
            return JsonResponse({'status': 'error', 'message': 'Email and aadhar_card are required'}, status=400)
            
        verification = extract_aadhar_details(aadhar_image)
        
        if verification.get('success'):
            data = verification.get('data', {})
            age = data.get('age')
            
            # Check Age
            if age is not None and age < 16:
                 return JsonResponse({'status': 'error', 'message': f'Age Restriction: You are {age} years old. Minimum age is 16.'}, status=403)
            
            # Check Unique Aadhar
            aadhar_num = data.get('aadhar_number')
            if aadhar_num and Player.objects.filter(aadhar_number=aadhar_num).exists():
                 return JsonResponse({'status': 'error', 'message': f'Identity Conflict: Aadhar number {aadhar_num} is already registered.'}, status=409)

            return JsonResponse({
                'status': 'success', 
                'message': 'Identity Verified',
                'data': data
            })
        else:
            return JsonResponse({'status': 'error', 'message': verification.get('message', 'Failed to extract Aadhar details')}, status=400)
            
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

@csrf_exempt
def api_register_step2(request):
    """Handles final player registration details."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email')
            full_name = data.get('full_name')
            age = data.get('age')
            aadhar_number = data.get('aadhar_number')
            uid = data.get('uid')
            mobile_no = data.get('mobile_no')
            
            if not all([email, full_name, age, aadhar_number, uid, mobile_no]):
                return JsonResponse({'status': 'error', 'message': 'All fields are required'}, status=400)
                
            if Player.objects.filter(email=email).exists():
                return JsonResponse({'status': 'error', 'message': 'Player with this email already exists'}, status=409)
                
            if Player.objects.filter(uid=uid).exists():
                return JsonResponse({'status': 'error', 'message': 'Player with this UID already exists'}, status=409)
                
            if Player.objects.filter(aadhar_number=aadhar_number).exists():
                return JsonResponse({'status': 'error', 'message': 'Player with this Aadhar already exists'}, status=409)
                
            # Create Player
            player = Player.objects.create(
                email=email,
                full_name=full_name,
                age=age,
                aadhar_number=aadhar_number,
                uid=uid,
                mobile_no=mobile_no,
                status='ACTIVE'
            )
            
            # Send Welcome Email
            try:
                subject = 'Welcome to E-Game Scout - Journey Started'
                html_content = render_to_string('web/emails/welcome.html', {'full_name': player.full_name, 'logo_url': request.build_absolute_uri('/static/web/images/logo.png')})
                text_content = strip_tags(html_content)
                
                msg = EmailMultiAlternatives(subject, text_content, settings.EMAIL_HOST_USER, [email])
                msg.attach_alternative(html_content, "text/html")
                msg.send()
                print(f"DEBUG: Welcome email sent to {email}")
            except Exception as e:
                print(f"ERROR: Failed to send welcome email: {e}")

            return JsonResponse({'status': 'success', 'message': 'Registration Complete'})
            
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
            
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

def auth_login(request):
    if SystemSettings.get_settings().is_maintenance_mode:
        messages.error(request, SystemSettings.get_settings().maintenance_message)
        return redirect('index')

    # Check if a verification flow is already in progress and verified
    if request.session.get('auth_email') and request.session.get('otp_verified'):
        # If verified, redirect based on player existence
        if Player.objects.filter(email=request.session['auth_email']).exists():
            player = Player.objects.get(email=request.session['auth_email'])
            request.session['player_id'] = player.id
            return redirect('player_dashboard')
        else:
            return redirect('auth_register_upload')
            
    # Strict Redirect: If already logged in, go to dashboard
    if request.session.get('player_id'):
        return redirect('player_dashboard')

    is_register = request.GET.get('action') == 'register'

    if request.method == 'POST':
        form = EmailLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            player_exists = Player.objects.filter(email=email).exists()
            
            # Logic Branching
            if not is_register: # LOGIN FLOW
                if not player_exists:
                    messages.error(request, "This email is not registered. Please Register first.")
                    # return redirect(f"{request.path}?action=register") # Removed redirect as requested
                    return redirect('auth_login') # Refresh to show message
                
                # Check Suspended Status
                player = Player.objects.get(email=email)
                if player.status == 'SUSPENDED':
                    messages.error(request, 'Your account has been suspended. Please contact support.')
                    return redirect('auth_login')
            
            else: # REGISTER FLOW
                if player_exists:
                    messages.info(request, "You are already registered. Please Login.")
                    return redirect('auth_login')

            # Generate OTP
            otp_code = str(random.randint(100000, 999999))
            
            # Save OTP in Session (Stateless)
            request.session['auth_email'] = email
            request.session['auth_otp'] = otp_code # Store OTP in session
            request.session['auth_otp_created_at'] = time.time() # Store timestamp
            request.session['otp_verified'] = False # Reset verification status
            
            # Send Email
                            
            html_message = render_to_string('web/emails/otp_verification.html', {'otp': otp_code, 'email': email, 'logo_url': request.build_absolute_uri('/static/web/images/logo.png')})
            plain_message = strip_tags(html_message)
            
            send_mail(
                'Your E-Game Scout Code',
                plain_message,
                settings.DEFAULT_FROM_EMAIL or 'noreply@egamescout.com',
                [email],
                fail_silently=False,
                html_message=html_message
            )
            
            print(f"DEBUG: Player OTP for {email}: {otp_code}")
            messages.success(request, f'OTP sent to {email}')
            return redirect('auth_verify_otp')
    else:
        form = EmailLoginForm()
    
    return render(request, 'web/Player/login.html', {'form': form, 'is_register': is_register})

def auth_verify_otp(request):
    # Strict Redirect
    if request.session.get('player_id'):
        return redirect('player_dashboard')

    email = request.session.get('auth_email')
    if not email:
        return redirect('auth_login')
        
    if request.method == 'POST':
        form = OTPVerifyForm(request.POST)
        if form.is_valid():
            otp_input = form.cleaned_data['otp_code']
            session_otp = request.session.get('auth_otp')
            created_at = request.session.get('auth_otp_created_at')
            
            # Check Expiry (2 minutes = 120 seconds)
            if created_at and (time.time() - float(created_at) > 120):
                messages.error(request, 'OTP Expired. Please login again.')
                if 'auth_otp' in request.session: del request.session['auth_otp']
                return redirect('auth_login')

            # Check OTP from Session
            if str(otp_input).strip() == str(session_otp).strip():
                # OTP is valid
                request.session['otp_verified'] = True # Mark as verified
                # Clear OTP from session for security
                del request.session['auth_otp']
                
                # Check if player exists
                try:
                    player = Player.objects.get(email=email)
                    # Login User
                    # Clear conflicting sessions
                    if request.user.is_authenticated: logout(request)
                    if 'organizer_id' in request.session: del request.session['organizer_id']
                    
                    # Set generic session ID for Django to recognize
                    if not request.session.session_key:
                        request.session.create()
                    
                    request.session['player_id'] = player.id
                    
                    # Secure Tracking Login
                    handle_secure_login(request, user_id=player.id, user_type='PLAYER')
                    
                    return redirect('player_dashboard')
                except Player.DoesNotExist:
                    # New User -> Register Step 1 (Aadhar Upload)
                    return redirect('auth_register_upload')
            else:
                messages.error(request, 'Invalid or Expired OTP')
    else:
        form = OTPVerifyForm()
        
    return render(request, 'web/Player/verify_otp.html', {'form': form, 'email': email})


def auth_register_upload(request):
    """Step 1: Upload Aadhar Card"""
    # Strict Redirect
    if request.session.get('player_id'):
        return redirect('player_dashboard')

    email = request.session.get('auth_email')
    if not email:
        return redirect('auth_login')
    
    if request.method == 'POST':
        form = AadharUploadForm(request.POST, request.FILES)
        if form.is_valid():
            aadhar_image = request.FILES.get('aadhar_card')
            verification = extract_aadhar_details(aadhar_image)
            
            if verification['success']:
                data = verification['data']
                age = data.get('age')
                
                # Check Age
                if age is not None and age < 16:
                     messages.error(request, f"Age Restriction: You are {age} years old. Minimum age is 16.")
                     return render(request, 'web/Player/register_step1.html', {'form': form, 'email': email})
                
                # Check Unique Aadhar
                aadhar_num = data.get('aadhar_number')
                if aadhar_num and Player.objects.filter(aadhar_number=aadhar_num).exists():
                     messages.error(request, f"Identity Conflict: Aadhar number {aadhar_num} is already registered.")
                     return render(request, 'web/Player/register_step1.html', {'form': form, 'email': email})

                # Store in session
                request.session['auth_register_data'] = data
                messages.success(request, f"Identity Verified! Name: {data.get('full_name')}, Age: {age}")
                return redirect('auth_register_details')
            else:
                messages.error(request, verification['message'])
    else:
        form = AadharUploadForm()
        
    return render(request, 'web/Player/register_step1.html', {'form': form, 'email': email})

def auth_register_details(request):
    """Step 2: Complete Profile"""
    # Strict Redirect
    if request.session.get('player_id'):
        return redirect('player_dashboard')

    email = request.session.get('auth_email')
    # Check if step 1 completed
    reg_data = request.session.get('auth_register_data')
    
    if not email:
        return redirect('auth_login')
    
    if not reg_data:
        messages.warning(request, "Please upload your Aadhar Card first.")
        return redirect('auth_register_upload')
        
    if request.method == 'POST':
        form = PlayerRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            player = form.save(commit=False)
            player.email = email
            player.age = reg_data.get('age', 18) # Default 18 if somehow missing, but step 1 checks it
            player.status = 'ACTIVE'
            player.save()
            
            # Send Welcome Email
            try:
                subject = 'Welcome to E-Game Scout - Journey Started'
                html_content = render_to_string('web/emails/welcome.html', {'full_name': player.full_name, 'logo_url': request.build_absolute_uri('/static/web/images/logo.png')})
                text_content = strip_tags(html_content)
                
                msg = EmailMultiAlternatives(subject, text_content, settings.EMAIL_HOST_USER, [email])
                msg.attach_alternative(html_content, "text/html")
                msg.send()
                print(f"DEBUG: Welcome email sent to {email}")
            except Exception as e:
                print(f"ERROR: Failed to send welcome email: {e}")

            # Clear session
            if 'auth_email' in request.session: del request.session['auth_email']
            if 'otp_verified' in request.session: del request.session['otp_verified']
            if 'auth_register_data' in request.session: del request.session['auth_register_data']
            if 'auth_otp' in request.session: del request.session['auth_otp']
            
            messages.success(request, f"Registration Complete! Welcome {player.full_name}. Please Login.")
            return redirect('auth_login')
    else:
        # Pre-fill form
        initial_data = {
            'full_name': reg_data.get('full_name', ''),
            'aadhar_number': reg_data.get('aadhar_number', ''),
            'age': reg_data.get('age', '')
        }
        form = PlayerRegistrationForm(initial=initial_data)
        
    return render(request, 'web/Player/register_details.html', {'form': form, 'email': email})

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
def player_dashboard(request):
    player_id = request.session.get('player_id')
    if not player_id:
        return redirect('auth_login')
        
    player = Player.objects.get(id=player_id)
    
    # Fetch Tasks & Events
    import json
    
    now = timezone.now()
    
    # Existing queries
    upcoming_events = PlayerTask.objects.filter(
        player=player, 
        task_type='EVENT', 
        due_date__gte=now
    ).order_by('due_date')[:50]
    
    todo_list = PlayerTask.objects.filter(
        player=player, 
        task_type='TASK', 
        is_completed=False
    ).order_by('due_date')

    # --- Calendar Data Injection ---
    # 1. Scheduled Tournaments
    calendar_tournaments = Tournament.objects.filter(
        Status__in=['Scheduled', 'Ongoing'],
        start_date__isnull=False
    ).values('Name', 'start_date', 'Status', 'Tournament_ID')

    # 2. Player Tasks (Events)
    calendar_tasks = PlayerTask.objects.filter(
        player=player,
        due_date__isnull=False
    ).values('title', 'due_date', 'task_type', 'is_completed')

    # Combine & Format for JS
    calendar_events = []

    for t in calendar_tournaments:
        if t['start_date']:
            calendar_events.append({
                'title': t['Name'],
                'date': t['start_date'].strftime('%Y-%m-%d'),
                'time': '00:00',
                'type': 'TOURNAMENT',
                'status': t['Status'],
                'color': '#66FCF1'
            })

    for task in calendar_tasks:
        if task['due_date']:
            calendar_events.append({
                'title': task['title'],
                'date': task['due_date'].strftime('%Y-%m-%d'), 
                'time': task['due_date'].strftime('%H:%M'),
                'type': task['task_type'],
                'status': 'Completed' if task['is_completed'] else 'Pending',
                'color': '#22c55e' if task['task_type'] == 'TASK' else '#a855f7' 
            })

    # Bidding system removed - show all scheduled/ongoing tournaments
    active_tournaments = Tournament.objects.filter(Status='Ongoing')[:5]
    upcoming_tournaments_list = Tournament.objects.filter(Status='Scheduled')[:5]
    total_tournaments_joined = 0
    player_credits = player.coins

    return render(request, 'web/Player/dashboard.html', {
        'player': player,
        'upcoming_events': upcoming_events,
        'todo_list': todo_list,
        'calendar_events_json': json.dumps(calendar_events, cls=DjangoJSONEncoder),
        'active_tournaments': active_tournaments,
        'upcoming_tournaments_list': upcoming_tournaments_list,
        'total_tournaments_joined': total_tournaments_joined,
        'player_credits': player_credits,
    })


def player_profile(request):
    player_id = request.session.get('player_id')
    if not player_id:
        return redirect('auth_login')
        
    player = get_object_or_404(Player, id=player_id)
    
    if request.method == 'POST':
        form = PlayerProfileForm(request.POST, request.FILES, instance=player)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('player_profile')
        else:
             messages.error(request, 'Error updating profile. Please check the fields.')
    else:
        form = PlayerProfileForm(instance=player)
        
    return render(request, 'web/Player/profile.html', {'player': player, 'form': form})

def player_delete_account(request):
    player_id = request.session.get('player_id')
    if not player_id:
        return redirect('auth_login')
        
    if request.method == 'POST':
        player = get_object_or_404(Player, id=player_id)
        player.delete()
        request.session.flush()
        messages.success(request, 'Your account has been permanently deleted.')
        return redirect('index')
        
    return render(request, 'web/Player/delete_account_confirm.html')

def auth_logout(request):
    handle_secure_logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('index')

def org_logout(request):
    """Logout organization and clear session"""
    handle_secure_logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('index')

def index(request):
    organizations = Organization.objects.filter(status='Active')[:10]
    # Check if bidding season is currently active - drives the LIVE SCOUTING badge
    try:
            live_scouting = BiddingSeason.objects.filter(is_active=True).exists()
    except Exception:
        live_scouting = False
        
    previous_tournaments = PreviousTournament.objects.filter(published=True).order_by('-date')[:6]
        
    return render(request, 'web/index.html', {
        'organizations': organizations,
        'live_scouting': live_scouting,
        'previous_tournaments': previous_tournaments,
    })

def public_tournaments(request):
    """Public view for upcoming tournaments"""
    # Published tournaments (visible and joinable)
    tournaments = Tournament.objects.filter(
        Status__in=['Scheduled', 'Ongoing'],
        is_published=True,
        is_archived=False
    ).order_by('start_date')

    # Coming soon - unpublished tournaments (teaser only)
    coming_soon = Tournament.objects.filter(
        is_published=False,
        is_archived=False
    ).order_by('start_date')

    # Bidding system removed
    joined_tournament_ids = []
    player_id = request.session.get('player_id')

    return render(request, 'web/tournaments.html', {
        'tournaments': tournaments,
        'coming_soon': coming_soon,
        'joined_tournament_ids': joined_tournament_ids,
        'player_id': player_id,
    })

def public_previous_tournaments(request):
    """Public view for all historic/previous tournaments"""
    tournaments = PreviousTournament.objects.filter(published=True).order_by('-date')
    return render(request, 'web/public_previous_tournaments.html', {
        'tournaments': tournaments
    })

def tournament_history_detail(request, tournament_id):
    """Public detail view for a published PreviousTournament"""
    tournament = get_object_or_404(PreviousTournament, id=tournament_id, published=True)
    teams = tournament.participating_teams.all().order_by('placement')
    scorecards = tournament.scorecards.all().order_by('match_number')
    
    # Extract unique organizations from the teams for the Org Grid
    organizations = set()
    for team in teams:
        if team.organization:
            organizations.add(team.organization)
            
    return render(request, 'web/tournament_history_detail.html', {
        'tournament': tournament,
        'teams': teams,
        'scorecards': scorecards,
        'organizations': list(organizations),
    })

# --- Registration Flow ---

def org_register_start(request):
    if request.session.get('organizer_id'):
        return redirect('organizer_dashboard')

    if request.method == 'POST':
        form = OrganizationEmailForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['organization_email']
            # Generate OTP
            otp = str(random.randint(100000, 999999))
            request.session['reg_email'] = email
            request.session['reg_otp'] = otp
            request.session['reg_otp_created_at'] = time.time()
            
            # Send OTP via Email
            # Send OTP via Email (HTML + Text)
            subject = 'E-Game Scout Registration OTP'
            html_content = render_to_string('web/emails/otp_verification.html', {'otp': otp, 'email': email, 'logo_url': request.build_absolute_uri('/static/web/images/logo.png')})
            text_content = strip_tags(html_content)
            
            msg = EmailMultiAlternatives(subject, text_content, settings.EMAIL_HOST_USER, [email])
            msg.attach_alternative(html_content, "text/html")
            msg.send()
            
            print(f"DEBUG: Registration OTP for {email}: {otp}") # Keep for dev backup
            
            messages.success(request, f'OTP sent to {email}')
            
            return redirect('org_register_otp')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
    else:
        form = OrganizationEmailForm()
    
    return render(request, 'web/Organization/org_register_start.html', {'form': form})

def org_register_otp(request):
    if request.session.get('organizer_id'):
        return redirect('organizer_dashboard')

    email = request.session.get('reg_email')
    if not email:
        return redirect('org_register_start')
        
    if request.method == 'POST':
        form = OTPForm(request.POST)
        if form.is_valid():
            otp = form.cleaned_data['otp']
            
            # Check Expiry
            created_at = request.session.get('reg_otp_created_at')
            if created_at and (time.time() - float(created_at) > 300):
                 messages.error(request, 'OTP Expired. Please register again.')
                 return redirect('org_register_start')

            if otp == request.session.get('reg_otp'):
                return redirect('org_register_details')
            else:
                messages.error(request, 'Invalid OTP')
    else:
        form = OTPForm()
    
    return render(request, 'web/Organization/org_register_otp.html', {'form': form, 'email': email})

def org_register_details(request):
    if request.session.get('organizer_id'):
        return redirect('organizer_dashboard')

    email = request.session.get('reg_email')
    if not email:
        return redirect('org_register_start')
        
    if request.method == 'POST':
        form = OrganizationDetailsForm(request.POST, request.FILES)
        if form.is_valid():
            org = form.save(commit=False)
            org.Organization_Email = email
            org.save()
            
            # Send congratulatory email
            try:
                subject = 'Welcome to E-Game Scout - Registration Successful!'
                html_content = render_to_string('web/emails/welcome.html', {
                    'user': {'username': org.Organization_Name},
                    'login_url': request.build_absolute_uri('/organization/login/'),
                    'logo_url': request.build_absolute_uri('/static/web/images/logo.png')
                })
                text_content = strip_tags(html_content)
                
                msg = EmailMultiAlternatives(subject, text_content, settings.EMAIL_HOST_USER, [email])
                msg.attach_alternative(html_content, "text/html")
                msg.send()
                
                print(f"DEBUG: Registration success email sent to {email}")
            except Exception as e:
                print(f"ERROR: Failed to send registration email: {e}")
            
            # Cleanup registration session
            if 'reg_email' in request.session:
                del request.session['reg_email']
            if 'reg_otp' in request.session:
                del request.session['reg_otp']
            
            # Show success message and redirect to login
            messages.success(request, f'🎉 Registration successful! Welcome to E-Game Scout, {org.Organization_Name}! A confirmation email has been sent to {email}. Please login to continue.')
            return redirect('org_login_start')
    else:
        form = OrganizationDetailsForm()
    
    return render(request, 'web/Organization/org_register_details.html', {'form': form})

# --- Login Flow ---

def org_login_start(request):
    if SystemSettings.get_settings().is_maintenance_mode:
        messages.error(request, SystemSettings.get_settings().maintenance_message)
        return redirect('index')

    if request.session.get('organizer_id'):
        return redirect('organizer_dashboard')

    if request.method == 'POST':
        form = OrganizationLoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['organization_email']
            try:
                org = Organization.objects.get(Organization_Email=email)
                
                if org.status == 'Suspended':
                    messages.error(request, 'Your account has been suspended. Please contact support.')
                    return redirect('org_login_start')

                # Generate OTP
                otp = str(random.randint(100000, 999999))
                request.session['login_email'] = email
                request.session['login_otp'] = otp
                request.session['login_otp_created_at'] = time.time()
                
                # Send OTP via Email
                # Send OTP via Email (HTML + Text)
                subject = 'E-Game Scout Login OTP'
                html_content = render_to_string('web/emails/otp_verification.html', {'otp': otp, 'email': email, 'logo_url': request.build_absolute_uri('/static/web/images/logo.png')})
                text_content = strip_tags(html_content)
                
                msg = EmailMultiAlternatives(subject, text_content, settings.EMAIL_HOST_USER, [email])
                msg.attach_alternative(html_content, "text/html")
                msg.send()
                
                print(f"DEBUG: Login OTP for {email}: {otp}") # Keep for dev backup
                
                messages.success(request, f'OTP sent to {email}')
                
                return redirect('org_login_otp')
            except Organization.DoesNotExist:
                messages.error(request, 'Email not found. Please register.')
    else:
        form = OrganizationEmailForm()
    
    return render(request, 'web/Organization/org_login_start.html', {'form': form})

def org_login_otp(request):
    email = request.session.get('login_email')
    if not email:
        return redirect('org_login_start')
        
    if request.method == 'POST':
        form = OTPForm(request.POST)
        if form.is_valid():
            otp = form.cleaned_data['otp']
            session_otp = request.session.get('login_otp')
            print(f"DEBUG: Login OTP Attempt. Input: '{otp}' (type: {type(otp)}), Session: '{session_otp}' (type: {type(session_otp)})")
            
            # Check Expiry
            created_at = request.session.get('login_otp_created_at')
            if created_at and (time.time() - float(created_at) > 300):
                 messages.error(request, 'OTP Expired. Please login again.')
                 return redirect('org_login_start')

            if str(otp).strip() == str(session_otp).strip():
                # Login Success
                # Clear conflicting sessions
                if request.user.is_authenticated: logout(request)
                if 'player_id' in request.session: del request.session['player_id']

                org = Organization.objects.get(Organization_Email=email)
                
                # Set generic session ID for Django to recognize
                if not request.session.session_key:
                    request.session.create()
                    
                request.session['organizer_id'] = org.id
                
                # Secure Tracking Login
                handle_secure_login(request, user_id=org.id, user_type='ORG')
                
                # Cleanup OTP session (Safe deletion)
                request.session.pop('login_email', None)
                request.session.pop('login_otp', None)
                
                return redirect('organizer_dashboard')
            else:
                messages.error(request, 'Invalid OTP')
    else:
        form = OTPForm()
    
    
    return render(request, 'web/Organization/org_login_otp.html', {'form': form, 'email': email})

def update_tournament_statuses(org):
    """Refreshes tournament statuses based on current time."""
    now = timezone.now()
    
    # 1. Update to 'Ongoing': Start Date passed AND End Date in future/now
    Tournament.objects.filter(
        Organization_Name=org,
        start_date__lte=now,
        end_date__gt=now
    ).exclude(Status__in=['Ongoing', 'Completed', 'Cancelled']).update(Status='Ongoing')
    
    # 2. Update to 'Completed': End Date passed
    Tournament.objects.filter(
        Organization_Name=org,
        end_date__lte=now
    ).exclude(Status__in=['Completed', 'Cancelled']).update(Status='Completed')
    
    # 3. Optional: Revert to 'Scheduled' if dates pushed back? 
    # Important: Do NOT revert if manually marked as Completed early.
    Tournament.objects.filter(
        Organization_Name=org,
        start_date__gt=now
    ).exclude(Status__in=['Scheduled', 'Completed', 'Cancelled']).update(Status='Scheduled')

@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required_organization
def organizer_dashboard(request):
    org_id = request.session.get('organizer_id')
        
    org = get_object_or_404(Organization, id=org_id)
    
    # Verify/Update tournament statuses first
    update_tournament_statuses(org)
    
    # --- Player Setup Popup Logic ---
    from .models import OrganizationPlayer
    import datetime
    
    show_player_setup_popup = False
    
    # Check if they have ever seen the initial popup
    if not org.has_seen_player_setup_popup:
        show_player_setup_popup = True
    else:
        # If they've seen it, check if they actually have players
        org_player_count = OrganizationPlayer.objects.filter(organization=org).count()
        if org_player_count == 0:
            # Check weekly reminder
            now_date = timezone.now().date()
            if not org.last_player_reminder_date or (now_date - org.last_player_reminder_date).days >= 7:
                show_player_setup_popup = True
                
    # --- Stats ---
    total_players = OrganizationPlayer.objects.filter(organization=org).count()
    active_tournaments = Tournament.objects.filter(Organization_Name=org, Status='Ongoing').count()
    
    # --- Notifications Logic ---
    
    # Fetch real notifications
    db_notifications = OrganizationNotification.objects.filter(recipient=org).order_by('-created_at')[:10]
    
    notifications = []
    
    # Convert DB objects to dict for template compatibility (or update template to use object)
    # Let's keep a consistent structure for now, but include ID for actions
    for n in db_notifications:
        notifications.append({
            'id': n.id,
            'type': n.notification_type, # 'BIDDING_INVITE' or 'INFO'
            'message': n.message,
            'time': n.created_at,
            'link': '#', # Placeholder
            'is_invite': n.notification_type == 'BIDDING_INVITE',
            'related_tournament_id': n.related_tournament.Tournament_ID if n.related_tournament else None
        })
    
    # --- Analytics: Player Growth (Last 6 Months) ---
    import datetime
    
    six_months_ago = timezone.now() - datetime.timedelta(days=180)
    
    # Get counts per month (Do in Python to avoid SQLite timezone issues)
    players = Player.objects.filter(
        organization=org, 
        created_at__gte=six_months_ago
    ).values_list('created_at', flat=True)

    data_map = {}
    for p_date in players:
        # Convert to local time if needed, or just use UTC
        # For simplicity and stability, use the datetime object directly
        month_str = p_date.strftime('%Y-%m')
        data_map[month_str] = data_map.get(month_str, 0) + 1
    
    # Format for Chart.js
    analytics_labels = []
    analytics_data = []
    
    # Pre-fill last 6 months to ensure continuous line even if 0
    current = six_months_ago
    end = timezone.now()
    
    while current <= end:
        month_str = current.strftime('%Y-%m')
        month_label = current.strftime('%b')
        analytics_labels.append(month_label)
        analytics_data.append(data_map.get(month_str, 0))
        
        # Increment month
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)
            
    # --- Recent Recruits ---
    recent_recruits = Player.objects.filter(organization=org).order_by('-created_at')[:5]
    
    print(f"DEBUG: Analytics Data: {analytics_data}")

    return render(request, 'web/Organization/organizer_dashboard.html', {
        'org': org,
        'total_players': total_players,
        'show_player_setup_popup': show_player_setup_popup,
        'active_tournaments': active_tournaments,
        'notifications': notifications,
        'notifications_count': len(notifications),
        'analytics_labels': analytics_labels,
        'analytics_data': analytics_data,
        'recent_recruits': recent_recruits
    })

@csrf_exempt
@login_required_organization
def dismiss_player_setup_popup(request):
    """AJAX endpoint to record that the org has dismissed the player setup popup"""
    if request.method == 'POST':
        org_id = request.session.get('organizer_id')
        if org_id:
            try:
                org = Organization.objects.get(id=org_id)
                org.has_seen_player_setup_popup = True
                org.last_player_reminder_date = timezone.now().date()
                org.save()
                return JsonResponse({"status": "success"})
            except Organization.DoesNotExist:
                return JsonResponse({"status": "error", "message": "Organization not found"}, status=404)
    return JsonResponse({"status": "error", "message": "Invalid request"}, status=400)

def resend_otp(request):
    if request.method == 'POST':
        # Check for Org Reg, Org Login, or Player Login
        email = request.session.get('reg_email') or request.session.get('login_email') or request.session.get('auth_email')
        
        if not email:
            return JsonResponse({'success': False, 'message': 'Session expired. Please restart.'})
            
        # Generate new OTP
        otp = str(random.randint(100000, 999999))
        
        # Update session (determine which one to update)
        if request.session.get('reg_email'):
            request.session['reg_otp'] = otp
            request.session['reg_otp_created_at'] = time.time()
        elif request.session.get('login_email'):
            request.session['login_otp'] = otp
            request.session['login_otp_created_at'] = time.time()
        elif request.session.get('auth_email'):
            request.session['auth_otp'] = otp
            request.session['auth_otp_created_at'] = time.time()
            
        # Send OTP via Email
        subject = 'E-Game Scout OTP Resend'
        html_content = render_to_string('web/emails/otp_verification.html', {'otp': otp, 'email': email, 'logo_url': request.build_absolute_uri('/static/web/images/logo.png')})
        text_content = strip_tags(html_content)
        
        msg = EmailMultiAlternatives(subject, text_content, settings.EMAIL_HOST_USER, [email])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        
        print(f"DEBUG: Resend OTP for {email}: {otp}")
        
        return JsonResponse({'success': True, 'message': 'OTP sent successfully'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})

# --- Scorecard AI Tool ---
import base64
import requests as _requests_module
from web.models import ScorecardAnalysis

@login_required_organization
def scorecard_tool(request):
    org_id = request.session.get('organizer_id')
        
    org = get_object_or_404(Organization, id=org_id)
    
    if request.method == 'POST':
        if 'scorecard_image' not in request.FILES:
            messages.error(request, 'No image uploaded.')
            return redirect('scorecard_tool')
            
        image_file = request.FILES['scorecard_image']
        
        # 1. Create initial record
        analysis = ScorecardAnalysis.objects.create(
            organization=org,
            image=image_file,
            ai_provider='pending',
            summary_text='Analyzing...'
        )
        
        try:
            # Prepare Prompt
            user_prompt = """
            Act as a professional esports journalist and data analyst. Analyze the provided standings image from a BGMI tournament. 
            Extract the data and write a detailed, narrative-style report.

            You MUST return a pure JSON object (no markdown formatting, no backticks, just the raw JSON string) with the following structure:
            {
                "tournament_name": "Extracted Name or 'Unknown Tournament'",
                "winner_team": "Name of Rank 1 Team",
                "runner_up_team": "Name of Rank 2 Team",
                "teams": [
                    {
                        "rank": 1,
                        "team_name": "Team A",
                        "points": 150
                    }
                ],
                "analysis_report": "Your detailed narrative report explaining how the leaderboard unfolded, highlighting the championship-winning team’s consistency, the close title race among the top teams, mid-table performances, and struggles of the lower-ranked teams, using only the visible data. Convert statistics into match-like insights, avoid inventing players or events, and conclude with an overall verdict on the competitiveness.",
                "match_number": 1
            }
            """
            
            # Providers Config - Multiple Gemini keys with Groq fallback
            providers = []
            
            # Add all Gemini API keys
            if hasattr(settings, 'GEMINI_API_KEYS') and settings.GEMINI_API_KEYS:
                for i, key in enumerate(settings.GEMINI_API_KEYS):
                    providers.append({"type": "gemini", "key": key, "index": i+1})
            elif settings.GEMINI_API_KEY:
                # Fallback for single key
                providers.append({"type": "gemini", "key": settings.GEMINI_API_KEY, "index": 1})
            
            # Add Groq as final fallback
            if settings.GROQ_API_KEY:
                providers.append({"type": "groq", "key": settings.GROQ_API_KEY})
                
            if not providers:
                analysis.summary_text = "Error: No API keys configured. Please contact admin."
                analysis.ai_provider = 'failed'
                analysis.save()
                messages.error(request, 'AI Configuration Missing.')
                return redirect('scorecard_tool')

            response_text = None
            used_provider = None
            
            # File path for AI reading
            file_path = analysis.image.path

            # AI Logic Loop - Try each provider in order
            for provider in providers:
                try:
                    if provider['type'] == 'gemini':
                        from google import genai
                        key_index = provider.get('index', 1)
                        print(f"DEBUG: Attempting Gemini API Key #{key_index}...")
                        client = genai.Client(api_key=provider['key'])
                        
                        # Upload file and generate content
                        uploaded_file = client.files.upload(file_path)
                        
                        response = client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=[user_prompt, uploaded_file]
                        )
                        response_text = response.text
                        used_provider = f'gemini_key_{key_index}'
                        print(f"SUCCESS: Gemini API Key #{key_index} worked!")
                        
                    elif provider['type'] == 'groq':
                        import os
                        file_extension = os.path.splitext(file_path)[1].lower()
                        mime_type = 'image/jpeg'
                        if file_extension == '.png':
                            mime_type = 'image/png'
                        elif file_extension == '.webp':
                            mime_type = 'image/webp'
                        
                        with open(file_path, "rb") as f:
                            encoded_string = base64.b64encode(f.read()).decode('utf-8')
                        
                        headers = {
                            "Authorization": f"Bearer {provider['key']}",
                            "Content-Type": "application/json"
                        }
                        payload = {
                            "messages": [
                                {
                                    "role": "user",
                                    "content": [
                                        {"type": "text", "text": user_prompt},
                                        {
                                            "type": "image_url",
                                            "image_url": {
                                                "url": f"data:{mime_type};base64,{encoded_string}",
                                            },
                                        },
                                    ],
                                }
                            ],
                            "model": "meta-llama/llama-4-scout-17b-16e-instruct",
                        }
                        import requests
                        groq_resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=60)
                        groq_resp.raise_for_status()
                        response_text = groq_resp.json()["choices"][0]["message"]["content"]
                        used_provider = 'groq'

                    if response_text:
                        break
                        
                except Exception as e:
                    provider_name = provider['type']
                    if provider['type'] == 'gemini':
                        provider_name = f"Gemini Key #{provider.get('index', 1)}"
                    print(f"AI Provider {provider_name} Error: {e}")
                    continue
            
            if response_text:
                # Clean up response text if the model returned markdown
                cleaned_text = response_text.strip()
                if cleaned_text.startswith("```json"):
                    cleaned_text = cleaned_text[7:]
                if cleaned_text.endswith("```"):
                    cleaned_text = cleaned_text[:-3]
                
                try:
                    data = json.loads(cleaned_text.strip())
                    
                    analysis.summary_text = data.get("analysis_report", "Analysis generated successfully.")
                    analysis.ai_provider = used_provider
                    analysis.save()
                    
                    # Store in Previous Tournament History
                    pt_name = data.get("tournament_name", "Unknown Tournament")
                    
                    # Create or Get the overall Tournament Record
                    prev_tournament, created = PreviousTournament.objects.get_or_create(
                        tournament_name=pt_name,
                        organization=org,
                        defaults={
                            'winner_team': data.get("winner_team", ""),
                            'runner_up_team': data.get("runner_up_team", ""),
                            'description': data.get("analysis_report", "")[:200] + "...",
                            'published': False
                        }
                    )
                    
                    # Save Match Scorecard
                    match_data_json = {
                        "teams": data.get("teams", [])
                    }
                    TournamentScorecard.objects.create(
                        tournament=prev_tournament,
                        match_number=data.get("match_number", 1),
                        match_data=match_data_json,
                        ai_analysis=data.get("analysis_report", "")
                    )
                    
                    # If this is a newly created tournament, add the teams
                    if created:
                        for team_data in data.get("teams", []):
                            TournamentTeam.objects.create(
                                tournament=prev_tournament,
                                team_name=team_data.get("team_name", "Unknown"),
                                placement=team_data.get("rank", 99),
                                points=team_data.get("points", 0)
                            )
                            
                    messages.success(request, 'Analysis Complete and added to Tournament History Workflow!')

                except json.JSONDecodeError as e:
                    print(f"JSON Parse Error: {e} - Raw output: {response_text}")
                    analysis.summary_text = "Analysis succeeded but format was invalid. Saved raw output:\n\n" + response_text
                    analysis.ai_provider = used_provider
                    analysis.save()
                    messages.warning(request, 'Analysis complete, but data formatting failed.')

            else:
                analysis.summary_text = "Analysis failed. Please try again later."
                analysis.ai_provider = 'failed'
                analysis.save()
                messages.error(request, 'AI Analysis Failed.')

        except Exception as e:
            print(f"Critical Error: {e}")
            messages.error(request, f"System Error: {e}")
            
        return redirect('scorecard_tool')

    # GET Request: Show history
    history = ScorecardAnalysis.objects.filter(organization=org).order_by('-created_at')
    
    # Get unpublished tournaments that can be reviewed and published
    unpublished_tournaments = PreviousTournament.objects.filter(
        organization=org, 
        published=False
    ).order_by('-date')
    
    return render(request, 'web/Organization/org_scorecard_tool.html', {
        'org': org, 
        'history': history,
        'unpublished_tournaments': unpublished_tournaments
    })

# --- Profile Management ---

@login_required_organization
def manage_profile(request):
    """Display the manage profile page"""
    org_id = request.session.get('organizer_id')
    
    org = get_object_or_404(Organization, id=org_id)
    return render(request, 'web/Organization/org_manage_profile.html', {'org': org})

@login_required_organization
def update_profile(request):
    """Update organization profile information"""
    org_id = request.session.get('organizer_id')
    
    org = get_object_or_404(Organization, id=org_id)
    
    if request.method == 'POST':
        org.Organization_Name = request.POST.get('organization_name', org.Organization_Name)
        org.Organization_UserName = request.POST.get('organization_username', org.Organization_UserName)
        org.Organization_Contact = request.POST.get('organization_contact', org.Organization_Contact)
        org.instagram_username = request.POST.get('instagram_username', '')
        org.instagram_link = request.POST.get('instagram_link', '')
        org.save()
        
        messages.success(request, 'Profile updated successfully!')
        return redirect('manage_profile')
    
    return redirect('manage_profile')

@login_required_organization
def update_profile_photo(request):
    """Update organization profile photo"""
    org_id = request.session.get('organizer_id')
    
    org = get_object_or_404(Organization, id=org_id)
    
    if request.method == 'POST' and request.FILES.get('profile_photo'):
        org.profile_photo = request.FILES['profile_photo']
        org.save()
        messages.success(request, 'Profile photo updated successfully!')
    return redirect('manage_profile')

@login_required_organization
def org_delete_account(request):
    org_id = request.session.get('organizer_id')
        
    if request.method == 'POST':
        org = get_object_or_404(Organization, id=org_id)
        org.delete()
        request.session.flush()
        messages.success(request, 'Organization account deleted successfully.')
        return redirect('index')
        
    return render(request, 'web/Organization/org_delete_confirm.html')
    
    return redirect('manage_profile')

# --- Tournament Management ---

@login_required_organization
def tournament_list(request):
    """Display list of tournaments for the organization"""
    org_id = request.session.get('organizer_id')
    
    org = get_object_or_404(Organization, id=org_id)
    
    # Verify/Update tournament statuses first
    update_tournament_statuses(org)
    
    # Logic for Completed Tournaments
    # Active: now < end_date
    # Completed: now >= end_date
    
    from datetime import timedelta
    
    # Get current local time
    now = timezone.now()
    
    # Completed = (Status='Completed') OR (end_date <= now)
    q_hidden = Q(Status='Completed') | Q(end_date__lte=now)
    
    # Filter Active Tournaments (Exclude only old completed ones)
    tournaments = Tournament.objects.filter(
        Organization_Name=org, 
        is_archived=False
    ).exclude(q_hidden).order_by('start_date').distinct()
    
    form = TournamentForm()

    # Count other organizations for bidding cost calculation
    total_org_count = Organization.objects.exclude(id=org_id).count()
    
    return render(request, 'web/Organization/org_tournament_list.html', {
        'org': org, 
        'tournaments': tournaments,
        'form': form,
        'show_form': False,
        'total_org_count': total_org_count
    })

@login_required_organization
def publish_previous_tournament(request, history_id):
    """Toggle the published state of a PreviousTournament"""
    if request.method == 'POST':
        pt = get_object_or_404(PreviousTournament, id=history_id)
        pt.published = not pt.published
        pt.save()
        status = "published" if pt.published else "unpublished"
        messages.success(request, f'Tournament history successfully {status}.')
        
    # Redirect back to the scorecard tool page (or wherever the button is placed)
    # The user request asks for it to be connected with AI Scorecard Generator, so we'll 
    # assume they meant that page or the tournament history list. We will redirect to scorecard_tool.
    return redirect('scorecard_tool')

@login_required_organization
def tournament_history(request):
    """Display list of completed tournaments for the organization"""
    org_id = request.session.get('organizer_id')
    
    org = get_object_or_404(Organization, id=org_id)
    
    
    # Ensure statuses are accurate
    update_tournament_statuses(org)
    
    # Logic for Completed Tournaments (Same as above)
    now = timezone.now()
    
    print(f"DEBUG HISTORY: Now={now}")
    
    # Completed = (Status='Completed') OR (end_date <= now)
    q_completed = Q(Status='Completed') | Q(end_date__lte=now)
    
    completed_tournaments = Tournament.objects.filter(
        Organization_Name=org,
        is_archived=False
    ).filter(q_completed).distinct().order_by('-end_date')
    
    print(f"DEBUG HISTORY: Found {completed_tournaments.count()} completed tournaments")
    for t in completed_tournaments:
        print(f"DEBUG HISTORY: - {t.Name} (End: {t.end_date}, Status: {t.Status})")

    return render(request, 'web/Organization/org_tournament_history.html', {
        'org': org, 
        'tournaments': completed_tournaments
    })

from django.db import models

@login_required_organization
def org_transaction_history(request):
    """Display coin transaction history for the organization."""
    org_id = request.session.get('organizer_id')
    org = get_object_or_404(Organization, id=org_id)

    transactions = Transaction.objects.filter(
        models.Q(sender=org) | models.Q(recipient=org)
    ).select_related('related_tournament').order_by('-timestamp')

    return render(request, 'web/Organization/org_transaction_history.html', {
        'org': org,
        'transactions': transactions,
        'notifications': [],
        'notifications_count': 0,
    })

@login_required_organization
def tournament_create(request):
    """Create a new tournament"""
    org_id = request.session.get('organizer_id')
    
    org = get_object_or_404(Organization, id=org_id)
    
    if request.method == 'POST':
        form = TournamentForm(request.POST)
        if form.is_valid():
            tournament = form.save(commit=False)
            tournament.Organization_Name = org
            tournament.save()
            messages.success(request, f'Tournament "{tournament.Name}" created successfully!')
            return redirect('tournament_list')
        else:
            messages.error(request, "Please correct the errors below.")
            return render(request, 'web/Organization/org_tournament_form.html', {
                'org': org,
                'form': form,
                'action': 'Create'
            })
    
    # GET Request
    form = TournamentForm()
    return render(request, 'web/Organization/org_tournament_form.html', {
        'org': org,
        'form': form,
        'action': 'Create'
    })

@login_required_organization
def tournament_update(request, tournament_id):
    """Update an existing tournament"""
    org_id = request.session.get('organizer_id')
    
    org = get_object_or_404(Organization, id=org_id)
    tournament = get_object_or_404(Tournament, Tournament_ID=tournament_id, Organization_Name=org)
    
    if request.method == 'POST':
        form = TournamentForm(request.POST, instance=tournament)
        if form.is_valid():
            form.save()
            messages.success(request, f'Tournament "{tournament.Name}" updated successfully!')
            return redirect('tournament_list')
    else:
        form = TournamentForm(instance=tournament)
    
    return render(request, 'web/Organization/org_tournament_form.html', {'org': org, 'form': form, 'action': 'Update', 'tournament': tournament})

@login_required_organization
def tournament_detail(request, tournament_id):
    """Display full details of a specific tournament"""
    org_id = request.session.get('organizer_id')
    
    org = get_object_or_404(Organization, id=org_id)
    
    # Allow access if: Owner OR Bidder OR Published
    tournament = get_object_or_404(Tournament, 
        Q(Tournament_ID=tournament_id) & 
        (Q(Organization_Name=org) | Q(bidders__organization=org) | Q(is_published=True))
    )
    
    return render(request, 'web/Organization/org_tournament_detail.html', {
        'org': org, 
        'tournament': tournament,
        'is_owner': tournament.Organization_Name == org,
        'is_participant': tournament.bidders.filter(organization=org).exists(),
        'source': request.GET.get('source')
    })

@login_required_organization
def cancel_tournament(request, tournament_id):
    """Cancel a tournament and notify the organization."""
    if request.method != 'POST':
        return redirect('tournament_list')
        
    org_id = request.session.get('organizer_id')
    org = get_object_or_404(Organization, id=org_id)
    tournament = get_object_or_404(Tournament, Tournament_ID=tournament_id, Organization_Name=org)
    
    # Check if already cancelled or completed
    if tournament.Status in ['Cancelled', 'Completed']:
        messages.error(request, "This tournament cannot be cancelled.")
        return redirect('tournament_list')
    
    # Update Status
    tournament.Status = 'Cancelled'
    tournament.save()
    
    # Create Notification
    message = f"Tournament '{tournament.Name}' has been cancelled."
    OrganizationNotification.objects.create(
        recipient=org,
        message=message,
        notification_type='INFO',
        related_tournament=tournament
    )
    
    # Send Email
    
    subject = f"Tournament Cancelled: {tournament.Name}"
    email_message = f"""
    Hello {org.Organization_Name},
    
    Your tournament '{tournament.Name}' has been successfully cancelled.
    
    If this was a mistake, please contact support.
    
    Regards,
    E-Game Scout Team
    """
    
    try:
        send_mail(
            subject,
            email_message,
            settings.DEFAULT_FROM_EMAIL,
            [org.Organization_Email],
            fail_silently=True,
        )
    except Exception as e:
        print(f"Failed to send email: {e}")
        
    messages.success(request, "Tournament cancelled successfully.")
    return redirect('tournament_list')

@login_required_organization
def tournament_delete(request, tournament_id):
    """Delete a tournament"""
    org_id = request.session.get('organizer_id')
    
    org = get_object_or_404(Organization, id=org_id)
    tournament = get_object_or_404(Tournament, Tournament_ID=tournament_id, Organization_Name=org)
    
    if request.method == 'POST':
        tournament_name = tournament.Name
        # Soft delete: archive instead of hard delete
        tournament.is_archived = True
        tournament.save()
        messages.success(request, f'Tournament "{tournament_name}" archived successfully!')
        return redirect('tournament_list')
    
    # If not POST, just redirect back to list (or show error, but redirection is cleaner for "action" URLs)
    messages.error(request, "Invalid request method for deletion.")
    return redirect('tournament_list')

@login_required_organization
def tournament_participants(request, tournament_id):
    """View to list participants (organizations) of a tournament"""
    print(f"DEBUG: tournament_participants called for ID {tournament_id}")
    print(f"DEBUG: Session keys: {request.session.keys()}")
    print(f"DEBUG: organizer_id in session: {request.session.get('organizer_id')}")
    
    org_id = request.session.get('organizer_id')
    if not org_id:
        print("DEBUG: No org_id, redirecting to login")
        return redirect('org_login_start')
    
    org = get_object_or_404(Organization, id=org_id)
    tournament = get_object_or_404(Tournament, Tournament_ID=tournament_id, Organization_Name=org)
    
    # Fetch Bidders (Participants)
    # Note: 'bidders' related_name on TournamentBidder model refers to the relation from Tournament to TournamentBidder
    bidders = tournament.bidders.all().select_related('organization').order_by('joined_at')
    
    return render(request, 'web/Organization/org_tournament_participants.html', {
        'org': org,
        'tournament': tournament,
        'bidders': bidders
    })

@login_required_organization
def my_players(request):
    """Display list of players recruited by the organization"""
    org_id = request.session.get('organizer_id')
    
    org = get_object_or_404(Organization, id=org_id)
    from .models import OrganizationPlayer, ExternalPlayerInvite
    from django.utils import timezone
    org_players = OrganizationPlayer.objects.filter(organization=org).order_by('-created_at')
    # Pending invites (not yet accepted and not expired)
    pending_invites = ExternalPlayerInvite.objects.filter(
        organization=org, status='PENDING', expires_at__gt=timezone.now()
    ).order_by('-created_at')
    
    return render(request, 'web/Organization/org_my_players.html', {
        'org': org, 'players': org_players, 'pending_invites': pending_invites
    })


@login_required_organization
def org_add_player(request):
    """View to handle adding a player to the organization's roster.
    - If player is REGISTERED in our system → error, they can only be added via Bidding.
    - If player is NOT registered → send an email invite to verify and add to organization's external roster.
    """
    org_id = request.session.get('organizer_id')
    org = get_object_or_404(Organization, id=org_id)
    from .forms import AddPlayerForm
    from .models import OrganizationPlayer, ExternalPlayerInvite
    
    if request.method == 'POST':
        form = AddPlayerForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            game_id = form.cleaned_data['game_id']
            name = form.cleaned_data.get('name', '').strip()
            
            # Check if player is registered in the system
            registered_player = Player.objects.filter(email__iexact=email).first()
            
            if registered_player:
                # Registered players can ONLY be added via Bidding
                messages.error(
                    request,
                    f'"{registered_player.full_name}" is a registered player on E-GameScout. '
                    f'To add registered players to your team, please use the Bidding System.'
                )
            else:
                # Player not in our system — proceed with email verification invite
                if not name:
                    messages.warning(request, 'Please enter the player\'s full name to send them an invitation.')
                else:
                    # Check if there's already a pending invite for this org+email
                    existing = ExternalPlayerInvite.objects.filter(
                        organization=org, email__iexact=email, status='PENDING'
                    ).first()
                    
                    if existing and not existing.is_expired:
                        messages.warning(request, f'An invitation has already been sent to {email}. Please ask the player to check their inbox.')
                    else:
                        # Mark old expired invites as expired
                        ExternalPlayerInvite.objects.filter(
                            organization=org, email__iexact=email
                        ).update(status='EXPIRED')
                        
                        # Create new invite
                        invite = ExternalPlayerInvite.objects.create(
                            organization=org,
                            name=name,
                            email=email,
                            game_id=game_id
                        )
                        
                        # Build verification link
                        invite_url = request.build_absolute_uri(f'/organization/player/accept-invite/{invite.token}/')
                        
                        # Send verification email
                        try:
                            from django.core.mail import send_mail
                            from django.template.loader import render_to_string
                            html_message = render_to_string('web/emails/player_invite.html', {
                                'org': org,
                                'invite': invite,
                                'invite_url': invite_url,
                            })
                            send_mail(
                                subject=f'[E-GameScout] {org.Organization_Name} wants you on their team!',
                                message=f'You have been invited to join {org.Organization_Name} on E-GameScout. Click here to accept: {invite_url}',
                                from_email=None,
                                recipient_list=[email],
                                html_message=html_message,
                                fail_silently=False
                            )
                            messages.success(request, f'Invitation sent to {email}! The player must accept within 3 days.')
                        except Exception as e:
                            invite.delete()
                            messages.error(request, f'Failed to send invite email: {str(e)}')
                        return redirect('my_players')
    else:
        form = AddPlayerForm()
        
    return render(request, 'web/Organization/org_add_player.html', {'org': org, 'form': form})


def accept_player_invite(request, token):
    """Public view — player clicks invite link from email to join the organization's external roster."""
    from .models import ExternalPlayerInvite, OrganizationPlayer
    
    try:
        invite = ExternalPlayerInvite.objects.get(token=token)
    except ExternalPlayerInvite.DoesNotExist:
        return render(request, 'web/Organization/invite_result.html', {
            'success': False, 'message': 'Invalid invitation link. It may have already been used or does not exist.'
        })
    
    if invite.status == 'ACCEPTED':
        return render(request, 'web/Organization/invite_result.html', {
            'success': False, 'message': 'This invitation has already been accepted.',
            'org': invite.organization
        })
    
    if invite.is_expired or invite.status == 'EXPIRED':
        invite.status = 'EXPIRED'
        invite.save()
        return render(request, 'web/Organization/invite_result.html', {
            'success': False, 'message': 'This invitation has expired. Please ask the organization to send a new invite.'
        })
    
    # Accept: create OrganizationPlayer as external verified
    OrganizationPlayer.objects.get_or_create(
        organization=invite.organization,
        email=invite.email,
        game_id=invite.game_id,
        defaults={
            'player': None,
            'name': invite.name,
            'status_label': 'External (Verified)'
        }
    )
    
    invite.status = 'ACCEPTED'
    invite.save()
    
    # Send registration prompt email to the player
    try:
        from django.core.mail import send_mail
        from django.template.loader import render_to_string
        register_url = request.build_absolute_uri('/player/register/')
        reg_html = render_to_string('web/emails/player_registration_prompt.html', {
            'org': invite.organization,
            'invite': invite,
            'register_url': register_url,
        })
        send_mail(
            subject=f'You joined {invite.organization.Organization_Name} — Complete your E-GameScout registration',
            message=f'Welcome! Register at {register_url} to unlock full platform features.',
            from_email=None,
            recipient_list=[invite.email],
            html_message=reg_html,
            fail_silently=True  # Don't block the success page if this fails
        )
    except Exception:
        pass  # Registration email is best-effort only
    
    return render(request, 'web/Organization/invite_result.html', {
        'success': True,
        'message': f'You have successfully joined {invite.organization.Organization_Name} as an External Player!',
        'org': invite.organization
    })



@login_required_organization
def org_view_player_profile(request, player_id):
    """Organization views a player's profile"""
    org_id = request.session.get('organizer_id')
    org = get_object_or_404(Organization, id=org_id)
    from .models import OrganizationPlayer
    # player_id passed from URL corresponds to OrganizationPlayer ID now for orgs or Player ID?
    # Context suggests we want to look at the link or the actual player info
    org_player_link = get_object_or_404(OrganizationPlayer, id=player_id, organization=org)
    player = org_player_link.player
    
    return render(request, 'web/Organization/org_player_profile.html', {'org': org, 'player': player, 'org_player_link': org_player_link})

@login_required_organization
def org_remove_player(request, player_id):
    """Remove a player from the organization's roster"""
    org_id = request.session.get('organizer_id')
    org = get_object_or_404(Organization, id=org_id)
    from .models import OrganizationPlayer
    org_player_link = get_object_or_404(OrganizationPlayer, id=player_id, organization=org)
    
    if request.method == "POST":
        org_player_link.delete()
        messages.success(request, f"{org_player_link.name} has been removed from your roster.")
        
    return redirect('my_players')

def custom_error_view(request, exception=None, status_code=500):
    """Generic error view for all HTTP status codes"""
    error_messages = {
        404: "Page Not Found",
        500: "Internal Server Error",
        403: "Access Forbidden",
        400: "Bad Request"
    }
    
    # If using Django's default handlers, standard function signature is used.
    # We allow flexible usage.
    
    message = error_messages.get(status_code, "System Error")
    
    return render(request, 'web/error.html', {
        'status_code': status_code,
        'message': message
    }, status=status_code)

# Specific Handlers to match Django's expected signature
def handler404(request, exception):
    return custom_error_view(request, exception=exception, status_code=404)

def handler500(request):
    return custom_error_view(request, status_code=500)

def handler403(request, exception):
    return custom_error_view(request, exception=exception, status_code=403)

def handler400(request, exception):
    return custom_error_view(request, exception=exception, status_code=400)

# --- Tournament Management ---

def publish_tournament(request, tournament_id):
    """Publish a tournament (or submit for admin approval first)"""
    org_id = request.session.get('organizer_id')
    if not org_id:
        return redirect('org_login_start')
        
    tournament = get_object_or_404(Tournament, Tournament_ID=tournament_id, Organization_Name_id=org_id)
    org = get_object_or_404(Organization, id=org_id)
    
    if request.method == 'POST':
        # 1. Block unverified orgs from publishing
        if not org.is_verified:
            messages.error(request, "Only verified organizations can publish tournaments to the platform.")
            return redirect('tournament_detail', tournament_id=tournament.Tournament_ID)

        # 2. If DRAFT or REJECTED -> Submit for Approval
        if tournament.approval_status in ['DRAFT', 'REJECTED']:
            tournament.approval_status = 'PENDING'
            tournament.save()
            
            # Notify Admin
            from .models import AdminNotification
            AdminNotification.objects.create(
                message=f"New tournament '{tournament.Name}' submitted for approval by {org.Organization_Name}.",
                notification_type='TOURNAMENT',
                link='/admin/tournament/approvals/'
            )
            
            messages.success(request, f"Tournament '{tournament.Name}' has been submitted for admin approval.")
            return redirect('tournament_detail', tournament_id=tournament.Tournament_ID)

        # 3. If APPROVED -> Actually publish -> send notifications
        if tournament.approval_status == 'APPROVED' and not tournament.is_published:
            tournament.is_published = True
            tournament.save()
            
            # Send Invites to all Active Organizations
            other_orgs = Organization.objects.filter(status='Active').exclude(id=org_id)
            
            org_notifications = []
            for other in other_orgs:
                org_notifications.append(OrganizationNotification(
                    recipient=other,
                    message=f"{org.Organization_Name} invites you to participate in '{tournament.Name}'",
                    notification_type='GENERAL',
                    related_tournament=tournament,
                    link=f"/organization/tournaments/upcoming/"
                ))
        
            if org_notifications:
                OrganizationNotification.objects.bulk_create(org_notifications)
                
            # Send Notifications to all Active Players
            active_players = Player.objects.filter(status='ACTIVE', is_archived=False)
            player_notifications = []
            for p in active_players:
                player_notifications.append(PlayerNotification(
                    recipient=p,
                    message=f"New Tournament '{tournament.Name}' has been published by {org.Organization_Name}!",
                notification_type='GENERAL',
                link=f"/player/tournaments/upcoming/"
            ))
            
        if player_notifications:
            PlayerNotification.objects.bulk_create(player_notifications)
        
        messages.success(request, f"Tournament published! Sent invites to {len(org_notifications)} organizations and {len(player_notifications)} players.")
        return redirect('tournament_list')
        
    return redirect('tournament_list')

def org_upcoming_tournaments(request):
    """View for organizations to see upcoming published tournaments"""
    org_id = request.session.get('organizer_id')
    if not org_id:
        return redirect('org_login_start')
        
    org = get_object_or_404(Organization, id=org_id)
    
    # Published upcoming tournaments
    tournaments = Tournament.objects.filter(
        Status__in=['Scheduled', 'Ongoing'],
        is_published=True,
        is_archived=False
    ).order_by('start_date')

    # Coming soon - unpublished tournaments
    coming_soon = Tournament.objects.filter(
        is_published=False,
        is_archived=False
    ).order_by('start_date')

    # Bidding system removed - no joined_tournament_ids
    # Actual implementation: Get participated tournaments from TournamentBidder (this model maps Org/Player to Tournament)
    from .models import TournamentBidder
    joined_tournament_ids = list(TournamentBidder.objects.filter(organization=org).values_list('tournament_id', flat=True))
    
    return render(request, 'web/Organization/org_upcoming_list.html', {
        'tournaments': tournaments,
        'coming_soon': coming_soon,
        'org': org,
        'joined_tournament_ids': joined_tournament_ids
    })

@login_required_organization
def org_join_tournament(request, tournament_id):
    """View indicating intent to participate in a tournament"""
    org_id = request.session.get('organizer_id')
    org = get_object_or_404(Organization, id=org_id)
    tournament = get_object_or_404(Tournament, Tournament_ID=tournament_id)
    
    # Check if they have at least 5 players in the roster
    from .models import OrganizationPlayer, TournamentBidder
    players = OrganizationPlayer.objects.filter(organization=org)
    if players.count() < 5:
        messages.error(request, f'You need at least 5 players in your roster to participate in {tournament.Name}. Please add players first.')
        return redirect('org_add_player')
    
    if request.method == 'POST':
        # Form submitted with selected players
        selected_player_ids = request.POST.getlist('players')
        
        if len(selected_player_ids) < 5:
            messages.error(request, 'You must select exactly 5 players to participate.')
            return redirect('org_join_tournament', tournament_id=tournament.Tournament_ID)
            
        if len(selected_player_ids) > 5:
            messages.error(request, 'You can only select exactly 5 players to participate.')
            return redirect('org_join_tournament', tournament_id=tournament.Tournament_ID)
            
        # Verify all selected players belong to the org
        selected_players = OrganizationPlayer.objects.filter(id__in=selected_player_ids, organization=org)
        if selected_players.count() != 5:
            messages.error(request, 'Invalid players selected.')
            return redirect('org_join_tournament', tournament_id=tournament.Tournament_ID)
        
        # Add them to the tournament participation list
        bidder, created = TournamentBidder.objects.get_or_create(
            tournament=tournament,
            organization=org
        )
        
        messages.success(request, f'Your organization {org.Organization_Name} has successfully joined {tournament.Name} with 5 players!')
        return redirect('org_upcoming_tournaments')
        
    return render(request, 'web/Organization/org_participate_confirm.html', {
        'org': org,
        'tournament': tournament,
        'players': players
    })

def player_upcoming_tournaments(request):
    """View for players to see all upcoming published tournaments"""
    player_id = request.session.get('player_id')
    if not player_id:
        return redirect('auth_login')
        
    player = get_object_or_404(Player, id=player_id)
    
    # Get all upcoming published tournaments from all organizations
    tournaments = Tournament.objects.filter(
        Status__in=['Scheduled', 'Ongoing'],
        is_published=True
    ).order_by('start_date')
    
    return render(request, 'web/Player/player_upcoming_list.html', {'tournaments': tournaments, 'player': player})




@login_required_organization
def org_mark_all_notifications_read(request):
    """Mark all notifications as read"""
    org = request.org
    
    # Mark as read instead of deleting
    OrganizationNotification.objects.filter(recipient=org, is_read=False).update(is_read=True)
    
    messages.success(request, "All notifications marked as read.")
    # Redirect back to where the user came from
    return request.META.get('HTTP_REFERER') and redirect(request.META.get('HTTP_REFERER')) or redirect('organizer_dashboard')

@login_required_organization
def delete_notification(request, notification_id):
    """Delete a single notification"""
    org = request.org
        
    
    notification = get_object_or_404(OrganizationNotification, id=notification_id, recipient=org)
    
    notification.delete()
    messages.success(request, "Notification deleted.")
    
    # Redirect back to where the user came from
    return request.META.get('HTTP_REFERER') and redirect(request.META.get('HTTP_REFERER')) or redirect('organizer_dashboard')

@login_required_organization
def org_notifications(request):
    """View all notifications for the organization"""
    org = request.org
    
    notifications = OrganizationNotification.objects.filter(recipient=org).order_by('-created_at')
    
    context = {
        'notifications': notifications,
        'org': org
    }
    return render(request, 'web/Organization/org_notifications.html', context)

@login_required_organization
def org_bidding_dashboard(request):
    """View for organizations to see available players, their roster, and bidding wallet."""
    org_id = request.session.get('organizer_id')
    org = get_object_or_404(Organization, id=org_id)
    
    active_season = BiddingSeason.objects.filter(is_active=True).first()
    
    # 1. Available Players (Not Sold yet)
    sold_player_ids = Bid.objects.filter(status='Accepted').values_list('player_id', flat=True)
    available_players = Player.objects.filter(is_archived=False, status='ACTIVE').exclude(id__in=sold_player_ids)
    
    # 2. My Bids
    my_bids = Bid.objects.filter(organization=org).order_by('-created_at')
    
    # 3. My Roster
    my_roster = Player.objects.filter(id__in=my_bids.filter(status='Accepted').values_list('player_id', flat=True))
    
    context = {
        'org': org,
        'active_season': active_season,
        'wallet_balance': org.coins,
        'available_players': available_players,
        'my_bids': my_bids,
        'my_roster': my_roster
    }
    return render(request, 'web/Organization/org_bidding.html', context)

def player_bidding_dashboard(request):
    """View for players to see their bidding and auction status."""
    player_id = request.session.get('player_id')
    if not player_id:
        return redirect('auth_login')
        
    player = get_object_or_404(Player, id=player_id)
    active_season = BiddingSeason.objects.filter(is_active=True).first()
    
    # Get all bids for this player
    bids = Bid.objects.filter(player=player).order_by('-created_at')
    
    # Determine Status
    highest_accepted = bids.filter(status='Accepted').order_by('-amount').first()
    in_negotiation = bids.filter(status='Negotiation').exists()
    
    auction_status = "Available"
    if highest_accepted:
        auction_status = f"Sold to {highest_accepted.organization.Organization_Name} for ₹{highest_accepted.amount}"
    elif in_negotiation:
        auction_status = "In Negotiation"
        
    context = {
        'player': player,
        'active_season': active_season,
        'bids': bids,
        'auction_status': auction_status
    }
    return render(request, 'web/Player/player_bidding.html', context)

@login_required_organization
def org_scout_players(request):
    """View for organizations to browse all players on the platform"""
    org_id = request.session.get('organizer_id')
    org = get_object_or_404(Organization, id=org_id)
    
    # Fetch all active non-archived players
    available_players = Player.objects.filter(is_archived=False, status='ACTIVE').order_by('-created_at')
    
    context = {
        'org': org,
        'available_players': available_players
    }
    return render(request, 'web/Organization/org_scout_players.html', context)

@login_required_organization
def place_bid(request, player_id):
    """Handle bid placement by an organization on a player"""
    if request.method != 'POST':
        return redirect('org_bidding_dashboard')
    
    org_id = request.session.get('organizer_id')
    org = get_object_or_404(Organization, id=org_id)
    player = get_object_or_404(Player, id=player_id, is_archived=False, status='ACTIVE')
    
    # Check active season
    active_season = BiddingSeason.objects.filter(is_active=True).first()
    if not active_season:
        messages.error(request, 'No active bidding season. Bids cannot be placed right now.')
        return redirect('org_bidding_dashboard')
    
    # Check player isn't already sold
    already_sold = Bid.objects.filter(player=player, status='Accepted').exists()
    if already_sold:
        messages.error(request, f'{player.full_name} has already been sold.')
        return redirect('org_bidding_dashboard')
    
    # Get and validate amount
    MIN_BID = 100  # Minimum bid amount in coins
    try:
        amount = int(request.POST.get('amount', 0))
        if amount < MIN_BID:
            raise ValueError()
    except (ValueError, TypeError):
        messages.error(request, f'Please enter a valid bid amount (minimum ₹{MIN_BID:,}).')
        return redirect('org_bidding_dashboard')
    
    # Check wallet balance
    if org.coins < amount:
        messages.error(request, f'Insufficient balance. You only have ₹{org.coins:,} available.')
        return redirect('org_bidding_dashboard')
    
    # Create the bid
    Bid.objects.create(
        season=active_season,
        player=player,
        organization=org,
        amount=amount,
        status='Pending'
    )
    
    # Deduct from wallet
    org.coins -= amount
    org.save()
    
    # Notify the player about the bid (Issue #7)
    PlayerNotification.objects.create(
        recipient=player,
        message=f'{org.Organization_Name} has placed a bid of ₹{amount:,} on you! Check your Bidding Hub.',
        link='/player/bidding/',
        notification_type='BID'
    )
    
    messages.success(request, f'Bid of ₹{amount:,} placed on {player.full_name} successfully!')
    return redirect('org_bidding_dashboard')
