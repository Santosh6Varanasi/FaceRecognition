"""
Database Connection Pool Manager
=================================
Provides a connection pool for PostgreSQL database operations.
"""

import psycopg2
from psycopg2 import pool
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """
    Database connection pool manager for PostgreSQL.
    
    This class manages a connection pool to efficiently handle database
    connections across the application.
    
    Attributes
    ----------
    host : str
        Database host address
    port : int
        Database port number
    database : str
        Database name
    user : str
        Database user
    password : str
        Database password
    min_connections : int
        Minimum number of connections in the pool
    max_connections : int
        Maximum number of connections in the pool
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "face_recognition",
        user: str = "admin",
        password: str = "admin",
        min_connections: int = 1,
        max_connections: int = 10
    ):
        """
        Initialize the database connection pool.
        
        Parameters
        ----------
        host : str
            Database host address
        port : int
            Database port number
        database : str
            Database name
        user : str
            Database user
        password : str
            Database password
        min_connections : int
            Minimum number of connections in the pool
        max_connections : int
            Maximum number of connections in the pool
        """
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.min_connections = min_connections
        self.max_connections = max_connections
        
        try:
            self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                min_connections,
                max_connections,
                host=host,
                port=port,
                database=database,
                user=user,
                password=password
            )
            
            if self.connection_pool:
                logger.info(
                    f"Database connection pool created successfully "
                    f"(min={min_connections}, max={max_connections})"
                )
        except (Exception, psycopg2.DatabaseError) as error:
            logger.error(f"Error creating connection pool: {error}")
            raise
    
    def get_connection(self):
        """
        Get a connection from the pool.
        
        Returns
        -------
        connection
            A psycopg2 connection object from the pool
            
        Raises
        ------
        Exception
            If unable to get a connection from the pool
        """
        try:
            connection = self.connection_pool.getconn()
            if connection:
                return connection
        except (Exception, psycopg2.DatabaseError) as error:
            logger.error(f"Error getting connection from pool: {error}")
            raise
    
    def return_connection(self, connection):
        """
        Return a connection to the pool.
        
        Parameters
        ----------
        connection
            The psycopg2 connection object to return to the pool
        """
        try:
            self.connection_pool.putconn(connection)
        except (Exception, psycopg2.DatabaseError) as error:
            logger.error(f"Error returning connection to pool: {error}")
            raise
    
    def close_all_connections(self):
        """
        Close all connections in the pool.
        
        This should be called when shutting down the application.
        """
        try:
            if self.connection_pool:
                self.connection_pool.closeall()
                logger.info("All database connections closed")
        except (Exception, psycopg2.DatabaseError) as error:
            logger.error(f"Error closing connections: {error}")
            raise
    
    def close_all(self):
        """
        Close all connections in the pool (alias for close_all_connections).
        
        This method provides backward compatibility with existing code.
        """
        self.close_all_connections()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - close all connections."""
        self.close_all_connections()
    
    def __del__(self):
        """Destructor - ensure connections are closed."""
        try:
            self.close_all_connections()
        except:
            pass  # Ignore errors during cleanup
