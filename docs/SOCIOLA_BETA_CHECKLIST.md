# Sociola beta: staging checklist

How to get Sociola running on a staging site with a real database and real social network
connections, for a small beta. Written 2026-11-18 from Sociola's code (commit `e702084`). Google Business Profile is being
restored in Sociola; its section assumes it works as in that commit.
See also [`SOCIOLA_REVIEW.md`](SOCIOLA_REVIEW.md).

Network developer consoles change often. If a menu name differs slightly from what's written
here, look for the closest match.

**Golden rule:** client secrets, the database password and `BETTER_AUTH_SECRET` go into
Vercel's settings only. Never into the code, a commit, a chat or an email.

---

## 0. Decide first

- [ ] **Staging address.** Every network needs it registered exactly, so pick it before
      anything else:
  - simplest: the Vercel address, e.g. `https://sociola-staging.vercel.app`
  - or your own: `https://social-staging.outlogik.com` (needs a DNS record, step 3)
- [ ] **Who the beta testers are.** Keep it to people you trust (see section 8).
- [ ] **Which networks.** Recommended for the beta: Facebook Pages, LinkedIn, Threads,
      Google Business Profile (once Google approves API access). Optional: X. Skip for now: Instagram posting, TikTok, YouTube,
      Pinterest (Sociola can't post images or video yet).

Write your staging address here: `______________________________`

Every network's callback address is that, plus `/api/networks/callback/<network>`:

| Network | Callback address |
|---|---|
| Facebook | `<staging address>/api/networks/callback/facebook` |
| Instagram | `<staging address>/api/networks/callback/instagram` |
| Threads | `<staging address>/api/networks/callback/threads` |
| LinkedIn | `<staging address>/api/networks/callback/linkedin` |
| Google Business Profile | `<staging address>/api/networks/callback/google_business` |
| X | `<staging address>/api/networks/callback/x` |

---

## 1. Check sign-in works outside Grok's builder (before deploying)

Sociola was made in Grok's app builder, which normally injects its own sign-in settings
(`GROK_PROJECT_ID`, `GROK_AUTH_*`). On your own hosting they're missing. Email and password
sign-in is switched on in the code, but some parts treat the app as a "preview" when
`GROK_PROJECT_ID` is missing.

- [ ] On the staging site (after step 4), create an account, sign out, sign back in.
- [ ] Close the browser, open it again: are you still signed in, as expected?
- [ ] Open the site in a private window: can you see anything without signing in? (You
      shouldn't.)
- [ ] Redeploy, then check you're still signed in. (If every deploy signs everyone out, the
      app isn't using your `BETTER_AUTH_SECRET`.)

If any of these fail, stop here and fix sign-in before connecting networks.

---

## 2. Staging database (Neon)

- [ ] Sign up at neon.tech (free tier is enough for a beta).
- [ ] Create a project `sociola-staging`, region closest to Toronto (e.g. AWS us-east).
- [ ] Copy the connection string (starts with `postgresql://`, ends with
      `?sslmode=require`).
- [ ] Keep it for step 4. Don't paste it anywhere else.

Notes:
- Sociola creates its tables itself: each build runs `npm run build`, which runs
  `db:migrate`.
- Without `DATABASE_URL`, Sociola uses an in-memory database that's wiped on every restart.
  If data disappears, check this setting first.
- [ ] Turn on Neon's backups / point-in-time restore if your plan includes them.

---

## 3. Your own staging domain (skip if using the Vercel address)

- [ ] In Vercel: project → Settings → Domains → add `social-staging.outlogik.com`.
- [ ] Add the DNS record Vercel shows (a CNAME) where outlogik.com's DNS is managed (GoDaddy
      today, DigitalOcean after the move in `DEPLOYMENT.md`).
- [ ] Wait until Vercel shows the domain as valid, with HTTPS.

---

## 4. Vercel settings (staging)

Vercel → the Sociola project → Settings → Environment Variables → add each for the
**Preview** or a dedicated staging environment (not Production, unless staging *is* your only
deployment).

| Setting | Value |
|---|---|
| `DATABASE_URL` | The Neon connection string from step 2 |
| `APP_URL` | Your staging address, no trailing slash |
| `BETTER_AUTH_URL` | The same staging address |
| `BETTER_AUTH_SECRET` | A random string of 40+ characters (a password manager's generator works) |
| `VITE_AUTH_ENABLED` | `true` |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM`, `SMTP_SECURE` | Optional, for email (Resend's SMTP details). `SMTP_FROM` like `Sociola <no-reply@outlogik.com>` |
| Network IDs and secrets | Added in step 5, one pair per network |

- [ ] All of the above added.
- [ ] Redeploy (settings only apply to new deployments).
- [ ] Open the staging address: the site loads.
- [ ] Now do the sign-in checks in step 1.

---

## 5. Social network apps (development mode)

In development or testing mode, **you and invited testers** can connect without the
network's app review. Real customers need the review later (section 9).

### Facebook Pages (Meta)

- [ ] developers.facebook.com → My Apps → Create app → type **Business**.
- [ ] Add product **Facebook Login for Business**.
- [ ] Valid OAuth redirect URIs: the Facebook callback address.
- [ ] Permissions: `pages_show_list`, `pages_manage_posts`, `pages_read_engagement`.
- [ ] App settings → Basic: add the privacy policy URL (e.g.
      `https://outlogik.com/privacy-policy`) and app domain.
- [ ] App roles → add each tester (they must accept the invitation in their Facebook
      account).
- [ ] In Vercel: `FACEBOOK_CLIENT_ID` = App ID, `FACEBOOK_CLIENT_SECRET` = App secret.
- [ ] Known limit: Sociola connects the **first Page** the person manages. Testers with
      several Pages should connect with an account that manages only the test Page, or expect
      the first one.

### Instagram (same Meta app; connect only)

- [ ] Add product **Instagram API with Instagram Login**.
- [ ] Redirect URI: the Instagram callback address.
- [ ] Testers need an Instagram **business or creator** account, added as Instagram testers.
- [ ] In Vercel: `INSTAGRAM_CLIENT_ID`, `INSTAGRAM_CLIENT_SECRET` (shown under the
      Instagram product, not the main app secret).
- [ ] Known limit: Sociola can connect Instagram but **won't post** to it (needs media
      posting).

### Threads (same Meta app)

- [ ] Add the **Threads** use case.
- [ ] Redirect URI: the Threads callback address.
- [ ] Add Threads testers (they accept in the Threads app or website settings).
- [ ] In Vercel: `THREADS_CLIENT_ID`, `THREADS_CLIENT_SECRET` (shown under Threads).

### LinkedIn

- [ ] linkedin.com/developers → Create app → link it to the Outlogik company page (a page
      admin approves the link).
- [ ] Products: **Sign In with LinkedIn using OpenID Connect** and **Share on LinkedIn**
      (both self-serve).
- [ ] Auth → Authorized redirect URLs: the LinkedIn callback address.
- [ ] In Vercel: `LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET`.
- [ ] Known limit: posts go to the person's **personal profile**, not a company page.
      Company pages need LinkedIn's Community Management API (application, see section 9).

### Google Business Profile

Start this one first: Google's API access approval can take weeks, and nothing works
until it's granted.

- [ ] console.cloud.google.com → new project `sociola-staging`.
- [ ] Enable: **My Business Account Management API**, **My Business Business Information
      API**, and the Business Profile (local posts) API.
- [ ] **Request Business Profile API access** from Google, for this project (the APIs have
      zero quota until approved). Use a Google account that manages a verified Business
      Profile, and describe the use plainly (posting updates for businesses that connect
      their own profile).
- [ ] OAuth consent screen: External, status **Testing**, add each tester's Google account
      as a test user. Scope: `https://www.googleapis.com/auth/business.manage`.
- [ ] Credentials → OAuth client ID → Web application → Authorized redirect URI: the Google
      Business callback address.
- [ ] In Vercel: `GOOGLE_BUSINESS_CLIENT_ID`, `GOOGLE_BUSINESS_CLIENT_SECRET`.
- [ ] Testers need **owner or manager** access to a verified Business Profile.
- [ ] Known limits (as of commit `e702084`): Sociola connects the **first location** of the
      first account, and posts text only. If access isn't approved yet, connecting still
      works but posting reports that no location was granted.

### X (optional)

- [ ] developer.x.com → project and app → User authentication settings: **OAuth 2.0**,
      type **Web App (confidential client)**, permissions **Read and write**.
- [ ] Callback URI: the X callback address. Website URL: your staging address.
- [ ] In Vercel: `X_CLIENT_ID`, `X_CLIENT_SECRET` (the OAuth 2.0 ones, not the API key).
- [ ] Check your access tier's monthly posting limit; free access is very limited.

- [ ] After adding network settings: **redeploy**.

---

## 6. Test each connection

For each network, with a tester account:

- [ ] Accounts page shows the network as available (not "set the client id and secret").
- [ ] Connect → the network's sign-in → back on Accounts with the account connected.
- [ ] Post a short test now (not scheduled). It appears on the network.
- [ ] The post's status in Sociola says it was sent, with the network's post ID.
- [ ] Disconnect → the account shows as disconnected.

If connecting fails, the message on the Accounts page usually names the cause. The most
common one is a callback address that doesn't match exactly (`http` vs `https`, a trailing
slash, `www`).

---

## 7. Scheduled posts

- [ ] Schedule a post 5 minutes ahead, **close the app**, wait 10 minutes. Did it post?

It most likely won't: Sociola sends due posts only when someone opens the workspace (there's
no background worker). For the beta, either:
- tell testers to open the app around scheduled times, or
- add a scheduled trigger (Vercel Cron calling a protected "send due posts" endpoint every
  few minutes). This needs a code change.

---

## 8. Beta rules (until the fixes in section 9 are done)

- [ ] Testers are people you trust, using **test Pages and accounts**, not important client
      accounts.
- [ ] Network access tokens are stored **unencrypted** in the database, so keep the Neon
      password private and limit who can open the Neon console.
- [ ] Password reset links are **shown on screen**, not emailed. Reset passwords for testers
      yourself, or fix this first.
- [ ] Tell testers: text posts only; Instagram, TikTok, YouTube and Pinterest are connect-only.
- [ ] Collect feedback somewhere simple (a shared doc or form): what they tried, what broke,
      what they'd pay for.

---

## 9. Before real customers (not needed for the beta)

- [ ] Code fixes: background sending, encrypted tokens, emailed reset links, Page/location
      pickers, token renewal, image and video posting, cross-tenant tests.
- [ ] **Meta:** business verification, then app review for `pages_manage_posts` and the
      Instagram and Threads publishing permissions (needs a screen recording of each feature
      and the privacy policy).
- [ ] **LinkedIn:** apply for the Community Management API (company page posting).
- [ ] **Google:** Business Profile API access approved; OAuth consent screen verified
      (needed before people outside the test-user list can connect).
- [ ] **TikTok:** app audit (until then, posts can only be private).
- [ ] A production database with tested backups, separate from staging.
- [ ] Decide how Sociola relates to Outlogik (port, plain link, or link with single sign-on;
      see `SOCIOLA_REVIEW.md`).

---

## Quick reference: all settings

```
DATABASE_URL=
APP_URL=
BETTER_AUTH_URL=
BETTER_AUTH_SECRET=
VITE_AUTH_ENABLED=true

SMTP_HOST=
SMTP_PORT=
SMTP_USER=
SMTP_PASS=
SMTP_FROM=
SMTP_SECURE=

FACEBOOK_CLIENT_ID=
FACEBOOK_CLIENT_SECRET=
INSTAGRAM_CLIENT_ID=
INSTAGRAM_CLIENT_SECRET=
THREADS_CLIENT_ID=
THREADS_CLIENT_SECRET=
LINKEDIN_CLIENT_ID=
LINKEDIN_CLIENT_SECRET=
GOOGLE_BUSINESS_CLIENT_ID=
GOOGLE_BUSINESS_CLIENT_SECRET=
X_CLIENT_ID=
X_CLIENT_SECRET=
```

(Names only. The values go into Vercel, never into a file in the repository.)
