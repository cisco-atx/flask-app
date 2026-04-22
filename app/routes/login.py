"""Login routes and authentication decorators.

This module handles user authentication, including login, registration,
logout, and role-based access control decorators. It integrates with the
application's authentication backend and manages session-based access.

Path: app/routes/login.py
"""

from functools import wraps

from flask import (
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)


def render_login():
    """Render login page and handle authentication logic."""
    auth_params = current_app.utils.AUTH_PARAMS

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        auth_kwargs = {}

        if auth_params["mode"] == "ssh":
            auth_kwargs["host"] = auth_params["host"]

        elif auth_params["mode"] == "sso":
            auth_kwargs["token"] = password
            auth_kwargs["provider"] = auth_params.get("sso_provider")
            password = None

        success = current_app.auth.authenticate(
            username=username,
            password=password,
            **auth_kwargs,
        )

        if not success:
            flash("Invalid credentials", "danger")
            return redirect(url_for("atx.render_login"))

        current_app.set_authenticated_user(username)

        flash("Login successful!", "success")
        return redirect(url_for("atx.render_home"))

    return render_template("atx.login.html")


def render_register():
    """Render registration page and handle user registration."""
    if request.method == "POST":
        firstname = request.form["firstname"].strip()
        lastname = request.form["lastname"].strip()
        username = request.form["username"]
        password = request.form["password"]
        email = request.form["email"]

        ok, msg = current_app.auth.register(
            username=username,
            password=password,
            role="user",
            profile={
                "email": email,
                "firstname": firstname,
                "lastname": lastname,
            },
        )

        if ok:
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for("atx.render_login"))

        flash(msg, "danger")

    return render_template("atx.register.html")


def logout():
    """Log out the user and clear session."""
    reason = request.args.get("reason")
    user = session.get("username")

    session.clear()

    if reason:
        flash(reason, "info")
    else:
        flash("You have been logged out.", "info")

    return redirect(url_for("atx.render_login"))


def no_auth_required(f):
    """Mark route as publicly accessible."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        return f(*args, **kwargs)

    decorated_function.is_public = True
    return decorated_function


def login_required(f):
    """Ensure user is logged in before accessing route."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("username"):
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("atx.render_login"))

        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    """Ensure user has admin role before accessing route."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = session.get("username")

        if not user:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("atx.render_login"))

        role = session.get("userdata", {}).get("meta", {}).get("role", "")
        if "admin" not in role:
            flash(
                "You do not have permission to access this page.", "danger"
            )
            return redirect(url_for("atx.render_home"))

        return f(*args, **kwargs)

    return decorated_function


def superadmin_required(f):
    """Ensure user has superadmin role before accessing route."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = session.get("username")

        if not user:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("atx.render_login"))

        role = session.get("userdata", {}).get("meta", {}).get("role", "")
        if role != "superadmin":
            flash(
                "You do not have permission to access this page.", "danger"
            )
            return redirect(url_for("atx.render_home"))

        return f(*args, **kwargs)

    return decorated_function
