from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import OrganizationEmailForm, OTPForm, OrganizationDetailsForm, OrganizationLoginForm, OrganizationPhotoForm, TournamentForm
from .models import Organization, Tournament
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import random
import time
from django.core.mail import send_mail
from .forms import EmailLoginForm, OTPVerifyForm, PlayerRegistrationForm
from .models import Player
from django.views.decorators.cache import cache_control

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
    
    return render(request, 'web/Player/dashboard.html', {'player': player})

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

def auth_logout(request):
    request.session.flush()
    return redirect('index')

def org_logout(request):
    """Logout organization and clear session"""
    request.session.flush()
    messages.success(request, 'You have been logged out successfully.')
    return redirect('index')

def index(request):
    return render(request, 'web/index.html')

# --- Registration Flow ---

def org_register_start(request):
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
                org = Organization.objects.get(Organization_Email=email)
                request.session['organizer_id'] = org.id
                
                # Cleanup OTP session
                del request.session['login_email']
                del request.session['login_otp']
                
                return redirect('organizer_dashboard')
            else:
                messages.error(request, 'Invalid OTP')
    else:
        form = OTPForm()
    
    return render(request, 'web/Organization/org_login_otp.html', {'form': form, 'email': email})

def organizer_dashboard(request):
    org_id = request.session.get('organizer_id')
    if not org_id:
        return redirect('org_login_start')
        
    org = get_object_or_404(Organization, id=org_id)
    
    # --- Stats ---
    total_players = Player.objects.filter(organization=org).count()
    active_tournaments = Tournament.objects.filter(Organization_Name=org, Status='Ongoing').count()
    
    # --- Notifications Logic (Simulated for Demo) ---
    # Combine recent player joins and tournament updates
    recent_players = Player.objects.filter(organization=org).order_by('-created_at')[:3]
    recent_tournaments = Tournament.objects.filter(Organization_Name=org).order_by('-UpdatedAt')[:3]
    
    notifications = []
    
    for p in recent_players:
        notifications.append({
            'type': 'player',
            'message': f"New player joined: {p.full_name}",
            'time': p.created_at,
            'link': '#'
        })
        
    for t in recent_tournaments:
        notifications.append({
            'type': 'tournament',
            'message': f"Tournament '{t.Name}' updated.",
            'time': t.UpdatedAt,
            'link': '#'
        })
    
    # Sort by time descending
    notifications.sort(key=lambda x: x['time'], reverse=True)
    notifications = notifications[:5] # Limit to 5
    
    # --- Analytics: Player Growth (Last 6 Months) ---
    from django.db.models.functions import TruncMonth
    from django.db.models import Count
    from django.utils import timezone
    import datetime
    
    six_months_ago = timezone.now() - datetime.timedelta(days=180)
    
    # Get counts per month
    growth_data = Player.objects.filter(
        organization=org, 
        created_at__gte=six_months_ago
    ).annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(
        count=Count('id')
    ).order_by('month')
    
    # Format for Chart.js
    analytics_labels = []
    analytics_data = []
    
    # Pre-fill last 6 months to ensure continuous line even if 0
    current = six_months_ago
    end = timezone.now()
    
    # Create a dict for easy lookup
    data_map = {item['month'].strftime('%Y-%m'): item['count'] for item in growth_data}
    
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

def scorecard_tool(request):
    org_id = request.session.get('organizer_id')
    if not org_id:
        return redirect('org_login_start')
        
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
            
            # Providers Config
            providers = []
            if settings.GEMINI_API_KEY:
                providers.append({"type": "gemini", "key": settings.GEMINI_API_KEY})
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

            # AI Logic Loop
            for provider in providers:
                try:
                    if provider['type'] == 'gemini':
                        client = genai.Client(api_key=provider['key'])
                        
                        # Upload file and generate content
                        uploaded_file = client.files.upload(file=file_path)
                        
                        response = client.models.generate_content(
                            model='gemini-2.0-flash-001',
                            contents=[user_prompt, uploaded_file]
                        )
                        response_text = response.text
                        used_provider = 'gemini'
                        
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
                    print(f"AI Provider {provider['type']} Error: {e}")
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

def manage_profile(request):
    """Display the manage profile page"""
    org_id = request.session.get('organizer_id')
    if not org_id:
        return redirect('org_login_start')
    
    org = get_object_or_404(Organization, id=org_id)
    return render(request, 'web/Organization/org_manage_profile.html', {'org': org})

def update_profile(request):
    """Update organization profile information"""
    org_id = request.session.get('organizer_id')
    if not org_id:
        return redirect('org_login_start')
    
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

def update_profile_photo(request):
    """Update organization profile photo"""
    org_id = request.session.get('organizer_id')
    if not org_id:
        return redirect('org_login_start')
    
    org = get_object_or_404(Organization, id=org_id)
    
    if request.method == 'POST' and request.FILES.get('profile_photo'):
        org.profile_photo = request.FILES['profile_photo']
        org.save()
        messages.success(request, 'Profile photo updated successfully!')
    
    return redirect('manage_profile')

# --- Tournament Management ---

def tournament_list(request):
    """Display list of tournaments for the organization"""
    org_id = request.session.get('organizer_id')
    if not org_id:
        return redirect('org_login_start')
    
    org = get_object_or_404(Organization, id=org_id)
    tournaments = Tournament.objects.filter(Organization_Name=org).order_by('-CreatedAt')
    form = TournamentForm()
    
    return render(request, 'web/Organization/org_tournament_list.html', {
        'org': org, 
        'tournaments': tournaments,
        'form': form,
        'show_form': False
    })

def tournament_create(request):
    """Create a new tournament"""
    org_id = request.session.get('organizer_id')
    if not org_id:
        return redirect('org_login_start')
    
    org = get_object_or_404(Organization, id=org_id)
    
    if request.method == 'POST':
        form = TournamentForm(request.POST)
        if form.is_valid():
            tournament = form.save(commit=False)
            tournament.Organization_Name = org
            tournament.save()
            messages.success(request, f'Tournament "{tournament.Name}" created successfully!')
            return redirect('tournament_list')
    if request.method == 'POST':
        form = TournamentForm(request.POST)
        if form.is_valid():
            tournament = form.save(commit=False)
            tournament.Organization_Name = org
            tournament.save()
            messages.success(request, f'Tournament "{tournament.Name}" created successfully!')
            return redirect('tournament_list')
        else:
            # If form is invalid, render the list template with the bound form and error flag
            tournaments = Tournament.objects.filter(Organization_Name=org).order_by('-CreatedAt')
            return render(request, 'web/Organization/org_tournament_list.html', {
                'org': org, 
                'tournaments': tournaments, 
                'form': form, 
                'show_form': True,
                'action': 'Create'
            })
    
    # If not POST, redirect to list
    return redirect('tournament_list')

def tournament_update(request, tournament_id):
    """Update an existing tournament"""
    org_id = request.session.get('organizer_id')
    if not org_id:
        return redirect('org_login_start')
    
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

def tournament_delete(request, tournament_id):
    """Delete a tournament"""
    org_id = request.session.get('organizer_id')
    if not org_id:
        return redirect('org_login_start')
    
    org = get_object_or_404(Organization, id=org_id)
    tournament = get_object_or_404(Tournament, Tournament_ID=tournament_id, Organization_Name=org)
    
    if request.method == 'POST':
        tournament_name = tournament.Name
        tournament.delete()
        messages.success(request, f'Tournament "{tournament_name}" deleted successfully!')
        return redirect('tournament_list')
    
    return render(request, 'web/Organization/org_tournament_confirm_delete.html', {'org': org, 'tournament': tournament})
def my_players(request):
    """Display list of players recruited by the organization"""
    org_id = request.session.get('organizer_id')
    if not org_id:
        return redirect('org_login_start')
    
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
