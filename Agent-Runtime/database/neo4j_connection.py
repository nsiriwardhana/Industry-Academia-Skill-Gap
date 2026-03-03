"""
Neo4j Database Connection Manager.
"""
import logging
from contextlib import contextmanager
from neo4j import GraphDatabase
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

logger = logging.getLogger(__name__)


class Neo4jConnection:
    """
    Singleton Neo4j connection manager.
    """
    _driver = None

    @classmethod
    def get_driver(cls):
        """
        Initialize and return Neo4j driver (singleton pattern).
        
        Returns:
            neo4j.Driver: Initialized Neo4j driver
        """
        if cls._driver is None:
            try:
                cls._driver = GraphDatabase.driver(
                    NEO4J_URI,
                    auth=(NEO4J_USER, NEO4J_PASSWORD)
                )
                logger.info(f"✓ Connected to Neo4j at {NEO4J_URI}")
            except Exception as e:
                logger.error(f"✗ Failed to connect to Neo4j: {e}")
                raise
        return cls._driver

    @classmethod
    def close(cls):
        """Close the Neo4j driver connection."""
        if cls._driver is not None:
            cls._driver.close()
            cls._driver = None
            logger.info("✓ Neo4j connection closed")

    @classmethod
    @contextmanager
    def get_session(cls):
        """
        Context manager for Neo4j sessions.
        
        Usage:
            with Neo4jConnection.get_session() as session:
                result = session.run(query)
        
        Yields:
            neo4j.Session: Database session
        """
        driver = cls.get_driver()
        session = driver.session()
        try:
            yield session
        finally:
            session.close()
