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
- **Sign-in lockout** (Redis):
  - Only **failed** attempts count: 5 on one account, or 20 from one IP address, within
    15 minutes lock sign-in for the rest of that window (`429` with `Retry-After`).
  - A successful sign-in clears the account's count, so people who sign in often are never
    locked out.
  - A failed browser check also counts as a failure.
- **Bot check on the app's sign-in forms:** sign-in, forgot password and accepting an
  invitation need the same invisible proof of work as the website's forms (see Website forms).
  Requests without a valid proof get `400 bot_check_failed`.
- **Other rate limits:** registration, password reset, invitation preview and acceptance,
  resending confirmation emails. If Redis is down the limiter lets requests through and logs
  a warning, rather than locking everyone out.
- **The client portal stays out of search results:** `app.outlogik.com/robots.txt` disallows
  everything, and every page and API response says `X-Robots-Tag: noindex, nofollow`. The
  website has its own robots.txt and sitemap (see Search).
- **Your account** (H1-10): changing your password needs the current one; wrong guesses count
  like failed sign-ins (5 in 15 minutes, then a pause). A change signs out every other device
  and emails the person, so a change they didn't make doesn't go unnoticed. Name changes are
  recorded in the audit log.
- **Super Admins** can only be created with the CLI.
- **Outlogik staff roles** (H1-11), one per person, granted with the CLI only:
  `platform_admin`, `support_admin`, `billing_admin` for the platform area, `site_admin` and
  `content_editor` for the website admin. Each platform endpoint checks a capability
  (`require_platform`), and anyone without it gets 404, so the API doesn't reveal itself; a
  test checks every `/api/v1/admin` route has a staff or capability check.
- **Suspending** needs a reason, signs a user out everywhere, and is recorded with who did it.
  Staff can't suspend themselves; only Super Admins can suspend other staff. A suspended
  organization's members are refused, its scheduled audits and Google syncs stop, and
  agencies lose access to a suspended business's shared workspace. Nothing is deleted.
- **Invitation codes** (SIGNUP_MODE=code): 12 characters from an alphabet without look-alikes
  (about 60 bits); only a hash is stored, the code is shown once; the row is locked while a
  use is counted, so a limited code can't be used twice at once; registration stays
  rate-limited.
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
  any object (member, role, client, workspace, website, invitation, portal user) returns 404
  and changes nothing. Tests try each of these.
- **Roles limited to assigned workspaces** (Account Manager, Client Viewer, or a custom role)
  see only the workspaces they're assigned to, everywhere: workspace lists, clients, websites
  and dashboard counts. Someone limited this way can only hand out workspaces they see
  themselves, and can't invite or promote anyone to a role that sees every workspace.
- **Agency access grants:** a business shares its own workspace with an agency without copying
  data. The grant is emailed to one person and only that account can accept it, into an agency
  where it's an owner or administrator. Access is "manage" (the agency's own roles apply) or
  "view only" (every change refused, in the API). Either side can end it; the agency's access
  and assignments stop at once. Grant, acceptance, changes made by the agency, and ending are
  recorded in both organizations' activity logs. A grant opens only that workspace: the
  business's team, roles, invitations and activity stay invisible to the agency.
- **Row-level security (second line of defence):** Postgres policies on every tenant table
  (migration 0012). Inside an organization request, each database transaction is told the
  organization (and any workspaces shared with it); the database then hides every other
  organization's rows and refuses to write them, even if a query forgot its organization
  filter. Outside an organization (sign-in, the public site, the CLI, migrations) the policies
  allow everything. They don't apply to superusers or `BYPASSRLS` users, so production uses
  an ordinary database user (DEPLOYMENT.md §4); the API warns at startup otherwise, and CI
  runs the tests as an ordinary user.
- **Fetching customers' websites (audits) safely:**
  - All fetching goes through `audits/fetch.py`, which resolves each host itself and refuses
    to connect unless every address it resolves to is on the public internet. That excludes
    private, loopback, link-local (including the cloud metadata address 169.254.169.254),
    carrier-grade NAT, multicast, reserved, and IPv4-mapped IPv6 addresses.
  - It connects to the exact address it checked, so a DNS answer can't change between check
    and connection.
  - Redirects are followed by hand, each hop checked again; only http and https.
  - No proxies; responses capped at 2 MB, 10 seconds per request, 40 minutes per audit.
  - Addresses are also checked when a website is added. `CRAWLER_ALLOW_PRIVATE` exists only
    for the test suite's local site, and the API refuses to start with it in production.
  - The crawler is polite: it identifies itself (`OutlogikBot`), obeys robots.txt, stays on
    the site's own host and port, waits between requests, and stops at the plan's page
    limit.
  - Sitemaps and pages are read as text (no XML parser), so a hostile file can't exploit
    one.
  - Audit results are under row-level security; an agency's audit of a shared workspace
    belongs to the business.
- **Google connections:**
  - Read-only scopes only (`analytics.readonly`, `webmasters.readonly`, plus `openid email` to
    show which account is connected). If someone unticks either read scope, the token is
    revoked and nothing is stored.
  - Sign-in uses PKCE and a one-time `state` kept in Redis for 10 minutes, tied to the person
    who started it. On return, Outlogik checks it's the same signed-in person, that they're
    still a member allowed to manage integrations, and that the workspace is still theirs and
    writable.
  - Refresh tokens are encrypted (Fernet, `INTEGRATIONS_ENCRYPTION_KEY`), never returned by the
    API, and revoked at Google on disconnect or when replaced. Disconnecting deletes the synced
    history.
  - If Google stops accepting a token, the connection is marked "reconnect" and nightly syncs
    skip it instead of retrying.
  - All nine tables of Google data are under row-level security; the cross-tenant suite
    includes a victim Google connection.
- **Dashboards:** the agency overview lists only workspaces the caller can see, and leaves out
  team details (account managers, reviews) for anyone without `members.read`, so client-portal
  users never see them. Parts the caller's role can't read (`analytics.read`, `audits.read`)
  are left out of the response, not just hidden in the app. Reviews belong to the reviewing
  organization (row-level security: that organization only), so a business never sees its
  agency's reviews. The cross-tenant suite includes a victim's review.
- **Reports:**
  - Search terms and page addresses are typed by strangers. In PDFs, every piece of outside
    text is escaped before ReportLab reads it (it has its own markup), and characters the font
    can't draw are shown as `?`. A test feeds markup through and checks it's printed, not obeyed.
  - CSV cells starting with `=`, `+`, `-` or `@` get a leading apostrophe, so spreadsheet apps
    don't run them as formulas (CSV injection; OWASP's advice). Tested with a `=HYPERLINK`.
  - Download file names are reduced to letters, digits and dashes.
  - A report is only opened by someone in the organization that made it, who can see its
    workspace and every section in it; reports are under row-level security for that
    organization only, and the cross-tenant suite includes a victim's report.
- **Background jobs:** emails are sent by a job, and their text (which can contain a sign-in,
  reset or invitation link) is erased from the job record as soon as the email is sent or gives
  up. Errors are stored without the payload. Finished jobs are deleted after 30 days, and
  expired sessions and used tokens nightly. The `jobs` table is under row-level security like
  other tenant tables.
- **Cross-tenant attack suite** (`tests/test_cross_tenant.py`): every organization route that
  takes an id, found automatically, is called by another organization's owner with the
  victim's ids, in the URL and in the body. All must fail, and the victim's data must be
  unchanged. A new route is covered without anyone remembering to add it.
- **Workspaces:** workspace routes (`/orgs/{slug}/workspaces/{id}/…`) check the organization
  first, then load the workspace within it. A workspace in another organization, or one the
  caller can't see, is a 404. A website is only reachable through its own workspace, and can
  only be moved to a workspace in the same organization.
- **Permissions:** each endpoint declares exactly one; a test fails the build if one doesn't,
  and another runs every built-in role against every endpoint.
- **No privilege escalation:** you can only assign or invite with a role whose permissions you
  hold. Only owners grant Owner, or change, disable or remove owners. The last owner can't be
  removed, demoted or leave. Nobody can change their own role or status.
- **Client-portal users** see only the clients they're linked to, those clients' workspaces
  and websites. They never see the agency's own workspace or its websites.
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
- **Invisible proof of work** (`backend/app/modules/leads/challenge.py`), built in, with no
  third-party service and no cookies (the same idea as the open ALTCHA scheme):
  - When a visitor starts on a form, the browser fetches a signed, expiring challenge
    (`GET /api/v1/public/challenge`).
  - It finds the matching number in the background: about 50,000 SHA-256 hashes at most,
    roughly 0.2 seconds on average on a desktop.
  - The form is sent with the solution. The API checks the HMAC signature (a key derived from
    `SITE_PROXY_SECRET`, or `FORM_CHALLENGE_SECRET` if set), the expiry (10 minutes) and the
    hash, and accepts each challenge once (Redis).
  - Missing, invalid, expired or reused proofs go to Spam ("no_proof" or "bad_proof").
  - The API refuses to issue challenges in production without a secret.
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
