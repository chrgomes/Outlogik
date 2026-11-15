// Captures the client-portal screenshots used on the marketing site, from the real app with
// example data. Run with the API (port 8000, SIGNUP_MODE=open, EMAIL_BACKEND=console logging to
// UVICORN_LOG) and the app dev server (port 4200) running, on an empty development database:
//
//   UVICORN_LOG=/tmp/uvicorn.log node scripts/capture-marketing-screenshots.mjs
//
// Needs Playwright (npx playwright, or a global install). Writes 1440×720 (1x) and 2880×1440 (2x) WebP files to
// projects/marketing/public/images/. Example data only: no real clients.
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const BASE = process.env.APP_URL ?? 'http://localhost:4200';
const LOG = process.env.UVICORN_LOG ?? '/tmp/uvicorn.log';
const OUT = new URL('../projects/marketing/public/images/', import.meta.url).pathname;
const ORG = '/api/v1/orgs/outlogik';
const PASSWORD = 'example password 1';
const lastToken = (path) =>
  [...readFileSync(LOG, 'utf8').matchAll(new RegExp(`/${path}\\?token=([\\w-]+)`, 'g'))].pop()[1];

async function session(browser) {
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 720 }, deviceScaleFactor: 2, colorScheme: 'light' });
  await ctx.request.get(`${BASE}/api/v1/auth/csrf`);
  const xsrf = (await ctx.cookies()).find((c) => c.name === 'XSRF-TOKEN').value;
  const call = async (method, path, data) => {
    const r = await ctx.request.fetch(BASE + path, { method, data, headers: { 'X-XSRF-TOKEN': xsrf } });
    if (!r.ok()) throw new Error(`${method} ${path}: ${r.status()} ${await r.text()}`);
    return r.status() === 204 ? null : r.json();
  };
  return { ctx, call };
}

const browser = await chromium.launch();
const agency = await session(browser);
await agency.call('POST', '/api/v1/auth/register', { email: 'team@outlogik.example.com', password: PASSWORD, full_name: 'Olive Okafor', organization_name: 'Outlogik' });
const roles = (await agency.call('GET', `${ORG}/roles`)).items;
const clientRole = roles.find((r) => r.system_key === 'client').id;
const bakery = await agency.call('POST', `${ORG}/clients`, { name: 'Harbour Bakery', contact_email: 'jo@harbourbakery.example.com' });
for (const url of ['harbourbakery.example.com', 'shop.harbourbakery.example.com', 'harbourbakery.example.com/catering']) {
  await agency.call('POST', `${ORG}/websites`, { client_id: bakery.id, url });
}
const sites = (await agency.call('GET', `${ORG}/websites?client_id=${bakery.id}`)).items;
await agency.call('PATCH', `${ORG}/websites/${sites.find((s) => s.url.includes('shop.')).id}`, { name: 'Online shop' });
await agency.call('PATCH', `${ORG}/websites/${sites.find((s) => s.url.includes('catering')).id}`, { name: 'Catering orders' });
await agency.call('POST', `${ORG}/invitations`, { email: 'jo@harbourbakery.example.com', role_id: clientRole, client_id: bakery.id });
const client = await session(browser);
await client.call('POST', '/api/v1/auth/accept-invite', { token: lastToken('accept-invite'), full_name: 'Jo Baker', password: PASSWORD });

const page = await client.ctx.newPage();
const shots = [
  [`/o/outlogik/clients/${bakery.id}`, '.ol-section tbody tr', 'portal-client'],
  ['/o/outlogik/websites', 'tbody tr', 'portal-websites'],
];
const childProcess = await import('node:child_process');
for (const [path, ready, name] of shots) {
  await page.goto(BASE + path);
  await page.locator(ready).first().waitFor();
  await page.waitForTimeout(400);
  await page.screenshot({ path: `${OUT}${name}.png` });
  // 2x PNG → WebP at 2x (2880 wide) and 1x (1440 wide), via Python Pillow (available in dev).
  childProcess.execFileSync('python3', ['-c', `
from PIL import Image
im = Image.open("${OUT}${name}.png").convert("RGB")
im.save("${OUT}${name}@2x.webp", "WEBP", quality=86, method=6)
im.resize((im.width // 2, im.height // 2), Image.LANCZOS).save("${OUT}${name}.webp", "WEBP", quality=88, method=6)
import os; os.remove("${OUT}${name}.png")`]);
  console.log(`Wrote ${name}.webp and ${name}@2x.webp`);
}
await browser.close();
