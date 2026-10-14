"""
DAST POC - Configuration
=========================
This is the ONLY file you need to edit to point the scan at your application.
"""

# ---------------------------------------------------------------------------
# 1. TARGET - change this to your QA/staging URL.
#    NEVER point this at a production environment without explicit written
#    sign-off from whoever owns that environment.
# ---------------------------------------------------------------------------
TARGET_URL = "https://staging.yourapp.example.com"

# ---------------------------------------------------------------------------
# 2. ZAP CONNECTION - leave as-is if you're running ZAP via docker-compose.yml
# ---------------------------------------------------------------------------
ZAP_API_URL = "http://localhost:8080"

# ---------------------------------------------------------------------------
# 3. AUTHENTICATION (optional) - fill this in if your app sits behind a login.
#    Without this, the scanner can only test the pages a logged-out user sees.
#    Leave LOGIN_URL = None to skip authentication entirely.
# ---------------------------------------------------------------------------
LOGIN_URL = None  # e.g. "https://staging.yourapp.example.com/login"
USERNAME_FIELD = "username"   # the HTML field name on your login form
PASSWORD_FIELD = "password"   # the HTML field name on your login form
TEST_USERNAME = "qa_test_user"
TEST_PASSWORD = "CHANGE_ME"   # use a test account, never a real/prod credential

# ---------------------------------------------------------------------------
# 4. SCAN SCOPE - URLs the scanner should ignore (logout links, 3rd-party
#    widgets, payment gateways, anything you don't own) to avoid noise or
#    accidentally hammering someone else's system.
# ---------------------------------------------------------------------------
EXCLUDE_URL_PATTERNS = [
    r".*logout.*",
    r".*stripe\.com.*",
    r".*google-analytics.*",
]

# ---------------------------------------------------------------------------
# 5. SCAN DEPTH
#    "baseline" = passive only, safe, fast (minutes) - good for CI on every run
#    "full"     = active scan, sends attack payloads, slower (can take hours
#                 on a large app) - good for a scheduled/nightly or one-off run
# ---------------------------------------------------------------------------
SCAN_MODE = "baseline"  # "baseline" or "full"

# ---------------------------------------------------------------------------
# 6. REPORT OUTPUT
# ---------------------------------------------------------------------------
REPORT_DIR = "reports"
