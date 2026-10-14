# DAST POC (OWASP ZAP)

Automated security scanning of a running web application. This does **not**
touch source code — it attacks the live app the way a basic external attacker
would, the same way your Playwright tests click through it as a user.

## Before you run this anywhere
Only run this against an application your company owns and has approved for
testing (staging/QA, not production, unless you have written sign-off).

## Setup on your office laptop
1. Install Docker Desktop and Python 3.9+.
2. `git clone <your-repo>` then `cd dast-poc`
3. `pip install -r requirements.txt`
4. `docker compose up -d` — starts OWASP ZAP locally on port 8080
5. Edit **`config.py`** — this is the only file you need to change:
   - `TARGET_URL` → your staging URL
   - `LOGIN_URL` / `USERNAME_FIELD` / `PASSWORD_FIELD` / test credentials, if your app needs login (skip if not)
   - `EXCLUDE_URL_PATTERNS` → add logout links, payment gateways, any third-party domains
   - `SCAN_MODE` → `"baseline"` for a safe first run, `"full"` once you're confident in scope
6. `python scan.py`
7. Open the generated file in `reports/dast_report_<timestamp>.html`

## What changes for YOUR application
Everything you need is in `config.py`:
- **URL**: swap `TARGET_URL`
- **Login**: if your app has a standard HTML login form, fill in the 4 auth
  fields. If it uses SSO/OAuth/MFA, form-based auth won't work — instead,
  log in once via Playwright, grab the session cookie, and set it on the ZAP
  session (ask me and I'll add that variant).
- **Scope**: add anything you don't want scanned to `EXCLUDE_URL_PATTERNS`
- Nothing else in `scan.py` needs to change for a standard app.

## Reading the output
Each finding has a risk level: **High / Medium / Low / Informational**.
Start by triaging High and Medium only — Low/Informational are often noise
(missing security headers, etc.) worth fixing later, not blockers.

## Adapting this repo with GitHub Copilot
This repo includes `.github/copilot-instructions.md` — GitHub Copilot reads
it automatically (Chat, inline suggestions, and Copilot coding agent) once
you push this to a repo and open it in VS Code / GitHub. It tells Copilot
exactly how to adapt `config.py` and `scan.py` to your application —
including SSO/OAuth logins, SPAs with Swagger specs, and CI wiring. Once
pushed, just open Copilot Chat and ask things like:
- "Here's my app's login page HTML, fill in config.py for me: `<paste>`"
- "My app uses Okta SSO, help me capture a session cookie for this"
- "Add a GitHub Actions workflow that runs this nightly against staging"

## Baseline vs Full scan
- **Baseline** (passive): just reads traffic, flags issues, never sends
  attack payloads. Safe to run on every CI build.
- **Full** (active): sends real attack strings (SQL injection attempts, XSS
  payloads, etc.) at your app's inputs. Can create junk data or trip alerts
  — only run against staging, and tell whoever monitors that environment
  before you run it the first time.
