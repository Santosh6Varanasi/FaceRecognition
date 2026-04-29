"""
Unit tests for BulkOperationHandler class.

Tests verify:
1. get_affected_count() returns correct counts for different filters
2. bulk_delete() deletes faces matching filter with transaction support
3. bulk_reject() updates status to 'rejected' for faces matching filter
4. Operations respect filter values: all, pending, labeled, rejected
5. Transaction rollback on errors

Requirements: 1.3, 1.4, 1.5, 2.3, 2.4, 2.5, 3.1, 3.2, 3.3, 3.4
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from unittest.mock import Mock, MagicMock, call
from services.bulk_operations import BulkOperationHandler


class TestBulkOperationHandler:
    """Test suite for BulkOperationHandler class."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.db_connection_mock = Mock()
        self.db_conn_mock = Mock()
        self.cursor_mock = Mock()
        
        # Setup default mock behavior
        self.db_connection_mock.get_connection.return_value = self.db_conn_mock
        self.db_connection_mock.return_connection = Mock()
        self.db_conn_mock.cursor.return_value = self.cursor_mock
        
        # Create handler instance
        self.handler = BulkOperationHandler(self.db_connection_mock)
    
    # -------------------------------------------------------------------------
    # Tests for get_affected_count()
    # -------------------------------------------------------------------------
    
    def test_get_affected_count_with_all_filter(self):
        """Test get_affected_count returns total count when filter is 'all'."""
        # Setup: 150 total faces
        self.cursor_mock.fetchone.return_value = (150,)
        
        # Execute
        count = self.handler.get_affected_count("all")
        
        # Verify
        assert count == 150
        self.cursor_mock.execute.assert_called_once()
        sql_call = self.cursor_mock.execute.call_args[0][0]
        assert "SELECT COUNT(*) FROM unknown_faces" in sql_call
        assert "WHERE" not in sql_call  # No filter for "all"
    
    def test_get_affected_count_with_pending_filter(self):
        """Test get_affected_count returns count of pending faces."""
        # Setup: 75 pending faces
        self.cursor_mock.fetchone.return_value = (75,)
        
        # Execute
        count = self.handler.get_affected_count("pending")
        
        # Verify
        assert count == 75
        self.cursor_mock.execute.assert_called_once()
        sql_call = self.cursor_mock.execute.call_args[0][0]
        assert "SELECT COUNT(*) FROM unknown_faces WHERE status = %s" in sql_call
        params = self.cursor_mock.execute.call_args[0][1]
        assert params == ("pending",)
    
    def test_get_affected_count_with_labeled_filter(self):
        """Test get_affected_count returns count of labeled faces."""
        # Setup: 50 labeled faces
        self.cursor_mock.fetchone.return_value = (50,)
        
        # Execute
        count = self.handler.get_affected_count("labeled")
        
        # Verify
        assert count == 50
        self.cursor_mock.execute.assert_called_once()
        sql_call = self.cursor_mock.execute.call_args[0][0]
        assert "WHERE status = %s" in sql_call
        params = self.cursor_mock.execute.call_args[0][1]
        assert params == ("labeled",)
    
    def test_get_affected_count_with_rejected_filter(self):
        """Test get_affected_count returns count of rejected faces."""
        # Setup: 25 rejected faces
        self.cursor_mock.fetchone.return_value = (25,)
        
        # Execute
        count = self.handler.get_affected_count("rejected")
        
        # Verify
        assert count == 25
        self.cursor_mock.execute.assert_called_once()
        sql_call = self.cursor_mock.execute.call_args[0][0]
        assert "WHERE status = %s" in sql_call
        params = self.cursor_mock.execute.call_args[0][1]
        assert params == ("rejected",)
    
    def test_get_affected_count_returns_zero_when_no_matches(self):
        """Test get_affected_count returns 0 when no faces match filter."""
        # Setup: 0 faces
        self.cursor_mock.fetchone.return_value = (0,)
        
        # Execute
        count = self.handler.get_affected_count("pending")
        
        # Verify
        assert count == 0
    
    # -------------------------------------------------------------------------
    # Tests for bulk_delete()
    # -------------------------------------------------------------------------
    
    def test_bulk_delete_with_all_filter(self):
        """Test bulk_delete deletes all faces when filter is 'all'."""
        # Setup: 150 faces deleted
        self.cursor_mock.rowcount = 150
        
        # Execute
        result = self.handler.bulk_delete("all")
        
        # Verify
        assert result["success_count"] == 150
        assert result["failure_count"] == 0
        assert result["total_count"] == 150
        assert "Successfully deleted 150" in result["message"]
        
        # Verify SQL
        self.cursor_mock.execute.assert_called_once()
        sql_call = self.cursor_mock.execute.call_args[0][0]
        assert "DELETE FROM unknown_faces" in sql_call
        assert "WHERE" not in sql_call  # No filter for "all"
        
        # Verify transaction committed
        self.db_conn_mock.commit.assert_called_once()
    
    def test_bulk_delete_with_pending_filter(self):
        """Test bulk_delete deletes only pending faces."""
        # Setup: 75 pending faces deleted
        self.cursor_mock.rowcount = 75
        
        # Execute
        result = self.handler.bulk_delete("pending")
        
        # Verify
        assert result["success_count"] == 75
        assert result["failure_count"] == 0
        assert result["total_count"] == 75
        assert "Successfully deleted 75" in result["message"]
        
        # Verify SQL with filter
        self.cursor_mock.execute.assert_called_once()
        sql_call = self.cursor_mock.execute.call_args[0][0]
        assert "DELETE FROM unknown_faces WHERE status = %s" in sql_call
        params = self.cursor_mock.execute.call_args[0][1]
        assert params == ("pending",)
        
        # Verify transaction committed
        self.db_conn_mock.commit.assert_called_once()
    
    def test_bulk_delete_with_labeled_filter(self):
        """Test bulk_delete deletes only labeled faces."""
        # Setup: 50 labeled faces deleted
        self.cursor_mock.rowcount = 50
        
        # Execute
        result = self.handler.bulk_delete("labeled")
        
        # Verify
        assert result["success_count"] == 50
        assert result["total_count"] == 50
        
        # Verify SQL with filter
        sql_call = self.cursor_mock.execute.call_args[0][0]
        assert "WHERE status = %s" in sql_call
        params = self.cursor_mock.execute.call_args[0][1]
        assert params == ("labeled",)
    
    def test_bulk_delete_with_rejected_filter(self):
        """Test bulk_delete deletes only rejected faces."""
        # Setup: 25 rejected faces deleted
        self.cursor_mock.rowcount = 25
        
        # Execute
        result = self.handler.bulk_delete("rejected")
        
        # Verify
        assert result["success_count"] == 25
        assert result["total_count"] == 25
        
        # Verify SQL with filter
        sql_call = self.cursor_mock.execute.call_args[0][0]
        assert "WHERE status = %s" in sql_call
        params = self.cursor_mock.execute.call_args[0][1]
        assert params == ("rejected",)
    
    def test_bulk_delete_returns_zero_when_no_matches(self):
        """Test bulk_delete returns 0 counts when no faces match filter."""
        # Setup: 0 faces deleted
        self.cursor_mock.rowcount = 0
        
        # Execute
        result = self.handler.bulk_delete("pending")
        
        # Verify
        assert result["success_count"] == 0
        assert result["failure_count"] == 0
        assert result["total_count"] == 0
        assert "Successfully deleted 0" in result["message"]
    
    def test_bulk_delete_rolls_back_on_error(self):
        """Test bulk_delete rolls back transaction on database error."""
        # Setup: Simulate database error
        self.cursor_mock.execute.side_effect = Exception("Database error")
        
        # Execute
        result = self.handler.bulk_delete("pending")
        
        # Verify error handling
        assert result["success_count"] == 0
        assert result["failure_count"] == 0
        assert result["total_count"] == 0
        assert "Bulk delete failed" in result["message"]
        assert "Database error" in result["message"]
        
        # Verify rollback was called
        self.db_conn_mock.rollback.assert_called_once()
        # Verify commit was NOT called
        self.db_conn_mock.commit.assert_not_called()
    
    # -------------------------------------------------------------------------
    # Tests for bulk_reject()
    # -------------------------------------------------------------------------
    
    def test_bulk_reject_with_all_filter(self):
        """Test bulk_reject updates all faces to rejected when filter is 'all'."""
        # Setup: 150 faces updated
        self.cursor_mock.rowcount = 150
        
        # Execute
        result = self.handler.bulk_reject("all")
        
        # Verify
        assert result["success_count"] == 150
        assert result["failure_count"] == 0
        assert result["total_count"] == 150
        assert "Successfully rejected 150" in result["message"]
        
        # Verify SQL
        self.cursor_mock.execute.assert_called_once()
        sql_call = self.cursor_mock.execute.call_args[0][0]
        assert "UPDATE unknown_faces SET status = 'rejected'" in sql_call
        assert "updated_at = NOW()" in sql_call
        # For "all" filter, WHERE clause should not be present
        assert "WHERE status = %s" not in sql_call
        
        # Verify transaction committed
        self.db_conn_mock.commit.assert_called_once()
    
    def test_bulk_reject_with_pending_filter(self):
        """Test bulk_reject updates only pending faces to rejected."""
        # Setup: 75 pending faces updated
        self.cursor_mock.rowcount = 75
        
        # Execute
        result = self.handler.bulk_reject("pending")
        
        # Verify
        assert result["success_count"] == 75
        assert result["failure_count"] == 0
        assert result["total_count"] == 75
        assert "Successfully rejected 75" in result["message"]
        
        # Verify SQL with filter
        self.cursor_mock.execute.assert_called_once()
        sql_call = self.cursor_mock.execute.call_args[0][0]
        assert "UPDATE unknown_faces SET status = 'rejected'" in sql_call
        assert "WHERE status = %s" in sql_call
        params = self.cursor_mock.execute.call_args[0][1]
        assert params == ("pending",)
        
        # Verify transaction committed
        self.db_conn_mock.commit.assert_called_once()
    
    def test_bulk_reject_with_labeled_filter(self):
        """Test bulk_reject updates only labeled faces to rejected."""
        # Setup: 50 labeled faces updated
        self.cursor_mock.rowcount = 50
        
        # Execute
        result = self.handler.bulk_reject("labeled")
        
        # Verify
        assert result["success_count"] == 50
        assert result["total_count"] == 50
        
        # Verify SQL with filter
        sql_call = self.cursor_mock.execute.call_args[0][0]
        assert "WHERE status = %s" in sql_call
        params = self.cursor_mock.execute.call_args[0][1]
        assert params == ("labeled",)
    
    def test_bulk_reject_with_rejected_filter(self):
        """Test bulk_reject handles rejected filter (no-op scenario)."""
        # Setup: 0 faces updated (already rejected)
        self.cursor_mock.rowcount = 0
        
        # Execute
        result = self.handler.bulk_reject("rejected")
        
        # Verify
        assert result["success_count"] == 0
        assert result["total_count"] == 0
        
        # Verify SQL with filter
        sql_call = self.cursor_mock.execute.call_args[0][0]
        assert "WHERE status = %s" in sql_call
        params = self.cursor_mock.execute.call_args[0][1]
        assert params == ("rejected",)
    
    def test_bulk_reject_updates_timestamp(self):
        """Test bulk_reject updates the updated_at timestamp."""
        # Setup
        self.cursor_mock.rowcount = 10
        
        # Execute
        result = self.handler.bulk_reject("pending")
        
        # Verify timestamp update in SQL
        sql_call = self.cursor_mock.execute.call_args[0][0]
        assert "updated_at = NOW()" in sql_call
    
    def test_bulk_reject_returns_zero_when_no_matches(self):
        """Test bulk_reject returns 0 counts when no faces match filter."""
        # Setup: 0 faces updated
        self.cursor_mock.rowcount = 0
        
        # Execute
        result = self.handler.bulk_reject("pending")
        
        # Verify
        assert result["success_count"] == 0
        assert result["failure_count"] == 0
        assert result["total_count"] == 0
        assert "Successfully rejected 0" in result["message"]
    
    def test_bulk_reject_rolls_back_on_error(self):
        """Test bulk_reject rolls back transaction on database error."""
        # Setup: Simulate database error
        self.cursor_mock.execute.side_effect = Exception("Database error")
        
        # Execute
        result = self.handler.bulk_reject("pending")
        
        # Verify error handling
        assert result["success_count"] == 0
        assert result["failure_count"] == 0
        assert result["total_count"] == 0
        assert "Bulk reject failed" in result["message"]
        assert "Database error" in result["message"]
        
        # Verify rollback was called
        self.db_conn_mock.rollback.assert_called_once()
        # Verify commit was NOT called
        self.db_conn_mock.commit.assert_not_called()
    
    # -------------------------------------------------------------------------
    # Tests for connection management
    # -------------------------------------------------------------------------
    
    def test_get_affected_count_closes_cursor_and_returns_connection(self):
        """Test get_affected_count properly closes cursor and returns connection."""
        # Setup
        self.cursor_mock.fetchone.return_value = (100,)
        
        # Execute
        self.handler.get_affected_count("all")
        
        # Verify cleanup
        self.cursor_mock.close.assert_called_once()
        self.db_connection_mock.return_connection.assert_called_once_with(self.db_conn_mock)
    
    def test_bulk_delete_closes_cursor_and_returns_connection(self):
        """Test bulk_delete properly closes cursor and returns connection."""
        # Setup
        self.cursor_mock.rowcount = 50
        
        # Execute
        self.handler.bulk_delete("pending")
        
        # Verify cleanup
        self.cursor_mock.close.assert_called_once()
        self.db_connection_mock.return_connection.assert_called_once_with(self.db_conn_mock)
    
    def test_bulk_reject_closes_cursor_and_returns_connection(self):
        """Test bulk_reject properly closes cursor and returns connection."""
        # Setup
        self.cursor_mock.rowcount = 50
        
        # Execute
        self.handler.bulk_reject("pending")
        
        # Verify cleanup
        self.cursor_mock.close.assert_called_once()
        self.db_connection_mock.return_connection.assert_called_once_with(self.db_conn_mock)
    
    def test_bulk_delete_closes_cursor_even_on_error(self):
        """Test bulk_delete closes cursor even when error occurs."""
        # Setup: Simulate error
        self.cursor_mock.execute.side_effect = Exception("Database error")
        
        # Execute
        self.handler.bulk_delete("pending")
        
        # Verify cleanup still happens
        self.cursor_mock.close.assert_called_once()
        self.db_connection_mock.return_connection.assert_called_once_with(self.db_conn_mock)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
