import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';

/** A challenge from the API (see backend/app/modules/leads/challenge.py). */
export interface Challenge {
  algorithm: string;
  challenge: string;
  salt: string;
  max_number: number;
  signature: string;
}

/** What's sent back with a form. */
export interface ProofSolution {
  algorithm: string;
  challenge: string;
  salt: string;
  number: number;
  signature: string;
}

const BATCH = 1000;

/**
 * Finds the number whose SHA-256(salt + number) matches the challenge, using the browser's own
 * hashing in batches and pausing between them, so the page stays responsive. About half a
 * second of work on a typical device.
 */
export async function solve(ch: Challenge): Promise<number | null> {
  const encoder = new TextEncoder();
  for (let start = 0; start <= ch.max_number; start += BATCH) {
    const numbers = Array.from({ length: Math.min(BATCH, ch.max_number - start + 1) }, (_, i) => start + i);
    const hashes = await Promise.all(
      numbers.map((n) => crypto.subtle.digest('SHA-256', encoder.encode(ch.salt + n))));
    const found = hashes.findIndex((h) => toHex(h) === ch.challenge);
    if (found >= 0) return numbers[found];
    await new Promise((resolve) => setTimeout(resolve));
  }
  return null;
}

function toHex(buffer: ArrayBuffer): string {
  return Array.from(new Uint8Array(buffer), (b) => b.toString(16).padStart(2, '0')).join('');
}

function expiresAt(salt: string): number {
  return Number(salt.split('?expires=')[1] ?? 0) * 1000;
}

/**
 * The invisible "are you a person's browser" check for one form. Call prepare() when the
 * visitor starts on the form, so the work is done while they type; take() gives the solution
 * when they press Send (fetching and solving then if needed, or if the earlier one expired).
 * Each solution is used once.
 */
export class FormProof {
  private pending: Promise<ProofSolution | null> | null = null;
  private validUntil = 0;

  constructor(private readonly http: HttpClient) {}

  prepare(): void {
    if (this.pending && Date.now() < this.validUntil - 30_000) return;
    this.validUntil = Number.MAX_SAFE_INTEGER; // until the challenge says otherwise
    this.pending = this.fetchAndSolve();
  }

  async take(): Promise<ProofSolution | null> {
    this.prepare();
    const pending = this.pending!;
    this.pending = null;
    return (await pending) ?? (await this.fetchAndSolve()); // one retry if the first attempt failed
  }

  private async fetchAndSolve(): Promise<ProofSolution | null> {
    try {
      const ch = await firstValueFrom(this.http.get<Challenge>('/api/public/challenge'));
      this.validUntil = expiresAt(ch.salt);
      const number = await solve(ch);
      if (number === null) return null;
      return { algorithm: ch.algorithm, challenge: ch.challenge, salt: ch.salt, number, signature: ch.signature };
    } catch {
      return null; // the form is still sent; the API then files it under spam for review
    }
  }
}
