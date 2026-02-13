from django.shortcuts import redirect
from functools import wraps

def login_required_organization(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.session.get('organizer_id'):
            return redirect('org_login_start')
        return view_func(request, *args, **kwargs)
    return _wrapped_view
