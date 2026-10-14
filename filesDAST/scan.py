"""
DAST POC - Scan Runner
======================
Drives OWASP ZAP against the target in config.py and writes an HTML + JSON
report to the reports/ folder.

Usage:
    1. docker compose up -d          # starts ZAP
    2. pip install -r requirements.txt
    3. python scan.py
"""

import os
import sys
import time
import json
import datetime

from zapv2 import ZAPv2

import config


def wait_for_zap(zap, timeout=60):
    print("Waiting for ZAP to be ready...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            if zap.core.version:
                print(f"ZAP is up (version {zap.core.version})")
                return
        except Exception:
            pass
        time.sleep(2)
    print("ERROR: ZAP did not respond in time. Is 'docker compose up -d' running?")
    sys.exit(1)


def set_scope_exclusions(zap):
    for pattern in config.EXCLUDE_URL_PATTERNS:
        zap.spider.exclude_from_scan(pattern)
        zap.ascan.exclude_from_scan(pattern)
    if config.EXCLUDE_URL_PATTERNS:
        print(f"Excluded {len(config.EXCLUDE_URL_PATTERNS)} URL pattern(s) from scope.")


def authenticate_if_configured(zap):
    """Very small helper for form-based auth. For anything more complex
    (SSO, MFA, token-based), use ZAP's context/auth scripts or feed ZAP a
    pre-authenticated session cookie captured from Playwright instead."""
    if not config.LOGIN_URL:
        print("No LOGIN_URL configured - scanning as an unauthenticated user.")
        return

    print(f"Attempting form-based login at {config.LOGIN_URL} ...")
    context_name = "dast-poc-context"
    context_id = zap.context.new_context(context_name)
    zap.context.include_in_context(context_name, f"{config.TARGET_URL}.*")

    login_request_data = (
        f"{config.USERNAME_FIELD}={{%username%}}&{config.PASSWORD_FIELD}={{%password%}}"
    )
    zap.authentication.set_authentication_method(
        contextid=context_id,
        authmethodname="formBasedAuthentication",
        authmethodconfigparams=(
            f"loginUrl={config.LOGIN_URL}&loginRequestData={login_request_data}"
        ),
    )

    user_id = zap.users.new_user(context_id, "qa-poc-user")
    zap.users.set_authentication_credentials(
        context_id,
        user_id,
        f"username={config.TEST_USERNAME}&password={config.TEST_PASSWORD}",
    )
    zap.users.set_user_enabled(context_id, user_id, "true")
    zap.forcedUser.set_forced_user(context_id, user_id)
    zap.forcedUser.set_forced_user_mode_enabled("true")
    print("Authentication configured.")


def run_spider(zap):
    print(f"Spidering {config.TARGET_URL} to discover pages...")
    scan_id = zap.spider.scan(config.TARGET_URL)
    while int(zap.spider.status(scan_id)) < 100:
        print(f"  Spider progress: {zap.spider.status(scan_id)}%")
        time.sleep(3)
    print("Spider complete.")


def run_passive_scan_wait(zap):
    print("Waiting for passive scan to finish analyzing discovered traffic...")
    while int(zap.pscan.records_to_scan) > 0:
        print(f"  Records remaining: {zap.pscan.records_to_scan}")
        time.sleep(2)
    print("Passive scan complete.")


def run_active_scan(zap):
    print(f"Starting ACTIVE scan against {config.TARGET_URL} (this sends attack payloads)...")
    scan_id = zap.ascan.scan(config.TARGET_URL)
    while int(zap.ascan.status(scan_id)) < 100:
        print(f"  Active scan progress: {zap.ascan.status(scan_id)}%")
        time.sleep(5)
    print("Active scan complete.")


def generate_reports(zap):
    os.makedirs(config.REPORT_DIR, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    html_report = zap.core.htmlreport()
    html_path = os.path.join(config.REPORT_DIR, f"dast_report_{timestamp}.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_report)

    alerts = zap.core.alerts(baseurl=config.TARGET_URL)
    json_path = os.path.join(config.REPORT_DIR, f"dast_findings_{timestamp}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(alerts, f, indent=2)

    summary = {}
    for alert in alerts:
        risk = alert.get("risk", "Unknown")
        summary[risk] = summary.get(risk, 0) + 1

    print("\n" + "=" * 50)
    print("SCAN SUMMARY")
    print("=" * 50)
    for risk in ["High", "Medium", "Low", "Informational"]:
        print(f"  {risk}: {summary.get(risk, 0)}")
    print(f"\nFull HTML report: {html_path}")
    print(f"Raw findings JSON: {json_path}")
    print("=" * 50)

    return html_path, json_path, summary


def main():
    zap = ZAPv2(apikey=None, proxies={
        "http": config.ZAP_API_URL,
        "https": config.ZAP_API_URL,
    })

    wait_for_zap(zap)
    set_scope_exclusions(zap)
    authenticate_if_configured(zap)
    run_spider(zap)
    run_passive_scan_wait(zap)

    if config.SCAN_MODE == "full":
        run_active_scan(zap)
    else:
        print("SCAN_MODE is 'baseline' - skipping active scan (passive findings only).")
        print("Set SCAN_MODE = 'full' in config.py to run attack payloads.")

    generate_reports(zap)


if __name__ == "__main__":
    main()
