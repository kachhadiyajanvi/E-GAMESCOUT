from django.shortcuts import redirect
from django.utils import timezone
from .models import UserSession

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
