# Security model

What Outlogik does to protect accounts and tenant data in Phase 1, and what a production
deployment must add. Each item is covered by backend or frontend tests unless noted.

## Accounts and sessions

- **Passwords:** Argon2id (argon2-cffi defaults), at least 10 characters, rehashed on login
  if the parameters change. Login takes the same time whether or not the email exists.
- **Sessions:** server-side, in PostgreSQL. The browser holds a random 256-bit token in an
  `HttpOnly`, `Secure`, `SameSite=Lax` cookie; only its SHA-256 hash is stored. Sessions expire
  after 24 hours idle or 14 days in total (configurable). Login replaces the browser's existing
  session.
- **Revocation:** logout, "sign out of all devices", a password reset, deactivating a user or
  disabling a membership take effect on the next request.
- **One-time tokens** (password reset, email confirmation, invitations) are 256-bit random,
  stored only as hashes, single-use and time-limited (1 hour, 48 hours, 7 days). Only the
  newest reset link works. The frontend removes tokens from the address bar after reading
  them and sends no referrer to other sites.
- **No account enumeration:** login errors and "forgot password" responses are identical
  whether or not the email exists.
- **Rate limits** (Redis): login per email and per IP, registration, password reset,
  invitation preview and acceptance, resending confirmation emails. If Redis is down the
  limiter lets requests through and logs a warning, rather than locking everyone out.
- **Super Admins** can only be created with the CLI.
- **Sign-up is invite-only by default** (`SIGNUP_MODE=invite_only`): clients and staff join through invitations, and organizations are created with the CLI.

## Requests

- **CSRF:** double-submit token. Every state-changing `/api/` request must echo the
  `XSRF-TOKEN` cookie in the `X-XSRF-TOKEN` header; Angular does this automatically.
- **Security headers** on every API response: `X-Content-Type-Options: nosniff`,
  `X-Frame-Options: DENY`, `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'`,
  `Referrer-Policy: no-referrer`, `Cross-Origin-Resource-Policy: same-origin`,
  `Cache-Control: no-store`.
- **Input validation** with Pydantic on every request; search terms escape SQL `LIKE`
  wildcards; sorting accepts whitelisted fields only.
- **Open redirects:** after sign-in the app only navigates to same-app paths.

## Tenant isolation and permissions

- Every organization endpoint lives under `/orgs/{slug}/…` and resolves the organization
  through one dependency. A non-member, or a disabled member, gets **404**, identical to an
  organization that doesn't exist.
- Rows are always loaded filtered by `organization_id`. Using another organization's IDs for
  any object (member, role, client, website, invitation, portal user) returns 404 and changes
  nothing. Tests try each of these.
- **Permissions:** each endpoint declares exactly one; a test fails the build if one doesn't,
  and another runs every built-in role against every endpoint.
- **No privilege escalation:** you can only assign or invite with a role whose permissions you
  hold. Only owners grant Owner, or change, disable or remove owners. The last owner can't be
  removed, demoted or leave. Nobody can change their own role or status.
- **Client-portal users** see only the clients they're linked to and those clients' websites.
  Internal notes and team information are never sent to them.
- **Audit log:** sensitive actions are recorded with actor, target, details and IP.

## Outlogik staff and the public API

- **Staff roles** (`content_editor`, `site_admin`) give access to the admin area for the marketing website. They're separate from organization roles, granted only by CLI, and audited. Super Admins count as site admins.
- **Admin endpoints** (`/api/v1/admin/…`) return 404 to anyone without a staff role, so their existence isn't revealed. A test fails the build if an admin route lacks the staff check.
- **Public endpoints** (`/api/v1/public/…`) need no sign-in and return only data meant to be public. Form submissions arrive with the forms (Phase 1.5 step 6), with origin checks, honeypot, timing and rate limits.
- **The marketing site's server** sends `nosniff`, `X-Frame-Options: DENY`, a referrer policy and a permissions policy, and doesn't announce Express. Its Content-Security-Policy is added in Phase 1.5 step 12.

## Website addresses

Website URLs are normalised. IP addresses, `localhost`, single-label hosts, internal suffixes
(`.local`, `.internal`, `.lan`, …) and URLs containing credentials are refused. **This is not
enough on its own:** the Phase 2 crawler must also resolve each hostname and refuse private,
loopback and link-local addresses at fetch time (SSRF).

## Website forms

The consultation, contact and newsletter forms post to `/api/v1/public/*` through the website's
own server, so the browser never talks to the API host.

- **No CSRF token:** these endpoints never read the session cookie, so CSRF doesn't apply.
  Everything else under `/api/` still requires the token.
- **Origin check:** requests must carry the website's `Origin` (`SITE_URL`, plus
  `PUBLIC_FORM_EXTRA_ORIGINS`); anything else gets 403.
- **Spam checks, with no third-party CAPTCHA:**
  - a hidden honeypot field
  - a minimum time the form must be open (`FORM_MIN_SECONDS`, 3 seconds)
  - Spam is stored with status `spam` for review, never emailed, and the sender sees the usual
    success message.
- **Content and email checks** (`backend/app/modules/leads/spam.py`), which flag as spam:
  - more than 2 links, HTML or forum link code in the message, or a link in the name
  - an address from a throwaway email service
  - an email domain that can't receive email, checked by DNS and cached. A failed lookup
    flags nothing, and if DNS itself looks broken (gmail.com can't be resolved) the check is
    skipped.
  - Newsletter sign-ups from such addresses are ignored.
- **Duplicates:** the same email sending the same form again within 24 hours adds a
  "Website" note to the earlier lead, keeping any new message, instead of creating a new lead
  or emailing anyone again.
- **Rate limits:** 5 submissions per IP address per 10 minutes, and 3 per email address per
  hour.
- **Strict validation:**
  - unknown fields are rejected
  - choices must be from fixed lists
  - lengths are capped
  - the proxy refuses bodies over 32 kB
- **Newsletter (CASL):**
  - an unticked consent box
  - the exact wording is stored with the date
  - double opt-in by email
  - an unsubscribe link in every email
  - Only token hashes are stored.
  - Confirm and unsubscribe need a button click, so link scanners can't trigger them.
  - The form responds identically whether or not an address is already subscribed.
- **Visit attribution:**
  - UTM tags, referrer and landing page are kept in the visitor's `sessionStorage`
  - no cookies are set
  - nothing is sent until a form is submitted
- **What's stored with a lead:** the form fields, the attribution, the IP address and the
  browser's user agent (for spam review). The privacy policy (step 12) must say so.

## Website: Content-Security-Policy and analytics

- Every page has a **nonce-based CSP**: a fresh nonce per response, added to every script tag by the website's server, with `'strict-dynamic'`, `object-src 'none'`, `base-uri 'self'`, `form-action 'self'` and `frame-ancestors 'none'`. Inline styles are allowed; inline scripts without the nonce are not. Helpers: `frontend/projects/marketing/src/csp.ts`.
- **Analytics** (GA4, GTM, Clarity) are off unless an ID is set in the admin area, and load only after a visitor accepts in the cookie banner. The only cookie the site sets itself is `ol_consent`, which remembers that choice.

## Website admin area

- `/api/v1/admin/*` needs a signed-in **site admin** (or super admin); everyone else gets 404. A test checks every admin route for a staff dependency.
- **Audited:** lead status changes, lead deletion, both CSV exports (with the number of rows), subscriber deletion, settings and portal feature changes. Audit entries for deletions hold no personal details.
- **CSV exports** neutralise cells starting with `=`, `+`, `-` or `@`, so spreadsheets don't run them as formulas, and are sent with `Cache-Control: no-store`.
- **Visitor input** is shown as text, never HTML. A visitor's website address becomes a link only as `http(s)`, and opens with `rel="noopener noreferrer"`.

## Production (DigitalOcean App Platform, Toronto)

Set up in step 14; the launch steps are in [`DEPLOYMENT.md`](DEPLOYMENT.md).

- [x] The Angular app and `/api` share **one origin** (`app.outlogik.com`, `/api` routed to the
      API), behind HTTPS (App Platform), with **HSTS** from all three services.
- [x] **Content-Security-Policy for the app** (nginx, `frontend/docker/app/`): `script-src 'self'`
      plus the SHA-256 hashes of the two inline scripts, computed from each build. The build
      fails if an inline event handler appears. The website has its own nonce-based CSP.
- [x] **Real visitor IPs:** the API reads the platform's header (`CLIENT_IP_HEADER`,
      `do-connecting-ip`), and trusts the website's forwarded visitor IP only with the shared
      `SITE_PROXY_SECRET`. A forged header without the secret is ignored. Uvicorn's own
      proxy-header handling stays at its safe default.
- [x] Website built with the real `OL_APP_URL` and `OL_SITE_URL`. Angular's server renders only
      for known host names (`security.allowedHosts`); anything else is redirected to
      `CANONICAL_HOST`.
- [x] Staging runs with `SITE_NOINDEX=true`.
- [x] `COOKIE_SECURE=true`, `FRONTEND_URL` and `SITE_URL` set in the app specs.
- [x] The **interactive API docs and OpenAPI schema are off** when `APP_ENV=production`.
- [x] **Containers run as non-root users** (`outlogik`, `node`, nginx-unprivileged).
- [x] **Secrets** (`SITE_PROXY_SECRET`, `SMTP_PASSWORD`) are App Platform encrypted secrets,
      never in the repository. Database URLs are injected from the managed clusters.
- [x] **Database backups:** managed PostgreSQL, with daily backups and 7-day point-in-time
      recovery. A restore test is in the launch checklist.
- [x] **Dependency audit** (step 14): `npm audit` and `pip-audit` found no known vulnerabilities.
- [ ] **Email:** Resend (port 2587) with SPF, DKIM and DMARC for outlogik.com (launch guide,
      step 3).
- [ ] Set `LEAD_NOTIFICATION_EMAILS` to the enquiries alias (decision 15).
- [ ] Optional later: PostgreSQL row-level security as a second isolation layer; MFA (the
      schema already has room for it).
