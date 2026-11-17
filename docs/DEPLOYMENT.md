# Outlogik — launch and deployment guide

How to put Outlogik online at **outlogik.com** (website) and **app.outlogik.com** (client portal
and admin), hosted on **DigitalOcean in Toronto**. Decided 2026-11-16 (Phase 1.5 plan,
decision 13).

Follow the steps in order. Steps marked **(you)** need your accounts; the rest is already in the
repository.

---

## How it fits together

```
                 ┌───────────────────────── DigitalOcean, Toronto ─────────────────────────┐
 outlogik.com ──▶│ App "outlogik-site":  site (Node, server-rendered website)              │
 www → redirect  │        │ reads settings, sends forms via https://app.outlogik.com/api    │
                 │        ▼                                                                 │
 app.outlogik.com│ App "outlogik-app":   web (nginx, the Angular app)   ← /                 │
           ─────▶│                       api (FastAPI)                  ← /api              │
                 │                       migrate (runs before each deploy)                  │
                 │        │                                                                 │
                 │        ▼                                                                 │
                 │ Managed PostgreSQL 16 "outlogik-db"   Managed Valkey "outlogik-cache"    │
                 └──────────────────────────────────────────────────────────────────────────┘
 Email: Google Workspace (mailboxes and aliases) · Resend (emails the system sends)
 DNS:   outlogik.com is registered at GoDaddy; its DNS is run by DigitalOcean (step 1)
```

| File | What it is |
|---|---|
| `backend/Dockerfile` | The API image (also runs `alembic upgrade head` before each deploy) |
| `frontend/Dockerfile.marketing` | The website image |
| `frontend/Dockerfile.app` | The client portal image (nginx, with its security headers) |
| `.do/production/app.yaml`, `.do/production/site.yaml` | App Platform settings for production |
| `.do/staging/app.yaml`, `.do/staging/site.yaml` | The same for staging (staging.outlogik.com, hidden from search engines) |

**Releases:** pushing to `main` deploys **staging** automatically. **Production** deploys only
when you start it (control panel → the app → **Deploy**), after checking staging.

**Estimated cost at launch:** about $55–70 a month (two small apps, PostgreSQL, Valkey), plus
Google Workspace per user. Check DigitalOcean's current prices.

---

## 1. Move outlogik.com's DNS to DigitalOcean (you)

App Platform needs the bare domain (`outlogik.com`, not just `www`) to point at it, which
GoDaddy's DNS can't do for App Platform. So the domain **stays registered at GoDaddy**, but
DigitalOcean answers its DNS. App Platform then creates the website's records itself.

1. In DigitalOcean: **Networking → Domains → Add domain** → `outlogik.com`.
2. **Before switching**, copy every existing record from GoDaddy's DNS page (especially
   Google Workspace's MX and TXT records, if email is already set up) into DigitalOcean.
3. At GoDaddy: **My Products → outlogik.com → DNS → Nameservers → Change → I'll use my own** →
   `ns1.digitalocean.com`, `ns2.digitalocean.com`, `ns3.digitalocean.com`.
4. Changes take from a few minutes to a day. Check with `dig NS outlogik.com +short`.

## 2. Email: Google Workspace (you)

1. Set up Google Workspace for `outlogik.com` and verify the domain (Google gives you a TXT
   record; add it in DigitalOcean's DNS).
2. **Mail records** (DigitalOcean DNS):
   - MX `@` → `smtp.google.com`, priority 1 (Google's current single MX record; follow the
     Admin console if it shows something different)
   - TXT `@` → `v=spf1 include:_spf.google.com ~all`
   - DKIM: Admin console → Apps → Google Workspace → Gmail → **Authenticate email** → generate,
     add the TXT record `google._domainkey`, then **Start authentication**
   - TXT `_dmarc` → `v=DMARC1; p=none; rua=mailto:privacy@outlogik.com` (start with `p=none`
     to monitor; move to `p=quarantine` after a few weeks of clean reports)
3. **Aliases** (Admin console → Users → your user → Add alternate emails):
   - `privacy@outlogik.com` (**required**: the privacy policy tells people to use it)
   - `sales@outlogik.com` (**required**: new enquiries are emailed here, and the consultation
     page offers it)
   - `billing@outlogik.com` (**required**: the payment and subscription policy gives it for
     invoice questions)
4. Send yourself a test email to each alias.

## 3. Email the system sends: Resend (you)

Sign-in links, invitations and enquiry confirmations go out through Resend. DigitalOcean blocks
the usual email ports, so Outlogik uses Resend's port **2587**.

1. Create a Resend account → **Domains → Add domain** → `outlogik.com` (choose the North America
   region if offered).
2. Add the records Resend shows to DigitalOcean's DNS: a DKIM TXT record (`resend._domainkey`)
   and, for the `send` subdomain, an MX and an SPF TXT record. They don't affect Google
   Workspace's records.
3. Wait for **Verified**.
4. **API Keys → Create** (permission: sending access, domain outlogik.com). Keep it for step 6;
   it's the `SMTP_PASSWORD`.

## 4. Databases (you, DigitalOcean control panel)

Create both in **Toronto (TOR1)**:

1. **Databases → Create → PostgreSQL 16**, name **`outlogik-db`**, the smallest Basic plan to
   start (1 GB). Then, in the cluster:
   - **Users & Databases**: create database `outlogik` and user `outlogik`
   - and, for staging, database `outlogik_staging` and user `outlogik_staging`
2. **Databases → Create → Valkey**, name **`outlogik-cache`**, the smallest plan.

The apps add themselves to the databases' trusted sources when they're created.

## 5. Generate the shared secret

The website forwards form posts to the API and vouches for each visitor's IP address with a
shared secret, so the rate limits see real visitors. Generate one (different for staging and
production):

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

## 6. Create the staging apps (you)

1. Give DigitalOcean access to GitHub: **Apps → Create App → GitHub → Manage access**, and allow
   the `chrgomes/Outlogik` repository.
2. Create the two staging apps from their specs, either with **Apps → Create App → Import from
   app spec** (upload the file), or with `doctl`:

   ```bash
   doctl apps spec validate .do/staging/app.yaml
   ```

   ```bash
   doctl apps create --spec .do/staging/app.yaml
   ```

   ```bash
   doctl apps create --spec .do/staging/site.yaml
   ```

3. In each app's **Settings → Environment variables**, replace every `CHANGE_ME`:
   - `outlogik-app-staging`, component **api**: `SITE_PROXY_SECRET` (step 5) and `SMTP_PASSWORD`
     (the Resend key, step 3)
   - `outlogik-site-staging`: `SITE_PROXY_SECRET` (the **same** value as the api's)
4. The first deploy builds the images, runs the database migrations (`migrate` job), then starts
   everything. App Platform creates the DNS records for `staging.outlogik.com` and
   `app.staging.outlogik.com` and their HTTPS certificates.

**Note:** these specs were written against DigitalOcean's app spec format but haven't been
validated against a real account yet. If the validator or the import complains (for example
about the `VALKEY` engine name or a field), tell me the message and I'll adjust the file.

## 7. Create the first staff account

In the control panel: `outlogik-app-staging` → **Console** → component **api**, then:

```bash
python -m app.cli create-organization --name "Outlogik" --owner-email you@outlogik.com --owner-name "Your Name"
```

(it asks for a password, at least 10 characters), then:

```bash
python -m app.cli grant-staff --email you@outlogik.com --role site_admin
```

Sign in at `https://app.staging.outlogik.com`. Invite colleagues and clients from the app.

## 8. Check staging

- [ ] `https://app.staging.outlogik.com/api/v1/health/ready` shows database **ok** and redis **ok**
      (if redis is unavailable, see Troubleshooting)
- [ ] `https://staging.outlogik.com` loads; `https://staging.outlogik.com/robots.txt` says
      `Disallow: /` (staging stays out of search results)
- [ ] Send the contact form and book a consultation: the confirmation emails arrive, and both
      appear in **Website admin → Inbox**
- [ ] The enquiry's IP address in the inbox's data looks like a real public address, not a
      DigitalOcean one (this confirms `CLIENT_IP_HEADER=do-connecting-ip`; see Troubleshooting)
- [ ] Newsletter sign-up: the confirmation email arrives and its link confirms
- [ ] Forgot password: the email arrives and the link works
- [ ] Website admin → Settings: change something and see it on the website within a minute
- [ ] Privacy policy and terms show Outlogik, Toronto, Ontario and privacy@outlogik.com

## 9. Go live: production (you)

1. Create the production apps:

   ```bash
   doctl apps create --spec .do/production/app.yaml
   ```

   ```bash
   doctl apps create --spec .do/production/site.yaml
   ```

2. Set the secrets as in step 6 (a **new** `SITE_PROXY_SECRET` for production, the same in both
   apps; the same Resend key).
3. `LEAD_NOTIFICATION_EMAILS` in `outlogik-app` → api is already `sales@outlogik.com` (add more
   addresses separated by commas if you like).
4. Repeat step 7 (first staff account) in `outlogik-app`, and the checks in step 8 on
   `https://outlogik.com` and `https://app.outlogik.com`. `robots.txt` should now allow
   everything and point to the sitemap; `www.outlogik.com` should redirect to `outlogik.com`.

## 10. Search engines (you)

1. **Google Search Console** → Add property → **Domain** `outlogik.com` → add the TXT record it
   shows in DigitalOcean's DNS → Verify. Then **Sitemaps** → `https://outlogik.com/sitemap.xml`.
2. **Bing Webmaster Tools** → import the site from Google Search Console → submit the same
   sitemap.

## Releasing updates

1. Changes are merged to `main`. CI runs the tests and builds the Docker images.
2. Staging deploys automatically. Check it.
3. Production: control panel → `outlogik-app` and `outlogik-site` → **Deploy** (or
   `doctl apps create-deployment <app-id>`). Database migrations run first; if they fail, the
   old version keeps running.

To roll back: the app's **Activity** tab → an earlier deployment → **Rollback**. Roll the
database back only if a migration requires it (each migration in `backend/alembic/versions` has
a `downgrade`).

## Backups and a restore test

- **PostgreSQL:** DigitalOcean takes daily backups and keeps 7 days of point-in-time recovery.
  Nothing to set up.
- **Valkey** holds only rate-limit counters; losing it is harmless.
- **Restore test** (do this once before launch, then every few months):
  1. `outlogik-db` → **Backups & Restore → Restore from backup** → a time a few hours ago →
     **as a new cluster** (it doesn't touch the live database).
  2. Connect to the new cluster (its **Connection details**) and check the data, for example
     `SELECT count(*) FROM users;` and `SELECT count(*) FROM leads;`.
  3. Delete the restored cluster.

## Monitoring

- The app specs alert you by email if a deployment or a domain fails.
- `outlogik-db` → **Insights / Alerts**: add alerts for CPU over 80% and disk over 75%.
- **Monitoring → Uptime**: add checks for `https://outlogik.com/healthz` and
  `https://app.outlogik.com/api/v1/health/ready`, with email alerts.

## Troubleshooting

| Symptom | Likely cause and fix |
|---|---|
| Website pages answer **400 Bad Request** | The host name isn't allowed by Angular's server. Allowed: `outlogik.com`, `staging.outlogik.com`, `localhost` (`frontend/angular.json` → `security.allowedHosts`). Other hosts are redirected by `CANONICAL_HOST`. |
| Forms say they can't be sent; the API answers **403 bad_origin** | The API's `SITE_URL` must be the website's exact address (`https://outlogik.com`). |
| `/api/v1/health/ready` shows **redis unavailable** | Check that `REDIS_URL` starts with `rediss://` (TLS) and the api's runtime logs. If the certificate is rejected, tell me the log message. Rate limits are skipped while Redis is unavailable, so fix it before launch. |
| Enquiries all show the same IP | DigitalOcean's client IP header has a different name. Check a request's headers in the api's runtime logs and set `CLIENT_IP_HEADER` on both apps accordingly. |
| No emails arrive | Resend → **Logs**. The domain must be **Verified**; `SMTP_PORT` must be `2587`; `SMTP_PASSWORD` is the API key. |
| Sign-in works but you're signed out immediately | `COOKIE_SECURE=true` needs HTTPS: use `https://app.outlogik.com`, not the `ondigitalocean.app` address. |

## Launch checklist

- [ ] DNS on DigitalOcean; Google Workspace mail records, SPF, DKIM, DMARC
- [ ] `privacy@`, `sales@` and `billing@` receive email
- [ ] Resend domain verified; API key set as `SMTP_PASSWORD`
- [ ] PostgreSQL and Valkey clusters in Toronto; restore test done
- [ ] Staging created and checked (step 8)
- [ ] Production created, secrets set, checked (a test enquiry reaches sales@)
- [ ] First staff account; Website admin → Settings reviewed (contact email, phone, social links)
- [ ] Copy reviewed (business promises listed in `IMPLEMENTATION_TRACKER_1_5.md`); legal pages
      reviewed, ideally by a lawyer
- [ ] Google Search Console and Bing: domain verified, sitemap submitted
- [ ] Uptime checks and database alerts set
