from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.core.config import settings


def _get_database_url() -> str:
    url = settings.DATABASE_URL
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not configured. "
            "Please set the DATABASE_URL environment variable on Render."
        )
    return url


engine = create_async_engine(
    _get_database_url(),
    echo=settings.DEBUG,
    pool_pre_ping=True,
    # NullPool is recommended for serverless/PaaS environments like Render
    # where the DB connection may be closed between requests
    poolclass=NullPool,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
