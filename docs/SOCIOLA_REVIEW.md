# Sociola: review for Outlogik's social media module

[Sociola](https://github.com/chrgomes/Sociola) (private) is an earlier social media
management platform by the Outlogik owner. Reviewed 2026-11-18 from its latest commit
(`e702084`), to decide what the H2 social media module can reuse.

**Status:** decided 2026-11-18: **Sociola stays a separate product.** It isn't ported into
Outlogik or linked to it. This review is kept as a record of Sociola's state and as input for
its own beta (see [`SOCIOLA_BETA_CHECKLIST.md`](SOCIOLA_BETA_CHECKLIST.md)).

## What Sociola has

Stack: TypeScript, React 19, TanStack Start, Better Auth, PostgreSQL. One app, hosted on
Vercel. Outlogik is Python (FastAPI) and Angular, so code is ported, not copied.

| Area | State in Sociola | Where |
|---|---|---|
| Connecting accounts (OAuth, PKCE, state) | Works for Instagram, Facebook Pages, LinkedIn (member), TikTok, YouTube, Pinterest, X, Threads, Google Business Profile. API versions reviewed 2026-10-20 | `src/lib/marquee/networks.ts`, `networks.server.ts` |
| Publishing | Text posts to X, Facebook Pages, LinkedIn (member), Threads, Google Business Profile | `publishVariant` in `networks.server.ts` |
| Publish jobs | Queued, locked, sent, not sent, failed (3 tries), dead, **ambiguous** (never resent automatically), closed. No duplicate posts | `src/lib/marquee/api.ts`, `migrations/` |
| Compose, per-network variants, calendar, approvals, campaigns, media library | Built | `src/components/marquee/`, `migrations/0002_marquee.sql` |
| AI captions with usage and cost caps | Built (estimated costs) | `api.ts`, `ai-rates.ts` |
| Plan limits, Super Admin desks | Built | `platform-*.ts`, migrations 0005–0015 |
| Honest status | `docs/production-readiness.md` lists the gaps plainly | |

## Gaps to fix when porting

- **No background worker:** due posts run only when someone opens the workspace.
  → Celery and beat (Outlogik H1-5).
- **No media publishing:** Instagram, TikTok, YouTube and Pinterest are disabled because media
  files are private. → Object storage (DigitalOcean Spaces) with short-lived signed URLs.
- **Network tokens stored in plain text** (`social_accounts.access_token`).
  → Encrypted credentials (Outlogik integration framework, H1-7).
- **Facebook connects the first Page only; LinkedIn posts as a member, not a company page.**
  → Page and organization pickers; LinkedIn Community Management API access.
- **No token refresh seen** (Instagram long-lived tokens expire after ~60 days).
- **Analytics** route is a placeholder: no network insights are pulled.
- **Inbox and listening:** not checked.
- **No cross-tenant tests.** → Outlogik's isolation suite and RLS (H1-3).

## Proposed approach

Port into Outlogik as the H2 social media module, per workspace:

1. Network adapters in Python behind one interface (connect, refresh, publish, insights),
   translated from `networks.server.ts`.
2. The publish job state machine, unchanged in behaviour, run by Celery.
3. Compose, variants, calendar and approvals in Angular, with client approval in the portal.
4. Fix the gaps above as part of the port.

## Alternatives discussed (2026-11-18)

- **Plain link** from Outlogik's sidebar to Sociola (e.g. social.outlogik.com): fastest, but two
  logins, two subscriptions, no shared reports or client approvals, two products to maintain.
- **Link with single sign-on:** Outlogik sign-in carries over, workspaces map to Sociola
  organizations, and Outlogik pulls social stats for reports. Faster than porting; still two
  products, and permissions must be kept in step.
- Either way, Sociola's blockers (background worker, encrypted tokens, tenant tests, media
  publishing, platform app reviews) must be fixed before paying customers use it.

Decided 2026-11-18: neither. Sociola stays separate.

## Open questions for the owner

- Have any network apps passed review (Meta, TikTok audit, LinkedIn)? They can be reused.
