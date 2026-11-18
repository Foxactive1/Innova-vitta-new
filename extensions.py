from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import request


def login_rate_key():
    identity = request.form.get('username', '').strip().lower()[:80]
    return f'{get_remote_address()}:{identity}'

login_manager = LoginManager()
csrf = CSRFProtect()

migrate = Migrate()
limiter = Limiter(key_func=get_remote_address, default_limits=[] )
