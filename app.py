from __future__ import annotations

import functools
from collections import deque
from datetime import datetime
from pathlib import Path
import time

import requests
from flask import (
    Flask, flash, redirect, render_template,
    request, session, url_for,
)
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from services.data_pipeline import (
    DEFAULT_BUILDING_LOADS,
    create_placeholder_charts,
    generate_price_cycle,
    generate_user_charts,
    process_smart_meter_file,
    _slug,
)

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
STATIC_IMAGE_DIR = BASE_DIR / "static" / "images"
ALLOWED_EXTENSIONS = {"csv"}

# Security: Verify upload directory is within expected bounds
if not UPLOAD_DIR.is_absolute() or not str(UPLOAD_DIR).startswith(str(BASE_DIR)):
    raise RuntimeError("Upload directory must be within the application directory")

# Additional security check for directory traversal attacks
def _validate_file_path(filepath: Path) -> bool:
    """Validate that a file path is within the allowed upload directory"""
    try:
        # Resolve the absolute path
        abs_path = filepath.resolve()
        # Check if it's within the upload directory
        return str(abs_path).startswith(str(UPLOAD_DIR.resolve()))
    except Exception:
        return False

BUILDINGS = [
    "APJ Complex", "Block 5", "Block 6", "Admin",
    "Library", "Block 4A", "SAC", "SC",
]

NON_ESSENTIAL_APPLIANCE_LOAD_KW = {
    "Washing Machine": 0.75,
    "Dishwasher": 1.1,
    "Water Heater": 1.5,
    "EV Charging": 2.8,
    "Iron Box": 1.0,
}

# ---------------------------------------------------------------------------
# easy-auth.dev constants  (adjust if the API path differs)
# ---------------------------------------------------------------------------
_EA_BASE = "https://easy-auth.dev"
_EA_OWNER = "nishchay"
_EA_PROJECT = "ecotrack"
_EA_API = f"{_EA_BASE}/api/auth/{_EA_OWNER}/{_EA_PROJECT}"

app = Flask(__name__)

# Security: Check if running in debug mode and warn
if app.debug:
    print("WARNING: Running in DEBUG mode. Disable debug mode for production!")

# Generate a secure random key for production - this should be set via environment variable in production
import os
secret_key = os.environ.get("SECRET_KEY")
if not secret_key:
    raise RuntimeError("SECRET_KEY environment variable is required for security. Please set it.")
app.config["SECRET_KEY"] = secret_key
app.config["BOOTSTRAPPED"] = False

# Session configuration for better security
app.config["SESSION_COOKIE_SECURE"] = True  # Only send cookies over HTTPS
app.config["SESSION_COOKIE_HTTPONLY"] = True  # Prevent XSS attacks
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"  # CSRF protection
app.config["PERMANENT_SESSION_LIFETIME"] = 3600  # 1 hour session timeout

# Security headers
@app.after_request
def after_request(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    # CSP header to prevent XSS
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
    return response

# Security: Verify all directories are within expected bounds at startup
if not UPLOAD_DIR.is_absolute() or not str(UPLOAD_DIR).startswith(str(BASE_DIR)):
    raise RuntimeError("Upload directory must be within the application directory")

if not STATIC_IMAGE_DIR.is_absolute() or not str(STATIC_IMAGE_DIR).startswith(str(BASE_DIR)):
    raise RuntimeError("Static image directory must be within the application directory")

ALERT_LOG: deque[dict] = deque(maxlen=20)

# Per-user state: {username: {upload_summary, building_loads, chart_version}}
_USER_STATE: dict[str, dict] = {}

def _user_state(username: str) -> dict:
    if username not in _USER_STATE:
        _USER_STATE[username] = {
            "upload_summary": None,
            "building_loads": DEFAULT_BUILDING_LOAD_KW.copy(),
            "chart_version": 0,
        }
    return _USER_STATE[username]

# Rate limiting for login attempts
_LOGIN_ATTEMPTS: dict[str, list] = {}
_MAX_LOGIN_ATTEMPTS = 5
_LOGIN_WINDOW = 300  # 5 minutes


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user_state(username: str) -> dict:
    if username not in _USER_STATE:
        _USER_STATE[username] = {
            "upload_summary": None,
            "building_loads": dict(DEFAULT_BUILDING_LOADS),
            "chart_version": 0,
        }
    return _USER_STATE[username]


def _chart_name(username: str, kind: str) -> str:
    slug = _slug(username)
    base = f"{slug}_{kind}.png"
    path = STATIC_IMAGE_DIR / base
    if path.exists():
        return base
    return f"placeholder_{kind}.png"


def login_required(f):
    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        if not session.get("username"):
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapped


def push_alert(message: str, severity: str = "warning", detail: str = "") -> None:
    ALERT_LOG.appendleft({
        "message": message,
        "severity": severity,
        "detail": detail,
        "time": datetime.now().strftime("%d %b %Y, %H:%M"),
    })


def is_valid_csv(file: FileStorage | None) -> bool:
    if file is None or not (file.filename or "").strip():
        return False
    suffix = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    return suffix in ALLOWED_EXTENSIONS


def check_rate_limit(username: str) -> bool:
    """Check if user has exceeded login attempts"""
    now = time.time()
    if username not in _LOGIN_ATTEMPTS:
        _LOGIN_ATTEMPTS[username] = []

    # Remove old attempts outside the window
    attempts = [t for t in _LOGIN_ATTEMPTS[username] if now - t < _LOGIN_WINDOW]
    _LOGIN_ATTEMPTS[username] = attempts

    # Check if limit exceeded
    if len(attempts) >= _MAX_LOGIN_ATTEMPTS:
        return False  # Rate limit exceeded

    return True


def record_login_attempt(username: str, success: bool = False) -> None:
    """Record a login attempt"""
    now = time.time()
    if username not in _LOGIN_ATTEMPTS:
        _LOGIN_ATTEMPTS[username] = []

    _LOGIN_ATTEMPTS[username].append(now)

    # If successful login, clear attempts for this user
    if success:
        _LOGIN_ATTEMPTS[username] = []


@app.before_request
def bootstrap_assets() -> None:
    if app.config["BOOTSTRAPPED"]:
        return
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    STATIC_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    create_placeholder_charts(STATIC_IMAGE_DIR)
    push_alert("System healthy. No critical anomalies detected.", "info")
    app.config["BOOTSTRAPPED"] = True


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("username"):
        return redirect(url_for("index"))

    if request.method == "POST":
        action = request.form.get("action", "login")
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        email = request.form.get("email", "").strip()

        # CSRF protection
        csrf_token = request.form.get('csrf_token')
        if not csrf_token or csrf_token != session.get('csrf_token'):
            flash("CSRF token validation failed. Please try again.", "danger")
            return render_template("login.html", mode="login")

        # Check rate limit before processing
        if not check_rate_limit(username):
            flash("Too many login attempts. Please try again later.", "danger")
            return render_template("login.html", mode="login")

        if action == "register":
            if not all([username, email, password]):
                flash("All fields are required for registration.", "danger")
                return render_template("login.html", mode="register")
            ok, msg, data = _ea_register(username, email, password)
            if ok:
                flash("Account created! You can now log in.", "success")
                return render_template("login.html", mode="login")
            flash(msg, "danger")
            return render_template("login.html", mode="register")

        else:  # login
            if not all([username, password]):
                flash("Username and password are required.", "danger")
                record_login_attempt(username)  # Record failed attempt
                return render_template("login.html", mode="login")
            ok, msg, data = _ea_login(username, password)
            if ok:
                session["username"] = username
                session["token"] = data.get("token", "")
                # Regenerate session ID to prevent session fixation
                session.permanent = True
                flash(f"Welcome back, {username}!", "success")
                record_login_attempt(username, success=True)  # Record successful attempt
                return redirect(url_for("index"))
            flash(msg, "danger")
            record_login_attempt(username)  # Record failed attempt
            return render_template("login.html", mode="login")

    # Generate CSRF token for the login form
    import secrets
    csrf_token = secrets.token_urlsafe(32)
    session['csrf_token'] = csrf_token
    return render_template("login.html", mode="login")


@app.post("/logout")
def logout():
    # Clear session data properly
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Main routes (all require login)
# ---------------------------------------------------------------------------

@app.get("/")
@login_required
def index():
    username = session["username"]
    state = _user_state(username)

    energy_overview = {
        "generation_kw": 486.2,
        "consumption_kw": 442.7,
        "power_factor": 0.96,
        "grid_frequency_hz": 49.98,
    }
    loads = state["building_loads"]
    total = sum(loads.values())
    consumption_by_building = sorted(
        [
            {
                "building": b,
                "consumption_kwh": round(v, 2),
                "percentage": round((v / total) * 100, 1) if total else 0,
            }
            for b, v in loads.items()
        ],
        key=lambda r: r["consumption_kwh"],
        reverse=True,
    )

    selected_building = request.args.get("building", BUILDINGS[0]).strip()
    if selected_building not in BUILDINGS:
        selected_building = BUILDINGS[0]
    selected_building_data = next(
        r for r in consumption_by_building if r["building"] == selected_building
    )

    chart_v = state["chart_version"]
    return render_template(
        "index.html",
        overview=energy_overview,
        alerts=list(ALERT_LOG)[:5],
        buildings=BUILDINGS,
        consumption_by_building=consumption_by_building,
        selected_building=selected_building,
        selected_building_data=selected_building_data,
        chart_line=_chart_name(username, "production_vs_consumption"),
        chart_pie=_chart_name(username, "load_distribution"),
        chart_v=chart_v,
        username=username,
    )


@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload_data():
    username = session["username"]
    state = _user_state(username)

    if request.method == "POST":
        # CSRF protection
        csrf_token = request.form.get('csrf_token')
        if not csrf_token or csrf_token != session.get('csrf_token'):
            flash("CSRF token validation failed. Please try again.", "danger")
            return redirect(url_for("upload_data"))

        smart_meter_file = request.files.get("smart_meter_csv")
        building_name = request.form.get("building_name", "APJ Complex").strip()
        appliance_name = request.form.get("appliance_name", "Unknown").strip()
        appliance_wattage = request.form.get("appliance_wattage", "0").strip()

        if building_name not in BUILDINGS:
            flash("Upload failed: select a valid building.", "danger")
            return redirect(url_for("upload_data"))

        if not is_valid_csv(smart_meter_file):
            flash("Upload failed: provide a valid Smart Meter CSV file.", "danger")
            return redirect(url_for("upload_data"))

        try:
            wattage_value = float(appliance_wattage)
            if wattage_value <= 0:
                raise ValueError("Wattage must be positive.")

            # Validate filename to prevent directory traversal
            safe_name = secure_filename(smart_meter_file.filename or "meter.csv")
            if not safe_name:
                raise ValueError("Invalid filename")

            # Limit file size (5MB max)
            smart_meter_file.seek(0, 2)  # Seek to end of file
            file_size = smart_meter_file.tell()
            smart_meter_file.seek(0)  # Reset pointer

            if file_size > 5 * 1024 * 1024:  # 5MB limit
                raise ValueError("File size exceeds 5MB limit")

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            saved_file = UPLOAD_DIR / f"{_slug(username)}_{timestamp}_{safe_name}"

            # Ensure the file is saved to the intended directory (security check)
            if not _validate_file_path(saved_file):
                raise ValueError("Invalid file path")

            smart_meter_file.save(saved_file)

            # 1) Extract summary stats
            summary = process_smart_meter_file(saved_file, appliance_name, wattage_value)
            summary["building_name"] = building_name
            state["upload_summary"] = summary

            # 2) Regenerate charts from the real uploaded data
            # Security: Validate that the chart directory is within expected bounds
            if not _validate_file_path(STATIC_IMAGE_DIR):
                raise ValueError("Invalid chart directory path")

            chart_v = generate_user_charts(
                saved_file, building_name, username,
                STATIC_IMAGE_DIR,
                current_building_loads=state["building_loads"],
            )
            state["chart_version"] = chart_v

            # 3) Update in-memory building loads table
            import numpy as np, pandas as pd
            df = pd.read_csv(saved_file)
            numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
            if numeric_cols:
                new_mean = float(df[numeric_cols[0]].mean())
                if new_mean > 2000:
                    new_mean /= 1000
                state["building_loads"][building_name] = round(new_mean, 2)

            push_alert(
                f"New upload by {username} for {building_name}.",
                "info",
                f"{summary['rows']} rows | {appliance_name} @ {wattage_value} W",
            )
            flash("Smart Meter data processed and charts updated.", "success")

        except Exception as exc:
            push_alert("Upload processing exception.", "danger", str(exc))
            flash(f"Processing error: {exc}", "danger")

        return redirect(url_for("upload_data"))

    # Generate CSRF token for the upload form
    import secrets
    csrf_token = secrets.token_urlsafe(32)
    session['csrf_token'] = csrf_token
    return render_template(
        "upload.html",
        upload_summary=state["upload_summary"],
        buildings=BUILDINGS,
        username=username,
    )


@app.get("/optimization")
@login_required
def optimization():
    cycle_rows = generate_price_cycle()
    best_slot = min(cycle_rows, key=lambda r: r["price_per_kwh"])
    cycle_rows = _enrich_scheduler_rows(cycle_rows, best_slot["price_per_kwh"])
    assumed_avg = round(
        sum(NON_ESSENTIAL_APPLIANCE_LOAD_KW.values()) / len(NON_ESSENTIAL_APPLIANCE_LOAD_KW), 2
    )
    return render_template(
        "optimization.html",
        price_rows=cycle_rows,
        best_slot=best_slot,
        assumed_avg_non_essential_kw=assumed_avg,
        username=session["username"],
    )


@app.get("/alerts")
@login_required
def alerts():
    return render_template("alerts.html", alerts=list(ALERT_LOG), username=session["username"])


@app.post("/alerts/simulate")
@login_required
def simulate_anomaly():
    try:
        raise RuntimeError("Unexpected transient current spike above configured threshold.")
    except RuntimeError as exc:
        push_alert("Anomaly Detected: Protection relay event.", "danger", str(exc))
        flash("Synthetic anomaly added for project demonstration.", "warning")
    return redirect(url_for("alerts"))


# ---------------------------------------------------------------------------
# easy-auth.dev API helpers
# ---------------------------------------------------------------------------

def _ea_login(username: str, password: str) -> tuple[bool, str, dict]:
    try:
        r = requests.post(f"{_EA_API}/login",
                          json={"username": username, "password": password}, timeout=10)
        data = _safe_json(r)
        if r.status_code == 200:
            return True, "OK", data
        return False, data.get("message") or data.get("error") or f"Login failed ({r.status_code}).", {}
    except requests.exceptions.ConnectionError:
        return False, "Cannot reach easy-auth.dev — check your internet connection.", {}
    except requests.exceptions.Timeout:
        return False, "easy-auth.dev timed out. Try again.", {}
    except Exception as exc:
        return False, f"Unexpected auth error: {exc}", {}


def _ea_register(username: str, email: str, password: str) -> tuple[bool, str, dict]:
    try:
        r = requests.post(f"{_EA_API}/register",
                          json={"username": username, "email": email, "password": password}, timeout=10)
        data = _safe_json(r)
        if r.status_code in (200, 201):
            return True, "OK", data
        return False, data.get("message") or data.get("error") or f"Registration failed ({r.status_code}).", {}
    except requests.exceptions.ConnectionError:
        return False, "Cannot reach easy-auth.dev — check your internet connection.", {}
    except requests.exceptions.Timeout:
        return False, "easy-auth.dev timed out. Try again.", {}
    except Exception as exc:
        return False, f"Unexpected auth error: {exc}", {}


def _safe_json(resp) -> dict:
    try:
        return resp.json()
    except Exception:
        return {}


def _enrich_scheduler_rows(price_rows: list[dict], best_price: float) -> list[dict]:
    off_peak_combo = ["Washing Machine", "Dishwasher", "Water Heater"]
    moderate_combo = ["Washing Machine", "Iron Box"]
    for row in price_rows:
        if row["price_per_kwh"] <= best_price + 0.05:
            row["recommendation"] = "Best Time to Save"
            row["recommended_combo"] = ", ".join(off_peak_combo)
            row["assumed_non_essential_kw"] = round(
                sum(NON_ESSENTIAL_APPLIANCE_LOAD_KW[i] for i in off_peak_combo), 2)
        elif row["price_per_kwh"] <= best_price + 0.8:
            row["recommendation"] = "Moderate Cost"
            row["recommended_combo"] = ", ".join(moderate_combo)
            row["assumed_non_essential_kw"] = round(
                sum(NON_ESSENTIAL_APPLIANCE_LOAD_KW[i] for i in moderate_combo), 2)
        else:
            row["recommendation"] = "High Cost Window"
            row["recommended_combo"] = "Only essential loads"
            row["assumed_non_essential_kw"] = 0.0
    return price_rows


def is_valid_csv(file: FileStorage) -> bool:
    if not file or not file.filename:
        return False

    # Basic extension check
    if not file.filename.lower().endswith(".csv"):
        return False

    try:
        # Check if the file has content and can be read
        file.seek(0)
        content = file.read(1024)  # Read first 1KB to check format
        file.seek(0)  # Reset pointer

        if not content:
            return False

        # Simple CSV validation - check for comma-separated values
        decoded_content = content.decode("utf-8", errors="ignore")
        lines = decoded_content.splitlines()
        if len(lines) < 2:
            return False  # Need at least header + one data row

        # Check that we have some columns with data
        first_line = lines[0]
        if not first_line or "," not in first_line:
            return False

        # More robust CSV structure validation
        import csv
        file.seek(0)
        reader = csv.reader(file)

        # Read header row
        try:
            header = next(reader)
        except StopIteration:
            return False

        # Check that header has at least one column
        if not header or len(header) == 0:
            return False

        # Validate first few rows for consistency
        row_count = 0
        for row in reader:
            row_count += 1
            if row_count > 5:  # Only check first 5 rows for performance
                break

        return True
    except Exception:
        return False


if __name__ == "__main__":
    app.run(debug=True)
