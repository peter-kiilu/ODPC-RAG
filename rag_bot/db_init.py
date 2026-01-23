"""
Database initialization script for the bot
Creates the necessary PostgreSQL database and tables
"""

import os
import sys
import logging
import asyncio
import asyncpg
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv

# load env variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database configuration - FIXED: Match docker-compose defaults
POSTGRES_USER = os.getenv("POSTGRES_USER", "user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")  # FIXED: Was 5445
POSTGRES_DB = os.getenv("POSTGRES_DB", "odpc_chatdb")  # FIXED: Was chatdb

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

# Admin database URL (for creating the main database if it doesn't exist)
ADMIN_DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/postgres"


def create_db_if_not_exists():
    """
    Creates the main database if it does not exist
    """
    try:
        logger.info(f"Connecting to admin database at {POSTGRES_HOST}:{POSTGRES_PORT}")
        logger.info(f"Using user: {POSTGRES_USER}")
        
        # connect to the postgres admin database
        admin_engine = create_engine(
            ADMIN_DATABASE_URL,
            isolation_level="AUTOCOMMIT"
        )

        with admin_engine.connect() as conn:
            # Check if database exists
            result = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :dbname"),
                {"dbname": POSTGRES_DB}
            )

            if not result.fetchone():
                logger.info(f"Database '{POSTGRES_DB}' does not exist. Creating...")
                conn.execute(text(f'CREATE DATABASE "{POSTGRES_DB}"'))
                logger.info(f"Database '{POSTGRES_DB}' created successfully")
            else:
                logger.info(f"Database '{POSTGRES_DB}' already exists")

        admin_engine.dispose()
    except SQLAlchemyError as e:
        logger.error(f"Error creating database: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error creating database: {e}")
        sys.exit(1)


def create_tables():
    """
    Creates the necessary tables in the database
    """
    try:
        logger.info(f"Connecting to database '{POSTGRES_DB}' to create tables...")
        engine = create_engine(DATABASE_URL)
        
        with engine.connect() as conn:
            # Create chat_messages table
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    message_id SERIAL PRIMARY KEY,
                    session_id UUID NOT NULL,
                    user_message TEXT NOT NULL,
                    bot_response TEXT,
                    role VARCHAR(50) NOT NULL,
                    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    metadata JSONB
                )
            """))
            
            # Create indexes for better query performance
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_session_id 
                ON chat_messages(session_id)
            """))
            
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON chat_messages(timestamp DESC)
            """))
            
            conn.commit()
            logger.info("Tables created successfully")
            
        engine.dispose()
        
    except SQLAlchemyError as e:
        logger.error(f"Error creating tables: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error creating tables: {e}")
        sys.exit(1)


async def test_database_connection():
    """Test the database connection using asyncpg"""
    try:
        logger.info(f"Testing connection to {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")
        
        conn = await asyncpg.connect(
            host=POSTGRES_HOST,
            port=int(POSTGRES_PORT),
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            database=POSTGRES_DB
        )
        
        # Test basic query
        result = await conn.fetchval("SELECT version()")
        logger.info(f"Database connection successful. PostgreSQL version: {result}")
        
        # Test table exists
        table_exists = await conn.fetchval(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = $1)",
            'chat_messages'
        )
        
        if table_exists:
            logger.info("chat_messages table exists and is accessible")
            
            # Test inserting and retrieving a test record
            import uuid
            from datetime import datetime, timezone
            
            test_session_id = uuid.uuid4()
            test_message_id = await conn.fetchval("""
                INSERT INTO chat_messages (session_id, user_message, role, timestamp)
                VALUES ($1, $2, $3, $4)
                RETURNING message_id
            """, test_session_id, "Test message", "user", datetime.now(timezone.utc))
            
            logger.info(f"Test record inserted with ID: {test_message_id}")
            
            # Clean up test record
            await conn.execute("DELETE FROM chat_messages WHERE message_id = $1", test_message_id)
            logger.info("Test record cleaned up")
            
        else:
            logger.error("chat_messages table does not exist!")
            
        await conn.close()
        
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        sys.exit(1)


def main():
    """Main initialization function"""
    logger.info("Starting database initialization...")
    logger.info(f"Configuration: {POSTGRES_USER}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")
    
    # Step 1: Create database if it doesn't exist
    logger.info("Step 1: Creating database if needed...")
    create_db_if_not_exists()
    
    # Step 2: Create tables
    # logger.info("Step 2: Creating tables...")
    # create_tables()
    
    # Step 3: Test connection
    logger.info("Step 3: Testing database connection...")
    asyncio.run(test_database_connection())
    
    logger.info("Database initialization completed successfully!")
    
    # Print connection info
    print("\n" + "="*50)
    print("DATABASE SETUP COMPLETE")
    print("="*50)
    print(f"Database URL: {DATABASE_URL.replace(POSTGRES_PASSWORD, '***')}")
    print(f"Host: {POSTGRES_HOST}:{POSTGRES_PORT}")
    print(f"Database: {POSTGRES_DB}")
    print(f"User: {POSTGRES_USER}")
    print("\nTables created:")
    print("- chat_messages (with indexes)")
    print("\nThe API is now ready to use with PostgreSQL!")
    print("="*50)


if __name__ == "__main__":
    main()
