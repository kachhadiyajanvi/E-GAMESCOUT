from django.contrib.sessions.models import Session
from user_agents import parse
from web.models import UserSession

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')

def handle_secure_login(request, user_id, user_type):
    # 1. Enforce specific "One Active Session" rule
    old_sessions = UserSession.objects.filter(
        user_id=user_id, 
        user_type=user_type, 
        is_active=True
    )
    for old_session in old_sessions:
        old_session.expire_session()
        
    # 2. Prevent Session Fixation/Hijacking by rolling the Session ID
    request.session.cycle_key()
    
    # 3. Handle "Remember Me" (7 days vs browser close)
    # Check if 'remember_me' is in request.POST
    remember_me = request.POST.get('remember_me') == 'on' or request.POST.get('remember_me') == 'true'
    if remember_me:
        request.session.set_expiry(7 * 24 * 60 * 60) # 7 days
    else:
        request.session.set_expiry(0) # Closes when browser closes
        
    # 4. Extract Device & IP metadata
    ip = get_client_ip(request)
    user_agent_str = request.META.get('HTTP_USER_AGENT', '')
    user_agent = parse(user_agent_str)
    device_info = f"{user_agent.os.family} - {user_agent.browser.family}"

    # 5. Store in Database
    if not request.session.session_key:
        request.session.create()

    session_obj = Session.objects.get(session_key=request.session.session_key)
    
    UserSession.objects.create(
        user_type=user_type,
        user_id=user_id,
        session=session_obj,
        session_key=request.session.session_key,
        ip_address=ip,
        device_info=device_info,
        is_active=True,
        is_remember_me=remember_me
    )

def handle_secure_logout(request):
    # Find active session metadata
    session_key = request.session.session_key
    if session_key:
        try:
            user_session = UserSession.objects.get(session_key=session_key)
            user_session.expire_session() # Marks inactive and destroys Django session
        except UserSession.DoesNotExist:
            pass
    
    # Failsafe destroy the browser cookie
    request.session.flush()
