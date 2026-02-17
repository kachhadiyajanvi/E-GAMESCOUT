from django.shortcuts import redirect, get_object_or_404
from functools import wraps

def login_required_organization(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        org_id = request.session.get('organizer_id')
        if not org_id:
            return redirect('org_login_start')
        
        # Fetch and attach organization to request
        from web.models import Organization
        request.org = get_object_or_404(Organization, id=org_id)
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view
