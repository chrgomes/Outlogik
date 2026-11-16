/**
 * Content-Security-Policy for pages. Scripts run only if they carry this response's random
 * nonce, or are loaded by one that does ('strict-dynamic': the site's lazy chunks, and analytics
 * tools after a visitor accepts them). Inline styles stay allowed: Angular's component styles
 * need them, and styles can't run code. Analytics hosts are listed so the optional tools work
 * once switched on in the admin area; nothing contacts them without consent.
 */
const ANALYTICS_HOSTS = [
  'https://*.google-analytics.com', 'https://*.analytics.google.com',
  'https://*.googletagmanager.com', 'https://*.clarity.ms', 'https://c.bing.com',
].join(' ');

export function contentSecurityPolicy(nonce: string): string {
  return [
    "default-src 'self'",
    `script-src 'nonce-${nonce}' 'strict-dynamic' 'self' https:`,
    "style-src 'self' 'unsafe-inline'",
    `img-src 'self' data: ${ANALYTICS_HOSTS}`,
    `connect-src 'self' ${ANALYTICS_HOSTS}`,
    "font-src 'self'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
  ].join('; ');
}

/** Gives every script tag (and module preload) in a page the response's nonce. */
export function addNonce(html: string, nonce: string): string {
  return html
    .replace(/<script(?![^>]*\snonce=)/g, `<script nonce="${nonce}"`)
    .replace(/<link rel="modulepreload"(?![^>]*\snonce=)/g, `<link rel="modulepreload" nonce="${nonce}"`);
}
