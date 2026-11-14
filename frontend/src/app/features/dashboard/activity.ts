import { ActivityItem } from './dashboard.types';

type Meta = Record<string, unknown>;
const str = (v: unknown) => (typeof v === 'string' ? v : '');
const change = (v: unknown) => (v && typeof v === 'object' ? (v as { to?: unknown }).to : undefined);

/** One plain-English line for an audit entry. Unknown actions fall back to the action code. */
export function describe(item: ActivityItem): string {
  const who = item.actor_name ?? 'Someone';
  const m: Meta = item.meta ?? {};
  switch (item.action) {
    case 'organization.create': return `${who} created the organization`;
    case 'organization.update': return `${who} renamed the organization to ${str(change(m['name']))}`;
    case 'client.create': return `${who} added client ${str(m['name'])}`;
    case 'client.update':
      if (m['status'] === 'archived') return `${who} archived client ${str(m['name'])}`;
      if (m['status'] === 'active') return `${who} restored client ${str(m['name'])}`;
      return `${who} updated client ${str(m['name'])}`;
    case 'client.delete': return `${who} deleted client ${str(m['name'])}`;
    case 'client_user.link': return `${who} gave ${str(m['user_email'])} portal access to ${str(m['client'])}`;
    case 'client_user.unlink': return `${who} removed ${str(m['user_email'])}'s portal access to ${str(m['client'])}`;
    case 'website.create': return `${who} added website ${str(m['url'])}`;
    case 'website.update': return `${who} updated a website`;
    case 'website.delete': return `${who} deleted website ${str(m['url'])}`;
    case 'member.update':
      if (change(m['role'])) return `${who} made ${str(m['user_email'])} ${str(change(m['role']))}`;
      if (change(m['status']) === 'disabled') return `${who} disabled ${str(m['user_email'])}'s access`;
      if (change(m['status']) === 'active') return `${who} restored ${str(m['user_email'])}'s access`;
      return `${who} updated ${str(m['user_email'])}`;
    case 'member.remove': return `${who} removed ${str(m['user_email'])}`;
    case 'member.leave': return `${who} left the organization`;
    case 'invitation.create': return `${who} invited ${str(m['email'])} as ${str(m['role'])}`;
    case 'invitation.resend': return `${who} resent the invitation to ${str(m['email'])}`;
    case 'invitation.revoke': return `${who} cancelled the invitation to ${str(m['email'])}`;
    case 'invitation.accept': return `${who} joined as ${str(m['role'])}`;
    case 'role.create': return `${who} created the ${str(m['name'])} role`;
    case 'role.update': return `${who} changed the ${str(m['role'])} role`;
    case 'role.delete': return `${who} deleted the ${str(m['name'])} role`;
    default: return `${who}: ${item.action}`;
  }
}

const UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
  ['year', 31_536_000], ['month', 2_592_000], ['week', 604_800], ['day', 86_400],
  ['hour', 3_600], ['minute', 60],
];
const rtf = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' });

/** "just now", "5 minutes ago", "yesterday"… */
export function timeAgo(iso: string, now = Date.now()): string {
  const seconds = Math.round((new Date(iso).getTime() - now) / 1000);
  if (Math.abs(seconds) < 45) return 'just now';
  for (const [unit, size] of UNITS) {
    if (Math.abs(seconds) >= size || unit === 'minute') return rtf.format(Math.round(seconds / size), unit);
  }
  return 'just now';
}
