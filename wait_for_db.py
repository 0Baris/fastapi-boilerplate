"""
Database connection health check script.

Waits for database to be ready before running migrations or starting the application.
Used in production deployments with Cloud SQL.
"""

import asyncio
import sys
import time

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.core.config import settings


async def wait_for_database(max_retries: int = 30, retry_interval: int = 2) -> bool:
    """
    Wait for database connection to be ready.

    Args:
        max_retries: Maximum number of connection attempts
        retry_interval: Seconds to wait between attempts

    Returns:
        True if connection successful, False otherwise
    """
    print("Waiting for database connection...")

    engine = create_async_engine(settings.DATABASE_URL, echo=False, pool_pre_ping=True)

    for attempt in range(max_retries):
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
                await conn.commit()

            print("Database connection established successfully")
            await engine.dispose()
            return True

        except Exception as e:
            print(f"Database is not ready yet... retrying in {retry_interval} seconds ({attempt}/{max_retries})")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_interval)
            else:
                print("Error: Could not connect to the database.")
                print(f"Last error: {e}")

    await engine.dispose()
    return False


if __name__ == "__main__":
    start_time = time.time()
    result = asyncio.run(wait_for_database())
    elapsed = time.time() - start_time

    if result:
        print(f"Database ready after {elapsed:.2f} seconds")
        sys.exit(0)
    else:
        print(f"Failed to connect to database after {elapsed:.2f} seconds")
        sys.exit(1)
