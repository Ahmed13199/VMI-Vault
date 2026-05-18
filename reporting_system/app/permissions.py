"""
Permission decorators for route protection.
"""
from functools import wraps
from flask_login import current_user
from .services.access_service import AccessService


def require_page_permission(page_key, access_type='view'):
    """Protect a route using page-level permissions."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not AccessService.can_access_page(current_user, page_key, access_type):
                return AccessService.deny_access(access_type)
            return func(*args, **kwargs)

        return wrapper

    return decorator
