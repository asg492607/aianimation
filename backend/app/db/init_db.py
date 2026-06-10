import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings
from app.models import Base
from app.core.logging import get_logger

logger = get_logger(__name__)

async def init_models():
    """Create all tables in the database"""
    if not settings.DATABASE_URL:
        logger.error("DATABASE_URL is not set. Cannot initialize DB.")
        return
        
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    
    async with engine.begin() as conn:
        logger.info("Dropping all tables...")
        await conn.run_sync(Base.metadata.drop_all)
        logger.info("Creating all tables...")
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database initialization completed.")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(init_models())
