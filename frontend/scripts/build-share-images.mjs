// Renders the website's share image (shown when a page is shared on LinkedIn, Facebook and the
// like) and a PNG logo for search engines, from the brand files and the bundled font. No
// third-party services. Run after changing the brand or the wording below:
//
//   NODE_PATH=$(npm root -g) node scripts/build-share-images.mjs
//
// Writes projects/marketing/public/images/og-default.png (1200×630) and outlogik-logo-512.png.
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const root = new URL('../', import.meta.url);
const read = (p) => readFileSync(new URL(p, root));
const font = (weight) => read(`node_modules/@fontsource/albert-sans/files/albert-sans-latin-${weight}-normal.woff2`).toString('base64');
const logo = read('brand/assets/logo/outlogik-logo-on-dark.svg').toString();
const symbol = read('brand/assets/logo/outlogik-symbol-on-light.svg').toString();
const out = (name) => new URL(`projects/marketing/public/images/${name}`, root).pathname;

const fonts = `
  @font-face { font-family: 'Albert Sans'; font-weight: 500; src: url(data:font/woff2;base64,${font(500)}) format('woff2'); }
  @font-face { font-family: 'Albert Sans'; font-weight: 600; src: url(data:font/woff2;base64,${font(600)}) format('woff2'); }
  * { margin: 0; box-sizing: border-box; }
  body { font-family: 'Albert Sans', sans-serif; -webkit-font-smoothing: antialiased; }`;

const share = `<!doctype html><style>${fonts}
  body { width: 1200px; height: 630px; padding: 72px 80px; background: #050505; color: #fff;
    display: flex; flex-direction: column; justify-content: space-between; }
  .logo svg { height: 48px; width: auto; display: block; }
  h1 { font-size: 72px; font-weight: 600; line-height: 1.05; letter-spacing: -0.02em; }
  p { font-size: 28px; font-weight: 500; color: #a3a3a3; }
</style><body>
  <div class="logo">${logo}</div>
  <h1>Digital marketing, handled.<br>And always in view.</h1>
  <p>SEO · Social media · Content · Analytics</p>
</body>`;

const mark = `<!doctype html><style>${fonts}
  body { width: 512px; height: 512px; display: grid; place-items: center; background: #fff; }
  svg { width: 360px; height: 360px; }
</style><body>${symbol}</body>`;

const browser = await chromium.launch();
for (const [html, width, height, file] of [[share, 1200, 630, 'og-default.png'], [mark, 512, 512, 'outlogik-logo-512.png']]) {
  const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: 1 });
  await page.setContent(html);
  await page.evaluate(() => document.fonts.ready);
  await page.screenshot({ path: out(file) });
  console.log('Wrote', file);
}
await browser.close();
