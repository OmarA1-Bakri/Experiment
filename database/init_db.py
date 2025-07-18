"""
Database initialization script for ComplianceGPT (Asynchronous)

This script creates all database tables and optionally populates them with default data.
Run this script after setting up your DATABASE_URL environment variable.
"""

import asyncio
import os
import sys

from dotenv import load_dotenv
from sqlalchemy import select

# Load environment variables
load_dotenv()

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.logging_config import get_logger, setup_logging  # noqa: E402
from database.db_setup import Base, _init_async_db, get_async_db  # noqa: E402
from services.framework_service import initialize_default_frameworks  # noqa: E402

# Setup logging first
setup_logging()
logger = get_logger(__name__)


async def create_tables():
    """Create all database tables asynchronously."""
    logger.info("Creating database tables...")
    try:
        # Initialize the async database engine
        _init_async_db()
        from database.db_setup import _async_engine

        async with _async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully.")
        return True
    except Exception as e:
        logger.error(f"Error creating tables: {e}", exc_info=True)
        return False


async def populate_default_data():
    """Populate database with default frameworks and data asynchronously."""
    logger.info("Populating default data...")
    try:
        async for db in get_async_db():
            await initialize_default_frameworks(db)
            # Ensure to commit if initialize_default_frameworks doesn't commit itself for new items
            # However, initialize_default_frameworks already handles its commit.
        logger.info("Default frameworks initialized successfully.")
        return True
    except Exception as e:
        logger.error(f"Error populating default data: {e}", exc_info=True)
        return False


async def test_connection():
    """Test database connection asynchronously."""
    logger.info("Testing database connection...")
    try:
        async for db in get_async_db():
            await db.execute(select(1))
        logger.info("Database connection successful.")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}", exc_info=True)
        return False


async def main():
    """Main asynchronous initialization function."""
    logger.info("ComplianceGPT Database Initialization")
    logger.info("========================================")

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL environment variable not set. Please set it in your .env file.")
        return False

    logger.info(f"Database URL: {database_url}")

    if not await test_connection():
        return False

    if not await create_tables():
        return False

    if not await populate_default_data():
        return False

    logger.info("Database initialization completed successfully!")
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
