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

## Production checklist (not yet done)

These depend on how Outlogik is hosted, which hasn't been decided:

- [ ] Serve the Angular app and `/api` from **one origin**, behind HTTPS, with HSTS.
- [ ] A **Content-Security-Policy** for the Angular app on the web server (the app needs no
      third-party origins; one inline script in `index.html` sets the theme before first
      paint, so allow it by hash).
- [ ] Run uvicorn with `--proxy-headers` and a trusted `--forwarded-allow-ips` so rate limits
      and audit entries see real client IPs.
- [ ] Keep `COOKIE_SECURE=true`; set `FRONTEND_URL` to the public URL (used in email links).
- [ ] A real SMTP provider with SPF, DKIM and DMARC for the sending domain.
- [ ] Database backups, and secrets supplied by the host rather than `.env` files.
- [ ] Optional later: PostgreSQL row-level security as a second isolation layer; MFA (the
      schema already has room for it).
