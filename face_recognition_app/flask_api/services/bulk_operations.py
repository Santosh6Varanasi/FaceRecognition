"""
Bulk operations handler for unknown faces management.

This module provides the BulkOperationHandler class for executing bulk operations
on unknown faces with filter-aware operations and transaction support.

Requirements: 1.3, 1.4, 1.5, 2.3, 2.4, 2.5, 3.1, 3.2, 3.3, 3.4
"""

from typing import Dict, Optional
from face_recognition_app.database.db_connection import DatabaseConnection


class BulkOperationHandler:
    """
    Handler for bulk operations on unknown faces.
    
    Supports filter-aware operations (all, pending, labeled, rejected) with
    database transaction support for atomicity.
    
    Attributes:
        db_connection: DatabaseConnection instance for database operations
    """
    
    def __init__(self, db_connection: DatabaseConnection):
        """
        Initialize BulkOperationHandler with database connection.
        
        Args:
            db_connection: DatabaseConnection instance
        """
        self.db_connection = db_connection
    
    def get_affected_count(self, filter_status: str) -> int:
        """
        Count faces that would be affected by a bulk operation.
        
        Returns the number of unknown faces matching the filter status.
        Used for preview before operation execution.
        
        Args:
            filter_status: Filter value - "all", "pending", "labeled", or "rejected"
        
        Returns:
            int: Count of faces matching the filter
        
        Requirements: 1.3, 2.3, 3.1, 3.2, 3.3, 3.4
        """
        db_conn = self.db_connection.get_connection()
        try:
            cursor = db_conn.cursor()
            
            # Build query based on filter
            if filter_status == "all":
                cursor.execute("SELECT COUNT(*) FROM unknown_faces")
            else:
                cursor.execute(
                    "SELECT COUNT(*) FROM unknown_faces WHERE status = %s",
                    (filter_status,)
                )
            
            count = cursor.fetchone()[0]
            return int(count)
        finally:
            cursor.close()
            self.db_connection.return_connection(db_conn)
    
    def bulk_delete(self, filter_status: str) -> Dict:
        """
        Delete all unknown faces matching the filter status.
        
        Executes delete operation in a database transaction for atomicity.
        If filter is "all", deletes all unknown faces regardless of status.
        
        Args:
            filter_status: Filter value - "all", "pending", "labeled", or "rejected"
        
        Returns:
            BulkOperationResult dict with keys:
                - success_count: Number of faces successfully deleted
                - failure_count: Number of faces that failed to delete (always 0 for delete)
                - total_count: Total number of faces affected
                - message: Human-readable result message
        
        Requirements: 1.3, 1.4, 1.5
        """
        db_conn = self.db_connection.get_connection()
        try:
            cursor = db_conn.cursor()
            
            # Build delete query based on filter
            if filter_status == "all":
                cursor.execute("DELETE FROM unknown_faces")
            else:
                cursor.execute(
                    "DELETE FROM unknown_faces WHERE status = %s",
                    (filter_status,)
                )
            
            # Get number of deleted rows
            deleted_count = cursor.rowcount
            
            # Commit transaction
            db_conn.commit()
            
            return {
                "success_count": deleted_count,
                "failure_count": 0,
                "total_count": deleted_count,
                "message": f"Successfully deleted {deleted_count} unknown face(s)"
            }
        except Exception as e:
            # Rollback on error
            db_conn.rollback()
            return {
                "success_count": 0,
                "failure_count": 0,
                "total_count": 0,
                "message": f"Bulk delete failed: {str(e)}"
            }
        finally:
            cursor.close()
            self.db_connection.return_connection(db_conn)
    
    def bulk_reject(self, filter_status: str) -> Dict:
        """
        Reject all unknown faces matching the filter status.
        
        Updates the status to 'rejected' for all faces matching the filter.
        Executes update operation in a database transaction for atomicity.
        If filter is "all", rejects all unknown faces regardless of current status.
        
        Args:
            filter_status: Filter value - "all", "pending", "labeled", or "rejected"
        
        Returns:
            BulkOperationResult dict with keys:
                - success_count: Number of faces successfully rejected
                - failure_count: Number of faces that failed to reject (always 0 for update)
                - total_count: Total number of faces affected
                - message: Human-readable result message
        
        Requirements: 2.3, 2.4, 2.5
        """
        db_conn = self.db_connection.get_connection()
        try:
            cursor = db_conn.cursor()
            
            # Build update query based on filter
            if filter_status == "all":
                cursor.execute(
                    "UPDATE unknown_faces SET status = 'rejected', updated_at = NOW()"
                )
            else:
                cursor.execute(
                    "UPDATE unknown_faces SET status = 'rejected', updated_at = NOW() "
                    "WHERE status = %s",
                    (filter_status,)
                )
            
            # Get number of updated rows
            updated_count = cursor.rowcount
            
            # Commit transaction
            db_conn.commit()
            
            return {
                "success_count": updated_count,
                "failure_count": 0,
                "total_count": updated_count,
                "message": f"Successfully rejected {updated_count} unknown face(s)"
            }
        except Exception as e:
            # Rollback on error
            db_conn.rollback()
            return {
                "success_count": 0,
                "failure_count": 0,
                "total_count": 0,
                "message": f"Bulk reject failed: {str(e)}"
            }
        finally:
            cursor.close()
            self.db_connection.return_connection(db_conn)
