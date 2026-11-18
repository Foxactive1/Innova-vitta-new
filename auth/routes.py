import hmac
from urllib.parse import urlsplit

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import check_password_hash

from core.models import User, db
from extensions import limiter, login_manager, login_rate_key

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@login_manager.user_loader
def load_user(user_id):
    try:
        user = db.session.get(User, int(user_id))
        return user if user and user.is_active else None
    except (ValueError, SQLAlchemyError):
        db.session.rollback()
        current_app.logger.exception("Falha ao carregar usuário da sessão")
        return None


def _safe_next_url(target):
    if not target:
        return None
    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc or not target.startswith("/"):
        return None
    return target


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute; 20 per hour", key_func=login_rate_key)
@limiter.limit("30 per hour", key_func=lambda: request.remote_addr or "unknown")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        identifier = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        try:
            user = User.query.filter(
                or_(User.username == identifier, User.email == identifier)
            ).first()
            valid = bool(
                user and user.is_active and
                check_password_hash(user.password_hash, password)
            )
        except (SQLAlchemyError, ValueError, TypeError):
            db.session.rollback()
            current_app.logger.exception("Falha durante autenticação persistente")
            flash("Serviço de autenticação temporariamente indisponível.", "danger")
            return render_template("auth/login.html"), 503

        if valid:
            login_user(user, remember=False, fresh=True)
            target = _safe_next_url(request.args.get("next"))
            return redirect(target or url_for("index"))

        # Não revela se o usuário existe.
        flash("Usuário ou senha inválidos.", "danger")

    return render_template("auth/login.html")


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("Sessão encerrada com segurança.", "success")
    return redirect(url_for("auth.login"))
