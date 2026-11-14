import { HttpErrorResponse } from '@angular/common/http';

import { apiProblem, safeReturnUrl } from './api-errors';

describe('safeReturnUrl', () => {
  it.each([
    ['/o/acme/clients', '/o/acme/clients'],
    ['/accept-invite?token=abc', '/accept-invite?token=abc'],
    [undefined, '/'],
    ['', '/'],
    ['https://evil.example.com', '/'],
    ['//evil.example.com', '/'],
    ['/\\evil.example.com', '/'],
    ['javascript:alert(1)', '/'],
  ])('%s → %s', (input, expected) => {
    expect(safeReturnUrl(input)).toBe(expected);
  });
});

describe('apiProblem', () => {
  const http = (status: number, error: unknown) => new HttpErrorResponse({ status, error });

  it('reads the API error format and field errors', () => {
    const p = apiProblem(http(422, { error: { code: 'validation_error', message: 'Some fields are invalid.',
      details: [{ field: 'password', message: 'String should have at least 10 characters' },
        { field: 'email', message: 'value is not a valid email address: bad' }] } }));
    expect(p.code).toBe('validation_error');
    expect(p.fields).toEqual({ password: 'Use at least 10 characters.',
      email: 'Enter a valid email address.' });
  });

  it('explains rate limits in minutes', () => {
    const p = apiProblem(http(429, { error: { code: 'rate_limited', message: 'x',
      details: { retry_after: 240 } } }));
    expect(p.message).toBe('Too many attempts. Try again in 4 minutes.');
  });

  it('explains network failures', () => {
    expect(apiProblem(http(0, null)).code).toBe('network');
  });
});
