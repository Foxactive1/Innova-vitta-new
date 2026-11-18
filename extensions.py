from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

login_manager = LoginManager()
csrf = CSRFProtect()

migrate = Migrate()
limiter = Limiter(key_func=get_remote_address, default_limits=[] )
