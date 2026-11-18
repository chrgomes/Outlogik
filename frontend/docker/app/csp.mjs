// Writes the nginx header line with the app's Content-Security-Policy. The built index.html has
// two small inline scripts (the theme switcher and the stylesheet loader); they're allowed by
// their SHA-256 hashes, computed here from the actual build so they always match.
// Usage: node docker/app/csp.mjs dist/frontend/browser/index.html > csp.conf
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';

const html = readFileSync(process.argv[2], 'utf8');
const hashes = [...html.matchAll(/<script(?![^>]*\ssrc=)[^>]*>([\s\S]*?)<\/script>/g)]
  .map((m) => `'sha256-${createHash('sha256').update(m[1]).digest('base64')}'`);

if (/\son[a-z]+=/i.test(html)) {
  console.error('index.html has an inline event handler, which the CSP would block. Remove it.');
  process.exit(1);
}

const policy = [
  "default-src 'self'",
  `script-src 'self' ${hashes.join(' ')}`,
  // Angular and the CDK set styles at runtime; styles can't run code.
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data:",
  "font-src 'self'",
  "connect-src 'self'",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
].join('; ');

process.stdout.write(`add_header Content-Security-Policy "${policy}" always;\n`);
