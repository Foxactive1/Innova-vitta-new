import hmac
from urllib.parse import urlsplit

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import UserMixin, current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash

from extensions import login_manager

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


class SessionUser(UserMixin):
    """Usuário temporário baseado em credenciais de ambiente.

    Esta implementação não altera o schema atual. Na próxima fase,
    pode ser substituída por um modelo Usuario persistido via Alembic.
    """

    def __init__(self, username: str, role: str = "admin"):
        self.username = username
        self.role = role

    def get_id(self):
        return self.username


def _configured_user():
    username = current_app.config.get("ADMIN_USERNAME")
    if not username:
        return None
    return SessionUser(username=username, role=current_app.config.get("ADMIN_ROLE", "admin"))


@login_manager.user_loader
def load_user(user_id):
    user = _configured_user()
    if user and hmac.compare_digest(str(user.id), str(user_id)):
        return user
    return None


def _password_is_valid(candidate: str) -> bool:
    password_hash = current_app.config.get("ADMIN_PASSWORD_HASH")
    password_plain = current_app.config.get("ADMIN_PASSWORD")

    if password_hash:
        try:
            return check_password_hash(password_hash, candidate)
        except (ValueError, TypeError):
            return False

    if password_plain:
        return hmac.compare_digest(str(password_plain), str(candidate))

    return False


def _safe_next_url(target: str | None) -> str | None:
    if not target:
        return None
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc:
        return None
    if not target.startswith("/"):
        return None
    return target


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        user = _configured_user()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not user or not current_app.config.get("ADMIN_PASSWORD_HASH") and not current_app.config.get("ADMIN_PASSWORD"):
            flash(
                "Credenciais administrativas não configuradas. Defina ADMIN_USERNAME e ADMIN_PASSWORD_HASH (recomendado).",
                "danger",
            )
            return render_template("auth/login.html"), 503

        if hmac.compare_digest(user.username, username) and _password_is_valid(password):
            login_user(user, remember=False)
            target = _safe_next_url(request.args.get("next"))
            return redirect(target or url_for("index"))

        flash("Usuário ou senha inválidos.", "danger")

    return render_template("auth/login.html")


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("Sessão encerrada com segurança.", "success")
    return redirect(url_for("auth.login"))
