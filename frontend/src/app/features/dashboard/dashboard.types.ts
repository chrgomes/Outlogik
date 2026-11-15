export interface ActivityItem {
  id: string;
  action: string;
  actor_name: string | null;
  target_type: string | null;
  target_id: string | null;
  meta: Record<string, unknown>;
  created_at: string;
}

export interface DashboardSummary {
  clients: { total: number; active: number; archived: number };
  websites: { total: number; active: number; paused: number; archived: number };
  team: { members: number; client_users: number; pending_invitations: number | null } | null;
  recent_activity: ActivityItem[] | null;
}
