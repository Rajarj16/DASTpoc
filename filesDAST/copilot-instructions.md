# GitHub Copilot Instructions — DAST POC

GitHub Copilot (Chat, inline suggestions, and Copilot coding agent) reads this
file automatically for repo-wide context — you don't need to paste it in.
This describes what the project does, how it's structured, and exactly what
Copilot should help you change to point it at your own web application.

---

## 1. What this project is

An automated DAST (Dynamic Application Security Testing) proof-of-concept.
It drives OWASP ZAP (an open-source security scanner) against a *running*
web application — no source code access, it just interacts with the app
over HTTP the way a browser or an attacker would — and produces an HTML +
JSON report of findings ranked by risk (High / Medium / Low / Informational).

It is designed to sit next to existing Playwright (functional) and k6
(performance) test suites as a third, security-focused pillar of the same
QA pipeline.

This is a **defensive security tool**. It only scans applications the user
owns or is explicitly authorized to test. It does not perform social
engineering, exploit development, or anything outside standard
vulnerability scanning.

## 2. File-by-file map

| File | Purpose | Do you normally edit it? |
|---|---|---|
| `config.py` | Every setting for YOUR application: target URL, login, scope exclusions, scan depth | **Yes — this is the primary file to change** |
| `scan.py` | Orchestrates ZAP: spider → passive scan → (optional) active scan → report | Rarely — only for new auth types or custom logic |
| `docker-compose.yml` | Runs the ZAP daemon locally on port 8080 | No, unless you need to change the port |
| `requirements.txt` | Python dependency (`zaproxy` — the ZAP API client) | No |
| `README.md` | Human-readable setup and usage guide | Keep in sync if you change workflow |
| `reports/` | Generated output (HTML + JSON), created at runtime | Never commit scan results — see `.gitignore` guidance below |

## 3. How to adapt this to YOUR application — step by step (A to Z)

This is the exact sequence Copilot should walk through with the user, or do
directly if asked ("adapt this repo to my application, here are the
details: ...").

### A. Target URL
In `config.py`, set:
```python
TARGET_URL = "https://<your-staging-or-qa-url>"
```
Never set this to a production URL unless the user explicitly confirms they
have written authorization to scan production.

### B. Authentication — pick ONE pattern based on what the user describes

**B1. Standard HTML form login** (username + password fields, no SSO/MFA)
Already implemented in `scan.py` via `authenticate_if_configured()`. Just
fill in `config.py`:
```python
LOGIN_URL = "https://.../login"
USERNAME_FIELD = "<name attribute of the username <input>>"
PASSWORD_FIELD = "<name attribute of the password <input>>"
TEST_USERNAME = "..."
TEST_PASSWORD = "..."   # a dedicated QA test account, never a real user's credentials
```
To find the field names: open the login page's HTML (DevTools → inspect the
input elements) and copy the `name="..."` attribute, not the `id` or label.

**B2. SSO / OAuth / MFA** (Okta, Azure AD, Google login, anything with a
redirect or a second factor) — form-based auth in B1 will NOT work. Instead:
1. Log in to the app manually once (or via the existing Playwright script).
2. Capture the session cookie(s) after login (Playwright: `page.context().cookies()`, or DevTools → Application → Cookies).
3. In `scan.py`, replace the `authenticate_if_configured()` call with code
   that injects the captured cookie into ZAP's session, e.g.:
   ```python
   zap.httpsessions.add_session_token(config.TARGET_URL, "session_token")
   zap.httpsessions.set_session_token_value(config.TARGET_URL, "<session-name>", "<cookie-value>")
   ```
   Ask the user for their exact cookie name (often `session`, `sid`, `JSESSIONID`,
   or an `Authorization: Bearer <token>` header instead — if it's a bearer
   token, set it as a ZAP "Replacer" rule on the `Authorization` header
   instead of a cookie).
4. Session cookies expire — for a recurring CI job, automate step 2 with a
   small Playwright login script that runs before `scan.py` and writes the
   fresh cookie to a file `scan.py` reads at startup. If the user wants
   this, write a `get_session.py` helper that does exactly that.

**B3. API-only / token-based app** (SPA calling a REST or GraphQL backend)
Point `TARGET_URL` at the API base URL, and consider importing an OpenAPI/
Swagger spec via `zap.openapi.import_url(...)` instead of relying on the
spider, since spiders don't navigate JS-heavy SPAs well. Ask the user if
they have a Swagger/OpenAPI JSON URL before writing custom crawl logic.

### C. Scope — what NOT to scan
Add to `EXCLUDE_URL_PATTERNS` in `config.py`:
- Logout endpoints (scanning would keep logging the session out)
- Any third-party domain embedded in the page (payment gateways, analytics,
  chat widgets) — the user does not own these and must not scan them
- Any destructive endpoint (account deletion, mass email send, etc.) if
  running in `"full"` (active) mode

Ask the user explicitly: "Does your staging environment have any endpoints
that send real emails/SMS, charge real money, or are shared with other
teams?" Exclude those before enabling active scan.

### D. Scan depth
- `SCAN_MODE = "baseline"` — passive only, safe for every CI run, minutes.
- `SCAN_MODE = "full"` — active scan, sends real attack payloads, can take
  significantly longer on a large app and should only run against
  staging/QA, ideally on a schedule (nightly) rather than every commit.

### E. CI integration (if asked)
Add a job that runs after the existing Playwright/k6 stages:
```yaml
# example GitHub Actions step
- name: Start ZAP
  run: docker compose up -d
- name: Wait for ZAP
  run: sleep 15
- name: Run DAST scan
  run: python scan.py
- name: Upload report
  uses: actions/upload-artifact@v4
  with:
    name: dast-report
    path: reports/
```
Keep `SCAN_MODE = "baseline"` for per-commit CI; use a separate scheduled
workflow with `SCAN_MODE = "full"` for nightly/weekly deep scans.

### F. Report handling
- Add `reports/` to `.gitignore` — scan results can contain sensitive
  details about real vulnerabilities and should not live in git history.
- If the user wants automated email of the report, that's a separate
  approval-gated step (see the project's chat history / manager notes) —
  do not wire up auto-send without an explicit human-approval gate.

## 4. Things Copilot should NOT do in this repo

- Do not write active exploit code beyond what ZAP's built-in scanners
  already do (e.g. don't hand-craft a working SQLi payload chain "to
  verify" a finding — that crosses from scanning into exploitation).
- Do not set `TARGET_URL` to a domain not explicitly provided by the user.
- Do not remove or weaken `EXCLUDE_URL_PATTERNS` without the user asking.
- Do not commit real credentials to `config.py` — if the user pastes real
  values, remind them to use environment variables instead:
  ```python
  import os
  TEST_PASSWORD = os.environ.get("DAST_TEST_PASSWORD")
  ```

## 5. Quick prompts the user can give Copilot Chat directly

- "Here's my app's login page HTML, fill in `config.py` for me: `<paste>`"
- "My app uses Okta SSO — help me write `get_session.py` to capture a
  cookie with Playwright and feed it to `scan.py`"
- "Add a GitHub Actions workflow that runs this nightly in full mode
  against staging and uploads the report"
- "My app is a SPA with a Swagger spec at `/api/docs/swagger.json` — adjust
  the scan to import that instead of spidering"
