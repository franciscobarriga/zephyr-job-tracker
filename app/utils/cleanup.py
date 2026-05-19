"""
Stale-job cleanup.

Retention rules (status-aware):
- New, never viewed:    delete if created_at  < now() - 14 days
- New, viewed once:     delete if last_viewed_at < now() - 14 days
- Ignored:              deleted immediately on status change (in routes/jobs.py),
                        but this also sweeps any lingering rows older than 1 day
- Thinking / Applied:   never auto-delete (user signaled intent / record of truth)
"""

from datetime import datetime, timedelta, timezone
from typing import Optional


NEW_STALE_DAYS = 14
IGNORED_SWEEP_DAYS = 1


def cleanup_stale_jobs(supabase_client, user_id: Optional[str] = None) -> dict:
    """
    Delete stale jobs for a single user (or all users if user_id is None).

    Returns:
        {"deleted_count": int, "breakdown": {"new_unviewed": N, "new_viewed": N, "ignored": N}}
    """
    now = datetime.now(timezone.utc)
    new_cutoff = (now - timedelta(days=NEW_STALE_DAYS)).isoformat()
    ignored_cutoff = (now - timedelta(days=IGNORED_SWEEP_DAYS)).isoformat()

    breakdown = {"new_unviewed": 0, "new_viewed": 0, "ignored": 0}

    # 1) New + never viewed + older than 14d
    q = (
        supabase_client.table("jobs")
        .delete()
        .eq("status", "New")
        .is_("last_viewed_at", "null")
        .lt("created_at", new_cutoff)
    )
    if user_id:
        q = q.eq("user_id", user_id)
    resp = q.execute()
    breakdown["new_unviewed"] = len(resp.data or [])

    # 2) New + viewed but no engagement for 14d
    q = (
        supabase_client.table("jobs")
        .delete()
        .eq("status", "New")
        .lt("last_viewed_at", new_cutoff)
    )
    if user_id:
        q = q.eq("user_id", user_id)
    resp = q.execute()
    breakdown["new_viewed"] = len(resp.data or [])

    # 3) Ignored older than 1d (safety sweep — immediate deletion lives in routes)
    q = (
        supabase_client.table("jobs")
        .delete()
        .eq("status", "Ignored")
        .lt("updated_at", ignored_cutoff)
    )
    if user_id:
        q = q.eq("user_id", user_id)
    resp = q.execute()
    breakdown["ignored"] = len(resp.data or [])

    total = sum(breakdown.values())

    # Log per-user (only when we know who; system-wide runs log per-user separately)
    if user_id and total > 0:
        supabase_client.table("cleanup_log").insert({
            "user_id": user_id,
            "deleted_count": total,
            "breakdown": breakdown,
        }).execute()

    return {"deleted_count": total, "breakdown": breakdown}


def cleanup_total_for_user(supabase_client, user_id: str, days: int = 30) -> int:
    """Sum of deleted_count for this user across the last `days` (for dashboard footer)."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    resp = (
        supabase_client.table("cleanup_log")
        .select("deleted_count")
        .eq("user_id", user_id)
        .gte("ran_at", cutoff)
        .execute()
    )
    return sum(row["deleted_count"] for row in (resp.data or []))
