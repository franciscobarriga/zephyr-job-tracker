"""
Stale-job cleanup runner. Invoked by GitHub Actions daily.

Iterates every user that has at least one job and runs cleanup_stale_jobs
per user (so each gets its own cleanup_log row).
"""

import os
from dotenv import load_dotenv
from supabase import create_client

from app.utils.cleanup import cleanup_stale_jobs


def main():
    load_dotenv()
    url = os.environ["SUPABASE_URL"]
    # Service key bypasses RLS so we can sweep across all users
    key = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ["SUPABASE_ANON_KEY"]
    sb = create_client(url, key)

    # Distinct user_ids with at least one job
    users_resp = sb.table("jobs").select("user_id").execute()
    user_ids = sorted({row["user_id"] for row in (users_resp.data or []) if row.get("user_id")})

    total = 0
    for uid in user_ids:
        result = cleanup_stale_jobs(sb, user_id=uid)
        if result["deleted_count"] > 0:
            print(f"[cleanup] user={uid} deleted={result['deleted_count']} breakdown={result['breakdown']}")
            total += result["deleted_count"]

    print(f"[cleanup] done. users_processed={len(user_ids)} total_deleted={total}")


if __name__ == "__main__":
    main()
