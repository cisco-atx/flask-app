"""
Authentication-related views and decorators for handling login, registration, and authorization
within the Flask application.
"""

from flask import render_template, current_app, request, session, flash, url_for, redirect
from functools import wraps


def render_login():
    """
    Handle the login page rendering and login logic.

    If the request method is POST, authenticate the user credentials.
    Sets session variables and redirects to the dashboard upon successful login.
    Renders the login page for GET requests.

    Returns:
        HTTP Response: Redirects or renders the login template.
    """
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
            **auth_kwargs
        )

        if not success:
            flash("Invalid credentials", "danger")
            return redirect(url_for("atx.render_login"))

        current_app.set_authenticated_user(username)

        flash("Login successful!", "success")
        return redirect(url_for("atx.render_home"))

    return render_template("atx.login.html")


def render_register():
    """
    Handle the registration page rendering and user registration logic.

    If the request method is POST, registers the user with the provided details.
    Redirects to the login page upon successful registration. Renders the
    registration page for GET requests.

    Returns:
        HTTP Response: Redirects or renders the registration template.
    """
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
            profile={"email": email, "firstname": firstname, "lastname": lastname}
        )
        if ok:
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for("atx.render_login"))
        flash(msg, "danger")

    return render_template("atx.register.html")


def logout():
    """
    Clear the current session and log out the user.

    Flash a message and redirect to the login page.

    Returns:
        HTTP Response: Redirects to the login page.
    """
    reason = request.args.get("reason")
    session.clear()
    if reason:
        flash(reason, "info")
    else:
        flash("You have been logged out.", "info")
    return redirect(url_for("atx.render_login"))


def login_required(f):
    """
    Decorator to enforce login for protected routes.

    Redirects to the login page if the user is not logged in.

    Arguments:
        f (function): The function to wrap.

    Returns:
        function: The wrapped function.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("username"):
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("atx.render_login"))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """
    Decorator to enforce admin role for accessing specific routes.

    Redirects to the login page if the user is not logged in, or
    to the dashboard if the user does not have admin privileges.

    Arguments:
        f (function): The function to wrap.

    Returns:
        function: The wrapped function.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = session.get("username")
        if not user:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("atx.render_login"))

        if "admin" not in session.get("userdata", {}).get('meta').get('role', ""):
            flash("You do not have permission to access this page.", "danger")
            return redirect(url_for("atx.render_home"))

        return f(*args, **kwargs)
    return decorated_function

def superadmin_required(f):
    """
    Decorator to enforce superadmin role for accessing specific routes.

    Redirects to the login page if the user is not logged in, or
    to the dashboard if the user does not have superadmin privileges.

    Arguments:
        f (function): The function to wrap.
    Returns:
        function: The wrapped function.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = session.get("username")
        if not user:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("atx.render_login"))

        if session.get("userdata", {}).get('meta').get('role', "") != "superadmin":
            flash("You do not have permission to access this page.", "danger")
            return redirect(url_for("atx.render_home"))

        return f(*args, **kwargs)
    return decorated_function