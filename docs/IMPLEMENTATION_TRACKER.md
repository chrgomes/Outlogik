# Implementation tracker — Phase 1

Plan: [`PHASE1_PLAN.md`](PHASE1_PLAN.md). Spec: `MASTER_SPEC.md` (not yet in the repo).

| # | Step | Status | Notes |
|---|---|---|---|
| 1 | Scaffold, Docker Compose, health endpoint, Angular shell | ✅ Done | Angular 22, FastAPI, Postgres 16, Redis 7, Mailpit |
| 2 | Database, Alembic, Phase 1 models, first migration | ✅ Done | Migration `0001`; upgrade/downgrade tested; `alembic check` clean |
| 3 | Authentication backend + tests | ✅ Done | 27 auth tests |
| 4 | Organizations, members, invitations + tests | ✅ Done | 37 tests, incl. tenant isolation |
| 5 | Roles and permissions + permission tests | ✅ Done | Roles API, custom roles, escalation guard, system-role sync; 38 tests incl. a permission matrix over every org route |
| 6 | Clients and websites + tenant isolation tests | ✅ Done | Migration `0002`; 56 tests incl. client-portal scoping and cross-org attempts |
| 7 | Frontend: brand, themes, layout shell | ✅ Done | Tokens + Bootstrap 5.3, light/dark/system theme, collapsible sidebar, org switcher, user menu; 15 frontend tests |
| 8 | Frontend: authentication pages | ✅ Done | Sign in/up, forgot/reset, verify email, accept invite, verify banner; 25 new frontend tests; all flows checked in Chromium |
| 9 | Frontend: clients, websites, settings pages | ☐ | |
| 10 | Dashboard (backend + frontend) | ✅ Done | `GET /orgs/{slug}/dashboard`; stat tiles, get-started checklist, recent activity, Phase 2 'Not connected yet' cards; 7 backend + 11 frontend tests |
| 11 | Docs, tracker, final test pass | ☐ | |

## Project rules

- **No third-party CDNs in the frontend.** Fonts, scripts, styles and icons are bundled and
  served by Outlogik itself. In particular, nothing loads from Google Fonts. (Privacy and
  GDPR: visitors' browsers only talk to Outlogik.)
- **Brand typeface: Albert Sans** (SIL OFL 1.1), for the wordmark and the UI. The
  AI-generated concept wordmark was dropped because it resembled Logitech's. See
  `docs/brand/README.md`.

## Changes from the plan

Small additions made while building. None change an approved decision.

- **`email_verification_tokens` table.** The plan lists email verification as a flow but had no table for its tokens. Same shape as `password_reset_tokens`; stored as hashes.
- **`roles.system_key`** (`owner` / `admin` / `member` / `client`): a stable key for system roles, so code doesn't depend on display names that owners may want to translate or rename.
- **`invitations.invited_by_user_id` and `invitations.revoked_at`**: who sent an invite, and support for cancelling one.
- **`users.last_login_at`**, and **`users.mfa_secret` / `mfa_enabled_at`** reserved for optional MFA.
- **`organization_members.role_id`** uses `ON DELETE RESTRICT`, so a role still assigned to members can't be deleted.
- **CSRF cookie/header names** are `XSRF-TOKEN` / `X-XSRF-TOKEN`, Angular's built-in names.
- **`POST /auth/resend-verification`** and **`GET /auth/csrf`** added to the auth API.
- **URL layout:** `GET /api/v1/organizations` lists your organizations. Everything inside one organization (including get/update, members and invitations) is under `/api/v1/orgs/{slug}/…`, so a single dependency resolves and checks the tenant.
- **`POST /auth/invitations/preview`** shows the accept-invite page who invited you to what. It takes the token in the body, not the URL, so tokens stay out of access logs.
- **`POST /orgs/{slug}/leave`**, **`…/invitations/{id}/resend`** added.
- **Organization slugs don't change** when the name changes, so bookmarked links keep working.

## Security behaviour implemented (step 3)

- Argon2id password hashing, with rehash on login when parameters change. Minimum 10 characters.
- Server-side sessions: a random 256-bit token in an HTTP-only, Secure, SameSite=Lax cookie; only its SHA-256 hash is stored.
- Idle timeout (default 24 h) plus absolute lifetime (default 14 days). Login rotates the session.
- Logout, logout-all, and password reset all revoke sessions server-side. Deactivated users lose access at once.
- Double-submit CSRF check on every state-changing `/api/` request.
- Redis rate limits on login (per email and per IP), register, forgot/reset password and resend-verification. If Redis is down the limiter allows requests and logs a warning.
- Login errors don't reveal whether an email exists, and forgot-password always returns 202. Only the newest reset link works, and each link works once.
- Audit entries: register, organization create, login, failed login, logout, logout-all, password reset requested / completed, email verified, Super Admin granted via CLI.

## Organization, member and invitation rules (step 4)

- Requests resolve the organization from the URL slug and require an **active** membership; otherwise **404**, with the same body as a slug that doesn't exist. Suspended organizations return 403 `org_suspended`.
- Each route declares its permission with `require("…")`. Lacking it returns 403 with the permission named in `details`.
- Tenant-owned rows are loaded through `get_scoped()`, which always filters by the active organization. IDs from another organization (members, roles, clients, invitations) return 404.
- **Owners:** only an owner can make someone an owner, invite an owner, or change, disable or remove an owner. The last active owner can't be demoted, disabled, removed, or leave.
- Nobody can change their own role or status (avoids locking yourself out); use **Leave** to leave.
- **Client users vs team:** the Client role and team roles can't be swapped on an existing member — remove them and invite again. Client invitations must name a client in the same organization; others can't.
- **Invitations:** a new invite to the same email replaces the open one; resend issues a new link and kills the old one. Links expire after 7 days and work once. Inviting an existing member returns 409.
- **Accepting:** if the email already has an account, the invitee must be signed in as that account. A new account is created with the email marked verified (they opened the emailed link) and is signed in. Invitations still work when sign-up is invite-only.
- Removing a member also removes their client-portal links in that organization.
- Audit entries: `organization.update`, `member.update` (with from/to), `member.remove`, `member.leave`, `invitation.create` / `resend` / `revoke` / `accept`.

## Roles and permissions (step 5)

- **Only owners manage roles.** The plan says owners create custom roles, so the Admin role no longer has `roles.manage`. Admins and Team Members can still view roles.
- **Built-in roles are read-only.** Custom roles are for anything else. Names are unique per organization, ignoring case.
- **Built-in roles stay in sync.** At startup, every organization's built-in roles are reset to the catalogue's default permission sets (set-based SQL, so cost doesn't grow per organization). New permissions reach existing organizations automatically. Custom roles are never touched.
- **No privilege escalation.** You can only assign a role, or invite someone with it, if you hold every permission in that role (`role_exceeds_yours`). Owners hold everything; only owners can grant Owner.
- A role still assigned to members or to open invitations can't be deleted (`role_in_use`, with counts).
- Permission changes apply on the member's next request; nothing is cached.
- `GET /orgs/{slug}/permissions` returns the catalogue with a display group for each code, for the role editor.
- **Custom roles are team roles.** Client-portal access still uses the built-in Client role.
- **Tests guard every route:** each `/orgs/{slug}/…` endpoint must resolve the organization and declare exactly one permission (only `leave` is exempt). Each built-in role is then run against every endpoint, and must be refused exactly where its permission set says so. Removing a permission check from any route fails the build.
- Audit entries: `role.create`, `role.update` (with permissions added/removed), `role.delete`.

## Clients and websites (step 6)

- **Client-portal scoping.** Members with the Client role see only the clients they're linked to (`client_users`) and those clients' websites. Anything else is a plain 404, including filtering websites by a hidden client's ID. A portal user with no links sees nothing.
- **Internal notes stay internal.** Client records sent to portal users have `notes` and `portal_user_count` set to null.
- **Portal access:** a client invitation links the new user to one client. `POST /clients/{id}/users` gives an existing Client-role member access to another client; only Client-role members can be linked (team members already see everything). Needs `client_users.manage`.
- **Deleting a client** also deletes its websites, portal links and open client invitations (database cascades). The audit entry records the counts.
- **Website URLs are normalised:** https is assumed, the host is lower-cased and IDNA-encoded, default ports, query, fragment and trailing slash are dropped. `domain` is the host without `www.`. If no name is given, it defaults to the domain.
- **One record per URL per organization** (migration `0002`, unique on `organization_id, url`). Different paths on one domain are separate websites, and other organizations can add the same URL.
- **Non-public addresses are refused:** IP literals, `localhost`, single-label hosts and internal suffixes (`.local`, `.internal`, `.lan`, …), plus URLs with credentials. This is a first line of defence only. The Phase 2 crawler must also check the resolved IP at fetch time (SSRF).
- Search inputs escape SQL `LIKE` wildcards, so searching for `_` or `%` matches them literally.
- Audit entries: `client.create` / `update` / `delete`, `client_user.link` / `unlink`, `website.create` / `update` / `delete`.

## Frontend foundation (step 7)

- **Styling:** Bootstrap 5.3.8 SCSS (only the modules used) under Outlogik tokens in `frontend/src/styles/`. Components use semantic CSS variables (`--ol-surface`, `--ol-text-muted`, …), defined for both themes. Colour is reserved for status.
- **Typeface:** Albert Sans 400/500/600, bundled from `@fontsource/albert-sans`. **Icons:** 28 Bootstrap Icons inlined as SVG via `<ol-icon>`; regenerate with `npm run icons`. Nothing loads from a CDN.
- **Themes:** Light, Dark or Match system (default), remembered per browser. An inline script in `index.html` applies it before first paint, so there's no flash.
- **Shell:** the sidebar collapses to icons (remembered) and becomes a slide-over below 992 px. The top bar has the organization switcher, theme menu and account menu (sign out / sign out of all devices). Menus use Angular CDK for keyboard and screen-reader support. There's a skip-to-content link, and navigation sets `aria-current`.
- **Routing:** `/` goes to your first organization. `/o/:slug/…` requires sign-in and membership; another organization's URL shows "not found". Pages your role can't open show "no access" (the API refuses too). Nav items are hidden by permission. If any API call returns 401, you're sent to sign-in with a link back.
- **Placeholders:** Dashboard, Clients, Websites and Settings say which step builds them, and show no sample data. `/login` is a placeholder until step 8.
- **Fixed during browser testing:** opening or reloading an organization URL showed "not found", because route guards run in parallel. The organization guard now waits for the user itself, and a unit test covers a fresh page load.
- **Bundle budget** raised to 700 kB warning / 1 MB error. Currently 579 kB raw, about 123 kB compressed.

## Authentication pages (step 8)

- **Pages:** `/login`, `/register`, `/forgot-password`, `/reset-password`, `/verify-email`, `/accept-invite`. Each loads on demand (1–6 kB) and uses the same centred card.
- **Return after sign-in** goes only to same-app paths; external, `//` and `/\` URLs fall back to `/` (no open redirect). Unit-tested.
- **Emailed-link tokens** are read once, then removed from the address bar (`replaceUrl`), so they don't stay in browser history. `<meta name="referrer" content="same-origin">` stops them leaking to other sites.
- **Accept invitation** covers every case: new account (name + password); existing account signed out ("Sign in to accept", coming back with the token); signed in as someone else ("Sign out and continue"); signed in as the invitee (one click); and invalid, expired or cancelled links.
- **Errors:** API field errors show on the matching inputs. "Email already registered" offers a sign-in link. Rate limits say how long to wait, and network failures say so. A failed sign-in clears the password field.
- **Unconfirmed email:** a banner in the app with "Resend link" until the address is confirmed.
- **Expired or revoked sessions:** the next API call sends the user to sign-in, with a link back and an explanation. Pages that make no API calls (the current placeholders) find out on the next call.
- Backend: the invitation preview now also returns `organization_slug`, so the page can open the right organization after accepting.

## Clients, websites and settings pages (step 9)

- **Clients:** a list with search, a status filter and pages. The detail page shows internal notes (team only), the client's websites, and client-portal access (list, invite, add an existing client user, remove). Archive and restore; delete asks you to type the client's name.
- **Websites:** a list with search and client and status filters. Add, edit (including moving to another client, or pausing) and delete from a row menu. URL errors from the API, such as IP addresses or duplicates, show on the address field.
- **Organization:** rename (the switcher updates straight away; the web address doesn't change), and Leave organization. The nav item now needs `organization.read`, so every member can find Leave; only `organization.update` can rename.
- **Team:** members with search and a status filter. Row actions are change role, disable or restore access, and remove. There are none on your own row, and owners can only be managed by owners. Pending and expired invitations can be resent or cancelled. The invite dialog asks which client when the Client role is chosen, and only owners see Owner.
- **Roles:** built-in roles open read-only. Owners create, edit and delete custom roles with grouped permission checkboxes; a role still in use explains how many people and invitations use it.
- **Shared UI:** CDK dialogs (focus trapped and restored), confirmation dialogs (type-to-confirm for destructive actions), toasts, a pager, debounced search, status badges, and the `*olCan` directive for hiding actions. Lists use Angular `httpResource`, with loading, empty, error-with-retry and no-results states on every page.
- **Backend:** memberships in `/auth/me` now include `role_key` (the built-in role key, or null), so the UI can tell owners and client users apart without relying on role names.
- **Bundle:** each page loads on demand; the first download is 625 kB raw, about 135 kB compressed.
- **Browser walkthrough:** sign up; add three clients and websites (an IP address was refused); invite a team member and a client user and accept both; change a role; create a custom role; rename the organization; delete a client. The client user saw only their client and its website, no notes or edit actions, and "no access" on Team. No console errors, and no horizontal scroll on a phone in dark mode.

## Dashboard (step 10)

- **API:** `GET /orgs/{slug}/dashboard` (`dashboard.read`) returns client counts by status, website counts by status, team counts (active members, active client-portal users, unexpired pending invitations), and the 10 most recent audit entries for the organization.
- **Every number comes from real records.** Nothing is sampled, estimated or invented, and there are no trends or sparklines until there's history to draw them from.
- **What each role sees:** client-portal users get counts for their own clients only, with no team section and no activity. Team counts need `members.read`, pending invitations need `members.invite`, and activity needs `audit.read`. With the default roles, only Owners and Admins see activity, because it includes emails and internal names.
- **Page:**
  - a greeting, then stat tiles linking to their pages
  - a "Get started" checklist (add a client, add a website, invite your team), built from the real counts and hidden once done
  - recent activity as plain sentences with relative times; hover for the exact time
  - "Coming in Phase 2" cards (search performance, traffic, site health, broken links), each marked **Not connected yet** with no numbers
- The temporary "isn't built yet" placeholder page was removed; no route uses it any more.

## Known gaps / follow-ups

- Emails are sent synchronously during the request. A Celery queue with retries comes when the first background job is needed.
- Behind a reverse proxy, uvicorn must run with `--proxy-headers` so rate limits and audit IPs see the real client address.
- `docker compose up` was validated (`docker compose config`) but not run in the build environment, which had no Docker daemon. Tests ran against local PostgreSQL 16 and Redis 7.
