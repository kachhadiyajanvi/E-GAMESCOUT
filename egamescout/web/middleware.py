from django.shortcuts import redirect
from django.utils import timezone
from django.core.cache import cache
from django.http import HttpResponseForbidden, JsonResponse
from web.models import UserSession

class RateLimitingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.limit = 5
        self.timeout = 15 * 60 # 15 minutes
        self.AUTH_ENDPOINTS = [
            '/auth/login',
            '/auth/register',
            '/auth/request-otp',
            '/organization/login',
            '/organization/register',
            '/organization/resend-otp',
            '/player/auth',
            '/player/login',
        ]

    def __call__(self, request):
        path = request.path_info
        
        # Only rate limit auth endpoints
        is_auth = any(path.startswith(endpoint) for endpoint in self.AUTH_ENDPOINTS)
        if is_auth and request.method == 'POST':
            ip = self.get_client_ip(request)
            cache_key = f'rate_limit_{ip}_{path}'
            requests = cache.get(cache_key, 0)
            
            if requests >= self.limit:
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'message': 'Too many requests. Please try again after 15 minutes.'}, status=429)
                return HttpResponseForbidden("Too many requests. Please try again later.")
                
            cache.set(cache_key, requests + 1, self.timeout)
            
        return self.get_response(request)

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        return x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')

class SecureSessionValidationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.PROTECTED_PREFIXES = ['/admin/', '/organization/', '/player/']
        
        # Paths that are inside protected prefixes but should NOT enforce session limits
        # (e.g., login pages, registration pages)
        self.EXCLUDED_PATHS = [
            '/admin/login/',
            '/organization/login/',
            '/organization/register/',
            '/organization/resend-otp/',
            '/organization/player/accept-invite/',
            '/player/login/', # if applicable
        ]

    def __call__(self, request):
        path = request.path_info
        
        # Check if route is protected
        is_protected = any(path.startswith(prefix) for prefix in self.PROTECTED_PREFIXES)
        is_excluded = any(path.startswith(excluded) for excluded in self.EXCLUDED_PATHS)
        
        if is_protected and not is_excluded:
            session_key = request.session.session_key
            
            if not session_key:
                # Decide redirect based on prefix
                if path.startswith('/admin/'):
                    return redirect('admin_login')
                if path.startswith('/organization/'):
                    return redirect('org_login_start')
                if path.startswith('/player/'):
                    return redirect('auth_login')
                return redirect('index') # Fallback
                
            try:
                # Retrieve secure session metadata
                secure_session = UserSession.objects.select_related('session').get(
                    session_key=session_key, 
                    is_active=True
                )
                
                # Security Check 1: Session Hijacking Prevention (IP/Device mismatch)
                current_ip = self.get_client_ip(request)
                if secure_session.ip_address != current_ip:
                    # Potential hijacking - IPs don't match, destroy session
                    secure_session.expire_session()
                    request.session.flush()
                    return redirect('index')
                
                # Security Check 2: Idle Timeout (30 minutes)
                now = timezone.now()
                inactivity_limit = 30 * 60 # 30 mins
                if not secure_session.is_remember_me:
                    time_idle = (now - secure_session.last_activity).total_seconds()
                    if time_idle > inactivity_limit:
                        secure_session.expire_session()
                        request.session.flush()
                        
                        # Decide redirect
                        if path.startswith('/admin/'):
                            return redirect('admin_login')
                        if path.startswith('/organization/'):
                            return redirect('org_login_start')
                        if path.startswith('/player/'):
                            return redirect('auth_login')
                        return redirect('index')
                
                # Update Last Activity
                secure_session.last_activity = now
                secure_session.save(update_fields=['last_activity'])
                
            except UserSession.DoesNotExist:
                # Invalid or expired session in DB, flush browser cookies
                request.session.flush()
                
                # Decide redirect
                if path.startswith('/admin/'):
                    return redirect('admin_login')
                if path.startswith('/organization/'):
                    return redirect('org_login_start')
                if path.startswith('/player/'):
                    return redirect('auth_login')
                return redirect('index')

        return self.get_response(request)

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        return x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')

class MaintenanceModeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info
        
        # Paths that should ignore maintenance mode
        EXCLUDED_PATHS = [
            '/admin/',
            '/maintenance/',
        ]
        
        # Exclude static/media files
        if path.startswith('/static/') or path.startswith('/media/'):
            return self.get_response(request)

        # Check if the path is explicitly excluded
        is_excluded = any(path.startswith(prefix) for prefix in EXCLUDED_PATHS)

        if not is_excluded:
            from web.models import SystemSettings
            try:
                settings = SystemSettings.get_settings()
                if settings.is_maintenance_mode:
                    return redirect('maintenance_page')
            except Exception:
                pass # db not ready or some other error during setup
                
        return self.get_response(request)

