/** localStorage for per-browser preferences only. Never throws (private mode, blocked storage). */
export const prefs = {
  get(key: string): string | null {
    try {
      return globalThis.localStorage?.getItem(key) ?? null;
    } catch {
      return null;
    }
  },
  set(key: string, value: string): void {
    try {
      globalThis.localStorage?.setItem(key, value);
    } catch {
      /* preference just won't persist */
    }
  },
};
