from functools import wraps

from flask import abort
from flask_login import current_user


def role_required(*roles):
    """Restringe uma rota autenticada aos papéis informados."""
    allowed = set(roles)

    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if getattr(current_user, "role", None) not in allowed:
                abort(403)
            return view(*args, **kwargs)

        return wrapped

    return decorator
