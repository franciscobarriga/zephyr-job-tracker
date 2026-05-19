from unittest.mock import MagicMock
from app.utils.cleanup import cleanup_stale_jobs, cleanup_total_for_user


def _delete_chain(deleted_rows):
    """Build a mock chain that returns `deleted_rows` from .execute()."""
    chain = MagicMock()
    chain.execute.return_value = MagicMock(data=deleted_rows)
    return chain


class TestCleanupStaleJobs:
    def test_returns_zero_when_nothing_stale(self):
        sb = MagicMock()
        # All three delete chains return empty
        sb.table.return_value.delete.return_value.eq.return_value.is_.return_value.lt.return_value.eq.return_value = _delete_chain([])
        sb.table.return_value.delete.return_value.eq.return_value.lt.return_value.eq.return_value = _delete_chain([])

        result = cleanup_stale_jobs(sb, user_id="user-1")

        assert result["deleted_count"] == 0
        assert result["breakdown"] == {"new_unviewed": 0, "new_viewed": 0, "ignored": 0}
        # No log row should be inserted when nothing was deleted
        sb.table.assert_called()
        insert_calls = [c for c in sb.table.return_value.insert.call_args_list]
        assert insert_calls == []

    def test_counts_and_logs_when_jobs_deleted(self):
        sb = MagicMock()

        # We don't bother chaining exactly — just make every .execute() on a
        # delete-style chain return our fake rows. To do that, patch each leaf.
        unviewed_chain = _delete_chain([{"id": 1}, {"id": 2}])
        viewed_chain = _delete_chain([{"id": 3}])
        ignored_chain = _delete_chain([{"id": 4}, {"id": 5}, {"id": 6}])

        # delete().eq("status","New").is_("last_viewed_at","null").lt(...).eq("user_id",...)
        sb.table.return_value.delete.return_value.eq.return_value.is_.return_value.lt.return_value.eq.return_value = unviewed_chain
        # delete().eq("status","New").lt("last_viewed_at",...).eq("user_id",...)
        # delete().eq("status","Ignored").lt("updated_at",...).eq("user_id",...)
        # The two non-is_ chains share the same path; we differentiate by side_effect
        non_is_chain_factory = MagicMock(side_effect=[viewed_chain, ignored_chain])
        sb.table.return_value.delete.return_value.eq.return_value.lt.return_value.eq = non_is_chain_factory

        result = cleanup_stale_jobs(sb, user_id="user-1")

        assert result["breakdown"] == {"new_unviewed": 2, "new_viewed": 1, "ignored": 3}
        assert result["deleted_count"] == 6
        # Log row inserted once
        log_inserts = sb.table.return_value.insert.call_args_list
        assert len(log_inserts) >= 1
        logged = log_inserts[-1].args[0]
        assert logged["user_id"] == "user-1"
        assert logged["deleted_count"] == 6
        assert logged["breakdown"]["ignored"] == 3

    def test_skips_user_filter_when_no_user_id(self):
        """System-wide sweep does not call .eq('user_id', ...) on the final link."""
        sb = MagicMock()
        sb.table.return_value.delete.return_value.eq.return_value.is_.return_value.lt.return_value = _delete_chain([])
        sb.table.return_value.delete.return_value.eq.return_value.lt.return_value = _delete_chain([])

        result = cleanup_stale_jobs(sb, user_id=None)

        assert result["deleted_count"] == 0
        # No log insert for system-wide call (per-user logging happens elsewhere)
        assert sb.table.return_value.insert.call_args_list == []


class TestCleanupTotalForUser:
    def test_sums_deleted_counts(self):
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = MagicMock(
            data=[{"deleted_count": 5}, {"deleted_count": 3}, {"deleted_count": 12}]
        )
        assert cleanup_total_for_user(sb, "user-1", days=30) == 20

    def test_returns_zero_when_no_log_rows(self):
        sb = MagicMock()
        sb.table.return_value.select.return_value.eq.return_value.gte.return_value.execute.return_value = MagicMock(data=[])
        assert cleanup_total_for_user(sb, "user-1") == 0
