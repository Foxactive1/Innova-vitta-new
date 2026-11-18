from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate

login_manager = LoginManager()
csrf = CSRFProtect()

migrate = Migrate()
