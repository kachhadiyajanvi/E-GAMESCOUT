from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from .forms import OrganizationEmailForm, OTPForm, OrganizationDetailsForm, OrganizationLoginForm, OrganizationPhotoForm, TournamentForm
from .models import Organization, Tournament
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from django.conf import settings
import random
import time
from django.core.mail import send_mail
from .forms import EmailLoginForm, OTPVerifyForm, PlayerRegistrationForm
from .models import Player, PlayerTask, Organization, Tournament, GlobalSettings
from django.views.decorators.cache import cache_control
from decimal import Decimal
from .decorators import login_required_organization
from django.views.decorators.csrf import csrf_exempt
import json
from django.http import JsonResponse

from django.core.cache import cache

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
                html_message = render_to_string('web/email/otp_email.html', {'otp_code': otp_code})
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
            html_message = render_to_string('web/email/otp_email.html', {'otp_code': otp_code})
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

from .helpers import extract_aadhar_details

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
                html_content = render_to_string('web/email/welcome_email.html', {'full_name': player.full_name})
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
            from django.template.loader import render_to_string
            from django.utils.html import strip_tags
            
            html_message = render_to_string('web/email/otp_email.html', {'otp_code': otp_code})
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
            
            # Check Expiry (5 minutes = 300 seconds)
            if created_at and (time.time() - float(created_at) > 300):
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
                    
                    request.session['player_id'] = player.id
                    return redirect('player_dashboard')
                except Player.DoesNotExist:
                    # New User -> Register Step 1 (Aadhar Upload)
                    return redirect('auth_register_upload')
            else:
                messages.error(request, 'Invalid or Expired OTP')
    else:
        form = OTPVerifyForm()
        
    return render(request, 'web/Player/verify_otp.html', {'form': form, 'email': email})

from .helpers import extract_aadhar_details
from .forms import AadharUploadForm

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
                html_content = render_to_string('web/email/welcome_email.html', {'full_name': player.full_name})
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
    from django.utils import timezone
    import json
    from django.core.serializers.json import DjangoJSONEncoder
    from .models import PlayerBid, Tournament
    
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
                'time': '00:00', # Default for tournaments if time not set
                'type': 'TOURNAMENT',
                'status': t['Status'],
                'color': '#66FCF1' # Accent Cyan
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

    # Find the tournaments the player is actually participating in
    accepted_tournament_ids = PlayerBid.objects.filter(
        player=player, 
        status='ACCEPTED', 
        tournament__isnull=False
    ).values_list('tournament_id', flat=True).distinct()

    active_tournaments = Tournament.objects.filter(
        Tournament_ID__in=accepted_tournament_ids,
        Status='Ongoing'
    )
    
    upcoming_tournaments_list = Tournament.objects.filter(
        Tournament_ID__in=accepted_tournament_ids,
        Status='Scheduled'
    )[:5] # limit to 5 for dashboard card
    
    # Calculate Stats
    total_tournaments_joined = len(accepted_tournament_ids)
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

from .forms import PlayerProfileForm

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
    request.session.flush()
    return redirect('index')

def org_logout(request):
    """Logout organization and clear session"""
    request.session.flush()
    messages.success(request, 'You have been logged out successfully.')
    return redirect('index')

def index(request):
    organizations = Organization.objects.filter(status='Active')[:10]
    return render(request, 'web/index.html', {'organizations': organizations})

def public_tournaments(request):
    """Public view for upcoming tournaments"""
    tournaments = Tournament.objects.filter(
        Status__in=['Scheduled', 'Ongoing'],
        is_archived=False
    ).order_by('start_date')

    # If a player is logged in, mark tournaments they've already joined (via PlayerBid)
    joined_tournament_ids = []
    player_id = request.session.get('player_id')
    if player_id:
        try:
            from .models import PlayerBid, Player
            player = Player.objects.get(id=player_id)
            joined_tournament_ids = list(PlayerBid.objects.filter(player=player, tournament__isnull=False)
                                         .values_list('tournament__Tournament_ID', flat=True))
        except Exception:
            joined_tournament_ids = []

    return render(request, 'web/tournaments.html', {
        'tournaments': tournaments,
        'joined_tournament_ids': joined_tournament_ids,
        'player_id': player_id,
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
            html_content = render_to_string('web/email/email_otp.html', {'otp': otp})
            text_content = strip_tags(html_content)
            
            msg = EmailMultiAlternatives(subject, text_content, settings.EMAIL_HOST_USER, [email])
            msg.attach_alternative(html_content, "text/html")
            msg.send()
            
            print(f"DEBUG: Registration OTP for {email}: {otp}") # Keep for dev backup
            
            return redirect('org_register_otp')
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
                html_content = render_to_string('web/email/registration_success.html', {
                    'org_name': org.Organization_Name,
                    'org_email': email,
                    'login_url': request.build_absolute_uri('/organization/login/')
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
                html_content = render_to_string('web/email/email_otp.html', {'otp': otp})
                text_content = strip_tags(html_content)
                
                msg = EmailMultiAlternatives(subject, text_content, settings.EMAIL_HOST_USER, [email])
                msg.attach_alternative(html_content, "text/html")
                msg.send()
                
                print(f"DEBUG: Login OTP for {email}: {otp}") # Keep for dev backup
                
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
                request.session['organizer_id'] = org.id
                
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
    from django.utils import timezone
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
    Tournament.objects.filter(
        Organization_Name=org,
        start_date__gt=now
    ).exclude(Status__in=['Scheduled', 'Cancelled']).update(Status='Scheduled')

@login_required_organization
def organizer_dashboard(request):
    org_id = request.session.get('organizer_id')
        
    org = get_object_or_404(Organization, id=org_id)
    
    # Verify/Update tournament statuses first
    update_tournament_statuses(org)
    
    # --- Stats ---
    total_players = Player.objects.filter(organization=org).count()
    active_tournaments = Tournament.objects.filter(Organization_Name=org, Status='Ongoing').count()
    
    # --- Notifications Logic ---
    from .models import OrganizationNotification
    
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
    from django.db.models.functions import TruncMonth
    from django.db.models import Count
    from django.utils import timezone
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
        'active_tournaments': active_tournaments,
        'notifications': notifications,
        'notifications_count': len(notifications),
        'analytics_labels': analytics_labels,
        'analytics_data': analytics_data,
        'recent_recruits': recent_recruits
    })

from django.http import JsonResponse

def resend_otp(request):
    if request.method == 'POST':
        email = request.session.get('reg_email') or request.session.get('login_email')
        
        if not email:
            return JsonResponse({'success': False, 'message': 'Session expired. Please restart.'})
            
        # Generate new OTP
        otp = str(random.randint(100000, 999999))
        
        # Update session (determine which one to update)
        if request.session.get('reg_email'):
            request.session['reg_otp'] = otp
            request.session['reg_otp_created_at'] = time.time()
        else:
            request.session['login_otp'] = otp
            request.session['login_otp_created_at'] = time.time()
            
        # Send OTP via Email
        subject = 'E-Game Scout OTP Resend'
        html_content = render_to_string('web/email/email_otp.html', {'otp': otp})
        text_content = strip_tags(html_content)
        
        msg = EmailMultiAlternatives(subject, text_content, settings.EMAIL_HOST_USER, [email])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        
        print(f"DEBUG: Resend OTP for {email}: {otp}")
        
        return JsonResponse({'success': True, 'message': 'OTP sent successfully'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})

# --- Scorecard AI Tool ---
from google import genai
from groq import Groq
import base64
from .models import ScorecardAnalysis

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
            Act as a professional esports journalist similar to Cricbuzz and analyze the provided standings image from the SkyeSports Skirmish Series Finals (BGMI). Write a detailed, narrative-style tournament report explaining how the leaderboard unfolded, highlighting the championship-winning team’s consistency, the close title race among the top teams, mid-table performances, and struggles of the lower-ranked teams, using only the visible data such as matches played, wins, placement points, eliminations, and total points. Maintain an analytical yet engaging tone, convert statistics into match-like insights, avoid inventing players or events, and conclude with an overall verdict on the competitiveness and quality of the tournament and its significance for upcoming BGMI events.
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
                        key_index = provider.get('index', 1)
                        print(f"DEBUG: Attempting Gemini API Key #{key_index}...")
                        client = genai.Client(api_key=provider['key'])
                        
                        # Upload file and generate content
                        uploaded_file = client.files.upload(file_path)
                        
                        response = client.models.generate_content(
                            model='gemini-2.0-flash-001',
                            contents=[user_prompt, uploaded_file]
                        )
                        response_text = response.text
                        used_provider = f'gemini_key_{key_index}'
                        print(f"SUCCESS: Gemini API Key #{key_index} worked!")
                        
                    elif provider['type'] == 'groq':
                        client = Groq(api_key=provider['key'])
                        
                        # Detect image format from file extension
                        import os
                        file_extension = os.path.splitext(file_path)[1].lower()
                        mime_type = 'image/jpeg'  # default
                        if file_extension == '.png':
                            mime_type = 'image/png'
                        elif file_extension == '.jpg' or file_extension == '.jpeg':
                            mime_type = 'image/jpeg'
                        elif file_extension == '.webp':
                            mime_type = 'image/webp'
                        
                        with open(file_path, "rb") as f:
                            encoded_string = base64.b64encode(f.read()).decode('utf-8')
                            
                        chat_completion = client.chat.completions.create(
                            messages=[
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
                            model="meta-llama/llama-4-scout-17b-16e-instruct",
                        )
                        response_text = chat_completion.choices[0].message.content
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
                analysis.summary_text = response_text
                analysis.ai_provider = used_provider
                analysis.save()
                messages.success(request, 'Analysis Complete!')
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
    return render(request, 'web/Organization/org_scorecard_tool.html', {'org': org, 'history': history})

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
    
    from django.db.models import Q
    from django.utils import timezone
    from datetime import timedelta
    
    # Get current local time
    now = timezone.now()
    
    # Only hide tournaments that are Completed AND ended more than 24 hours ago
    # This allows users to see/fix tournaments they just created with wrong dates (auto-completed)
    cutoff = now - timedelta(hours=24)
    
    q_hidden = Q(Status='Completed', end_date__lt=cutoff)
    
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
def tournament_history(request):
    """Display list of completed tournaments for the organization"""
    org_id = request.session.get('organizer_id')
    
    org = get_object_or_404(Organization, id=org_id)
    
    from django.db.models import Q
    from django.utils import timezone
    
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
        'completed_tournaments': completed_tournaments
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
    from django.db.models import Q
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
    from .models import OrganizationNotification
    message = f"Tournament '{tournament.Name}' has been cancelled."
    OrganizationNotification.objects.create(
        recipient=org,
        message=message,
        notification_type='INFO',
        related_tournament=tournament
    )
    
    # Send Email
    from django.core.mail import send_mail
    from django.conf import settings
    
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
    players = Player.objects.filter(organization=org).order_by('-created_at')
    
    return render(request, 'web/Organization/org_my_players.html', {'org': org, 'players': players})

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
    """Publish a tournament to make it visible to players"""
    org_id = request.session.get('organizer_id')
    if not org_id:
        return redirect('org_login_start')
        
    from .models import Organization, OrganizationNotification
    tournament = get_object_or_404(Tournament, Tournament_ID=tournament_id, Organization_Name_id=org_id)
    org = get_object_or_404(Organization, id=org_id)
    
    if request.method == 'POST':
        tournament.is_published = True
        tournament.save()
        
        # Send Invites to all Active Organizations
        other_orgs = Organization.objects.filter(status='Active').exclude(id=org_id)
        
        notifications = []
        for other in other_orgs:
            notifications.append(OrganizationNotification(
                recipient=other,
                message=f"{org.Organization_Name} invites you to bid for '{tournament.Name}'",
                notification_type='BIDDING_INVITE',
                related_tournament=tournament
            ))
        
        OrganizationNotification.objects.bulk_create(notifications)
        
        messages.success(request, f"Tournament published! Sent invites to {len(notifications)} organizations.")
        return redirect('tournament_list')
        
    return redirect('tournament_list')

def org_upcoming_tournaments(request):
    """View for organizations to see their upcoming published tournaments"""
    org_id = request.session.get('organizer_id')
    if not org_id:
        return redirect('org_login_start')
        
    org = get_object_or_404(Organization, id=org_id)
    
    # Get upcoming published tournaments
    # Logic: Status is Scheduled or Ongoing, and is_published is True
    tournaments = Tournament.objects.filter(
        Status__in=['Scheduled', 'Ongoing'],
        is_published=True
    ).order_by('start_date')

    # Get list of tournaments this org has joined
    from .models import TournamentBidder
    joined_tournament_ids = list(TournamentBidder.objects.filter(
        organization=org
    ).values_list('tournament_id', flat=True))
    
    return render(request, 'web/Organization/org_upcoming_list.html', {
        'tournaments': tournaments, 
        'org': org,
        'joined_tournament_ids': joined_tournament_ids
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

# --- Bidding System ---

def open_bidding(request, tournament_id):
    org_id = request.session.get('organizer_id')
    if not org_id:
        return redirect('org_login_start')
        
    org = get_object_or_404(Organization, id=org_id)
    tournament = get_object_or_404(Tournament, Tournament_ID=tournament_id, Organization_Name=org)
    
    if request.method == 'POST':
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        coin_amount = request.POST.get('coin_amount', '0')
        
        try:
            from decimal import Decimal
            coin_amount = Decimal(coin_amount)
        except:
            coin_amount = Decimal('0.00')
            
        # Calculate Cost
        other_orgs = Organization.objects.filter(status='Active').exclude(id=org_id)
        print(f"DEBUG: Sending invites to {other_orgs.count()} organizations")
        
        # User Logic: "One Payment, All Receive"
        # Organizer pays 'coin_amount' TOTAL.
        # Each Invitee receives 'coin_amount'.
        
        total_cost = coin_amount 
        
        # REMOVED: Wallet Balance Check (Overdraft allowed)
        # if org.coins < total_cost: ...
            
        from django.db import transaction
        from .models import OrganizationNotification, Transaction
        
        try:
            with transaction.atomic():
                # Deduct from Organizer (Flat Fee) - REMOVED as per user request
                # org.coins -= total_cost
                # org.save()
                
                # RECORD TRANSACTION: Sender
                Transaction.objects.create(
                    sender=org,
                    amount=total_cost,
                    transaction_type='BIDDING_INCENTIVE',
                    related_tournament=tournament,
                    description=f"Sent bidding incentives for '{tournament.Name}'"
                )
                
                # Parse dates to be timezone aware
                from django.utils.dateparse import parse_datetime
                from django.utils import timezone
                
                dt_start = None
                dt_end = None

                if start_date:
                    dt_start = parse_datetime(start_date)
                    if dt_start and timezone.is_naive(dt_start):
                        dt_start = timezone.make_aware(dt_start)
                
                if end_date:
                    dt_end = parse_datetime(end_date)
                    if dt_end and timezone.is_naive(dt_end):
                        dt_end = timezone.make_aware(dt_end)
                
                # Update Tournament
                tournament.bidding_open = True
                tournament.bidding_start_date = dt_start
                tournament.bidding_end_date = dt_end
                tournament.bidding_invite_fee = total_cost 
                tournament.save()
                
                # Send invites immediately, but funds are claimed on join
                for other in other_orgs:
                    OrganizationNotification.objects.create(
                        recipient=other,
                        message=f"You are invited! Join '{tournament.Name}' to claim {total_cost} coins participation bonus.",
                        notification_type='BIDDING_INVITE',
                        related_tournament=tournament
                    )
                
            messages.success(request, f"Bidding opened! Fee set to {total_cost}.")
        except Exception as e:
            messages.error(request, f"Error processing transaction: {str(e)}")
            
        return redirect('tournament_list')
        
    return redirect('tournament_list')

def handle_bidding_invite(request, notification_id, action):
    org_id = request.session.get('organizer_id')
    if not org_id:
        return redirect('org_login_start')
        
    from .models import OrganizationNotification, TournamentBidder
    org = get_object_or_404(Organization, id=org_id)
    notification = get_object_or_404(OrganizationNotification, id=notification_id, recipient_id=org_id)
    
    if action == 'accept':
        # Create Bidder entry
        if notification.related_tournament:
            bidder, created = TournamentBidder.objects.get_or_create(
                tournament=notification.related_tournament,
                organization_id=org_id
            )
            
            if created:
                # Credit Invite Fee to Organization
                invite_fee = notification.related_tournament.bidding_invite_fee
                if invite_fee > 0:
                    from django.db import transaction as db_transaction
                    from .models import Transaction
                    
                    with db_transaction.atomic():
                        org.coins += invite_fee
                        org.save()
                        
                        Transaction.objects.create(
                            recipient=org,
                            amount=invite_fee,
                            transaction_type='BIDDING_INCENTIVE',
                            related_tournament=notification.related_tournament,
                            description=f"Received bidding incentive for '{notification.related_tournament.Name}'"
                        )
                    messages.success(request, f"Accepted! You received {invite_fee} coins.")
                else:
                    messages.success(request, f"You have accepted the invitation for '{notification.related_tournament.Name}'")
            else:
                messages.info(request, "You have already joined this tournament.")
        
        # Delete notification after action
        notification.delete()
        
    elif action == 'decline':
        notification.delete()
        messages.info(request, "Invitation declined.")
        
    return redirect('organizer_dashboard')

@login_required_organization
def join_tournament(request, tournament_id):
    """Handle organization joining a tournament directly"""
    if request.method != 'POST':
        return redirect('tournament_detail', tournament_id=tournament_id)
        
    org_id = request.session.get('organizer_id')
    org = get_object_or_404(Organization, id=org_id)
    tournament = get_object_or_404(Tournament, Tournament_ID=tournament_id)
    
    # Check if already joined
    if tournament.bidders.filter(organization=org).exists():
        messages.info(request, "You have already joined this tournament.")
        return redirect('tournament_detail', tournament_id=tournament_id)
        
    # Check if owner
    if tournament.Organization_Name == org:
        messages.error(request, "You cannot join your own tournament.")
        return redirect('tournament_detail', tournament_id=tournament_id)
        
    # Create Participant (Bidder)
    from .models import TournamentBidder, Transaction, OrganizationNotification
    from django.db import transaction as db_transaction
    
    try:
        with db_transaction.atomic():
            bidder = TournamentBidder.objects.create(
                tournament=tournament,
                organization=org
            )
            
            # Credit Invite Fee to Organization (Participation Bonus)
            invite_fee = tournament.bidding_invite_fee
            if invite_fee > 0:
                org.coins += invite_fee
                org.save()
                
                Transaction.objects.create(
                    recipient=org,
                    amount=invite_fee,
                    transaction_type='BIDDING_INCENTIVE',
                    related_tournament=tournament,
                    description=f"Received participation bonus for '{tournament.Name}'"
                )
                messages.success(request, f"Successfully joined! You received {invite_fee} coins.")
            else:
                messages.success(request, f"Successfully joined '{tournament.Name}'!")
                
            # Notify Tournament Owner
            OrganizationNotification.objects.create(
                recipient=tournament.Organization_Name,
                message=f"{org.Organization_Name} has joined your tournament '{tournament.Name}'",
                notification_type='INFO',
                related_tournament=tournament
            )
                
    except Exception as e:
        messages.error(request, f"Error joining tournament: {e}")
        
    return redirect('tournament_detail', tournament_id=tournament_id)


def transaction_history(request):
    """View to display transaction history for the organization"""
    org_id = request.session.get('organizer_id')
    if not org_id:
        return redirect('org_login_start')
        
    org = get_object_or_404(Organization, id=org_id)
    
    # Fetch transactions where org is sender OR recipient
    from django.db.models import Q
    from .models import Transaction
    
    transactions = Transaction.objects.filter(
        Q(sender=org) | Q(recipient=org)
    ).order_by('-timestamp')
    
    return render(request, 'web/Organization/org_transaction_history.html', {
        'org': org, 
        'transactions': transactions
    })

# --- Live Player Bidding Views (Organization) ---


def org_live_bidding(request):
    """View to list players available for bidding"""
    org_id = request.session.get('organizer_id')
    if not org_id:
        return redirect('org_login_start')
    
    org = get_object_or_404(Organization, id=org_id)
    
    # Get Active Bidding Tournaments
    # Prioritize: 
    # 1. Active (Live)
    # 2. Upcoming (Scheduled)
    # 3. Just Completed
    
    from django.db.models import Q
    now = timezone.now()
    
    # --- Process Completed Bidding Sessions ---
    completed_biddings = Tournament.objects.filter(
        bidding_end_date__lt=now,
        bidding_open=True,
        bidding_notifications_sent=False
    )
    
    if completed_biddings.exists():
        from .models import PlayerNotification, OrganizationNotification, TournamentBidder
        
        for tournament in completed_biddings:
            # 1. Notify All Players
            players = Player.objects.exclude(status='SUSPENDED')
            player_notifs = [
                PlayerNotification(
                    recipient=p,
                    message=f"Bidding for '{tournament.Name}' has ended.",
                    notification_type='INFO'
                ) for p in players
            ]
            PlayerNotification.objects.bulk_create(player_notifs)
            
            # 2. Notify Accepted Organizations (Bidders)
            bidders = TournamentBidder.objects.filter(tournament=tournament)
            org_notifs = [
                OrganizationNotification(
                    recipient=bidder.organization,
                    message=f"Bidding for '{tournament.Name}' has ended.",
                    notification_type='INFO',
                    related_tournament=tournament
                ) for bidder in bidders
            ]
            OrganizationNotification.objects.bulk_create(org_notifs)
            
            # Empty the wallet of participating organizations
            from .models import Transaction
            for bidder in bidders:
                org = bidder.organization
                if org.coins > 0:
                    amount_to_remove = org.coins
                    org.coins = 0
                    org.save()
                    
                    Transaction.objects.create(
                        sender=org,
                        amount=amount_to_remove,
                        transaction_type='OTHER',
                        related_tournament=tournament,
                        description=f"Unused bidding coins flushed upon closing '{tournament.Name}'"
                    )
            
            # 3. Create Matches (Optional/Future: If "match" meant creating matches)
            # For now, just mark processed.
            
            # 4. Update Tournament
            tournament.bidding_notifications_sent = True
            tournament.bidding_open = False # Close bidding
            tournament.save()
            
            messages.info(request, f"Bidding for '{tournament.Name}' has ended and notifications sent.")
            
    # --- End Processing ---
    
    # Check for LIVE tournaments
    active_tournament = Tournament.objects.filter(
        bidding_open=True, 
        bidding_start_date__lte=now, 
        bidding_end_date__gte=now
    ).first()
    
    status = 'NOT_CONFIGURED'
    start_time = None
    end_time = None
    tournament_name = None
    
    if active_tournament:
        status = 'LIVE'
        start_time = active_tournament.bidding_start_date
        end_time = active_tournament.bidding_end_date
        tournament_name = active_tournament.Name
    else:
        # Check for UPCOMING
        upcoming_tournament = Tournament.objects.filter(
            bidding_open=True,
            bidding_start_date__gt=now
        ).order_by('bidding_start_date').first()
        
        if upcoming_tournament:
            status = 'UPCOMING'
            start_time = upcoming_tournament.bidding_start_date
            end_time = upcoming_tournament.bidding_end_date
            tournament_name = upcoming_tournament.Name
        else:
            # Check for RECENTLY COMPLETED (Optional, but good for UX)
            completed_tournament = Tournament.objects.filter(
                bidding_open=True,
                bidding_end_date__lt=now
            ).order_by('-bidding_end_date').first()
            
            if completed_tournament:
                status = 'COMPLETED'
                start_time = completed_tournament.bidding_start_date
                end_time = completed_tournament.bidding_end_date
                tournament_name = completed_tournament.Name

    # Check if starting soon (within 30 mins)
    is_starting_soon = False
    if status == 'UPCOMING' and start_time:
        time_diff = start_time - now
        if time_diff.total_seconds() <= 1800: # 30 mins
             is_starting_soon = True

    # Get players who are NOT already in an organization (or status='ACTIVE'/'PENDING' but free agents)
    # Get ALL players (excluding Suspended) to show Sold Out status
    # Players with organization__isnull=False will be marked as Sold Out
    available_players = Player.objects.exclude(status='SUSPENDED')
    
    return render(request, 'web/Organization/org_live_bidding.html', {
        'org': org,
        'players': available_players,
        'bidding_status': status,
        'start_time': start_time,
        'end_time': end_time,
        'tournament_name': tournament_name
    })


def place_player_bid(request, player_id):
    """Handle placing a bid on a player"""
    if request.method != 'POST':
        return redirect('org_live_bidding')
        
    org_id = request.session.get('organizer_id')
    if not org_id:
        return redirect('org_login_start')
        
    org = get_object_or_404(Organization, id=org_id)
    player = get_object_or_404(Player, id=player_id)
    
    amount = Decimal(request.POST.get('amount', '0'))
    message = request.POST.get('message', '')
    
    if amount <= 0:
        messages.error(request, "Bid amount must be greater than 0.")
        return redirect('org_live_bidding')
        
    if org.coins < amount:
        messages.error(request, "Insufficient funds to place this bid.")
        return redirect('org_live_bidding')
        
    # Create Bid
    from .models import PlayerBid, PlayerNotification
    
    PlayerBid.objects.create(
        organization=org,
        player=player,
        amount=amount,
        message=message,
        status='PENDING'
    )
    
    # Notify Player
    PlayerNotification.objects.create(
        recipient=player,
        message=f"You received a bid of {amount} coins from {org.Organization_Name}!",
        notification_type='BID',
        link='/player/bids/' # We will create this URL
    )
    
    messages.success(request, f"Bid of {amount} placed for {player.username}!")
    return redirect('org_live_bidding')


def org_negotiations(request):
    """List ongoing negotiations for the organization"""
    org_id = request.session.get('organizer_id')
    if not org_id:
        return redirect('org_login_start')
        
    org = get_object_or_404(Organization, id=org_id)
    
    # Bids where status is NEGOTIATING
    from .models import PlayerBid
    negotiations = PlayerBid.objects.filter(organization=org, status='NEGOTIATING').order_by('-updated_at')
    
    return render(request, 'web/Organization/org_negotiations.html', {
        'org': org,
        'negotiations': negotiations
    })


def handle_negotiation(request, bid_id, action):
    """Handle negotiation response (Accept Counter / Reject)"""
    org_id = request.session.get('organizer_id')
    if not org_id:
        return redirect('org_login_start')
        
    org = get_object_or_404(Organization, id=org_id)
    from .models import PlayerBid, Transaction, PlayerNotification
    
    bid = get_object_or_404(PlayerBid, id=bid_id, organization=org)
    
    if action == 'accept':
        # Finalize Deal with Counter Amount
        final_amount = bid.counter_amount
        
        if org.coins < final_amount:
            messages.error(request, "Insufficient funds to accept this counter-offer.")
            return redirect('org_negotiations')
            
        # 1. Deduct from Org
        org.coins -= final_amount
        org.save()
        
        # 2. Add to Player
        bid.player.coins += final_amount
        bid.player.organization = org
        bid.player.status = 'ACTIVE' # Marked as sold/active in team
        bid.player.save()
        
        # 3. Create Transactions
        Transaction.objects.create(
            sender=org,
            amount=final_amount,
            transaction_type='PLAYER_PURCHASE', # Need to add this type or use OTHER
            description=f"Purchased player {bid.player.username} (Negotiated)"
        )
        
        Transaction.objects.create( # Using Transaction model for player? 
            # Wait, Transaction model links Org->Org. 
            # We might need to adjust Transaction model to support Player recipient OR just track it as outgoing.
            # For now, let's track as outgoing from Org. Player has 'coins' field but no Transaction linkage yet.
            # We will just log it.
            recipient=None, 
            amount=final_amount,
            description=f"Received payment from {org.Organization_Name}",
            # We can't link to player in Transaction model yet.
        )
        
        # 4. Update Bid
        bid.status = 'ACCEPTED'
        bid.amount = final_amount # Update to final agreed amount
        bid.save()
        
        # 5. Notify Player
        PlayerNotification.objects.create(
            recipient=bid.player,
            message=f"Deal Concluded! {org.Organization_Name} accepted your counter-offer of {final_amount}.",
            notification_type='INFO'
        )
        
        # 6. Reject all other pending/negotiating bids for this player
        other_bids = PlayerBid.objects.filter(
            player=bid.player,
            status__in=['PENDING', 'NEGOTIATING']
        ).exclude(id=bid_id)
        
        for other_bid in other_bids:
            other_bid.status = 'REJECTED'
            other_bid.save()
            
            # Notify the organization
            from .models import OrganizationNotification
            OrganizationNotification.objects.create(
                recipient=other_bid.organization,
                message=f"{bid.player.username} has accepted another offer. Your bid has been automatically rejected.",
                notification_type='INFO'
            )
        
        messages.success(request, f"Deal finalized! {bid.player.username} is now in your team.")
        
    elif action == 'reject':
        bid.status = 'REJECTED'
        bid.save()
        
        PlayerNotification.objects.create(
            recipient=bid.player,
            message=f"{org.Organization_Name} rejected your counter-offer.",
            notification_type='INFO'
        )
        messages.info(request, "Negotiation rejected.")
        
    return redirect('org_negotiations')

# --- Live Player Bidding Views (Player) ---


def player_bids(request):
    """View for player to see received bids"""
    player_id = request.session.get('player_id')
    if not player_id:
        return redirect('auth_login')
        
    player = get_object_or_404(Player, id=player_id)
    
    # Get bids
    from .models import PlayerBid
    bids = PlayerBid.objects.filter(player=player).exclude(status='REJECTED').order_by('-created_at')
    
    return render(request, 'web/Player/player_bids.html', {
        'player': player,
        'bids': bids
    })


def handle_player_bid(request, bid_id, action):
    """Handle player response to a bid (Accept/Reject/Negotiate)"""
    player_id = request.session.get('player_id')
    if not player_id:
        return redirect('auth_login')
        
    player = get_object_or_404(Player, id=player_id)
    from .models import PlayerBid, Transaction, PlayerNotification, Organization
    
    bid = get_object_or_404(PlayerBid, id=bid_id, player=player)
    
    if action == 'accept':
        
        org = bid.organization
        final_amount = bid.amount
        
        if org.coins < final_amount:
            messages.error(request, f"Cannot accept bid: {org.Organization_Name} has insufficient funds.")
            return redirect('player_bids')
            
        # 1. Deduct from Org
        org.coins -= final_amount
        org.save()
        
        # 2. Add to Player
        player.coins += final_amount
        player.organization = org
        player.status = 'ACTIVE'
        player.save()
        
        # 3. Create Transactions
        Transaction.objects.create(
            sender=org,
            amount=final_amount,
            transaction_type='PLAYER_PURCHASE', # Need to add this type or use OTHER
            description=f"Purchased player {player.username}"
        )
        
        # 4. Update Bid
        bid.status = 'ACCEPTED'
        bid.save()
        
        # 5. Notify Org
        from .models import OrganizationNotification
        player_name = player.username or player.full_name or "Player"
        OrganizationNotification.objects.create(
            recipient=org,
            message=f"{player_name} ACCEPTED your bid of {final_amount}!",
            notification_type='INFO'
        )
        
        # 6. Reject all other pending/negotiating bids for this player
        other_bids = PlayerBid.objects.filter(
            player=player,
            status__in=['PENDING', 'NEGOTIATING']
        ).exclude(id=bid_id)
        
        for other_bid in other_bids:
            other_bid.status = 'REJECTED'
            other_bid.save()
            
            # Notify the organization
            OrganizationNotification.objects.create(
                recipient=other_bid.organization,
                message=f"{player.username} has accepted another offer. Your bid has been automatically rejected.",
                notification_type='INFO'
            )
        
        messages.success(request, f"Congratulations! You have joined {org.Organization_Name}.")
        
    elif action == 'reject':
        bid.status = 'REJECTED'
        bid.save()
        
        from .models import OrganizationNotification
        OrganizationNotification.objects.create(
            recipient=bid.organization,
            message=f"{player.username} REJECTED your bid.",
            notification_type='INFO'
        )
        messages.info(request, "Bid rejected.")
        
    elif action == 'negotiate':
        if request.method == 'POST':
            counter_amount = Decimal(request.POST.get('counter_amount', '0'))
            counter_message = request.POST.get('counter_message', '')
            
            if counter_amount <= 0:
                messages.error(request, "Counter amount must be greater than 0.")
                return redirect('player_bids')
                
            bid.counter_amount = counter_amount
            bid.counter_message = counter_message
            bid.status = 'NEGOTIATING'
            bid.save()
            
            from .models import OrganizationNotification
            OrganizationNotification.objects.create(
                recipient=bid.organization,
                message=f"{player.username} wants to NEGOTIATE: {counter_amount} coins.",
                notification_type='INFO',
                related_tournament=None 
            )
            
            messages.success(request, "Counter-offer sent successfully.")
            
    return redirect('player_bids')


@login_required_organization
def org_mark_all_notifications_read(request):
    """Mark all notifications as read"""
    org = request.org
    
    # Mark as read instead of deleting
    from .models import OrganizationNotification
    OrganizationNotification.objects.filter(recipient=org, is_read=False).update(is_read=True)
    
    messages.success(request, "All notifications marked as read.")
    # Redirect back to where the user came from
    return request.META.get('HTTP_REFERER') and redirect(request.META.get('HTTP_REFERER')) or redirect('organizer_dashboard')

@login_required_organization
def delete_notification(request, notification_id):
    """Delete a single notification"""
    org = request.org
        
    from .models import OrganizationNotification
    from django.shortcuts import get_object_or_404
    
    notification = get_object_or_404(OrganizationNotification, id=notification_id, recipient=org)
    
    notification.delete()
    messages.success(request, "Notification deleted.")
    
    # Redirect back to where the user came from
    return request.META.get('HTTP_REFERER') and redirect(request.META.get('HTTP_REFERER')) or redirect('organizer_dashboard')

@login_required_organization
def org_notifications(request):
    """View all notifications for the organization"""
    org = request.org
    from .models import OrganizationNotification
    
    notifications = OrganizationNotification.objects.filter(recipient=org).order_by('-created_at')
    
    context = {
        'notifications': notifications,
        'org': org
    }
    return render(request, 'web/Organization/org_notifications.html', context)
